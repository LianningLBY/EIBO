#!/usr/bin/env python3
"""X3 control (b): deliberate per-context flow thinning dose-response."""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import time
from pathlib import Path

import numpy as np

from x3_controls import (
    K_VALUES,
    codes_from_bits,
    d_chain_fast,
    fit_growth,
    service_counts_fast_from_codes,
    synthetic_bits,
    synthetic_counts_on_real_prefix_occupancy,
)


PROJECT = Path("/root/eibo")
CACHE_DIR = Path("/dev/shm/eibo_x3_chain_rule")
MERGED_PATH = CACHE_DIR / "merged.pkl"
ARTIFACT_PATH = PROJECT / "artifacts" / "x3_control_occupancy_dose_response.json"
RUNNER_PATH = PROJECT / "x3_control_occupancy_dose_response.py"
SEED = 20260914
PLAIN_N = 200_000
P = 0.30
Q = 0.70
RETAINED_FRACTIONS = (1.0, 0.50, 0.25, 0.10, 0.05)
ANALYTIC_PER_POSITION = 0.3389191441548814


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def cache_inventory() -> dict:
    required = [CACHE_DIR / "ledger.json", MERGED_PATH, CACHE_DIR / "results.pkl"]
    parts = sorted(CACHE_DIR.glob("part_*.npz")) if CACHE_DIR.exists() else []
    files = [p for p in CACHE_DIR.iterdir() if p.is_file()] if CACHE_DIR.exists() else []
    return {
        "present": bool(all(p.is_file() for p in required) and len(parts) == 360),
        "cache_dir": str(CACHE_DIR),
        "required_files": {p.name: p.is_file() for p in required},
        "npz_part_count": len(parts),
        "file_count": len(files),
        "total_bytes": int(sum(p.stat().st_size for p in files)),
        "h5_rescan": False,
    }


def load_merged() -> tuple[dict, dict]:
    inventory = cache_inventory()
    if not inventory["present"]:
        raise RuntimeError(
            "cached state incomplete at /dev/shm/eibo_x3_chain_rule; refusing to rescan the H5"
        )
    with MERGED_PATH.open("rb") as handle:
        return pickle.load(handle), inventory


def copy_transition(trans: dict) -> dict:
    return {
        "ctx0": np.asarray(trans["ctx0"], dtype=np.uint32).copy(),
        "cnt0": np.asarray(trans["cnt0"], dtype=np.float64).copy(),
        "ctx1": np.asarray(trans["ctx1"], dtype=np.uint32).copy(),
        "cnt1": np.asarray(trans["cnt1"], dtype=np.float64).copy(),
        "n": int(trans["n"]),
    }


def thin_counts(counts: list[dict], retained_fraction: float, rng: np.random.Generator) -> list[dict]:
    """Uniformly retain flows within every observed context via hypergeometric sampling."""
    if retained_fraction == 1.0:
        return [copy_transition(t) for t in counts]
    output = []
    for trans in counts:
        contexts = np.union1d(trans["ctx0"], trans["ctx1"])
        zeros = np.zeros(contexts.size, dtype=np.int64)
        ones = np.zeros(contexts.size, dtype=np.int64)
        if trans["ctx0"].size:
            zeros[np.searchsorted(contexts, trans["ctx0"])] = np.rint(trans["cnt0"]).astype(np.int64)
        if trans["ctx1"].size:
            ones[np.searchsorted(contexts, trans["ctx1"])] = np.rint(trans["cnt1"]).astype(np.int64)
        totals = zeros + ones
        retained = np.floor(retained_fraction * totals).astype(np.int64)
        retained_ones = rng.hypergeometric(ones, totals - ones, retained)
        retained_zeros = retained - retained_ones
        zmask = retained_zeros > 0
        omask = retained_ones > 0
        output.append({
            "ctx0": contexts[zmask].astype(np.uint32),
            "cnt0": retained_zeros[zmask].astype(np.float64),
            "ctx1": contexts[omask].astype(np.uint32),
            "cnt1": retained_ones[omask].astype(np.float64),
            "n": int(np.sum(retained)),
        })
    return output


