#!/usr/bin/env python3
"""Validate the X3 vote and parametric-curve index conventions on controls.

The checked runners are imported only for their production observations.  The
vote criterion and the known-order curve expectation are implemented again in
this file so agreement is not a self-reproduction by the checked code.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Callable

import numpy as np

from x3_parametric_growth import marginal_and_entropy_curve
from x3_variant_c_nested_lr import fit_nested_models


PROJECT = Path("/root/eibo")
ARTIFACT = PROJECT / "artifacts" / "x3_axis_validation.json"
RUNNER = PROJECT / "x3_axis_validation.py"
HORIZON = 30
PREFIXES = tuple(range(2, HORIZON + 1))
ITEMS = 8
FLOWS = 3000
MC_REPLICATES = 8
SEED = 20260914
TIMESTAMP = "2026-09-14T07:19:01Z"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entropy(probabilities: np.ndarray) -> float:
    values = np.asarray(probabilities, dtype=float)
    values = values[values > 0.0]
    return float(-np.sum(values * np.log(values)))


def log_term(count: int, total: int) -> float:
    if count == 0:
        return 0.0
    return float(count) * math.log(float(count) / float(total))


def independent_vote(bits: np.ndarray, k: int) -> tuple[str, float]:
    """Separately written reproduction of the production BIC sign rule."""
    prefix = np.asarray(bits[:, :k], dtype=np.uint8)
    n_flows = int(prefix.shape[0])
    n_obs = int(prefix.size)

    ones = int(prefix.sum())
    iid_ll = log_term(ones, n_obs) + log_term(n_obs - ones, n_obs)

    first_one = int(prefix[:, 0].sum())
    first_zero = n_flows - first_one
    previous = prefix[:, :-1]
    following = prefix[:, 1:]
    n00 = int(np.sum((previous == 0) & (following == 0)))
    n01 = int(np.sum((previous == 0) & (following == 1)))
    n10 = int(np.sum((previous == 1) & (following == 0)))
    n11 = int(np.sum((previous == 1) & (following == 1)))
    markov_ll = (
        log_term(first_one, n_flows)
        + log_term(first_zero, n_flows)
        + log_term(n01, n00 + n01)
        + log_term(n00, n00 + n01)
        + log_term(n11, n10 + n11)
        + log_term(n10, n10 + n11)
    )

    iid_bic = -2.0 * iid_ll + math.log(n_obs)
    markov_bic = -2.0 * markov_ll + 3.0 * math.log(n_obs)
    delta = iid_bic - markov_bic
    if delta > 0.0:
        winner = "MARKOV"
    elif delta < 0.0:
        winner = "IID"
    else:
        winner = "TIE"
    return winner, float(delta)


def production_report(items: list[tuple[str, np.ndarray]]) -> dict:
    rows_by_k = {}
    for k in PREFIXES:
        rows = []
        for item, bits in items:
            row = fit_nested_models(bits, k)
            rows.append({"item": item, "winner": row["winner"], "delta": row["delta_bic_iid_minus_markov"]})
        rows_by_k[str(k)] = rows
    return rows_by_k


def independent_report(items: list[tuple[str, np.ndarray]]) -> dict:
    rows_by_k = {}
    for k in PREFIXES:
        rows = []
        for item, bits in items:
            winner, delta = independent_vote(bits, k)
            rows.append({"item": item, "winner": winner, "delta": delta})
        rows_by_k[str(k)] = rows
    return rows_by_k


def summarize(rows_by_k: dict[str, list[dict]]) -> dict:
    result = {}
    for key, rows in rows_by_k.items():
        counts = {name: sum(row["winner"] == name for row in rows) for name in ("MARKOV", "IID", "TIE")}
        result[key] = {
            "n_items": len(rows),
            "markov": counts["MARKOV"],
            "iid": counts["IID"],
            "tie": counts["TIE"],
            "delta_min": float(min(row["delta"] for row in rows)),
            "delta_max": float(max(row["delta"] for row in rows)),
        }
    return result


def make_iid(rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    probability = 0.37
    return [
        (f"S1_iid_{item:02d}", (rng.random((FLOWS, HORIZON)) < probability).astype(np.uint8))
        for item in range(ITEMS)
    ]


def make_markov(rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    p01, p11 = 0.02, 0.98
    stationary_one = p01 / (1.0 - p11 + p01)
    items = []
    for item in range(ITEMS):
        bits = np.empty((FLOWS, HORIZON), dtype=np.uint8)
        bits[:, 0] = (rng.random(FLOWS) < stationary_one).astype(np.uint8)
        for position in range(1, HORIZON):
            probability = np.where(bits[:, position - 1] == 1, p11, p01)
            bits[:, position] = (rng.random(FLOWS) < probability).astype(np.uint8)
        items.append((f"S2_markov_{item:02d}", bits))
    return items


def make_heterogeneous_iid(rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    rate_support = np.asarray([0.10, 0.90], dtype=float)
    items = []
    for item in range(ITEMS):
        rates = rng.choice(rate_support, size=FLOWS, replace=True)
        bits = (rng.random((FLOWS, HORIZON)) < rates[:, None]).astype(np.uint8)
        items.append((f"S3_heterogeneous_iid_{item:02d}", bits))
    return items


def make_dependency_death(rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    """Three dependent transitions, then an i.i.d. Bernoulli(.5) suffix."""
    bits = np.empty((FLOWS, HORIZON), dtype=np.uint8)
    bits[:, 0] = (rng.random(FLOWS) < 0.5).astype(np.uint8)
    # Weak dependence makes the BIC sign change at the first all-i.i.d. prefix.
    p01, p11 = 0.48, 0.52
    for position in range(1, 4):
        probability = np.where(bits[:, position - 1] == 1, p11, p01)
        bits[:, position] = (rng.random(FLOWS) < probability).astype(np.uint8)
    bits[:, 4:] = (rng.random((FLOWS, HORIZON - 4)) < 0.5).astype(np.uint8)
    return [("axis_dependence_first_3_transitions", bits)]


def monte_carlo_expectation(
    builder: Callable[[np.random.Generator], list[tuple[str, np.ndarray]]],
    seed: int,
) -> dict:
    replicate_summaries = []
    for replicate in range(MC_REPLICATES):
        items = builder(np.random.default_rng(seed + replicate))
        replicate_summaries.append(summarize(independent_report(items)))

    expectation = {}
    for k in PREFIXES:
        key = str(k)
        expectation[key] = {}
        for winner in ("MARKOV", "IID", "TIE"):
            values = np.asarray([summary[key][winner.lower()] for summary in replicate_summaries], dtype=float)
            expectation[key][winner.lower()] = {
                "mean": float(np.mean(values)),
                "sd": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
                "replicates": [int(value) for value in values],
            }
    return {"replicates": MC_REPLICATES, "expectation": expectation}


def independent_curve(model: dict, max_length: int) -> list[dict]:
    """Independent chain-rule calculation for a binary order-2 model."""
    order = int(model["order"])
    if order != 2:
        raise ValueError("this independent check is intentionally for order 2")
    initial = np.asarray(model["initial"], dtype=float)
    transition = np.asarray(model["transition"], dtype=float)

    state = initial.copy()
    q = [float(state[2] + state[3]), float(state[1] + state[3])]
    joint_entropy = entropy(state)
    curves = [{"k": 1, "D_k": 0.0}]
    h_x1 = -(q[0] * math.log(q[0]) if q[0] else 0.0) - ((1 - q[0]) * math.log(1 - q[0]) if q[0] < 1 else 0.0)
    h_x2 = -(q[1] * math.log(q[1]) if q[1] else 0.0) - ((1 - q[1]) * math.log(1 - q[1]) if q[1] < 1 else 0.0)
    curves.append({"k": 2, "D_k": float(h_x1 + h_x2 - joint_entropy)})

    for k in range(3, max_length + 1):
        conditional_entropy = float(sum(state[c] * entropy(transition[c]) for c in range(4)))
        joint_entropy += conditional_entropy
        next_state = np.zeros(4, dtype=float)
        for context in range(4):
            for bit in (0, 1):
                next_context = ((context & 1) << 1) | bit
                next_state[next_context] += state[context] * transition[context, bit]
        state = next_state
        q.append(float(state[1] + state[3]))
        marginal_entropy = 0.0
        for probability in q:
            marginal_entropy += -(probability * math.log(probability) if probability else 0.0)
            marginal_entropy += -((1 - probability) * math.log(1 - probability) if probability < 1 else 0.0)
        curves.append({"k": k, "D_k": float(marginal_entropy - joint_entropy)})
    return curves


def curve_check() -> dict:
    transition = np.asarray([[0.08, 0.92], [0.72, 0.28], [0.22, 0.78], [0.90, 0.10]], dtype=float)
    model = {"order": 2, "initial": np.full(4, 0.25, dtype=float), "transition": transition}
    observed = marginal_and_entropy_curve(model, HORIZON)
    expected = independent_curve(model, HORIZON)
    rows = []
    for got, want in zip(observed, expected):
        residual = float(got["D_k"] - want["D_k"])
        rows.append({
            "k_label": int(got["k"]),
            "analytic_k": int(want["k"]),
            "observed_D_k": float(got["D_k"]),
            "analytic_D_k": float(want["D_k"]),
            "residual": residual,
            "same_k": int(got["k"]) == int(want["k"]),
        })
    max_abs = max(abs(row["residual"]) for row in rows)
    max_abs_route = max(abs(row["residual"]) for row in rows[4:])
    return {
        "known_order": 2,
        "initial": [0.25, 0.25, 0.25, 0.25],
        "transition_probability_one_by_context_00_01_10_11": [0.08, 0.72, 0.22, 0.90],
        "expectation_method": "separately written order-2 chain-rule/state-propagation expression",
        "per_k": rows,
        "max_abs_residual": float(max_abs),
        "max_abs_residual_route_k5_to_k30": float(max_abs_route),
        # The parametric route consumes curve_rows, which deliberately starts at k=5.
        "axis_pass": bool(all(row["same_k"] for row in rows[4:]) and max_abs_route <= 1e-12),
        "checked_route_range": "k=5..30 (the parametric runner passes curve_rows through k>=5)",
        "boundary_k1_to_k4_residuals_reported_but_not_in_route": True,
        "route_repaired": False,
    }


def case_report(name: str, items: list[tuple[str, np.ndarray]], builder: Callable, seed: int) -> dict:
    observed_rows = production_report(items)
    independent_rows = independent_report(items)
    mismatches = []
    for k in PREFIXES:
        key = str(k)
        for observed, independent in zip(observed_rows[key], independent_rows[key]):
            if observed["winner"] != independent["winner"] or not math.isclose(observed["delta"], independent["delta"], rel_tol=0.0, abs_tol=1e-10):
                mismatches.append({"k": k, "item": observed["item"], "production": observed, "independent": independent})
    return {
        "name": name,
        "source_definition": {
            "items": ITEMS,
            "flows_per_item": FLOWS,
            "sequence_length": HORIZON,
        },
        "observed_vote_counts_by_k": summarize(observed_rows),
        "independent_reproduction_counts_by_k": summarize(independent_rows),
        "production_vs_independent_mismatch_count": len(mismatches),
        "production_vs_independent_mismatches": mismatches,
        "independent_expected_vote_counts": monte_carlo_expectation(builder, seed),
    }


def axis_report(items: list[tuple[str, np.ndarray]]) -> dict:
    observed = production_report(items)
    sequence = [observed[str(k)][0]["winner"] for k in PREFIXES]
    observed_transition = None
    for index, winner in enumerate(sequence[1:], start=3):
        if sequence[index - 3] == "MARKOV" and all(value == "IID" for value in sequence[index - 2:]):
            observed_transition = index
            break
    return {
        "built_dependence_transitions": "bits 0->1, 1->2, and 2->3 (three transitions); bits 4..29 sampled i.i.d.",
        "first_iid_suffix_transition": "bits 3->4, which first appears in prefix k=5",
        "observed_winner_by_k": {str(k): observed[str(k)][0]["winner"] for k in PREFIXES},
        "observed_first_stable_iid_after_markov_k": observed_transition,
        "axis_pass": observed_transition == 5,
    }


def main() -> int:
    master = np.random.default_rng(SEED)
    s1 = make_iid(master)
    s2 = make_markov(master)
    s3 = make_heterogeneous_iid(master)
    axis_items = make_dependency_death(master)

    payload = {
        "artifact": str(ARTIFACT),
        "validation_timestamp": TIMESTAMP,
        "vote_construction_code_quote": (
            "prefix = np.asarray(bits[:, :prefix_length], dtype=np.uint8)\n"
            "iid_bic = -2.0 * iid_log_likelihood + iid_parameters * math.log(n_observations)\n"
            "markov_bic = -2.0 * markov_log_likelihood + markov_parameters * math.log(n_observations)\n"
            "delta_bic = iid_bic - markov_bic\n"
            "if delta_bic > 0.0: winner = \\\"MARKOV\\\"\n"
            "elif delta_bic < 0.0: winner = \\\"IID\\\"\n"
            "else: winner = \\\"TIE\\\""
        ),
        "vote_scope": {"prefix_lengths": list(PREFIXES), "production_runner": "/root/eibo/x3_control_heterogeneous_iid.py", "fit_entry_point": "/root/eibo/x3_variant_c_nested_lr.py:fit_nested_models"},
        "cases": {
            "S1_pure_iid": case_report("S1_pure_iid", s1, make_iid, SEED + 1000),
            "S2_dependent_markov": case_report("S2_dependent_markov", s2, make_markov, SEED + 2000),
            "S3_heterogeneous_iid": case_report("S3_heterogeneous_iid", s3, make_heterogeneous_iid, SEED + 3000),
        },
        "axis_test": axis_report(axis_items),
        "parametric_curve_check": curve_check(),
        "checked_files": [
            "/root/eibo/x3_control_heterogeneous_iid.py",
            "/root/eibo/x3_parametric_growth.py",
            "/root/eibo/x3_controls.py",
        ],
        "runner_sha256": sha256_file(RUNNER),
    }

    payload["artifact_status"] = {
        "vote_artifact": "verified-correct" if all(case["production_vs_independent_mismatch_count"] == 0 for case in payload["cases"].values()) and payload["axis_test"]["axis_pass"] else "failed",
        # Axis alignment is NOT the same claim as conclusion validity: the parametric route's
        # LINEAR verdict is constructively forced (D057) and stays non-diagnostic however well
        # its k axis is labelled. Both facts must travel together, or a bare "verified-correct"
        # here reads as D057 having been overturned.
        "parametric_artifact": (
            "axis-verified; conclusion remains NON-DIAGNOSTIC per D057" if payload["parametric_curve_check"]["axis_pass"]
            else "failed"
        ),
        "parametric_artifact_note": (
            "The k axis is correctly labelled (what this check tested). That says nothing about "
            "whether the route's LINEAR verdict is informative: per D057 the verdict is a "
            "mathematical tautology -- D_k is affine by construction for any fitted order >= 1 "
            "and identically 0 for order 0 -- so the route cannot distinguish the hypotheses. "
            "Axis correct != conclusion usable."
        ),
        "self_reference_note": (
            "The embedded artifact_size_bytes / artifact_sha256 are a SNAPSHOT TAKEN BEFORE this "
            "field was written, so they intentionally do not equal this file's own bytes. Verify "
            "against the externally reported hash instead."
        ),
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    temporary = ARTIFACT.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(temporary, ARTIFACT)
    payload["artifact_size_bytes"] = ARTIFACT.stat().st_size
    payload["artifact_sha256"] = sha256_file(ARTIFACT)
    temporary = ARTIFACT.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(temporary, ARTIFACT)

    print(json.dumps({
        "artifact": str(ARTIFACT),
        "artifact_size_bytes": ARTIFACT.stat().st_size,
        "artifact_sha256": sha256_file(ARTIFACT),
        "runner": str(RUNNER),
        "runner_size_bytes": RUNNER.stat().st_size,
        "runner_sha256": sha256_file(RUNNER),
        "artifact_status": payload["artifact_status"],
        "axis": payload["axis_test"],
        "curve_max_abs_residual": payload["parametric_curve_check"]["max_abs_residual"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
