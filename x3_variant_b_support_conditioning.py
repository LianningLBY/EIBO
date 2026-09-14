#!/usr/bin/env python3
"""X3 variant B: support-conditioned chain-rule divergence.

The divergence calculation itself is imported from x3_controls.py.  This
runner changes only the exposure: at every prefix position it retains the
intersection of contexts with at least MIN_CONTEXT_COUNT observations under
both laws, then calls the reference divergence implementation on the retained
counts after empirical renormalization.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import sys
from pathlib import Path

import numpy as np

from x3_controls import (
    K_VALUES,
    MIN_SERVICE_FLOWS,
    codes_from_bits,
    d_chain_fast,
    fast_service_n,
    fit_growth,
    pair_key,
    real_counts_fast,
    service_counts_fast_from_codes,
    synthetic_bits,
    synthetic_counts_on_real_prefix_occupancy,
    take_counts,
)


PROJECT = Path("/root/eibo")
CACHE_DIR = Path("/dev/shm/eibo_x3_chain_rule")
MERGED = CACHE_DIR / "merged.pkl"
RESULTS = CACHE_DIR / "results.pkl"
LEDGER = CACHE_DIR / "ledger.json"
PAIR_PATH = PROJECT / "artifacts" / "q1_eps_lo_symbol_map.json"
ORIGINAL_ARTIFACT = PROJECT / "artifacts" / "x3_chain_rule_divergence.json"
OUTPUT = PROJECT / "artifacts" / "x3_variant_b_support_conditioning.json"
RUNNER_PATH = PROJECT / "x3_variant_b_support_conditioning.py"

SEED = 20260914
PLAIN_N = 200_000
SMOOTHING = 0.5
MIN_CONTEXT_COUNT = 5
THRESHOLD_CANDIDATES = (5, 10, 20, 50, 100)
TWIN_SEED_OFFSET = 1_000_003
ALPHA = 0.05

ESTIMATOR_SENTENCE = (
    "For each prefix position i, estimate the symmetrized conditional Bernoulli "
    "KL contribution used by the reference d_chain_fast implementation, but "
    "condition both empirical context laws on the intersection of contexts with "
    "at least T observations under P and at least T observations under Q; "
    "renormalize each law over the retained transition mass, and use the "
    "reference add-0.5 conditional smoothing only on those retained contexts. "
    "T is fixed by the control-only threshold rule below and is never selected "
    "using real-data divergence values."
)

CRITERIA = {
    "linear_exponent_p": "power.exponent_p > 0.95",
    "aic_advantage": "linear_model_aic_advantage_over_sqrt > 6",
    "increment_ratio": "first_to_last_median_increment_ratio <= 1.10",
    "required_for_each_arm": True,
    "arm_names": ["plain_iid_known_truth", "twin_real_occupancy_known_truth"],
}


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(json_ready(payload), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def json_ready(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_ready(item) for item in value]
    return value


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cache_inventory() -> dict:
    npz_parts = sorted(CACHE_DIR.glob("part_*.npz"))
    files = [MERGED, RESULTS, LEDGER]
    required_present = all(path.is_file() for path in files)
    total_bytes = sum(path.stat().st_size for path in files if path.is_file())
    total_bytes += sum(path.stat().st_size for path in npz_parts)
    return {
        "cache_dir": str(CACHE_DIR),
        "present": bool(required_present and len(npz_parts) == 360),
        "required_files": {
            str(path): {"present": path.is_file(), "bytes": path.stat().st_size if path.is_file() else None}
            for path in files
        },
        "npz_part_count": len(npz_parts),
        "npz_bytes": sum(path.stat().st_size for path in npz_parts),
        "total_inventory_bytes": total_bytes,
        "inputs_used": [str(MERGED), str(RESULTS), str(LEDGER)],
        "h5_rescan": False,
    }


def load_merged() -> dict:
    inventory = cache_inventory()
    if not inventory["present"]:
        raise RuntimeError(
            "cached state incomplete at /dev/shm/eibo_x3_chain_rule; "
            "refusing to rescan the H5"
        )
    with MERGED.open("rb") as handle:
        return pickle.load(handle)


def pack_sparse(contexts: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mask = values > 0
    return contexts[mask].astype(np.uint32), values[mask].astype(np.float64)


def condition_counts(
    counts_p: list[dict],
    counts_q: list[dict],
    threshold: int,
) -> tuple[list[dict], list[dict], dict]:
    """Filter both laws to shared occupied contexts and return mass accounting."""

    filtered_p: list[dict] = []
    filtered_q: list[dict] = []
    per_position = []
    total_p = 0.0
    total_q = 0.0
    excluded_p = 0.0
    excluded_q = 0.0

    for position, (cp, cq) in enumerate(zip(counts_p, counts_q), start=1):
        contexts = np.union1d(
            np.union1d(cp["ctx0"], cp["ctx1"]),
            np.union1d(cq["ctx0"], cq["ctx1"]),
        )
        p0 = take_counts(contexts, cp["ctx0"], cp["cnt0"])
        p1 = take_counts(contexts, cp["ctx1"], cp["cnt1"])
        q0 = take_counts(contexts, cq["ctx0"], cq["cnt0"])
        q1 = take_counts(contexts, cq["ctx1"], cq["cnt1"])
        np_ctx = p0 + p1
        nq_ctx = q0 + q1
        keep = (np_ctx >= threshold) & (nq_ctx >= threshold)

        raw_p = float(cp["n"])
        raw_q = float(cq["n"])
        kept_p = float(np.sum(np_ctx[keep]))
        kept_q = float(np.sum(nq_ctx[keep]))
        drop_p = max(0.0, raw_p - kept_p)
        drop_q = max(0.0, raw_q - kept_q)
        total_p += raw_p
        total_q += raw_q
        excluded_p += drop_p
        excluded_q += drop_q

        kept_contexts = contexts[keep]
        p0_k, p0_v = pack_sparse(kept_contexts, p0[keep])
        p1_k, p1_v = pack_sparse(kept_contexts, p1[keep])
        q0_k, q0_v = pack_sparse(kept_contexts, q0[keep])
        q1_k, q1_v = pack_sparse(kept_contexts, q1[keep])
        filtered_p.append(
            {"ctx0": p0_k, "cnt0": p0_v, "ctx1": p1_k, "cnt1": p1_v, "n": int(kept_p)}
        )
        filtered_q.append(
            {"ctx0": q0_k, "cnt0": q0_v, "ctx1": q1_k, "cnt1": q1_v, "n": int(kept_q)}
        )
        per_position.append(
            {
                "position": position,
                "distinct_contexts": int(contexts.size),
                "retained_contexts": int(np.sum(keep)),
                "p_total": int(raw_p),
                "q_total": int(raw_q),
                "p_retained": int(kept_p),
                "q_retained": int(kept_q),
                "p_excluded_mass": float(drop_p / raw_p) if raw_p else None,
                "q_excluded_mass": float(drop_q / raw_q) if raw_q else None,
            }
        )

    summary = {
        "threshold": int(threshold),
        "p_excluded_mass": float(excluded_p / total_p) if total_p else None,
        "q_excluded_mass": float(excluded_q / total_q) if total_q else None,
        "mean_two_sided_excluded_mass": (
            float(0.5 * (excluded_p / total_p + excluded_q / total_q))
            if total_p and total_q
            else None
        ),
        "per_position": per_position,
    }
    return filtered_p, filtered_q, summary


def estimate_pair(
    counts_p: list[dict],
    counts_q: list[dict],
    threshold: int,
) -> tuple[float, dict]:
    conditioned_p, conditioned_q, mass = condition_counts(counts_p, counts_q, threshold)
    value = d_chain_fast(conditioned_p, conditioned_q, SMOOTHING)
    return float(value), mass


def fit_passes(fit: dict) -> bool:
    return bool(
        fit.get("status", "FIT_EMITTED") == "FIT_EMITTED"
        and fit["power"]["exponent_p"] > 0.95
        and fit["linear_model_aic_advantage_over_sqrt"] > 6
        and fit["first_to_last_median_increment_ratio"] <= 1.10
    )


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


def guarded_fit_growth(curve: list[dict]) -> dict:
    freeze = detect_constant_tail(curve)
    assertion_error = None
    try:
        assert not freeze["tail_freeze"], (
            f"constant-tail freeze detected at k={freeze['tail_freeze_onset_k']} "
            f"through k={freeze['tail_freeze_end_k']}"
        )
    except AssertionError as exc:
        assertion_error = str(exc)
    if assertion_error is not None:
        onset = freeze["tail_freeze_onset_k"]
        non_frozen_curve = [row for row in curve if int(row["k"]) <= int(onset)]
        non_frozen_fit = fit_growth(non_frozen_curve) if len(non_frozen_curve) >= 3 else None
        return {
            "status": "REFUSED_CONSTANT_TAIL",
            "fit_refused": True,
            "normal_fit_emitted": False,
            "reason": (
                "D_k_median is exactly constant over the tail; a full-window "
                "power-law exponent would fit a script-induced retained-context freeze."
            ),
            "assertion_error": assertion_error,
            "freeze_assertion": freeze,
            "non_frozen_window": {
                "k_min": int(non_frozen_curve[0]["k"]) if non_frozen_curve else None,
                "k_max": int(non_frozen_curve[-1]["k"]) if non_frozen_curve else None,
                "n_points": len(non_frozen_curve),
                "fit": non_frozen_fit,
            },
        }
    fit = fit_growth(curve)
    fit["status"] = "FIT_EMITTED"
    fit["fit_refused"] = False
    fit["normal_fit_emitted"] = True
    fit["assertion_error"] = None
    fit["freeze_assertion"] = freeze
    return fit


def conditioning_summary_for_k(k: int, mass: dict) -> dict:
    positions = mass["per_position"]
    p_total = sum(row["p_total"] for row in positions)
    q_total = sum(row["q_total"] for row in positions)
    p_retained = sum(row["p_retained"] for row in positions)
    q_retained = sum(row["q_retained"] for row in positions)
    return {
        "k": int(k),
        "threshold": int(mass["threshold"]),
        "distinct_contexts_total": int(sum(row["distinct_contexts"] for row in positions)),
        "retained_contexts_total": int(sum(row["retained_contexts"] for row in positions)),
        "new_position_distinct_contexts": int(positions[-1]["distinct_contexts"]) if positions else 0,
        "new_position_retained_contexts": int(positions[-1]["retained_contexts"]) if positions else 0,
        "p_retained_transition_mass": float(p_retained / p_total) if p_total else None,
        "q_retained_transition_mass": float(q_retained / q_total) if q_total else None,
        "mean_two_sided_retained_transition_mass": (
            float(0.5 * (p_retained / p_total + q_retained / q_total))
            if p_total and q_total
            else None
        ),
        "mean_two_sided_excluded_mass": mass["mean_two_sided_excluded_mass"],
    }


def summarize_mass(rows: list[dict]) -> dict:
    p = np.asarray([r["p_excluded_mass"] for r in rows], dtype=float)
    q = np.asarray([r["q_excluded_mass"] for r in rows], dtype=float)
    both = np.asarray([r["mean_two_sided_excluded_mass"] for r in rows], dtype=float)
    return {
        "n_pairs": int(len(rows)),
        "mean_p_excluded_mass": float(np.mean(p)) if p.size else None,
        "mean_q_excluded_mass": float(np.mean(q)) if q.size else None,
        "mean_two_sided_excluded_mass": float(np.mean(both)) if both.size else None,
        "median_two_sided_excluded_mass": float(np.median(both)) if both.size else None,
        "max_two_sided_excluded_mass": float(np.max(both)) if both.size else None,
    }


def evaluate_raw_curve(raw_curve: list[tuple[list[dict], list[dict]]], threshold: int) -> dict:
    curve = []
    masses = []
    conditioning = []
    for k, (counts_p, counts_q) in zip(K_VALUES, raw_curve):
        value, mass = estimate_pair(counts_p, counts_q, threshold)
        curve.append(
            {
                "k": int(k),
                "D_k_median": float(value),
                "D_k_mean": float(value),
                "n_p": int(counts_p[0]["n"]) if counts_p else 0,
                "n_q": int(counts_q[0]["n"]) if counts_q else 0,
            }
        )
        masses.append({"k": int(k), **summarize_mass([mass])})
        conditioning.append(conditioning_summary_for_k(k, mass))
    fit = guarded_fit_growth(curve)
    return {
        "curve": curve,
        "fit": fit,
        "verdict": "LINEAR" if fit_passes(fit) else "NOT_LINEAR",
        "excluded_mass_by_k": masses,
        "conditioning_by_k": conditioning,
    }


def evaluate_real_curve(
    pair_rows: list[dict],
    merged: dict,
    threshold: int,
) -> tuple[dict, dict]:
    curve = []
    excluded_mass = []
    conditioning_by_k = []
    reconciliation = None

    for k in K_VALUES:
        counts = real_counts_fast(merged, k, fixed_long=False)
        eligible = [
            row
            for row in pair_rows
            if fast_service_n(counts[int(row["service_a"])]) >= MIN_SERVICE_FLOWS
            and fast_service_n(counts[int(row["service_b"])]) >= MIN_SERVICE_FLOWS
        ]
        values = []
        masses = []
        for row in eligible:
            a = int(row["service_a"])
            b = int(row["service_b"])
            value, mass = estimate_pair(counts[a], counts[b], threshold)
            values.append(value)
            masses.append(mass)
            if reconciliation is None and k == K_VALUES[0]:
                conditioned_zero_p, conditioned_zero_q, _ = condition_counts(counts[a], counts[b], 0)
                reference = d_chain_fast(counts[a], counts[b], SMOOTHING)
                wrapper_at_zero = d_chain_fast(conditioned_zero_p, conditioned_zero_q, SMOOTHING)
                reconciliation = {
                    "k": int(k),
                    "pair": pair_key(a, b),
                    "reference_path": "/root/eibo/x3_controls.py:d_chain_fast",
                    "reference_value": float(reference),
                    "wrapper_at_threshold_zero_value": float(wrapper_at_zero),
                    "absolute_difference": float(abs(reference - wrapper_at_zero)),
                }
        values_array = np.asarray(values, dtype=float)
        curve.append(
            {
                "k": int(k),
                "n_pairs": int(values_array.size),
                "D_k_median": float(np.median(values_array)) if values_array.size else None,
                "D_k_mean": float(np.mean(values_array)) if values_array.size else None,
            }
        )
        if masses:
            p = np.asarray([m["p_excluded_mass"] for m in masses], dtype=float)
            q = np.asarray([m["q_excluded_mass"] for m in masses], dtype=float)
            both = np.asarray([m["mean_two_sided_excluded_mass"] for m in masses], dtype=float)
            retained = [conditioning_summary_for_k(k, m) for m in masses]
            excluded_mass.append(
                {
                    "k": int(k),
                    "n_pairs": int(len(masses)),
                    "mean_p_excluded_mass": float(np.mean(p)),
                    "mean_q_excluded_mass": float(np.mean(q)),
                    "mean_two_sided_excluded_mass": float(np.mean(both)),
                    "median_two_sided_excluded_mass": float(np.median(both)),
                    "max_two_sided_excluded_mass": float(np.max(both)),
                }
            )
            conditioning_by_k.append(
                {
                    "k": int(k),
                    "n_pairs": int(len(retained)),
                    "mean_retained_contexts_total": float(
                        np.mean([row["retained_contexts_total"] for row in retained])
                    ),
                    "mean_new_position_retained_contexts": float(
                        np.mean([row["new_position_retained_contexts"] for row in retained])
                    ),
                    "mean_two_sided_retained_transition_mass": float(
                        np.mean([row["mean_two_sided_retained_transition_mass"] for row in retained])
                    ),
                }
            )
        else:
            excluded_mass.append(
                {
                    "k": int(k),
                    "n_pairs": 0,
                    "mean_p_excluded_mass": None,
                    "mean_q_excluded_mass": None,
                    "mean_two_sided_excluded_mass": None,
                    "median_two_sided_excluded_mass": None,
                    "max_two_sided_excluded_mass": None,
                }
            )
            conditioning_by_k.append(
                {
                    "k": int(k),
                    "n_pairs": 0,
                    "mean_retained_contexts_total": None,
                    "mean_new_position_retained_contexts": None,
                    "mean_two_sided_retained_transition_mass": None,
                }
            )

    fit = guarded_fit_growth(curve)
    return (
        {
            "curve": curve,
            "fit": fit,
            "verdict": "LINEAR" if fit_passes(fit) else "NOT_LINEAR",
            "criteria_pass": fit_passes(fit),
            "pair_denominator": "original variable population rule: service has >= 2000 flows eligible at k",
            "excluded_mass_by_k": excluded_mass,
            "conditioning_by_k": conditioning_by_k,
        },
        reconciliation or {"status": "not-computed"},
    )


def build_control_raw_curves(merged: dict) -> tuple[dict, dict]:
    rng = np.random.default_rng(SEED)
    bits_p = synthetic_bits(PLAIN_N, 30, 0.30, rng)
    bits_q = synthetic_bits(PLAIN_N, 30, 0.70, rng)
    codes_p = codes_from_bits(bits_p)
    codes_q = codes_from_bits(bits_q)
    lens_plain = np.full(PLAIN_N, 30, dtype=np.uint8)
    plain = []
    twin = []
    services = list(map(int, merged["services"]))
    twin_a, twin_b = services[0], services[1]
    for k in K_VALUES:
        plain.append(
            (
                service_counts_fast_from_codes(codes_p, lens_plain, k),
                service_counts_fast_from_codes(codes_q, lens_plain, k),
            )
        )
        rng_twin = np.random.default_rng(SEED + TWIN_SEED_OFFSET * k)
        twin.append(
            (
                synthetic_counts_on_real_prefix_occupancy(merged, twin_a, k, 0.30, rng_twin),
                synthetic_counts_on_real_prefix_occupancy(merged, twin_b, k, 0.70, rng_twin),
            )
        )
    return {"plain_iid_known_truth": plain}, {
        "twin_real_occupancy_known_truth": twin,
        "services_used": [twin_a, twin_b],
    }


def control_gate(merged: dict) -> tuple[dict, int | None]:
    plain_raw, twin_raw_meta = build_control_raw_curves(merged)
    twin_raw = {"twin_real_occupancy_known_truth": twin_raw_meta.pop("twin_real_occupancy_known_truth")}
    candidates = []
    selected = None
    selected_arms = None
    for threshold in THRESHOLD_CANDIDATES:
        plain_result = evaluate_raw_curve(plain_raw["plain_iid_known_truth"], threshold)
        twin_result = evaluate_raw_curve(twin_raw["twin_real_occupancy_known_truth"], threshold)
        both_pass = bool(fit_passes(plain_result["fit"]) and fit_passes(twin_result["fit"]))
        candidates.append(
            {
                "threshold": int(threshold),
                "plain_pass": bool(fit_passes(plain_result["fit"])),
                "twin_pass": bool(fit_passes(twin_result["fit"])),
                "plain_fit": plain_result["fit"],
                "twin_fit": twin_result["fit"],
                "plain_freeze_assertion": plain_result["fit"]["freeze_assertion"],
                "twin_freeze_assertion": twin_result["fit"]["freeze_assertion"],
            }
        )
        if selected is None and both_pass:
            selected = int(threshold)
            selected_arms = {
                "plain_iid_known_truth": plain_result,
                "twin_real_occupancy_known_truth": twin_result,
            }

    if selected is None:
        chosen_arms = {
            "plain_iid_known_truth": evaluate_raw_curve(plain_raw["plain_iid_known_truth"], MIN_CONTEXT_COUNT),
            "twin_real_occupancy_known_truth": evaluate_raw_curve(
                twin_raw["twin_real_occupancy_known_truth"], MIN_CONTEXT_COUNT
            ),
        }
    else:
        chosen_arms = selected_arms

    gate_pass = selected is not None
    gate = {
        "preregistered_criteria": CRITERIA,
        "threshold_selection_rule": (
            "Evaluate thresholds [5, 10, 20, 50, 100] on the two known-truth arms "
            "only, in ascending order; select the smallest threshold for which "
            "both arms satisfy all three fixed linearity criteria. Threshold 5 "
            "is the minimum because the diagnosed sparse-context tail is defined "
            "by counts below 5. No real-data value participates in selection."
        ),
        "analytic_truth": {
            "p": 0.30,
            "q": 0.70,
            "natural_log_symmetric_bernoulli_kl": True,
            "per_position_truth": 0.3389191441548814,
            "D_k_truth": "k * 0.3389191441548814",
        },
        "control_seed": SEED,
        "plain_sample_size_per_law": PLAIN_N,
        "twin_definition": (
            "Count-level synthetic draws use the exact cached real prefix "
            "occupancy for the first two services and draw each outgoing bit "
            "count from Binomial(n_context, p) or Binomial(n_context, q)."
        ),
        "twin_services_used": twin_raw_meta["services_used"],
        "candidate_thresholds": candidates,
        "selected_threshold": selected,
        "plain_iid_known_truth": chosen_arms["plain_iid_known_truth"],
        "twin_real_occupancy_known_truth": chosen_arms["twin_real_occupancy_known_truth"],
        "both_arms_pass": gate_pass,
    }
    return gate, selected


def make_base_payload(cache: dict, original_sha: str, gate: dict, selected: int | None) -> dict:
    if selected is None:
        excluded = {
            "definition": (
                "For each known-truth arm, mass excluded is the transition "
                "mass outside the shared context set with n_P >= T and n_Q >= T, "
                "aggregated over all positions and reported separately for P and Q."
            ),
            "known_truth_plain_iid_by_k": gate["plain_iid_known_truth"]["excluded_mass_by_k"],
            "known_truth_twin_real_occupancy_by_k": gate["twin_real_occupancy_known_truth"][
                "excluded_mass_by_k"
            ],
            "real_data": {"status": "NOT_COMPUTED_BECAUSE_GATE_FAILED"},
        }
    else:
        excluded = {
            "definition": (
                "For each arm and k, mass excluded is the transition mass "
                "outside the shared context set with n_P >= T and n_Q >= T, "
                "aggregated over all positions and reported separately for P and Q."
            ),
            "known_truth_plain_iid_by_k": gate["plain_iid_known_truth"]["excluded_mass_by_k"],
            "known_truth_twin_real_occupancy_by_k": gate["twin_real_occupancy_known_truth"][
                "excluded_mass_by_k"
            ],
            "real_data_by_k": [],
        }
    return {
        "gate": gate,
        "estimator_sentence": ESTIMATOR_SENTENCE,
        "excluded_mass": excluded,
        "gate_outcome": {
            "status": "PASS" if selected is not None else "FAIL",
            "selected_threshold": selected,
            "deciding_numbers": {
                "plain_iid_known_truth_fit": gate["plain_iid_known_truth"]["fit"],
                "twin_real_occupancy_known_truth_fit": gate["twin_real_occupancy_known_truth"]["fit"],
            },
        },
        "if_failed": (
            {
                "statement": (
                    "FAIL: the known-truth gate did not recover LINEAR in both "
                    "arms under any preregistered threshold. Real data was not touched."
                ),
                "numbers": {
                    "plain_iid_known_truth_fit": gate["plain_iid_known_truth"]["fit"],
                    "twin_real_occupancy_known_truth_fit": gate["twin_real_occupancy_known_truth"]["fit"],
                },
            }
            if selected is None
            else {"statement": "Not applicable: the known-truth gate passed."}
        ),
        "verification": {
            "cache": cache,
            "original_artifact_path": str(ORIGINAL_ARTIFACT),
            "original_artifact_sha256_before": original_sha,
            "original_artifact_sha256_after": None,
            "original_artifact_unchanged": None,
            "runner_path": str(RUNNER_PATH),
            "runner_sha256": sha256_file(RUNNER_PATH),
        },
    }


def main() -> int:
    cache = cache_inventory()
    print("CACHE_STATUS", json.dumps(cache, sort_keys=True))
    if not cache["present"]:
        print(
            "ERROR cached state incomplete at /dev/shm/eibo_x3_chain_rule; "
            "refusing to rescan the H5"
        )
        return 2

    original_sha_before = sha256_file(ORIGINAL_ARTIFACT)
    preregistration = {
        "variant": "B_SUPPORT_CONDITIONING",
        "threshold_minimum": MIN_CONTEXT_COUNT,
        "threshold_candidates": list(THRESHOLD_CANDIDATES),
        "smoothing": SMOOTHING,
        "k_values": K_VALUES,
        "criteria": CRITERIA,
        "real_data_allowed_only_after_both_control_arms_pass": True,
        "estimated_real_work_if_gate_passes": {
            "pair_evaluations": len(K_VALUES) * 990,
            "h5_rescan": False,
            "execution": "CPU-only from cached merged.pkl/results.pkl",
        },
    }
    print("PREREGISTRATION", json.dumps(preregistration, sort_keys=True))

    merged = load_merged()
    gate, selected = control_gate(merged)
    payload = make_base_payload(cache, original_sha_before, gate, selected)
    print(
        "KNOWN_TRUTH_GATE",
        json.dumps(
            {
                "status": payload["gate_outcome"]["status"],
                "selected_threshold": selected,
                "plain": gate["plain_iid_known_truth"]["fit"],
                "twin": gate["twin_real_occupancy_known_truth"]["fit"],
            },
            sort_keys=True,
        ),
    )
    atomic_write_json(OUTPUT, payload)

    if selected is None:
        original_sha_after = sha256_file(ORIGINAL_ARTIFACT)
        payload["verification"]["original_artifact_sha256_after"] = original_sha_after
        payload["verification"]["original_artifact_unchanged"] = original_sha_before == original_sha_after
        payload["verification"]["artifact_path"] = str(OUTPUT)
        atomic_write_json(OUTPUT, payload)
        print(
            "FINAL",
            json.dumps(
                {
                    "gate_outcome": "FAIL",
                    "real_data_touched": False,
                    "excluded_mass": payload["excluded_mass"],
                    "original_artifact_unchanged": payload["verification"]["original_artifact_unchanged"],
                    "artifact_path": str(OUTPUT),
                    "artifact_sha256": sha256_file(OUTPUT),
                    "artifact_bytes": OUTPUT.stat().st_size,
                    "runner_path": str(RUNNER_PATH),
                    "runner_sha256": sha256_file(RUNNER_PATH),
                },
                sort_keys=True,
            ),
        )
        return 0

    pair_rows = json.loads(PAIR_PATH.read_text(encoding="utf-8"))["rows"]
    real_result, reconciliation = evaluate_real_curve(pair_rows, merged, selected)
    payload["excluded_mass"]["real_data_by_k"] = real_result["excluded_mass_by_k"]
    payload["real_data"] = {
        "growth_result": real_result,
        "reference_reconciliation": reconciliation,
        "data_touched_only_after_gate": True,
    }
    original_sha_after = sha256_file(ORIGINAL_ARTIFACT)
    payload["verification"]["original_artifact_sha256_after"] = original_sha_after
    payload["verification"]["original_artifact_unchanged"] = original_sha_before == original_sha_after
    payload["verification"]["artifact_path"] = str(OUTPUT)
    atomic_write_json(OUTPUT, payload)
    print(
        "REAL_DATA_RESULT",
        json.dumps(
            {
                "selected_threshold": selected,
                "growth_result": real_result,
                "reference_reconciliation": reconciliation,
            },
            sort_keys=True,
        ),
    )
    print(
        "FINAL",
        json.dumps(
            {
                "gate_outcome": "PASS",
                "real_data_touched": True,
                "real_verdict": real_result["verdict"],
                "excluded_mass": real_result["excluded_mass_by_k"],
                "original_artifact_unchanged": payload["verification"]["original_artifact_unchanged"],
                "artifact_path": str(OUTPUT),
                "artifact_sha256": sha256_file(OUTPUT),
                "artifact_bytes": OUTPUT.stat().st_size,
                "runner_path": str(RUNNER_PATH),
                "runner_sha256": sha256_file(RUNNER_PATH),
            },
            sort_keys=True,
        ),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR {type(exc).__name__}: {exc}")
        raise