def occupancy_one_transition(trans: dict, k: int, position: int) -> dict:
    contexts = np.union1d(trans["ctx0"], trans["ctx1"])
    zeros = np.zeros(contexts.size, dtype=np.float64)
    ones = np.zeros(contexts.size, dtype=np.float64)
    if trans["ctx0"].size:
        zeros[np.searchsorted(contexts, trans["ctx0"])] = trans["cnt0"]
    if trans["ctx1"].size:
        ones[np.searchsorted(contexts, trans["ctx1"])] = trans["cnt1"]
    totals = zeros + ones
    n_contexts = int(contexts.size)
    return {
        "k": int(k),
        "position": int(position),
        "distinct_contexts": n_contexts,
        "total_transitions": int(np.sum(totals)),
        "contexts_below_5": int(np.sum(totals < 5)),
        "fraction_contexts_below_5": float(np.mean(totals < 5)) if n_contexts else None,
        "median_context_count": float(np.median(totals)) if n_contexts else None,
    }


def occupancy_stats(counts: list[dict], start_k: int = 5) -> dict:
    rows = []
    for position, trans in enumerate(counts, start=1):
        k = start_k + position - 1
        row = occupancy_one_transition(trans, k, position)
        rows.append(row)
    return {
        "by_position": rows,
        "mean_fraction_contexts_below_5": float(np.mean([
            r["fraction_contexts_below_5"] for r in rows if r["fraction_contexts_below_5"] is not None
        ])) if rows else None,
        "mean_distinct_contexts": float(np.mean([r["distinct_contexts"] for r in rows])) if rows else None,
        "mean_total_transitions": float(np.mean([r["total_transitions"] for r in rows])) if rows else None,
        "k30": rows[-1] if rows else None,
    }


def paired_occupancy(counts_p: list[dict], counts_q: list[dict]) -> dict:
    p = occupancy_stats(counts_p)
    q = occupancy_stats(counts_q)
    return {
        "p": p,
        "q": q,
        "mean_fraction_contexts_below_5": float(np.mean([
            p["mean_fraction_contexts_below_5"], q["mean_fraction_contexts_below_5"]
        ])),
        "mean_distinct_contexts": float(np.mean([p["mean_distinct_contexts"], q["mean_distinct_contexts"]])),
        "mean_total_transitions": float(np.mean([p["mean_total_transitions"], q["mean_total_transitions"]])),
        "k30_mean_fraction_contexts_below_5": float(np.mean([
            p["k30"]["fraction_contexts_below_5"], q["k30"]["fraction_contexts_below_5"]
        ])),
    }


def detect_constant_tail(curve: list[dict], min_tail_values: int = 2) -> dict:
    values = [row["D_k_median"] for row in curve]
    ks = [int(row["k"]) for row in curve]
    zero_increment_ks = [
        ks[index]
        for index in range(1, len(values))
        if values[index] is not None and values[index] == values[index - 1]
    ]
    runs = []
    run_start = 0
    for index in range(1, len(values) + 1):
        if index < len(values) and values[index] == values[index - 1]:
            continue
        if index - run_start >= min_tail_values:
            runs.append(
                {
                    "start_k": ks[run_start],
                    "end_k": ks[index - 1],
                    "length_values": index - run_start,
                    "value": values[run_start],
                }
            )
        run_start = index
    tail_run = runs[-1] if runs and runs[-1]["end_k"] == ks[-1] else None
    return {
        "assertion": f"no constant tail of >= {min_tail_values} exactly equal D_k_median values",
        "status": "FAIL" if tail_run else "PASS",
        "tail_freeze": tail_run is not None,
        "tail_freeze_onset_k": tail_run["start_k"] if tail_run else None,
        "tail_freeze_end_k": tail_run["end_k"] if tail_run else None,
        "tail_freeze_length_values": tail_run["length_values"] if tail_run else 0,
        "zero_increment_count": len(zero_increment_ks),
        "zero_increment_ks": zero_increment_ks,
        "constant_runs": runs,
    }


