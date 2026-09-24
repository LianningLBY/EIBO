#!/usr/bin/env python3
"""D181: joint-coverage reaggregation with the Eq(9) m-free upper bound.

This runner consumes only existing JSON ledgers. It does not load the corpus and
does not edit manuscript files.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median
from typing import Any

from scipy.optimize import linprog


PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOWER_FULL_N_PATH = PROJECT_ROOT / "artifacts" / "_project" / "data" / "q1_lower_side_full_n.json"
CANONICAL_LOWER_PATH = PROJECT_ROOT / "artifacts" / "_project" / "data" / "q1_eps_lo_symbol_map.json"
OUTPUT_PATH = PROJECT_ROOT / "artifacts" / "d181_joint_coverage_reaggregation.json"
SCRIPT_PATH = PROJECT_ROOT / "artifacts" / "_project" / "intermediate" / "d181_joint_coverage_reaggregation.py"

OVERALL_ALPHA = 0.05
EXPECTED_PAIR_COUNT = 990
REFERENCE_UNIFORM_M46 = 0.186
REFERENCE_LP_M46 = 0.363
REFERENCE_UNIFORM_M46_UNROUNDED = 0.18577
REFERENCE_LP_M46_UNROUNDED = 0.36307


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def quantiles(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)

    def q(prob: float) -> float:
        if not ordered:
            raise ValueError("cannot compute quantiles of an empty list")
        pos = prob * (len(ordered) - 1)
        lo = math.floor(pos)
        hi = math.ceil(pos)
        if lo == hi:
            return float(ordered[lo])
        frac = pos - lo
        return float(ordered[lo] * (1.0 - frac) + ordered[hi] * frac)

    return {
        "min": float(ordered[0]),
        "q05": q(0.05),
        "q25": q(0.25),
        "median": q(0.50),
        "q75": q(0.75),
        "q95": q(0.95),
        "max": float(ordered[-1]),
    }


def service_pair(row: dict[str, Any]) -> tuple[int, int]:
    return int(row["service_a"]), int(row["service_b"])


def canonical_upper(row: dict[str, Any]) -> float:
    return min(1.0, max(0.0, float(row["upper_recomputed"]["eps_hi"])))


def mfree_upper(row: dict[str, Any], alpha_pair: float) -> dict[str, float]:
    n_a = int(row["n_a"])
    n_b = int(row["n_b"])
    if n_a <= 0 or n_b <= 0:
        raise ValueError(f"non-positive sample size for pair {service_pair(row)}")
    upper = row["upper_recomputed"]
    tv_hat = float(upper["tv_hat"])
    radius_a = math.sqrt(math.log(2.0 / alpha_pair) / (2.0 * n_a))
    radius_b = math.sqrt(math.log(2.0 / alpha_pair) / (2.0 * n_b))
    eps_hi = min(1.0, max(0.0, tv_hat + radius_a + radius_b))
    return {
        "tv_hat": tv_hat,
        "n_a": n_a,
        "n_b": n_b,
        "radius_a_mfree": radius_a,
        "radius_b_mfree": radius_b,
        "eps_hi_mfree": eps_hi,
    }


def uniform_floors(pair_rows: list[dict[str, Any]], eps_hi_key: str) -> dict[str, float]:
    services = sorted({int(r["service_a"]) for r in pair_rows} | {int(r["service_b"]) for r in pair_rows})
    known_count = len(services)
    open_set_class_count = known_count + 1
    s_known = sum(1.0 - min(1.0, max(0.0, float(r[eps_hi_key]))) for r in pair_rows)
    return {
        "S_known": float(s_known),
        "known_service_count_K": known_count,
        "open_set_class_count_M": open_set_class_count,
        "floor_M45_known_closed_set": float(s_known / (known_count * (known_count - 1))),
        "floor_M46_open_set": float(s_known / (open_set_class_count * (open_set_class_count - 1))),
    }


def lp_floor(pair_rows: list[dict[str, Any]], eps_hi_key: str) -> dict[str, Any]:
    services = sorted({int(r["service_a"]) for r in pair_rows} | {int(r["service_b"]) for r in pair_rows})
    known_count = len(services)
    open_set_class_count = known_count + 1
    costs = [1.0 - min(1.0, max(0.0, float(r[eps_hi_key]))) for r in pair_rows]
    constraints = [
        [
            1.0 if int(row["service_a"]) == service or int(row["service_b"]) == service else 0.0
            for row in pair_rows
        ]
        for service in services
    ]
    result = linprog(
        c=[-value for value in costs],
        A_eq=constraints,
        b_eq=[1.0] * known_count,
        bounds=(0.0, None),
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"LP solve failed: {result.message}")
    objective = float(-result.fun)
    weights = [float(x) for x in result.x]
    positive_edges = [
        {
            "service_a": int(row["service_a"]),
            "service_b": int(row["service_b"]),
            "weight": weights[index],
            "one_minus_eps_hi": costs[index],
        }
        for index, row in enumerate(pair_rows)
        if weights[index] > 1e-10
    ]
    return {
        "solver": "scipy.optimize.linprog(method='highs')",
        "form": (
            "Equivalent undirected LP for ordered-pair weights: maximize sum_e x_e*(1-eps_hi_e) "
            "subject to each known service having incident weight sum 1 and x_e >= 0; "
            "the open-set reported floor divides by M=K+1."
        ),
        "known_service_count_K": known_count,
        "open_set_class_count_M": open_set_class_count,
        "objective": objective,
        "floor_M46_open_set": float(objective / open_set_class_count),
        "floor_M45_known_closed_set": float(objective / known_count),
        "positive_edge_count": len(positive_edges),
        "positive_edges": positive_edges,
    }


def per_service_diagnostics(pair_rows: list[dict[str, Any]], eps_hi_key: str) -> dict[str, Any]:
    services = sorted({int(r["service_a"]) for r in pair_rows} | {int(r["service_b"]) for r in pair_rows})
    by_service: dict[int, list[float]] = {service: [] for service in services}
    for row in pair_rows:
        contribution = max(0.0, (1.0 - min(1.0, max(0.0, float(row[eps_hi_key])))) / 2.0)
        by_service[int(row["service_a"])].append(contribution)
        by_service[int(row["service_b"])].append(contribution)
    service_rows = []
    for service in services:
        values = by_service[service]
        service_rows.append(
            {
                "service": service,
                "degree": len(values),
                "min_pair_error_floor": float(min(values)),
                "mean_pair_error_floor": float(mean(values)),
                "max_pair_error_floor": float(max(values)),
            }
        )
    return {
        "note": (
            "Diagnostic only. The paper's 0.186 aggregation is the complete-graph uniform sum "
            "S/[M(M-1)], not the average of per-service minima."
        ),
        "average_of_min_pair_error_floor_by_service": float(mean(r["min_pair_error_floor"] for r in service_rows)),
        "average_of_mean_pair_error_floor_by_service": float(mean(r["mean_pair_error_floor"] for r in service_rows)),
        "average_of_max_pair_error_floor_by_service": float(mean(r["max_pair_error_floor"] for r in service_rows)),
        "rows": service_rows,
    }


def compare(value: float, reference: float) -> dict[str, float]:
    return {
        "new_value": float(value),
        "reference_value": float(reference),
        "difference": float(value - reference),
        "ratio_new_over_reference": float(value / reference),
    }


def main() -> None:
    full_n = load_json(LOWER_FULL_N_PATH)
    canonical = load_json(CANONICAL_LOWER_PATH)
    full_rows = full_n.get("rows")
    canonical_rows = canonical.get("rows")
    if not isinstance(full_rows, list) or not isinstance(canonical_rows, list):
        raise TypeError("both input ledgers must contain a rows array")
    if len(full_rows) != EXPECTED_PAIR_COUNT or len(canonical_rows) != EXPECTED_PAIR_COUNT:
        raise ValueError(f"expected 990 rows in both inputs, got {len(full_rows)} and {len(canonical_rows)}")

    canonical_by_pair = {service_pair(row): row for row in canonical_rows}
    if len(canonical_by_pair) != EXPECTED_PAIR_COUNT:
        raise ValueError("canonical lower ledger does not contain 990 unique service pairs")

    alpha_pair = OVERALL_ALPHA / EXPECTED_PAIR_COUNT
    output_rows: list[dict[str, Any]] = []
    for row in full_rows:
        pair = service_pair(row)
        if pair not in canonical_by_pair:
            raise KeyError(f"missing canonical eps_lo for pair {pair}")
        upper = mfree_upper(row, alpha_pair)
        eps_lo = float(canonical_by_pair[pair]["eps_lo"])
        eps_hi_mfree = upper["eps_hi_mfree"]
        output_rows.append(
            {
                "service_a": pair[0],
                "service_b": pair[1],
                "n_a": upper["n_a"],
                "n_b": upper["n_b"],
                "tv_hat": upper["tv_hat"],
                "alpha_pair": alpha_pair,
                "radius_a_mfree": upper["radius_a_mfree"],
                "radius_b_mfree": upper["radius_b_mfree"],
                "eps_lo": eps_lo,
                "eps_hi_mfree": eps_hi_mfree,
                "eps_lo_le_eps_hi_mfree": bool(eps_lo <= eps_hi_mfree + 1e-12),
                "pair_error_floor": float(max(0.0, (1.0 - eps_hi_mfree) / 2.0)),
                "eps_hi_mfree_lt_1": bool(eps_hi_mfree < 1.0),
                "eps_hi_mfree_lt_0_5": bool(eps_hi_mfree < 0.5),
                "canonical_eps_hi": canonical_upper(row),
            }
        )

    pair_floors = [float(row["pair_error_floor"]) for row in output_rows]
    invariant_violations = [
        {
            "service_a": row["service_a"],
            "service_b": row["service_b"],
            "eps_lo": row["eps_lo"],
            "eps_hi_mfree": row["eps_hi_mfree"],
        }
        for row in output_rows
        if not row["eps_lo_le_eps_hi_mfree"]
    ]

    control_rows = [
        {
            "service_a": int(row["service_a"]),
            "service_b": int(row["service_b"]),
            "canonical_eps_hi": canonical_upper(row),
        }
        for row in full_rows
    ]
    controls = {
        "purpose": "Reproduce known submitted values from the existing canonical eps_hi before reporting the changed Eq(9) radius.",
        "canonical_uniform": uniform_floors(control_rows, "canonical_eps_hi"),
        "canonical_lp": lp_floor(control_rows, "canonical_eps_hi"),
    }
    controls["canonical_uniform"]["comparison_to_0_18577"] = compare(
        controls["canonical_uniform"]["floor_M46_open_set"], REFERENCE_UNIFORM_M46_UNROUNDED
    )
    controls["canonical_lp"]["comparison_to_0_36307"] = compare(
        controls["canonical_lp"]["floor_M46_open_set"], REFERENCE_LP_M46_UNROUNDED
    )

    uniform = uniform_floors(output_rows, "eps_hi_mfree")
    lp = lp_floor(output_rows, "eps_hi_mfree")
    result = {
        "artifact": "d181_joint_coverage_reaggregation",
        "created_at_utc": "2026-09-22T03:21:27+00:00",
        "status": "COMPLETE",
        "source_h5_read": False,
        "input_files": {
            str(LOWER_FULL_N_PATH.relative_to(PROJECT_ROOT)): {
                "sha256": sha256_file(LOWER_FULL_N_PATH),
                "row_count": len(full_rows),
                "first_row_keys": sorted(full_rows[0].keys()),
                "tv_hat_location": "row['upper_recomputed']['tv_hat']",
                "n_location": "row['n_a'], row['n_b']",
            },
            str(CANONICAL_LOWER_PATH.relative_to(PROJECT_ROOT)): {
                "sha256": sha256_file(CANONICAL_LOWER_PATH),
                "row_count": len(canonical_rows),
                "first_row_keys": sorted(canonical_rows[0].keys()),
                "eps_lo_location": "row['eps_lo']",
            },
        },
        "guarantee_statement": {
            "upper_side": (
                "Finite-sample m-free Hoeffding upper bound, alpha_pair=0.05/990; "
                "Bonferroni gives simultaneous upper-side coverage at least 0.95 over 990 pairs."
            ),
            "lower_side": (
                "eps_lo is copied from q1_eps_lo_symbol_map.json and retains that ledger's "
                "classifier-based nominal/asymptotic lower-side status; it is not upgraded by this run."
            ),
            "aggregate": (
                "The uniform and LP aggregates are high-probability lower bounds to the extent they use "
                "the simultaneous upper-side event; lower-side values are included only as bracket endpoints "
                "and invariant checks, not as inputs to the error-floor aggregation."
            ),
        },
        "parameters": {
            "overall_alpha": OVERALL_ALPHA,
            "pair_count_for_union_bound": EXPECTED_PAIR_COUNT,
            "alpha_pair": alpha_pair,
            "eq9_eps_hi_mfree": "min(1, tv_hat + sqrt(ln(2/alpha_pair)/(2*n_a)) + sqrt(ln(2/alpha_pair)/(2*n_b)))",
            "paper_uniform_aggregation": "S_known/[M(M-1)] with S_known=sum_{i<j}(1-eps_hi_ij), K=45, M=46",
        },
        "controls": controls,
        "summary": {
            "row_count": len(output_rows),
            "known_service_count_K": uniform["known_service_count_K"],
            "open_set_class_count_M": uniform["open_set_class_count_M"],
            "eps_hi_mfree_lt_1_count": sum(1 for row in output_rows if row["eps_hi_mfree_lt_1"]),
            "eps_hi_mfree_ge_1_count": sum(1 for row in output_rows if not row["eps_hi_mfree_lt_1"]),
            "eps_hi_mfree_lt_0_5_count": sum(1 for row in output_rows if row["eps_hi_mfree_lt_0_5"]),
            "eps_lo_le_eps_hi_mfree_violations": len(invariant_violations),
            "pair_error_floor_mean": float(mean(pair_floors)),
            "pair_error_floor_median": float(median(pair_floors)),
            "pair_error_floor_quantiles": quantiles(pair_floors),
            "uniform_floor_M46_open_set": uniform["floor_M46_open_set"],
            "uniform_floor_M45_known_closed_set": uniform["floor_M45_known_closed_set"],
            "lp_floor_M46_open_set": lp["floor_M46_open_set"],
            "lp_floor_M45_known_closed_set": lp["floor_M45_known_closed_set"],
            "falsifier": {
                "criterion": "uniform_floor_M46_open_set > 0 under the 990-pair Bonferroni Eq(9) upper side",
                "strictly_positive": bool(uniform["floor_M46_open_set"] > 0.0),
                "eps_hi_mfree_ge_1_count": sum(1 for row in output_rows if not row["eps_hi_mfree_lt_1"]),
                "statement": (
                    "PASS: the joint high-probability Eq(9) uniform floor is strictly positive."
                    if uniform["floor_M46_open_set"] > 0.0
                    else "FAIL: union-bounding drove the joint high-probability Eq(9) uniform floor to zero."
                ),
            },
        },
        "uniform_aggregation": uniform,
        "lp_aggregation": lp,
        "per_service_min_diagnostic": per_service_diagnostics(output_rows, "eps_hi_mfree"),
        "comparison_with_expectation_form_values": {
            "uniform_floor_vs_0_186": compare(uniform["floor_M46_open_set"], REFERENCE_UNIFORM_M46),
            "uniform_floor_vs_0_18577": compare(uniform["floor_M46_open_set"], REFERENCE_UNIFORM_M46_UNROUNDED),
            "lp_floor_vs_0_363": compare(lp["floor_M46_open_set"], REFERENCE_LP_M46),
            "lp_floor_vs_0_36307": compare(lp["floor_M46_open_set"], REFERENCE_LP_M46_UNROUNDED),
        },
        "invariant_violations": invariant_violations,
        "rows": output_rows,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"{sha256_file(OUTPUT_PATH)}  {OUTPUT_PATH}")
    print(f"{sha256_file(SCRIPT_PATH)}  {SCRIPT_PATH}")


if __name__ == "__main__":
    main()
