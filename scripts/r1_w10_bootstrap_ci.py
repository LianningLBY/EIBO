#!/usr/bin/env python3
"""Compute R1-W10 bootstrap intervals from existing project artifacts."""

import json
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOWER_PATH = PROJECT_ROOT / "artifacts/_project/data/q1_lower_side_full_n.json"
X1_PATH = PROJECT_ROOT / "artifacts/_project/data/x1_headline_table.json"
OUTPUT_PATH = PROJECT_ROOT / "artifacts/_project/data/ci_main_table_pairbootstrap.json"

SEED = 20260915
REPLICATES = 2000
ALPHA = 0.05
PERCENTILES = (100 * ALPHA / 2, 100 * (1 - ALPHA / 2))
N_EXPECTED = 990


def percentile_ci(values, statistic):
    values = np.asarray(values)
    rng = np.random.default_rng(SEED)
    indices = rng.integers(0, values.size, size=(REPLICATES, values.size))
    bootstrap_statistics = np.asarray(
        [statistic(values[index]) for index in indices], dtype=float
    )
    return [
        float(np.percentile(bootstrap_statistics, PERCENTILES[0])),
        float(np.percentile(bootstrap_statistics, PERCENTILES[1])),
    ]


def count_ci(indicators):
    indicators = np.asarray(indicators, dtype=np.int8)
    return percentile_ci(indicators, np.sum)


def main():
    with LOWER_PATH.open() as handle:
        lower_artifact = json.load(handle)
    with X1_PATH.open() as handle:
        x1_artifact = json.load(handle)

    rows = lower_artifact["rows"]
    if len(rows) != N_EXPECTED:
        raise ValueError(f"expected {N_EXPECTED} rows, found {len(rows)}")

    required_fields = ("eps_lo", "upper_recomputed")
    missing = [
        (index, field)
        for index, row in enumerate(rows)
        for field in required_fields
        if field not in row
    ]
    missing_eps_hi = [
        index
        for index, row in enumerate(rows)
        if "eps_hi" not in row["upper_recomputed"]
    ]
    missing_tv_hat = [
        index
        for index, row in enumerate(rows)
        if "tv_hat" not in row["upper_recomputed"]
    ]
    if missing or missing_eps_hi or missing_tv_hat:
        raise ValueError(
            "required row fields missing: "
            f"base={missing[:3]}, eps_hi={missing_eps_hi[:3]}, "
            f"tv_hat={missing_tv_hat[:3]}"
        )

    invalid_m_k = [
        (row["M"], row["k"])
        for row in rows
        if row["M"] != 1 or row["k"] != 5
    ]
    if invalid_m_k:
        raise ValueError(f"unexpected M/k values in lower-side rows: {invalid_m_k[:3]}")

    eps_lo = np.asarray([row["eps_lo"] for row in rows], dtype=float)
    eps_hi = np.asarray(
        [row["upper_recomputed"]["eps_hi"] for row in rows], dtype=float
    )
    tv_hat = np.asarray(
        [row["upper_recomputed"]["tv_hat"] for row in rows], dtype=float
    )

    crossing_rows = np.flatnonzero(eps_lo > eps_hi)
    if crossing_rows.size:
        raise ValueError(
            "hard invariant violated: eps_lo > eps_hi on rows "
            f"{crossing_rows[:10].tolist()}"
        )

    joint_gate = (eps_lo > 0.05) & (eps_hi < 0.5)
    upper_side = eps_hi < 0.5
    lower_side = eps_lo > 0.05

    source_summary = lower_artifact.get("joint_gate", {})
    x1_rows = [
        row
        for row in x1_artifact.get("headline_table_unified_calibre", [])
        if row.get("M") == 1 and row.get("k") == 5
    ]
    x1_summary = x1_rows[0] if x1_rows else {}
    observed_counts = {
        "joint_gate": int(joint_gate.sum()),
        "upper_side": int(upper_side.sum()),
        "lower_side": int(lower_side.sum()),
    }
    recorded_counts = {
        "joint_gate": source_summary.get("gate_count"),
        "upper_side": source_summary.get("upper_set_size_recomputed"),
        "lower_side": source_summary.get("full_n_lower_set_size"),
    }
    x1_counts = {
        "joint_gate": x1_summary.get("gate_pairs_both"),
        "upper_side": x1_summary.get("upper_side_pairs"),
        "lower_side": x1_summary.get("lower_side_pairs"),
    }
    consistency_checks = {
        "eps_lo_le_eps_hi_violation_count": int(crossing_rows.size),
        "row_count": len(rows),
        "row_level_counts": observed_counts,
        "recorded_q1_counts": recorded_counts,
        "recorded_x1_counts": x1_counts,
        "row_vs_q1_counts_match": observed_counts == recorded_counts,
        "row_vs_x1_counts_match": observed_counts == x1_counts,
    }

    median_ci = percentile_ci(tv_hat, np.median)
    non_estimable = []
    for m in (2, 4, 8, 16):
        non_estimable.append(
            {
                "quantity": f"per-M median tv CI at M={m}",
                "estimable": False,
                "reason": (
                    "Not estimable from the available per-pair rows: "
                    "q1_lower_side_full_n.json contains 990 rows only for "
                    "k=5, M=1. x1_headline_table.json has aggregate summaries "
                    "but no per-pair tv_hat values for this M."
                ),
            }
        )

    def interval_payload(indicators):
        ci = count_ci(indicators)
        count = int(np.sum(indicators))
        return {
            "count": count,
            "n": int(indicators.size),
            "fraction": float(count / indicators.size),
            "ci_lo": ci[0] / indicators.size,
            "ci_hi": ci[1] / indicators.size,
            "ci_scale": "fraction",
            "count_ci_lo": ci[0],
            "count_ci_hi": ci[1],
        }

    result = {
        "method": "nonparametric pair bootstrap over service pairs, percentile CI",
        "confidence_level": 0.95,
        "alpha": ALPHA,
        "percentile_levels": [PERCENTILES[0], PERCENTILES[1]],
        "resampling_unit": "service pairs (treats 990 dependent pairs as iid)",
        "seed": SEED,
        "replicates": REPLICATES,
        "source_artifacts": [
            "artifacts/_project/data/q1_lower_side_full_n.json",
            "artifacts/_project/data/x1_headline_table.json",
        ],
        "joint_gate": interval_payload(joint_gate),
        "upper_side": interval_payload(upper_side),
        "lower_side": interval_payload(lower_side),
        "median_tv": {
            "n": int(tv_hat.size),
            "median_tv": float(np.median(tv_hat)),
            "ci_lo": median_ci[0],
            "ci_hi": median_ci[1],
        },
        "estimability_notes": [
            {
                "quantity": "per-M median tv CI at M=1",
                "estimable": True,
                "reason": (
                    "All 990 k=5, M=1 rows contain upper_recomputed.tv_hat."
                ),
            },
            *non_estimable,
            {
                "quantity": "joint-gate CI at k=5, M=1",
                "estimable": True,
                "reason": (
                    "All 990 rows contain eps_lo and upper_recomputed.eps_hi."
                ),
            },
            {
                "quantity": "upper-side CI at k=5, M=1",
                "estimable": True,
                "reason": "All 990 rows contain upper_recomputed.eps_hi.",
            },
            {
                "quantity": "lower-side CI at k=5, M=1",
                "estimable": True,
                "reason": "All 990 rows contain eps_lo.",
            },
        ],
        "consistency_checks": consistency_checks,
    }

    with OUTPUT_PATH.open("w") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
if __name__ == "__main__":
    main()