def compact_fit(fit: dict) -> dict:
    return {
        "status": "FIT_EMITTED",
        "fit_refused": False,
        "normal_fit_emitted": True,
        "exponent_p": float(fit["power"]["exponent_p"]),
        "coefficient": float(fit["power"]["coefficient"]),
        "linear_model_aic_advantage_over_sqrt": float(fit["linear_model_aic_advantage_over_sqrt"]),
        "first_to_last_median_increment_ratio": float(fit["first_to_last_median_increment_ratio"]),
        "verdict": fit["verdict"],
    }


def guarded_fit_growth(curve: list[dict]) -> dict:
    freeze = detect_constant_tail(curve)
    if freeze["tail_freeze"]:
        onset = freeze["tail_freeze_onset_k"]
        non_frozen_curve = [row for row in curve if int(row["k"]) <= int(onset)]
        non_frozen_fit = fit_growth(non_frozen_curve) if len(non_frozen_curve) >= 3 else None
        return {
            "status": "REFUSED_CONSTANT_TAIL",
            "fit_refused": True,
            "normal_fit_emitted": False,
            "reason": (
                "D_k_median is exactly constant over the tail; a full-window "
                "power-law exponent would report thinning-induced saturation as data."
            ),
            "freeze_assertion": freeze,
            "non_frozen_window": {
                "k_min": int(non_frozen_curve[0]["k"]) if non_frozen_curve else None,
                "k_max": int(non_frozen_curve[-1]["k"]) if non_frozen_curve else None,
                "n_points": len(non_frozen_curve),
                "fit": compact_fit(non_frozen_fit) if non_frozen_fit is not None else None,
            },
        }
    fit = compact_fit(fit_growth(curve))
    fit["freeze_assertion"] = freeze
    return fit


def fit_thinned_curve(raw_p: list[dict], raw_q: list[dict], retained_fraction: float, seed_offset: int) -> dict:
    curve = []
    occupancy = []
    rng = np.random.default_rng(SEED + seed_offset)
    thinned_p = thin_counts(raw_p, retained_fraction, rng)
    thinned_q = thin_counts(raw_q, retained_fraction, rng)
    for index, k in enumerate(K_VALUES):
        counts_p = thinned_p[:k]
        counts_q = thinned_q[:k]
        value = d_chain_fast(counts_p, counts_q, 0.5)
        curve.append({"k": int(k), "D_k_median": float(value), "D_k_mean": float(value)})
        occupancy_p = occupancy_one_transition(thinned_p[index], k, index + 1)
        occupancy_q = occupancy_one_transition(thinned_q[index], k, index + 1)
        occupancy.append({
            "k": int(k),
            "p": occupancy_p,
            "q": occupancy_q,
            "mean_fraction_contexts_below_5": float(np.mean([
                occupancy_p["fraction_contexts_below_5"], occupancy_q["fraction_contexts_below_5"]
            ])),
            "mean_distinct_contexts": float(np.mean([
                occupancy_p["distinct_contexts"], occupancy_q["distinct_contexts"]
            ])),
            "mean_total_transitions": float(np.mean([
                occupancy_p["total_transitions"], occupancy_q["total_transitions"]
            ])),
            "k30_mean_fraction_contexts_below_5": float(np.mean([
                occupancy_p["fraction_contexts_below_5"], occupancy_q["fraction_contexts_below_5"]
            ])),
        })
    fit = guarded_fit_growth(curve)
    return {
        "retained_fraction": retained_fraction,
        "thinning_fraction": 1.0 - retained_fraction,
        "fit": fit,
        "occupancy_summary": {
            "mean_fraction_contexts_below_5": float(np.mean([
                r["mean_fraction_contexts_below_5"] for r in occupancy
            ])),
            "k30_mean_fraction_contexts_below_5": occupancy[-1]["k30_mean_fraction_contexts_below_5"],
            "mean_distinct_contexts": float(np.mean([
                r["mean_distinct_contexts"] for r in occupancy
            ])),
            "mean_total_transitions": float(np.mean([
                r["mean_total_transitions"] for r in occupancy
            ])),
        },
        "occupancy_by_k": occupancy,
        "curve": curve,
    }


