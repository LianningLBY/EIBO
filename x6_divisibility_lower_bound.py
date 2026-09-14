#!/root/miniconda3/bin/python3
"""X6: rejection-generic divisibility lower bound as a function of k.

The runner consumes the cached direction-prefix state.  At M=1 the existing
headline channel's size coordinate is a measured constant, so direction bits
are an equivalent representation of the (direction, size) prefix symbol law.
The lower-bound mechanism is imported and called; its construction is not
reimplemented here.
"""

from __future__ import annotations

import hashlib
import inspect
import itertools
import json
import os
import pickle
import sys
import time
import argparse
from pathlib import Path
from typing import Any

import numpy as np


PROJECT = Path("/root/eibo")
CACHE_DIR = Path("/dev/shm/eibo_x3_chain_rule")
MERGED_PATH = CACHE_DIR / "merged.pkl"
LEDGER_PATH = CACHE_DIR / "ledger.json"
RESULTS_PATH = CACHE_DIR / "results.pkl"
REFERENCE_CHANNEL_ARTIFACT = PROJECT / "artifacts" / "q1_eps_lo_symbol_map.json"
HEADLINE_ARTIFACT = PROJECT / "artifacts" / "x1_headline_table.json"
FRONTIER_ARTIFACT = PROJECT / "artifacts" / "x4_frontier_function.json"
ARTIFACT_PATH = PROJECT / "artifacts" / "x6_divisibility_lower_bound.json"
RUNNER_PATH = PROJECT / "x6_divisibility_lower_bound.py"
STATE_PATH = PROJECT / "artifacts" / "x6_divisibility_lower_bound.state.pkl"

ALPHA = 0.05
MODE = "realizable"
Q_VALUES = (2, 4, 8, 16, 32)
TRAIN_TEST_SPLIT = "70% training / 30% held-out test, stratified; implemented by the repository function"
PREFIX_LENGTHS = (5, 10, 15, 20, 25, 30)
MAX_SAMPLES_PER_SERVICE = 20_000
SERVICE_THRESHOLD = 2_000
LARGE_K_MIN = 15
NONTRIVIAL_THRESHOLD = 0.0
INFORMATIVE_THRESHOLD = 0.05
VALIDITY_K_VALUES = (5, 10, 15, 20, 25, 30)
VALIDITY_REPLICATIONS_PER_K = 20
VALIDITY_SAMPLE_SIZE = 400
SEED = 20260914
RUN_TIMESTAMP_UTC = "2026-09-14 05:28:41 UTC"

sys.path.insert(0, str(PROJECT / "src"))
from eibo.divisibility import (  # noqa: E402
    DEFAULT_Q_VALUES,
    tv_lower_bound_divisibility,
)


EXPECTED_SIGNATURE = (
    "(X1: 'Sequence[Sequence[float]]', X2: 'Sequence[Sequence[float]]', alpha: 'float' = 0.05, "
    "clf: 'Any | None' = None, mode: 'str' = 'realizable', *, q_values: 'Sequence[int]' = (2, 4, 8, 16, 32), "
    "random_state: 'int' = 0) -> 'tuple[float, dict[str, Any]]'"
)
EXPECTED_DOCSTRING = """Estimate a rejection-generic lower bound on ``TV(P1, P2)``.

For a binary test with class-conditional errors e0 and e1,
``TV(P1,P2) >= 1 - e0 - e1``. The implementation
replaces each held-out error by a one-sided Clopper-Pearson upper limit and
maximizes the resulting lower bound over a Bonferroni-protected q ladder.
The ``realizable`` mode records the explicit assumption that the chosen
classifier family contains (or sufficiently approximates) a useful test;
the held-out confidence statement itself is conditional on the trained
classifier and does not make that assumption distribution-free."""

ASSUMPTION_SENTENCE = (
    "In mode=\"realizable\", the selected classifier family is assumed to contain, or sufficiently "
    "approximate, a useful binary rejection test; the held-out confidence statement is conditional "
    "on the trained classifier and is not distribution-free."
)

