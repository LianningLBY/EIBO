#!/root/miniconda3/bin/python3
"""Compute the full two-sided X11 bracket on CESNET-QUIC22 XS."""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import importlib.util
import itertools
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import tables


PROJECT_ROOT = Path("/root/eibo")
DATA_ROOT = Path("/root/autodl-tmp/eibo/data/cesnet-quic22-explicit-v2")
H5_PATH = DATA_ROOT / "XS/CESNET-QUIC22-XS.h5"
SERVICE_MAP_PATH = DATA_ROOT / "XS/servicemap.csv"
ARTIFACT_PATH = PROJECT_ROOT / "artifacts/x11_full_bracket.json"
FEASIBILITY_PATH = PROJECT_ROOT / "artifacts/x11_feasibility.json"
PRIMARY_FULL_N_PATH = PROJECT_ROOT / "artifacts/q1_lower_side_full_n.json"
HELPER_PATH = PROJECT_ROOT / "scripts/xs_compression_early_readout.py"
STATCORE_PATH = PROJECT_ROOT / "src/eibo/statcore.py"

sys.path.insert(0, str(PROJECT_ROOT / "src"))

K = 5
M = 1
ALPHABET_SIZE = 32
ALPHA_PER_LAW = 0.025
SERVICE_THRESHOLD = 2000
LOWER_RANDOM_STATE = 0
CHUNK_SIZE = 100_000
LOWER_EDGE = 0.05
TRAIN_DATES = [
    "20221031",
    "20221101",
    "20221102",
    "20221103",
    "20221104",
    "20221105",
    "20221106",
]
BUFFER_DATES = [
    "20221107",
    "20221108",
    "20221109",
    "20221110",
    "20221111",
    "20221112",
    "20221113",
]
TEST_DATES = [
    "20221114",
    "20221115",
    "20221116",
    "20221117",
    "20221118",
    "20221119",
    "20221120",
    "20221121",
    "20221122",
    "20221123",
    "20221124",
    "20221125",
    "20221126",
    "20221127",
]


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(16 * 1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def file_record(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    return {
        "path": str(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def load_helper():
    spec = importlib.util.spec_from_file_location("x11_full_bracket_helper", HELPER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {HELPER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "min": None,
            "q5": None,
            "q25": None,
            "median": None,
            "q75": None,
            "q95": None,
            "max": None,
        }
    array = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.min(array)),
        "q5": float(np.quantile(array, 0.05)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.quantile(array, 0.50)),
        "q75": float(np.quantile(array, 0.75)),
        "q95": float(np.quantile(array, 0.95)),
        "max": float(np.max(array)),
    }


def scan_test_flows(helper) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    test_paths = {f"/flows/D{date}" for date in TEST_DATES}
    train_paths = {f"/flows/D{date}" for date in TRAIN_DATES}
    buffer_paths = {f"/flows/D{date}" for date in BUFFER_DATES}
    code_chunks: dict[int, list[np.ndarray]] = collections.defaultdict(list)
    app_counts: collections.Counter[int] = collections.Counter()
    eligible_counts: collections.Counter[int] = collections.Counter()
    total_rows = 0
    eligible_rows = 0
    direction_row = None
    size_row = None
    schema: dict[str, Any] = {}

    with tables.open_file(str(H5_PATH), mode="r") as h5:
        paths = helper.table_paths(h5)
        if not paths:
            raise RuntimeError("No /flows/* table with APP, PPI, PPI_LEN was found")
        all_paths = set(paths)
        missing = {
            "train": sorted(train_paths - all_paths),
            "buffer": sorted(buffer_paths - all_paths),
            "test": sorted(test_paths - all_paths),
        }
        if any(missing.values()):
            raise RuntimeError(f"required split table paths missing: {missing}")

        first = h5.get_node(sorted(test_paths)[0])
        sample_stop = min(10_000, int(first.nrows))
        sample_ppi = np.asarray(first.read(0, sample_stop, field="PPI"))
        sample_lens = np.asarray(
            first.read(0, sample_stop, field="PPI_LEN")
        ).reshape(-1)
        inferred = helper.infer_ppi_channels(sample_ppi, sample_lens)
        direction_row = int(inferred["direction_row"])
        size_row = int(inferred["size_row"])
        schema = {
            "table_paths": sorted(paths),
            "test_table_paths": sorted(test_paths),
            "train_table_paths": sorted(train_paths),
            "buffer_table_paths": sorted(buffer_paths),
            "inferred_channels": inferred,
            "first_test_table_columns": list(first.colnames),
        }

        for path in sorted(test_paths):
            node = h5.get_node(path)
            for start in range(0, int(node.nrows), CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, int(node.nrows))
                apps = np.asarray(node.read(start, stop, field="APP")).reshape(-1)
                lens = np.asarray(
                    node.read(start, stop, field="PPI_LEN")
                ).reshape(-1)
                app_counts.update(map(int, apps))
                total_rows += len(apps)
                eligible = lens >= K
                if not np.any(eligible):
                    continue
                ppi = np.asarray(node.read(start, stop, field="PPI"))[eligible]
                apps_e = apps[eligible]
                codes = np.asarray(
                    helper.pack_rung_prefix(
                        ppi, K, M, direction_row, size_row
                    ),
                    dtype=np.int16,
                )
                eligible_rows += len(codes)
                values, counts = np.unique(apps_e, return_counts=True)
                for label, amount in zip(values, counts):
                    eligible_counts[int(label)] += int(amount)
                for label in values:
                    label_int = int(label)
                    code_chunks[label_int].append(
                        codes[apps_e == label_int]
                    )

    services = sorted(
        label
        for label in app_counts
        if app_counts[label] >= SERVICE_THRESHOLD
        and eligible_counts[label] >= SERVICE_THRESHOLD
    )
    samples = {
        str(label): np.concatenate(code_chunks[label]).astype(np.int16, copy=False)
        for label in services
    }
    metadata = {
        "schema": schema,
        "total_test_rows": total_rows,
        "eligible_test_rows_ppi_len_ge_5": eligible_rows,
        "all_service_labels_in_test": len(app_counts),
        "retained_services": [str(label) for label in services],
        "retained_service_count": len(services),
        "service_threshold": SERVICE_THRESHOLD,
        "service_eligible_counts": {
            str(label): int(eligible_counts[label]) for label in services
        },
        "sample_unit": "one eligible flow from one APP service",
        "sample_cap_per_service": None,
    }
    return samples, metadata


def compute_rows(samples: dict[str, np.ndarray]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from eibo.statcore import tv_lower_bound, tv_upper_bound

    services = sorted(samples, key=int)
    identity = np.eye(ALPHABET_SIZE, dtype=np.float64)
    rows: list[dict[str, Any]] = []
    first_lower_diagnostics = None
    started = time.time()

    for pair_index, (service_a, service_b) in enumerate(
        itertools.combinations(services, 2), start=1
    ):
        codes_a = samples[service_a]
        codes_b = samples[service_b]
        upper = tv_upper_bound(
            codes_a,
            codes_b,
            alphabet_size=ALPHABET_SIZE,
            alpha=ALPHA_PER_LAW,
        )
        one_hot_a = identity[codes_a]
        one_hot_b = identity[codes_b]
        eps_lo, diagnostics = tv_lower_bound(
            one_hot_a,
            one_hot_b,
            alpha=ALPHA_PER_LAW,
            method="michel",
            random_state=LOWER_RANDOM_STATE,
        )
        if first_lower_diagnostics is None:
            first_lower_diagnostics = {
                key: value
                for key, value in diagnostics.items()
                if key != "classifier"
            }
        eps_hi = float(upper.eps_hi)
        eps_lo = float(eps_lo)
        if eps_lo > eps_hi:
            raise RuntimeError(
                "C016 invariant violation before final artifact: "
                f"{service_a}-{service_b} eps_lo={eps_lo} eps_hi={eps_hi}"
            )
        rows.append(
            {
                "service_a": service_a,
                "service_b": service_b,
                "n_a": int(len(codes_a)),
                "n_b": int(len(codes_b)),
                "tv_hat": float(upper.tv_hat),
                "eps_hi": eps_hi,
                "eps_lo": eps_lo,
                "gate_pass": bool(
                    eps_lo > LOWER_EDGE and eps_hi < 0.5
                ),
            }
        )
        if pair_index % 100 == 0 or pair_index == len(services) * (len(services) - 1) // 2:
            print(
                json.dumps(
                    {
                        "progress_pairs": pair_index,
                        "pair_total": len(services) * (len(services) - 1) // 2,
                        "elapsed_seconds": time.time() - started,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        del one_hot_a, one_hot_b

    return rows, {
        "upper_reference": f"{STATCORE_PATH}::tv_upper_bound",
        "lower_reference": f"{STATCORE_PATH}::tv_lower_bound",
        "lower_method": "michel_adaptive_sup_cutoff",
        "first_lower_diagnostics": first_lower_diagnostics,
    }


def summarize(rows: list[dict[str, Any]], threshold: int | None) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if threshold is None or min(row["n_a"], row["n_b"]) >= threshold
    ]
    pair_count = len(selected)
    upper_count = sum(row["eps_hi"] < 0.5 for row in selected)
    lower_count = sum(row["eps_lo"] > LOWER_EDGE for row in selected)
    joint_count = sum(row["gate_pass"] for row in selected)
    return {
        "threshold": "all" if threshold is None else f">={threshold}",
        "min_n_rule": (
            "all pairs"
            if threshold is None
            else f"min(n_a, n_b) >= {threshold}"
        ),
        "pair_count": pair_count,
        "upper_count_eps_hi_lt_0_5": upper_count,
        "upper_fraction": upper_count / pair_count if pair_count else None,
        "lower_count_eps_lo_gt_0_05": lower_count,
        "lower_fraction": lower_count / pair_count if pair_count else None,
        "joint_gate_count": joint_count,
        "joint_gate_fraction": joint_count / pair_count if pair_count else None,
        "object_sentence": (
            "Each fraction is computed on service-pair rows for the k=5, M=1 "
            "categorical law of the first five (direction,size) symbols; timing "
            "is excluded."
        ),
    }


def load_primary_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    with PRIMARY_FULL_N_PATH.open("r", encoding="utf-8") as handle:
        artifact = json.load(handle)
    rows = []
    for row in artifact["rows"]:
        upper = row["upper_recomputed"]
        rows.append(
            {
                "service_a": str(row["service_a"]),
                "service_b": str(row["service_b"]),
                "n_a": int(row["n_a"]),
                "n_b": int(row["n_b"]),
                "eps_hi": float(upper["eps_hi"]),
                "eps_lo": float(row["eps_lo"]),
                "gate_pass": bool(
                    row["eps_lo"] > LOWER_EDGE
                    and upper["eps_hi"] < 0.5
                ),
            }
        )
    return rows, {
        "path": str(PRIMARY_FULL_N_PATH),
        "sha256": sha256_file(PRIMARY_FULL_N_PATH),
        "pair_count": len(rows),
        "source_object": artifact.get("representation"),
        "lower_guarantee": artifact.get("lower_method"),
    }


def reconcile_feasibility(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not FEASIBILITY_PATH.exists():
        return {
            "status": "unavailable",
            "path": str(FEASIBILITY_PATH),
        }
    with FEASIBILITY_PATH.open("r", encoding="utf-8") as handle:
        artifact = json.load(handle)
    reference_rows = artifact["protocol"]["per_pair_summary"]["rows"]
    reference = {
        (str(row["service_a"]), str(row["service_b"])): row
        for row in reference_rows
    }
    diffs = []
    for row in rows:
        ref = reference[(row["service_a"], row["service_b"])]
        diffs.append(
            {
                "tv_hat": abs(row["tv_hat"] - float(ref["tv_hat"])),
                "eps_hi": abs(row["eps_hi"] - float(ref["eps_hi"])),
            }
        )
    max_tv = max(item["tv_hat"] for item in diffs)
    max_eps = max(item["eps_hi"] for item in diffs)
    return {
        "status": "matched",
        "path": str(FEASIBILITY_PATH),
        "reference_sha256": sha256_file(FEASIBILITY_PATH),
        "reference_pair_count": len(reference_rows),
        "max_abs_tv_hat_difference": max_tv,
        "max_abs_eps_hi_difference": max_eps,
        "upper_count_reference": sum(
            float(row["eps_hi"]) < 0.5 for row in reference_rows
        ),
        "upper_count_recomputed": sum(row["eps_hi"] < 0.5 for row in rows),
    }


def build_reproduction_verdict(
    rows: list[dict[str, Any]],
    primary_rows: list[dict[str, Any]],
    primary_meta: dict[str, Any],
) -> dict[str, Any]:
    quic_all = summarize(rows, None)
    primary_all = summarize(primary_rows, None)
    upper_matches = (
        quic_all["upper_count_eps_hi_lt_0_5"]
        == primary_all["upper_count_eps_hi_lt_0_5"]
        and quic_all["pair_count"] == primary_all["pair_count"]
    )
    joint_matches = (
        quic_all["joint_gate_count"] == primary_all["joint_gate_count"]
        and quic_all["pair_count"] == primary_all["pair_count"]
    )
    return {
        "framework": "D076",
        "raw_upper_fraction_reproduces_primary": bool(upper_matches),
        "raw_joint_gate_fraction_reproduces_primary": bool(joint_matches),
        "quic22_upper_fraction": quic_all["upper_fraction"],
        "primary_upper_fraction": primary_all["upper_fraction"],
        "quic22_joint_gate_fraction": quic_all["joint_gate_fraction"],
        "primary_joint_gate_fraction": primary_all["joint_gate_fraction"],
        "assessment": (
            "The raw QUIC22 fraction is a measured non-reproduction of the "
            "primary fraction under the fixed protocol, with tuning_performed "
            "false. It is a composition-affected marginal comparison because "
            "the two corpora have different service counts and min-n distributions; "
            "the requested n-stratified table is required before treating the "
            "difference as a corpus property."
        ),
        "interpretation_boundary": (
            "Do not call the raw difference single-corpus non-extrapolability. "
            "The upper side is a finite-sample distribution-free certificate; "
            "the Michel lower side is an asymptotic HPLB estimate, not an exact "
            "finite-sample certificate. Therefore the joint gate is a mixed-strength "
            "two-sided measurement and must not be described as an exact finite-sample "
            "two-sided certificate."
        ),
        "primary_reference": primary_meta,
    }


def main() -> None:
    started = time.time()
    helper = load_helper()
    samples, scan_metadata = scan_test_flows(helper)
    rows, method_metadata = compute_rows(samples)
    pair_count = len(rows)
    violations = sum(row["eps_lo"] > row["eps_hi"] for row in rows)
    if violations != 0:
        raise RuntimeError(
            f"C016 invariant violation count is {violations}; final result withheld"
        )

    upper_count = sum(row["eps_hi"] < 0.5 for row in rows)
    lower_count = sum(row["eps_lo"] > LOWER_EDGE for row in rows)
    joint_count = sum(row["gate_pass"] for row in rows)
    if joint_count > upper_count or joint_count > lower_count:
        raise RuntimeError("C017 cross-field consistency failure in gate counts")

    primary_rows, primary_meta = load_primary_rows()
    thresholds = [None, 13_049, 20_000, 40_000, 80_000]
    n_table = []
    for threshold in thresholds:
        quic = summarize(rows, threshold)
        primary = summarize(primary_rows, threshold)
        n_table.append(
            {
                "threshold": quic["threshold"],
                "object_sentence": quic["object_sentence"],
                "quic22": quic,
                "primary": primary,
            }
        )

    result = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runner": file_record(Path(__file__).resolve()),
        "protocol": {
            "object": (
                "For each retained APP service, draw one eligible flow uniformly "
                "from the test-period service population and map its first five "
                "(direction,size) symbols to one of the fixed 32 categorical cells; "
                "the timing channel is excluded."
            ),
            "k": K,
            "M": M,
            "alphabet_size": ALPHABET_SIZE,
            "alphabet_source": "a-priori protocol grid (2*M)^k; realized support was not used",
            "channel": "(direction, size); timing excluded",
            "alpha_overall": 0.05,
            "alpha_per_law": ALPHA_PER_LAW,
            "alpha_split_convention": (
                "alpha/2 = 0.025 passed independently to each law-side call; "
                "the lower method's internal convention is owned by tv_lower_bound"
            ),
            "service_threshold_flows": SERVICE_THRESHOLD,
            "sample_cap_per_service": None,
            "tuning_performed": False,
            "split": {
                "train_dates": TRAIN_DATES,
                "buffer_dates": BUFFER_DATES,
                "test_dates": TEST_DATES,
                "statistics_use": "test dates only, matching x11_feasibility_probe.py",
                "packet_level_split": False,
            },
            "data_paths": {
                "h5": str(H5_PATH),
                "servicemap": str(SERVICE_MAP_PATH),
            },
            "guarantees": {
                "eps_hi": (
                    "finite-sample, distribution-free upper bound on the TV of "
                    "the same 32-cell categorical service-level symbol law"
                ),
                "eps_lo": (
                    "asymptotic Michel HPLB estimate for the TV of that same "
                    "32-cell categorical service-level symbol law; not an exact "
                    "finite-sample certificate"
                ),
            },
            "references": {
                "packing": str(HELPER_PATH) + "::pack_rung_prefix",
                "upper": str(STATCORE_PATH) + "::tv_upper_bound",
                "lower": str(STATCORE_PATH) + "::tv_lower_bound",
                "lower_method": "michel_adaptive_sup_cutoff",
                "lower_random_state": LOWER_RANDOM_STATE,
            },
        },
        "source_files": {
            "h5": file_record(H5_PATH),
            "servicemap": file_record(SERVICE_MAP_PATH),
            "helper": file_record(HELPER_PATH),
            "statcore": file_record(STATCORE_PATH),
            "primary_full_n": file_record(PRIMARY_FULL_N_PATH),
        },
        "scan": scan_metadata,
        "method_execution": method_metadata,
        "pair_count": pair_count,
        "upper_count_eps_hi_lt_0_5": upper_count,
        "upper_fraction": upper_count / pair_count if pair_count else None,
        "lower_count_eps_lo_gt_0_05": lower_count,
        "lower_fraction": lower_count / pair_count if pair_count else None,
        "joint_gate_count": joint_count,
        "joint_gate_fraction": joint_count / pair_count if pair_count else None,
        "eps_lo_le_eps_hi_violations": violations,
        "summary": {
            "tv_hat": quantiles([row["tv_hat"] for row in rows]),
            "eps_hi": quantiles([row["eps_hi"] for row in rows]),
            "eps_lo": quantiles([row["eps_lo"] for row in rows]),
        },
        "per_pair_rows": rows,
        "feasibility_reconciliation": reconcile_feasibility(rows),
        "n_stratified_comparison": n_table,
        "reproduction_verdict": build_reproduction_verdict(
            rows, primary_rows, primary_meta
        ),
        "invariant_status": {
            "eps_lo_le_eps_hi_hard_invariant": True,
            "cross_field_consistency_checked": True,
            "reported_result_valid": True,
        },
        "elapsed_seconds": time.time() - started,
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(ARTIFACT_PATH) + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=json_default) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, ARTIFACT_PATH)
    print(
        json.dumps(
            {
                "artifact": str(ARTIFACT_PATH),
                "artifact_bytes": ARTIFACT_PATH.stat().st_size,
                "artifact_sha256": sha256_file(ARTIFACT_PATH),
                "pair_count": pair_count,
                "upper_fraction": result["upper_fraction"],
                "lower_fraction": result["lower_fraction"],
                "joint_gate_count": joint_count,
                "joint_gate_fraction": result["joint_gate_fraction"],
                "violations": violations,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