def assert_plain_unthinned_reference(
    raw_p: list[dict],
    raw_q: list[dict],
    baseline: dict,
) -> dict:
    reference_curve = [
        {
            "k": int(k),
            "D_k": float(d_chain_fast(raw_p[:k], raw_q[:k], 0.5)),
        }
        for k in K_VALUES
    ]
    actual_curve = [
        {"k": int(row["k"]), "D_k": float(row["D_k_median"])}
        for row in baseline["curve"]
    ]
    assert actual_curve == reference_curve, (
        "un-thinned baseline diverged from the reference curve at its labelled k"
    )
    k5 = next(row["D_k"] for row in actual_curve if row["k"] == 5)
    truth_k5 = 5.0 * ANALYTIC_PER_POSITION
    ratio_k5 = k5 / truth_k5
    assert abs(ratio_k5 - 1.0) <= 0.001, (
        f"un-thinned k=5 analytic-truth ratio out of tolerance: {ratio_k5:.12f}"
    )
    return {
        "reference_curve_bit_identical": True,
        "analytic_truth": {
            "per_position": ANALYTIC_PER_POSITION,
            "k": 5,
            "D_k": truth_k5,
            "estimated_D_k": k5,
            "est_over_true": ratio_k5,
            "tolerance": 0.001,
        },
    }


def monotone_nonincreasing(values: list[float]) -> bool:
    return all(a >= b for a, b in zip(values, values[1:]))