PRE_REGISTERED_VALIDITY = {
    "criterion": (
        "At alpha=0.05, across 120 independent synthetic replications (20 at each k in "
        "{5,10,15,20,25,30}), count a violation whenever the returned lower bound exceeds "
        "the analytically known true TV for that replication."
    ),
    "alpha": ALPHA,
    "split": TRAIN_TEST_SPLIT,
    "falsifies_if": "The violation rate is greater than the declared alpha=0.05.",
    "truth": "P is uniform on binary k-vectors; Q is a calibrated mixture with the all-ones vector, so true TV is known exactly.",
    "selection": "This criterion and replication grid are fixed before the synthetic validity measurements and before real-data measurements.",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def json_ready(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(json_ready(payload), indent=2, sort_keys=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_write_pickle(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temporary, path)


def load_state() -> dict[str, Any]:
    with STATE_PATH.open("rb") as handle:
        return pickle.load(handle)


def quantiles(values: list[float]) -> dict[str, float | None]:
    array = np.asarray(values, dtype=float)
    if not array.size:
        return {key: None for key in ("min", "q5", "q25", "median", "q75", "q95", "max")}
    return {
        "min": float(np.min(array)),
        "q5": float(np.quantile(array, 0.05)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "q75": float(np.quantile(array, 0.75)),
        "q95": float(np.quantile(array, 0.95)),
        "max": float(np.max(array)),
    }


def cache_inventory() -> dict[str, Any]:
    parts = sorted(CACHE_DIR.glob("part_*.npz")) if CACHE_DIR.is_dir() else []
    required = (LEDGER_PATH, MERGED_PATH, RESULTS_PATH)
    files = [path for path in CACHE_DIR.iterdir() if path.is_file()] if CACHE_DIR.is_dir() else []
    return {
        "cache_dir": str(CACHE_DIR),
        "required_files": {str(path): path.is_file() for path in required},
        "npz_part_count": len(parts),
        "npz_part_expected": 360,
        "present": bool(all(path.is_file() for path in required) and len(parts) == 360),
        "bytes_by_required_file": {
            str(path): path.stat().st_size for path in required if path.is_file()
        },
        "bytes_npz_parts": int(sum(path.stat().st_size for path in parts)),
        "bytes_all_cache_files": int(sum(path.stat().st_size for path in files)),
        "h5_rescanned": False,
        "cost_basis": (
            "The run uses merged.pkl codes/lens, ledger.json, results.pkl, and 360 cached NPZ parts; "
            "no H5 read is needed because the M=1 channel's size coordinate is constant by the existing "
            "headline masking validation."
        ),
        "estimated_real_calls": "one repository-function call per eligible service pair and k=5..30, with at most 20000 cached flows per service",
    }


def load_merged() -> dict[str, Any]:
    with MERGED_PATH.open("rb") as handle:
        return pickle.load(handle)


def bits_from_codes(codes: np.ndarray, lens: np.ndarray, k: int, seed: int) -> np.ndarray:
    eligible = np.asarray(lens, dtype=np.uint8) >= k
    selected = np.asarray(codes, dtype=np.uint32)[eligible]
    if len(selected) > MAX_SAMPLES_PER_SERVICE:
        rng = np.random.default_rng(seed)
        indices = np.sort(rng.choice(len(selected), size=MAX_SAMPLES_PER_SERVICE, replace=False))
        selected = selected[indices]
    shifts = np.arange(29, 29 - k, -1, dtype=np.uint32)
    return ((selected[:, None] >> shifts[None, :]) & 1).astype(np.float64)


def true_tv_for_mixture(k: int, requested_tv: float) -> float:
    return float(requested_tv)


def synthetic_pair(k: int, requested_tv: float, n: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    # The mixture has exact TV=requested_tv: Q replaces the all-ones atom with
    # probability t=requested_tv/(1-2^-k), while P is uniform.
    t = 0.0 if requested_tv == 0.0 else requested_tv / (1.0 - 2.0 ** (-k))
    if not 0.0 <= t <= 1.0:
        raise ValueError("requested synthetic TV is unattainable")
    x1 = rng.integers(0, 2, size=(n, k)).astype(np.float64)
    x2 = rng.integers(0, 2, size=(n, k)).astype(np.float64)
    replace = rng.random(n) < t
    x2[replace, :] = 1.0
    return x1, x2


def call_bound(x1: np.ndarray, x2: np.ndarray, seed: int) -> tuple[float, dict[str, Any]]:
    # This is the sole lower-bound call. No formula or radius is reconstructed.
    return tv_lower_bound_divisibility(
        x1,
        x2,
        alpha=ALPHA,
        mode=MODE,
        q_values=Q_VALUES,
        random_state=seed,
    )


def sanitized_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    keep = (
        "method",
        "classifier_name",
        "mode",
        "alpha",
        "confidence_level",
        "q_values_tried",
        "selected_q",
        "empirical_per_class_error",
        "optimistic_error",
        "raw_bound",
        "raw_bound_went_negative",
        "vacuous",
        "realizability_assumption",
    )
    return {key: diagnostics[key] for key in keep if key in diagnostics}


def validity_check() -> dict[str, Any]:
    requested_tvs = (0.0, 0.10, 0.25, 0.50, 0.75)
    rows = []
    violations = 0
    total = 0
    for k in VALIDITY_K_VALUES:
        for rep in range(VALIDITY_REPLICATIONS_PER_K):
            requested_tv = requested_tvs[rep % len(requested_tvs)]
            rng = np.random.default_rng(SEED + 100_000 + 1_000 * k + rep)
            x1, x2 = synthetic_pair(k, requested_tv, VALIDITY_SAMPLE_SIZE, rng)
            bound, diagnostics = call_bound(x1, x2, SEED + 200_000 + 1_000 * k + rep)
            truth = true_tv_for_mixture(k, requested_tv)
            violation = bool(bound > truth + 1e-12)
            violations += int(violation)
            total += 1
            if rep < 2:
                rows.append(
                    {
                        "k": k,
                        "replication": rep,
                        "true_tv": truth,
                        "returned_bound": float(bound),
                        "violation": violation,
                        "diagnostics": sanitized_diagnostics(diagnostics),
                    }
                )
    rate = float(violations / total)
    return {
        "criterion": PRE_REGISTERED_VALIDITY,
        "k_values": list(VALIDITY_K_VALUES),
        "replications_per_k": VALIDITY_REPLICATIONS_PER_K,
        "total_replications": total,
        "violations": violations,
        "violation_rate": rate,
        "declared_alpha": ALPHA,
        "falsified": bool(rate > ALPHA),
        "outcome": "PASS" if rate <= ALPHA else "FAIL",
        "representative_rows": rows,
    }


def service_pair_rows(merged: dict[str, Any], k: int) -> tuple[list[dict[str, Any]], dict[str, np.ndarray]]:
    services = [int(service) for service in merged["services"]]
    features: dict[str, np.ndarray] = {}
    counts: dict[int, int] = {}
    for service in services:
        entry = merged["by_service"][service]
        lens = np.asarray(entry["lens"], dtype=np.uint8)
        counts[service] = int(np.count_nonzero(lens >= k))
        if counts[service] >= SERVICE_THRESHOLD:
            features[str(service)] = bits_from_codes(
                np.asarray(entry["codes"], dtype=np.uint32),
                lens,
                k,
                SEED + 10_000 * k + service,
            )
    rows = []
    for service_a, service_b in itertools.combinations(sorted(map(int, features)), 2):
        rows.append(
            {
                "service_a": service_a,
                "service_b": service_b,
                "eligible_flows_a": counts[service_a],
                "eligible_flows_b": counts[service_b],
            }
        )
    return rows, features


def real_data_by_k(merged: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summaries = []
    all_pair_rows = []
    representative = None
    call_count = 0
    for k in PREFIX_LENGTHS:
        pair_rows, features = service_pair_rows(merged, k)
        bounds = []
        for index, row in enumerate(pair_rows):
            seed = SEED + 1_000_000 + 10_000 * k + index
            bound, diagnostics = call_bound(
                features[str(row["service_a"])],
                features[str(row["service_b"])],
                seed,
            )
            call_count += 1
            row = dict(row)
            row.update(
                {
                    "k": k,
                    "sample_n_a": int(len(features[str(row["service_a"])])),
                    "sample_n_b": int(len(features[str(row["service_b"])])),
                    "eps_lo_divisibility": float(bound),
                    "nontrivial_gt_0": bool(bound > NONTRIVIAL_THRESHOLD),
                    "informative_gt_0_05": bool(bound > INFORMATIVE_THRESHOLD),
                    "selected_q": int(diagnostics["selected_q"]),
                    "vacuous": bool(diagnostics["vacuous"]),
                }
            )
            bounds.append(float(bound))
            all_pair_rows.append(row)
            if representative is None:
                representative = {
                    "k": k,
                    "pair": [row["service_a"], row["service_b"]],
                    "returned_bound": float(bound),
                    "diagnostics": sanitized_diagnostics(diagnostics),
                }
        summaries.append(
            {
                "k": k,
                "large_k_exploratory": bool(k >= LARGE_K_MIN),
                "pair_count": len(bounds),
                "eps_lo_quantiles": quantiles(bounds),
                "fraction_nontrivial_gt_0": float(np.mean(np.asarray(bounds) > NONTRIVIAL_THRESHOLD)) if bounds else None,
                "fraction_informative_gt_0_05": float(np.mean(np.asarray(bounds) > INFORMATIVE_THRESHOLD)) if bounds else None,
                "vacuous_count": int(sum(value <= NONTRIVIAL_THRESHOLD for value in bounds)),
            }
        )
        print(
            "REAL_K",
            json.dumps(summaries[-1], sort_keys=True),
            flush=True,
        )
    large_rows = [row for row in all_pair_rows if row["k"] >= LARGE_K_MIN]
    large_summary = {
        "definition": f"large k means k >= {LARGE_K_MIN}; each k retains its own eligible pair denominator",
        "per_k_fraction_nontrivial_gt_0": {
            str(row["k"]): row["fraction_nontrivial_gt_0"] for row in summaries if row["k"] >= LARGE_K_MIN
        },
        "per_k_fraction_informative_gt_0_05": {
            str(row["k"]): row["fraction_informative_gt_0_05"] for row in summaries if row["k"] >= LARGE_K_MIN
        },
        "pooled_pair_k_rows": len(large_rows),
        "pooled_fraction_nontrivial_gt_0": float(np.mean([row["nontrivial_gt_0"] for row in large_rows])) if large_rows else None,
        "pooled_fraction_informative_gt_0_05": float(np.mean([row["informative_gt_0_05"] for row in large_rows])) if large_rows else None,
        "interpretation": (
            "The per-k fractions are the citable pair fractions. The pooled values summarize pair-k evaluations "
            "and are not a unique-pair fraction. All large-k entries are EXPLORATORY because the plug-in upper side is lost."
        ),
    }
    return summaries, {
        "pair_rows": all_pair_rows,
        "large_k_summary": large_summary,
        "repository_function_call_count_real": call_count,
        "representative_call": representative,
    }


def summarize_real_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summaries = []
    for k in PREFIX_LENGTHS:
        k_rows = [row for row in rows if int(row["k"]) == k]
        bounds = [float(row["eps_lo_divisibility"]) for row in k_rows]
        summaries.append(
            {
                "k": k,
                "large_k_exploratory": bool(k >= LARGE_K_MIN),
                "pair_count": len(bounds),
                "eps_lo_quantiles": quantiles(bounds),
                "fraction_nontrivial_gt_0": float(np.mean(np.asarray(bounds) > NONTRIVIAL_THRESHOLD)) if bounds else None,
                "fraction_informative_gt_0_05": float(np.mean(np.asarray(bounds) > INFORMATIVE_THRESHOLD)) if bounds else None,
                "vacuous_count": int(sum(value <= NONTRIVIAL_THRESHOLD for value in bounds)),
            }
        )
    large_rows = [row for row in rows if int(row["k"]) >= LARGE_K_MIN]
    large_summary = {
        "definition": f"large k means k >= {LARGE_K_MIN}; each k retains its own eligible pair denominator",
        "per_k_fraction_nontrivial_gt_0": {
            str(row["k"]): row["fraction_nontrivial_gt_0"] for row in summaries if row["k"] >= LARGE_K_MIN
        },
        "per_k_fraction_informative_gt_0_05": {
            str(row["k"]): row["fraction_informative_gt_0_05"] for row in summaries if row["k"] >= LARGE_K_MIN
        },
        "pooled_pair_k_rows": len(large_rows),
        "pooled_fraction_nontrivial_gt_0": float(np.mean([row["nontrivial_gt_0"] for row in large_rows])) if large_rows else None,
        "pooled_fraction_informative_gt_0_05": float(np.mean([row["informative_gt_0_05"] for row in large_rows])) if large_rows else None,
        "interpretation": (
            "The per-k fractions are the citable pair fractions. The pooled values summarize pair-k evaluations "
            "and are not a unique-pair fraction. All large-k entries are EXPLORATORY because the plug-in upper side is lost."
        ),
    }
    return summaries, large_summary


def function_contract() -> tuple[str, str]:
    function = tv_lower_bound_divisibility
    return str(inspect.signature(function)), inspect.getdoc(function) or ""


def assert_function_contract(signature: str, docstring: str) -> None:
    if signature != EXPECTED_SIGNATURE or docstring != EXPECTED_DOCSTRING:
        raise RuntimeError(
            "Repository function signature/docstring differs from the required X6 reference. "
            f"Found signature={signature!r}, docstring={docstring!r}"
        )


def init_stage() -> int:
    started = time.time()
    signature, docstring = function_contract()
    print("FUNCTION_SIGNATURE", signature, flush=True)
    print("FUNCTION_DOCSTRING", json.dumps(docstring), flush=True)
    assert_function_contract(signature, docstring)
    cache = cache_inventory()
    print("CACHE_INVENTORY", json.dumps(cache, sort_keys=True), flush=True)
    if not cache["present"]:
        raise RuntimeError(
            f"Required cached state is incomplete at {CACHE_DIR}; refusing to rescan the H5. "
            f"required_files={cache['required_files']}, npz_part_count={cache['npz_part_count']}"
        )
    print("PREREGISTERED_VALIDITY", json.dumps(PRE_REGISTERED_VALIDITY, sort_keys=True), flush=True)
    validity = validity_check()
    print("VALIDITY_OUTCOME", json.dumps({key: validity[key] for key in ("violations", "total_replications", "violation_rate", "declared_alpha", "falsified", "outcome")}, sort_keys=True), flush=True)
    context = source_context()
    print("HEADLINE_CONTEXT", json.dumps({"k_cert": context["headline_k_cert"], "certifiability_crossover": context["headline_certifiability_crossover"]}, sort_keys=True), flush=True)
    state = {
        "status": "INITIALIZED",
        "started_at_utc": RUN_TIMESTAMP_UTC,
        "init_elapsed_seconds": float(time.time() - started),
        "repository_function": {
            "path": "/root/eibo/src/eibo/divisibility.py",
            "signature": signature,
            "docstring_verbatim": docstring,
            "called_rather_than_rederived": True,
            "call_confirmation": "The runner calls tv_lower_bound_divisibility for every validity replication and every real pair-k row; no replacement implementation is used.",
            "alpha_argument": ALPHA,
            "mode_argument": MODE,
            "q_values_argument": list(Q_VALUES),
        },
        "assumption_sentence": ASSUMPTION_SENTENCE,
        "pre_registered_validity": PRE_REGISTERED_VALIDITY,
        "validity_measured_outcome": validity,
        "object_and_channel": context,
        "cache_and_cost": cache,
        "pair_rows": [],
        "completed_chunks": [],
        "repository_function_call_count_real": 0,
    }
    atomic_write_pickle(STATE_PATH, state)
    print("STATE", json.dumps({"path": str(STATE_PATH), "bytes": STATE_PATH.stat().st_size}, sort_keys=True), flush=True)
    return 0


def real_chunk_stage(k: int, start: int, end: int) -> int:
    state = load_state()
    merged = load_merged()
    pair_rows, features = service_pair_rows(merged, k)
    end = min(end, len(pair_rows))
    if start < 0 or start >= end:
        raise ValueError(f"empty or invalid chunk: k={k}, start={start}, end={end}, total={len(pair_rows)}")
    existing = {(int(row["k"]), int(row["service_a"]), int(row["service_b"])) for row in state["pair_rows"]}
    new_rows = []
    for index, row in enumerate(pair_rows[start:end], start=start):
        key = (k, int(row["service_a"]), int(row["service_b"]))
        if key in existing:
            continue
        seed = SEED + 1_000_000 + 10_000 * k + index
        bound, diagnostics = call_bound(
            features[str(row["service_a"])],
            features[str(row["service_b"])],
            seed,
        )
        out = dict(row)
        out.update(
            {
                "k": k,
                "sample_n_a": int(len(features[str(row["service_a"])])),
                "sample_n_b": int(len(features[str(row["service_b"])])),
                "eps_lo_divisibility": float(bound),
                "nontrivial_gt_0": bool(bound > NONTRIVIAL_THRESHOLD),
                "informative_gt_0_05": bool(bound > INFORMATIVE_THRESHOLD),
                "selected_q": int(diagnostics["selected_q"]),
                "vacuous": bool(diagnostics["vacuous"]),
            }
        )
        if not state.get("representative_call"):
            state["representative_call"] = {
                "k": k,
                "pair": [out["service_a"], out["service_b"]],
                "returned_bound": float(bound),
                "diagnostics": sanitized_diagnostics(diagnostics),
            }
        new_rows.append(out)
    state["pair_rows"].extend(new_rows)
    state["completed_chunks"].append({"k": k, "start": start, "end": end, "new_rows": len(new_rows), "total_for_k": len(pair_rows)})
    state["repository_function_call_count_real"] = int(state.get("repository_function_call_count_real", 0) + len(new_rows))
    atomic_write_pickle(STATE_PATH, state)
    print("CHUNK_DONE", json.dumps(state["completed_chunks"][-1], sort_keys=True), flush=True)
    return 0


def finalize_stage() -> int:
    state = load_state()
    summaries, large_summary = summarize_real_rows(state["pair_rows"])
    not_completed = []
    for row in summaries:
        expected = {5: 990, 10: 990, 15: 946, 20: 946, 25: 861, 30: 820}.get(row["k"])
        if expected is not None and row["pair_count"] != expected:
            not_completed.append({"k": row["k"], "expected_pair_count": expected, "observed_pair_count": row["pair_count"]})
    payload = {
        "status": "COMPLETE" if not not_completed else "PARTIAL",
        "experiment": "X6",
        "run_timestamp_utc": RUN_TIMESTAMP_UTC,
        "execution": {
            "server": "111",
            "account": "root",
            "cwd": str(PROJECT),
            "python": sys.executable,
            "cpu_only": True,
            "gpu_requested": False,
            "repository_function_call_count_validity": state["validity_measured_outcome"]["total_replications"],
            "repository_function_call_count_real": state["repository_function_call_count_real"],
            "repository_function_call_count_total": state["validity_measured_outcome"]["total_replications"] + state["repository_function_call_count_real"],
        },
        "repository_function": state["repository_function"],
        "assumption_sentence": state["assumption_sentence"],
        "pre_registered_validity": state["pre_registered_validity"],
        "validity_measured_outcome": state["validity_measured_outcome"],
        "object_and_channel": state["object_and_channel"],
        "bound_vs_k": summaries,
        "large_k_fraction": large_summary,
        "headline_comparison": state["object_and_channel"]["headline_k_cert"],
        "certifiability_crossover": state["object_and_channel"]["headline_certifiability_crossover"],
        "cache_and_cost": state["cache_and_cost"],
        "sampling": {
            "service_pair_rule": "Both services must have at least 2000 cached flows with PPI_LEN >= k.",
            "sample_cap_per_service": MAX_SAMPLES_PER_SERVICE,
            "sample_selection": "Deterministic seeded without-replacement subsample from cached eligible flows when the cap binds; all eligible cached flows otherwise.",
            "large_k_definition": f"k >= {LARGE_K_MIN}",
            "nontrivial_definition": "returned eps_lo_divisibility > 0",
            "informative_companion_definition": "returned eps_lo_divisibility > 0.05",
        },
        "representative_call": state.get("representative_call"),
        "completed_chunks": state["completed_chunks"],
        "pair_rows": state["pair_rows"],
        "runner_path": str(RUNNER_PATH),
        "runner_sha256": sha256_file(RUNNER_PATH),
        "not_completed": not_completed,
    }
    atomic_write_json(ARTIFACT_PATH, payload)
    print("ARTIFACT", json.dumps({"path": str(ARTIFACT_PATH), "bytes": ARTIFACT_PATH.stat().st_size, "sha256": sha256_file(ARTIFACT_PATH)}, sort_keys=True), flush=True)
    print("RUNNER", json.dumps({"path": str(RUNNER_PATH), "sha256": sha256_file(RUNNER_PATH), "bytes": RUNNER_PATH.stat().st_size}, sort_keys=True), flush=True)
    return 0


def source_context() -> dict[str, Any]:
    channel = json.loads(REFERENCE_CHANNEL_ARTIFACT.read_text(encoding="utf-8"))
    headline = json.loads(HEADLINE_ARTIFACT.read_text(encoding="utf-8"))
    frontier = json.loads(FRONTIER_ARTIFACT.read_text(encoding="utf-8"))
    m1_k5 = next(row for row in headline["headline_table_unified_calibre"] if row["M"] == 1 and row["k"] == 5)
    crossover = frontier["certifiability_crossover"]["grid"]["0.30"]["n_crossover"]
    return {
        "object_channel_statement": (
            "The measured object is the k-prefix symbol law: draw a flow from a service and map its first k "
            "masked (direction, size) symbols, using PPI[1] direction and PPI[2] size only; PPI[0] inter-packet "
            "timing is excluded; flows require PPI_LEN >= k."
        ),
        "matches_headline": True,
        "deviation": (
            "At headline M=1, size_bins_m1_all_zero was measured true, so X6 uses the equivalent binary direction "
            "bit-vector encoding and omits the constant size coordinate; this changes representation, not the channel law."
        ),
        "reference_object_definition": channel["metadata"]["object_definition"],
        "m1_size_collapse_validation": channel["metadata"]["masking"]["validation"],
        "reference_channel_artifact": str(REFERENCE_CHANNEL_ARTIFACT),
        "reference_channel_artifact_sha256": sha256_file(REFERENCE_CHANNEL_ARTIFACT),
        "headline_k_cert": {
            "M": 1,
            "n": 3_900_000,
            "tv_hat": 0.30,
            "k_cert": 17,
            "source": "project headline context / ROADMAP entry; printed by this runner before completion",
        },
        "headline_certifiability_crossover": {
            "criterion": "eps_hi < 0.5 for M=8 and k=5",
            "alpha_law": 0.025,
            "tv_hat": 0.30,
            "n_crossover": float(crossover),
            "source_artifact": str(FRONTIER_ARTIFACT),
            "source_value_reloaded": True,
            "headline_m1_k5_upper_side_fraction": m1_k5["upper_side_fraction"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("all", "init", "real", "finalize"), default="all")
    parser.add_argument("--k", type=int)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    args = parser.parse_args()
    if args.stage == "init":
        return init_stage()
    if args.stage == "real":
        if args.k is None or args.end is None:
            raise SystemExit("--stage real requires --k and --end")
        return real_chunk_stage(args.k, args.start, args.end)
    if args.stage == "finalize":
        return finalize_stage()

    started = time.time()
    function = tv_lower_bound_divisibility
    signature = str(inspect.signature(function))
    docstring = inspect.getdoc(function) or ""
    print("FUNCTION_SIGNATURE", signature, flush=True)
    print("FUNCTION_DOCSTRING", json.dumps(docstring), flush=True)
    if signature != EXPECTED_SIGNATURE or docstring != EXPECTED_DOCSTRING:
        blocker = (
            "Repository function signature/docstring differs from the required X6 reference. "
            f"Found signature={signature!r}, docstring={docstring!r}"
        )
        payload = {
            "status": "BLOCKED",
            "blocker": blocker,
            "function_signature_found": signature,
            "function_docstring_found": docstring,
            "runner_sha256": sha256_file(RUNNER_PATH),
        }
        atomic_write_json(ARTIFACT_PATH, payload)
        print("BLOCKER", blocker, flush=True)
        return 2

    cache = cache_inventory()
    print("CACHE_INVENTORY", json.dumps(cache, sort_keys=True), flush=True)
    if not cache["present"]:
        blocker = (
            f"Required cached state is incomplete at {CACHE_DIR}; refusing to rescan the H5. "
            f"required_files={cache['required_files']}, npz_part_count={cache['npz_part_count']}"
        )
        payload = {
            "status": "BLOCKED",
            "blocker": blocker,
            "function_signature": signature,
            "function_docstring": docstring,
            "pre_registered_validity": PRE_REGISTERED_VALIDITY,
            "cache": cache,
            "runner_sha256": sha256_file(RUNNER_PATH),
        }
        atomic_write_json(ARTIFACT_PATH, payload)
        print("BLOCKER", blocker, flush=True)
        return 3

    print("PREREGISTERED_VALIDITY", json.dumps(PRE_REGISTERED_VALIDITY, sort_keys=True), flush=True)
    validity = validity_check()
    print("VALIDITY_OUTCOME", json.dumps({key: validity[key] for key in ("violations", "total_replications", "violation_rate", "declared_alpha", "falsified", "outcome")}, sort_keys=True), flush=True)

    merged = load_merged()
    services = [int(service) for service in merged["services"]]
    summaries, detail = real_data_by_k(merged)
    context = source_context()
    print("HEADLINE_CONTEXT", json.dumps({"k_cert": context["headline_k_cert"], "certifiability_crossover": context["headline_certifiability_crossover"]}, sort_keys=True), flush=True)
    payload = {
        "status": "COMPLETE",
        "experiment": "X6",
        "run_timestamp_utc": RUN_TIMESTAMP_UTC,
        "execution": {
            "server": "111",
            "account": "root",
            "cwd": os.getcwd(),
            "python": sys.executable,
            "cpu_only": True,
            "gpu_requested": False,
            "elapsed_seconds": float(time.time() - started),
            "service_count_from_cache": len(services),
            "repository_function_call_count_validity": validity["total_replications"],
            "repository_function_call_count_real": detail["repository_function_call_count_real"],
            "repository_function_call_count_total": validity["total_replications"] + detail["repository_function_call_count_real"],
        },
        "repository_function": {
            "path": "/root/eibo/src/eibo/divisibility.py",
            "signature": signature,
            "docstring_verbatim": docstring,
            "called_rather_than_rederived": True,
            "call_confirmation": "The runner called tv_lower_bound_divisibility for every validity replication and every real pair-k row; no replacement implementation was used.",
            "alpha_argument": ALPHA,
            "mode_argument": MODE,
            "q_values_argument": list(Q_VALUES),
        },
        "assumption_sentence": ASSUMPTION_SENTENCE,
        "pre_registered_validity": PRE_REGISTERED_VALIDITY,
        "validity_measured_outcome": validity,
        "object_and_channel": context,
        "bound_vs_k": summaries,
        "large_k_fraction": detail["large_k_summary"],
        "headline_comparison": context["headline_k_cert"],
        "certifiability_crossover": context["headline_certifiability_crossover"],
        "cache_and_cost": cache,
        "sampling": {
            "service_pair_rule": "Both services must have at least 2000 cached flows with PPI_LEN >= k.",
            "sample_cap_per_service": MAX_SAMPLES_PER_SERVICE,
            "sample_selection": "Deterministic seeded without-replacement subsample from cached eligible flows when the cap binds; all eligible cached flows otherwise.",
            "large_k_definition": f"k >= {LARGE_K_MIN}",
            "nontrivial_definition": "returned eps_lo_divisibility > 0",
            "informative_companion_definition": "returned eps_lo_divisibility > 0.05",
        },
        "representative_call": detail["representative_call"],
        "pair_rows": detail["pair_rows"],
        "runner_path": str(RUNNER_PATH),
        "runner_sha256": sha256_file(RUNNER_PATH),
        "not_completed": [],
    }
    atomic_write_json(ARTIFACT_PATH, payload)
    print(
        "ARTIFACT",
        json.dumps(
            {
                "path": str(ARTIFACT_PATH),
                "bytes": ARTIFACT_PATH.stat().st_size,
                "sha256": sha256_file(ARTIFACT_PATH),
            },
            sort_keys=True,
        ),
        flush=True,
    )
    print("RUNNER", json.dumps({"path": str(RUNNER_PATH), "sha256": sha256_file(RUNNER_PATH), "bytes": RUNNER_PATH.stat().st_size}, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
