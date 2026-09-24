"""D181: balanced-accuracy risk interval for the same-channel classifier.

This runner intentionally preserves the Exp2 feature extraction, split, and
classifier path, then recomputes the per-class recalls needed for the
balanced-prior Bayes-risk comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np
import tables
from scipy.sparse import csr_matrix, vstack
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
SRC_ROOT = ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))
from eibo import statcore  # noqa: E402


H5_PATH = Path("/efs/workspace/_corpus/CESNET-QUICEXT-25-XS.h5")
EXP1_PATH = ROOT / "artifacts/_project/data/d181_joint_coverage_reaggregation.json"
EXP2_PATH = ROOT / "artifacts/d181_same_channel_classifier.json"
OUT_PATH = ROOT / "artifacts/d181_balanced_accuracy_risk_interval.json"
PACKER_PATH = ROOT / "scripts/xs_compression_early_readout.py"
EXPECTED_H5_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"

K = 5
M = 1
ALPHABET_SIZE = 2**K
SERVICE_THRESHOLD = 2000
CHUNK_SIZE = 100_000
TEST_SIZE = 0.30
RANDOM_STATE = 0
PILOT_PAIRS = 10
MAX_WALL_HOURS = 4.0
RAW_ERROR_TOL = 1e-15


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_packer():
    spec = importlib.util.spec_from_file_location("d181_xs_packer", PACKER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load packer from {PACKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_exp1_rows() -> tuple[dict[tuple[int, int], dict], list[int], str]:
    exp1_sha = sha256_file(EXP1_PATH)
    with EXP1_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload["rows"]
    if len(rows) != 990:
        raise RuntimeError(f"expected 990 Exp1 rows, found {len(rows)}")
    row_map = {}
    for row in rows:
        key = (int(row["service_a"]), int(row["service_b"]))
        if key in row_map:
            raise RuntimeError(f"duplicate Exp1 pair {key}")
        for field in ("eps_hi_mfree", "eps_lo"):
            if field not in row:
                raise RuntimeError(f"missing {field} for Exp1 pair {key}")
        row_map[key] = row
    services = sorted({a for a, _ in row_map} | {b for _, b in row_map})
    if len(services) != 45:
        raise RuntimeError(f"expected 45 services, found {len(services)}")
    expected_pairs = list(itertools.combinations(services, 2))
    if sorted(row_map) != expected_pairs:
        raise RuntimeError("Exp1 pair set is not the complete 45-service set")
    return row_map, services, exp1_sha


def load_exp2_rows(expected_pairs: list[tuple[int, int]]) -> tuple[dict[tuple[int, int], dict], str]:
    exp2_sha = sha256_file(EXP2_PATH)
    with EXP2_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload["rows"]
    if len(rows) != 990:
        raise RuntimeError(f"expected 990 Exp2 rows, found {len(rows)}")
    row_map = {}
    for row in rows:
        key = (int(row["service_a"]), int(row["service_b"]))
        if key in row_map:
            raise RuntimeError(f"duplicate Exp2 pair {key}")
        for field in ("error_rate", "test_errors", "test_n", "n_a", "n_b", "train_n"):
            if field not in row:
                raise RuntimeError(f"missing {field} for Exp2 pair {key}")
        row_map[key] = row
    if sorted(row_map) != expected_pairs:
        raise RuntimeError("Exp2 pair set does not match Exp1 pair set")
    return row_map, exp2_sha


def build_sparse_one_hot(symbols: np.ndarray) -> csr_matrix:
    symbols = np.asarray(symbols, dtype=np.int32)
    if symbols.ndim != 1 or np.any(symbols < 0) or np.any(symbols >= ALPHABET_SIZE):
        raise RuntimeError("symbol array is not a 1-D array in [0, 32)")
    rows = np.arange(symbols.size, dtype=np.int32)
    data = np.ones(symbols.size, dtype=np.float32)
    return csr_matrix(
        (data, (rows, symbols)),
        shape=(symbols.size, ALPHABET_SIZE),
        dtype=np.float32,
    )


def scan_symbols(packer, services: list[int]) -> tuple[dict[int, np.ndarray], dict]:
    if sha256_file(H5_PATH) != EXPECTED_H5_SHA256:
        raise RuntimeError("corpus SHA-256 does not match the verified input")

    service_set = set(services)
    chunks: dict[int, list[np.ndarray]] = {service: [] for service in services}
    eligible_counts = {service: 0 for service in services}
    total_rows = 0
    eligible_rows = 0
    table_count = 0
    direction_row = None
    size_row = None
    inference = None
    scan_start = time.perf_counter()

    with tables.open_file(str(H5_PATH), mode="r") as h5:
        paths = packer.table_paths(h5)
        if not paths:
            raise RuntimeError("no /flows/* tables with APP, PPI and PPI_LEN found")
        first = h5.get_node(paths[0])
        sample_stop = min(10_000, int(first.nrows))
        sample_ppi = np.asarray(first.read(0, sample_stop, field="PPI"))
        sample_lens = np.asarray(first.read(0, sample_stop, field="PPI_LEN")).reshape(-1)
        inference = packer.infer_ppi_channels(sample_ppi, sample_lens)
        direction_row = int(inference["direction_row"])
        size_row = int(inference["size_row"])
        if (direction_row, size_row) != (1, 2):
            raise RuntimeError(
                f"packer channel inference changed: direction={direction_row}, size={size_row}"
            )

        for path in paths:
            node = h5.get_node(path)
            table_count += 1
            for start in range(0, int(node.nrows), CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, int(node.nrows))
                app = np.asarray(node.read(start, stop, field="APP")).reshape(-1)
                lens = np.asarray(node.read(start, stop, field="PPI_LEN")).reshape(-1)
                total_rows += int(app.size)
                eligible = lens >= K
                if not np.any(eligible):
                    continue
                app = app[eligible]
                ppi = np.asarray(node.read(start, stop, field="PPI"))[eligible]
                eligible_rows += int(app.size)
                symbols = np.asarray(
                    packer.pack_rung_k5(ppi, M, direction_row, size_row),
                    dtype=np.int32,
                )
                if symbols.size != app.size:
                    raise RuntimeError(f"symbol count mismatch in {path}:{start}:{stop}")
                if np.any(symbols < 0) or np.any(symbols >= ALPHABET_SIZE):
                    raise RuntimeError("packer emitted a symbol outside the fixed alphabet")
                for service in np.unique(app):
                    service = int(service)
                    if service not in service_set:
                        continue
                    values = symbols[app == service]
                    chunks[service].append(values.astype(np.int8, copy=False))
                    eligible_counts[service] += int(values.size)

    symbols_by_service = {
        service: np.concatenate(chunks[service]).astype(np.int8, copy=False)
        for service in services
    }
    too_small = {
        service: count
        for service, count in eligible_counts.items()
        if count < SERVICE_THRESHOLD
    }
    if too_small:
        raise RuntimeError(f"ledger services below the eligibility threshold: {too_small}")

    scan_seconds = time.perf_counter() - scan_start
    return symbols_by_service, {
        "h5_sha256": EXPECTED_H5_SHA256,
        "h5_bytes": H5_PATH.stat().st_size,
        "actual_h5_schema": {
            "table_source": "/flows/* tables",
            "table_count": table_count,
            "note": (
                "The artifact has no root-level cols node; APP, PPI and PPI_LEN "
                "were read from each actual /flows/* table in bounded chunks."
            ),
        },
        "total_corpus_rows": total_rows,
        "eligible_corpus_rows": eligible_rows,
        "direction_row": direction_row,
        "size_row": size_row,
        "channel_inference": inference,
        "eligible_counts": {str(k): int(v) for k, v in eligible_counts.items()},
        "scan_seconds": scan_seconds,
    }


def fit_pair(
    symbols_a: np.ndarray,
    symbols_b: np.ndarray,
    exp1_row: dict,
    exp2_row: dict,
    service_a: int,
    service_b: int,
) -> dict:
    xa = build_sparse_one_hot(symbols_a)
    xb = build_sparse_one_hot(symbols_b)
    x = vstack((xa, xb), format="csr")
    y = np.concatenate(
        (
            np.zeros(symbols_a.size, dtype=np.int8),
            np.ones(symbols_b.size, dtype=np.int8),
        )
    )
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_STATE,
    )
    classifier = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    classifier.fit(x_train, y_train)
    predicted = classifier.predict(x_test)

    mask_a = y_test == 0
    mask_b = y_test == 1
    test_n_a = int(np.count_nonzero(mask_a))
    test_n_b = int(np.count_nonzero(mask_b))
    correct_a = int(np.count_nonzero(predicted[mask_a] == 0))
    correct_b = int(np.count_nonzero(predicted[mask_b] == 1))
    errors = int(np.count_nonzero(predicted != y_test))
    test_n = int(y_test.size)
    train_n = int(y_train.size)
    error_rate = float(errors / test_n)

    if test_n != int(exp2_row["test_n"]):
        raise RuntimeError(
            f"test_n mismatch for {(service_a, service_b)}: "
            f"{test_n} != {exp2_row['test_n']}"
        )
    if train_n != int(exp2_row["train_n"]):
        raise RuntimeError(
            f"train_n mismatch for {(service_a, service_b)}: "
            f"{train_n} != {exp2_row['train_n']}"
        )
    if errors != int(exp2_row["test_errors"]):
        raise RuntimeError(
            f"test_errors mismatch for {(service_a, service_b)}: "
            f"{errors} != {exp2_row['test_errors']}"
        )
    if not math.isclose(error_rate, float(exp2_row["error_rate"]), abs_tol=RAW_ERROR_TOL):
        raise RuntimeError(
            f"error_rate mismatch for {(service_a, service_b)}: "
            f"{error_rate} != {exp2_row['error_rate']}"
        )

    recall_a = float(correct_a / test_n_a)
    recall_b = float(correct_b / test_n_b)
    balanced_accuracy = float((recall_a + recall_b) / 2.0)
    balanced_error = float(1.0 - balanced_accuracy)
    tv_implied = float(max(0.0, 1.0 - 2.0 * balanced_error))
    eps_hi_mfree = float(exp1_row["eps_hi_mfree"])
    eps_lo = float(exp1_row["eps_lo"])
    certified_error_floor = float(max(0.0, (1.0 - eps_hi_mfree) / 2.0))
    violation = bool(balanced_error < certified_error_floor)

    return {
        "service_a": int(service_a),
        "service_b": int(service_b),
        "n_a": int(symbols_a.size),
        "n_b": int(symbols_b.size),
        "train_n": train_n,
        "test_n": test_n,
        "test_n_a": test_n_a,
        "test_n_b": test_n_b,
        "test_errors": errors,
        "raw_error_rate": error_rate,
        "exp2_raw_error_rate": float(exp2_row["error_rate"]),
        "raw_error_reconciled": True,
        "recall_A": recall_a,
        "recall_B": recall_b,
        "balanced_accuracy": balanced_accuracy,
        "balanced_error": balanced_error,
        "tv_implied": tv_implied,
        "eps_lo": eps_lo,
        "eps_hi_mfree": eps_hi_mfree,
        "certified_error_floor": certified_error_floor,
        "violation": violation,
        "tv_implied_minus_eps_lo": float(tv_implied - eps_lo),
        "eps_hi_mfree_minus_tv_implied": float(eps_hi_mfree - tv_implied),
    }


def finite_values(rows: list[dict], field: str) -> np.ndarray:
    values = np.asarray([float(row[field]) for row in rows], dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise RuntimeError(f"non-finite values in {field}")
    return values


def describe(values: np.ndarray) -> dict:
    quantile_points = [0.0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0]
    return {
        "min": float(np.min(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "max": float(np.max(values)),
        "std": float(np.std(values)),
        "quantiles": {
            f"q{int(q * 100):02d}": float(np.quantile(values, q))
            for q in quantile_points
        },
    }


def summarize(rows: list[dict]) -> dict:
    balanced_error = finite_values(rows, "balanced_error")
    certified_error_floor = finite_values(rows, "certified_error_floor")
    tv_implied = finite_values(rows, "tv_implied")
    eps_lo = finite_values(rows, "eps_lo")
    eps_hi_mfree = finite_values(rows, "eps_hi_mfree")
    tv_minus_eps_lo = tv_implied - eps_lo
    eps_hi_minus_tv = eps_hi_mfree - tv_implied
    violations = balanced_error < certified_error_floor
    return {
        "pair_count": len(rows),
        "completed_pair_count": len(rows),
        "raw_error_reconciliation": {
            "status": "passed",
            "tolerance": RAW_ERROR_TOL,
            "checked_pair_count": len(rows),
        },
        "violation_count": int(np.count_nonzero(violations)),
        "nonviolation_count": int(len(rows) - np.count_nonzero(violations)),
        "violation_fraction": float(np.mean(violations)),
        "falsifier_fired": bool(np.any(violations)),
        "falsifier_outcome": (
            "genuine_upper_bound_violation_found"
            if np.any(violations)
            else "zero_violations_observed_certificate_validated_on_its_own_object"
        ),
        "balanced_error": describe(balanced_error),
        "certified_error_floor": describe(certified_error_floor),
        "tv_implied": describe(tv_implied),
        "eps_lo": describe(eps_lo),
        "eps_hi_mfree": describe(eps_hi_mfree),
        "tv_implied_vs_eps_lo": {
            "tv_implied_lt_eps_lo_count": int(np.count_nonzero(tv_implied < eps_lo)),
            "tv_implied_ge_eps_lo_count": int(np.count_nonzero(tv_implied >= eps_lo)),
            "tv_implied_minus_eps_lo": describe(tv_minus_eps_lo),
        },
        "tv_implied_vs_eps_hi_mfree": {
            "tv_implied_gt_eps_hi_mfree_count": int(np.count_nonzero(tv_implied > eps_hi_mfree)),
            "tv_implied_le_eps_hi_mfree_count": int(np.count_nonzero(tv_implied <= eps_hi_mfree)),
            "eps_hi_mfree_minus_tv_implied": describe(eps_hi_minus_tv),
        },
        "balanced_error_vs_floor": {
            "balanced_error_lt_floor_count": int(np.count_nonzero(balanced_error < certified_error_floor)),
            "balanced_error_ge_floor_count": int(np.count_nonzero(balanced_error >= certified_error_floor)),
            "balanced_error_minus_floor": describe(balanced_error - certified_error_floor),
        },
    }


def environment() -> dict:
    import scipy
    import sklearn

    probe = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE)
    return {
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "sklearn": sklearn.__version__,
        "host": platform.node(),
        "cwd": os.getcwd(),
        "statcore_path": str(Path(statcore.__file__).resolve()),
        "logistic_regression_constructor": (
            "LogisticRegression(max_iter=1000, random_state=0)"
        ),
        "resolved_solver": probe.solver,
        "resolved_penalty": probe.penalty,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pilot-only",
        action="store_true",
        help="scan and fit the first 10 pairs, then stop without writing the result",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    exp1_map, services, exp1_sha = load_exp1_rows()
    pairs = list(itertools.combinations(services, 2))
    exp2_map, exp2_sha = load_exp2_rows(pairs)
    packer = load_packer()
    symbols_by_service, extraction = scan_symbols(packer, services)

    fit_start = time.perf_counter()
    pilot_rows = []
    for index, (service_a, service_b) in enumerate(pairs[:PILOT_PAIRS], start=1):
        row = fit_pair(
            symbols_by_service[service_a],
            symbols_by_service[service_b],
            exp1_map[(service_a, service_b)],
            exp2_map[(service_a, service_b)],
            service_a,
            service_b,
        )
        row["pair_index"] = index - 1
        pilot_rows.append(row)
        elapsed = time.perf_counter() - fit_start
        projected = elapsed / index * len(pairs)
        print(
            json.dumps(
                {
                    "phase": "pilot",
                    "pair": [service_a, service_b],
                    "completed": index,
                    "elapsed_seconds": elapsed,
                    "projected_all_fit_hours": projected / 3600.0,
                    "balanced_error": row["balanced_error"],
                    "certified_error_floor": row["certified_error_floor"],
                    "violation": row["violation"],
                },
                sort_keys=True,
            ),
            flush=True,
        )

    pilot_elapsed = time.perf_counter() - fit_start
    projected_fit_seconds = pilot_elapsed / PILOT_PAIRS * len(pairs)
    projected_total_seconds = (
        time.perf_counter() - started - pilot_elapsed + projected_fit_seconds
    )
    if projected_total_seconds > MAX_WALL_HOURS * 3600.0:
        message = (
            "measured pilot projection exceeds the four-hour budget: "
            f"{projected_total_seconds / 3600.0:.3f} h"
        )
        if args.pilot_only:
            print(message, file=sys.stderr)
            return 2
        raise RuntimeError(message)
    if args.pilot_only:
        print(
            json.dumps(
                {
                    "status": "pilot_complete",
                    "pair_count": len(pairs),
                    "pilot_pairs": PILOT_PAIRS,
                    "pilot_fit_seconds": pilot_elapsed,
                    "projected_all_fit_hours": projected_fit_seconds / 3600.0,
                    "projected_total_hours": projected_total_seconds / 3600.0,
                },
                sort_keys=True,
            )
        )
        return 0

    rows = list(pilot_rows)
    fit_start_full = time.perf_counter()
    for pair_index, (service_a, service_b) in enumerate(pairs[PILOT_PAIRS:], start=PILOT_PAIRS):
        row = fit_pair(
            symbols_by_service[service_a],
            symbols_by_service[service_b],
            exp1_map[(service_a, service_b)],
            exp2_map[(service_a, service_b)],
            service_a,
            service_b,
        )
        row["pair_index"] = pair_index
        rows.append(row)
        if (pair_index + 1) % 25 == 0 or pair_index + 1 == len(pairs):
            elapsed = time.perf_counter() - fit_start
            print(
                json.dumps(
                    {
                        "phase": "full",
                        "completed": pair_index + 1,
                        "pair_count": len(pairs),
                        "elapsed_seconds": elapsed,
                        "rate_seconds_per_pair": elapsed / (pair_index + 1),
                        "violation_count_so_far": sum(int(r["violation"]) for r in rows),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    if len(rows) != len(pairs):
        raise RuntimeError(f"expected {len(pairs)} rows, found {len(rows)}")
    if sorted((r["service_a"], r["service_b"]) for r in rows) != pairs:
        raise RuntimeError("balanced-risk output does not cover the exact pair set")
    if not all(row["raw_error_reconciled"] for row in rows):
        raise RuntimeError("raw-error reconciliation failed")

    violations = [row for row in rows if row["violation"]]
    output = {
        "status": "complete",
        "experiment": "D181_balanced_accuracy_risk_interval",
        "created_at_utc": "2026-09-22T04:22:36Z",
        "object": {
            "name": "packed k=5, M=1 prefix symbol law",
            "representation": "32-dimensional one-hot vector",
            "packing_reference": (
                "scripts/xs_compression_early_readout.py::pack_rung_k5"
            ),
            "alphabet_size": ALPHABET_SIZE,
            "k": K,
            "M": M,
            "same_object_as_exp2_classifier": True,
            "same_object_as_exp1_eps_hi_mfree": True,
        },
        "classifier": {
            "model": "LogisticRegression(max_iter=1000, random_state=0)",
            "split": (
                "train_test_split(test_size=0.30, stratify=y, random_state=0)"
            ),
            "raw_error_reconciliation_source": str(EXP2_PATH),
            "balanced_error_definition": (
                "1 - (recall_A + recall_B) / 2 on the held-out test split"
            ),
            "tv_implied_definition": "max(0, 1 - 2 * balanced_error)",
        },
        "certificate_reference": {
            "path": str(EXP1_PATH),
            "sha256": exp1_sha,
            "eps_hi_field": "rows[*].eps_hi_mfree",
            "certified_error_floor_definition": "max(0, (1 - eps_hi_mfree) / 2)",
            "guarantee": "finite-sample upper side from the m-free route",
            "pair_count": len(exp1_map),
        },
        "exp2_reference": {
            "path": str(EXP2_PATH),
            "sha256": exp2_sha,
            "artifact_id": "art_20260922_91028b",
            "fields_reconciled": ["test_n", "train_n", "test_errors", "error_rate"],
            "raw_error_tolerance": RAW_ERROR_TOL,
        },
        "source": {
            "corpus_path": str(H5_PATH),
            "corpus_sha256": extraction["h5_sha256"],
            "packer_path": str(PACKER_PATH),
            "packer_sha256": sha256_file(PACKER_PATH),
            "runner_path": str(Path(__file__).resolve()),
            "runner_sha256": sha256_file(Path(__file__).resolve()),
        },
        "execution_environment": environment(),
        "extraction": extraction,
        "benchmark": {
            "pilot_pairs": PILOT_PAIRS,
            "pilot_fit_seconds": pilot_elapsed,
            "projected_all_fit_seconds": projected_fit_seconds,
            "projected_all_fit_hours": projected_fit_seconds / 3600.0,
            "projected_total_hours": projected_total_seconds / 3600.0,
            "max_wall_hours": MAX_WALL_HOURS,
            "full_fit_seconds_after_pilot": time.perf_counter() - fit_start_full,
        },
        "summary": summarize(rows),
        "rows": rows,
        "violations": violations,
        "timing": {
            "total_wall_seconds": time.perf_counter() - started,
            "pilot_and_full_fit_seconds": time.perf_counter() - fit_start,
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT_PATH.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, OUT_PATH)
    print(
        json.dumps(
            {
                "status": "complete",
                "output": str(OUT_PATH),
                "rows": len(rows),
                "violations": len(violations),
                "json_sha256": sha256_file(OUT_PATH),
                "script_sha256": sha256_file(Path(__file__).resolve()),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