def main() -> int:
    started = time.time()
    preregistration = {
        "arm_definitions": {
            "plain_iid": "200000 synthetic 30-bit flows at p=0.30 and p=0.70, using the existing plain synthetic arm path",
            "twin_real_occupancy": "existing count-level synthetic arm using exact cached prefix occupancy for services 0 and 1, with p=0.30 and q=0.70",
        },
        "thinning_levels": [
            {"retained_fraction": r, "thinning_fraction": 1.0 - r} for r in RETAINED_FRACTIONS
        ],
        "thinning_operation": "within each law and each observed context, uniformly retain floor(r*n_context) flows and split retained zero/one counts by hypergeometric sampling",
        "occupancy_primary_statistic": "mean across k=5..30 and both laws of the fraction of observed contexts with fewer than 5 retained transitions",
        "decision_rule": "For an arm, deflation tracks thinning iff the primary sparse-context statistic is nondecreasing and fitted exponent p is nonincreasing as retained_fraction decreases across all five levels. The joint result tracks iff both arms satisfy this rule.",
        "fit_reference": "/root/eibo/x3_controls.py:fit_growth",
        "divergence_reference": "/root/eibo/x3_controls.py:d_chain_fast",
    }

    merged, cache = load_merged()
    rng = np.random.default_rng(SEED)
    plain_p = synthetic_bits(PLAIN_N, 30, P, rng)
    plain_q = synthetic_bits(PLAIN_N, 30, Q, rng)
    plain_lens = np.full(PLAIN_N, 30, dtype=np.uint8)
    plain_raw_p = service_counts_fast_from_codes(codes_from_bits(plain_p), plain_lens, 30)
    plain_raw_q = service_counts_fast_from_codes(codes_from_bits(plain_q), plain_lens, 30)

    services = list(map(int, merged["services"]))
    twin_a, twin_b = services[0], services[1]
    twin_rng_p = np.random.default_rng(SEED + 1_000_003)
    twin_rng_q = np.random.default_rng(SEED + 2_000_003)
    twin_raw_p = synthetic_counts_on_real_prefix_occupancy(merged, twin_a, 30, P, twin_rng_p)
    twin_raw_q = synthetic_counts_on_real_prefix_occupancy(merged, twin_b, 30, Q, twin_rng_q)

    plain_levels = [fit_thinned_curve(plain_raw_p, plain_raw_q, r, 10_000 + i * 100_000) for i, r in enumerate(RETAINED_FRACTIONS)]
    twin_levels = [fit_thinned_curve(twin_raw_p, twin_raw_q, r, 20_000 + i * 100_000) for i, r in enumerate(RETAINED_FRACTIONS)]
    acceptance = assert_plain_unthinned_reference(plain_raw_p, plain_raw_q, plain_levels[0])

    def trend(levels: list[dict]) -> dict:
        # Levels are ordered from least thinning to most thinning.
        p_values = [
            x["fit"]["exponent_p"] if x["fit"].get("status") == "FIT_EMITTED" else None
            for x in levels
        ]
        sparse_values = [x["occupancy_summary"]["mean_fraction_contexts_below_5"] for x in levels]
        emitted_p = [value for value in p_values if value is not None]
        p_nonincreasing = len(emitted_p) == len(p_values) and monotone_nonincreasing(emitted_p)
        sparse_nondec = all(a <= b for a, b in zip(sparse_values, sparse_values[1:]))
        return {
            "exponent_p_by_retained_fraction": p_values,
            "refused_fit_retained_fractions": [
                x["retained_fraction"]
                for x in levels
                if x["fit"].get("status") == "REFUSED_CONSTANT_TAIL"
            ],
            "freeze_assertions": [
                {
                    "retained_fraction": x["retained_fraction"],
                    "assertion": x["fit"]["freeze_assertion"],
                }
                for x in levels
            ],
            "sparse_context_stat_by_retained_fraction": sparse_values,
            "p_nonincreasing_with_thinning": p_nonincreasing,
            "sparse_context_stat_nondecreasing_with_thinning": sparse_nondec,
            "tracks_thinning": bool(p_nonincreasing and sparse_nondec),
        }

    plain_trend = trend(plain_levels)
    twin_trend = trend(twin_levels)
    payload = {
        "control": "b",
        "preregistration": preregistration,
        "seed": SEED,
        "arms": {
            "plain_iid": {
                "levels": plain_levels,
                "trend": plain_trend,
            },
            "twin_real_occupancy": {
                "services_used": [twin_a, twin_b],
                "levels": twin_levels,
                "trend": twin_trend,
            },
        },
        "decision": {
            "plain_arm_tracks_thinning": plain_trend["tracks_thinning"],
            "twin_arm_tracks_thinning": twin_trend["tracks_thinning"],
            "joint_tracks_thinning": bool(plain_trend["tracks_thinning"] and twin_trend["tracks_thinning"]),
            "observed_trend": {
                "plain_iid": plain_trend,
                "twin_real_occupancy": twin_trend,
            },
        },
        "acceptance": acceptance,
        "execution": {
            "cache": cache,
            "cache_reused": True,
            "h5_rescan": False,
            "x12_touched": False,
            "elapsed_seconds": float(time.time() - started),
        },
    }
    atomic_write_json(ARTIFACT_PATH, payload)
    print(json.dumps({
        "artifact": str(ARTIFACT_PATH),
        "artifact_bytes": ARTIFACT_PATH.stat().st_size,
        "artifact_sha256": sha256_file(ARTIFACT_PATH),
        "plain": plain_trend,
        "twin": twin_trend,
        "acceptance": acceptance,
        "runner": str(RUNNER_PATH),
        "runner_sha256": sha256_file(RUNNER_PATH),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
