#!/usr/bin/env python3
"""Compute R1-W9 bootstrap confidence intervals from existing JSON artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
PRIMARY_PATH = PROJECT / "artifacts/_project/data/q1_lower_side_full_n.json"
QUIC_PATH = PROJECT / "artifacts/X11/data/x11_full_bracket.json"
OUTPUT_PATH = PROJECT / "artifacts/_project/data/ci_cross_corpus_pairbootstrap.json"
SEED = 20260915
REPLICATES = 2000


def fraction_ci(values: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    """Return observed fraction and percentile bootstrap 95% CI."""
    values = np.asarray(values, dtype=bool)
    n = values.size
    if n == 0:
        raise AssertionError("cannot bootstrap an empty stratum")
    observed = float(values.mean())
    samples = rng.integers(0, n, size=(REPLICATES, n))
    bootstrap = values[samples].mean(axis=1)
    ci_lo, ci_hi = np.percentile(bootstrap, [2.5, 97.5])
    return observed, float(ci_lo), float(ci_hi)


def numeric_threshold(label: str) -> int | None:
    if label == "all":
        return None
    return int(label.removeprefix(">="))


def assert_close(name: str, actual: float, expected: float) -> None:
    if not np.isclose(actual, expected, rtol=0.0, atol=1e-12):
        raise AssertionError(f"{name}: computed {actual} != stored {expected}")


def main() -> None:
    primary = json.loads(PRIMARY_PATH.read_text())
    quic = json.loads(QUIC_PATH.read_text())
    primary_rows = primary["rows"]
    quic_rows = quic["per_pair_rows"]
    comparisons = quic["n_stratified_comparison"]

    assert len(primary_rows) == 990
    assert len(quic_rows) == 3321
    assert len(comparisons) == 5
    assert all("eps_hi" in row["upper_recomputed"] for row in primary_rows)

    primary_lower = np.array([row["eps_lo"] > 0.05 for row in primary_rows])
    quic_lower = np.array([row["eps_lo"] > 0.05 for row in quic_rows])
    assert int(primary_lower.sum()) == 986
    assert int(quic_lower.sum()) == 3310

    # One seeded generator is used sequentially; each corpus is resampled independently.
    rng = np.random.default_rng(SEED)
    primary_fraction, primary_ci_lo, primary_ci_hi = fraction_ci(primary_lower, rng)
    quic_fraction, quic_ci_lo, quic_ci_hi = fraction_ci(quic_lower, rng)

    lower_side_ci = {
        "primary": {
            "fraction": primary_fraction,
            "ci_lo": primary_ci_lo,
            "ci_hi": primary_ci_hi,
            "n_pairs": len(primary_rows),
        },
        "quic22": {
            "fraction": quic_fraction,
            "ci_lo": quic_ci_lo,
            "ci_hi": quic_ci_hi,
            "n_pairs": len(quic_rows),
        },
    }

    primary_eps_hi = np.array([row["upper_recomputed"]["eps_hi"] < 0.5 for row in primary_rows])
    quic_eps_hi = np.array([row["eps_hi"] < 0.5 for row in quic_rows])
    gap_ci = []

    for comparison in comparisons:
        label = comparison["threshold"]
        threshold = numeric_threshold(label)
        if threshold is None:
            primary_mask = np.ones(len(primary_rows), dtype=bool)
            quic_mask = np.ones(len(quic_rows), dtype=bool)
        else:
            primary_mask = np.array(
                [min(row["n_a"], row["n_b"]) >= threshold for row in primary_rows]
            )
            quic_mask = np.array(
                [min(row["n_a"], row["n_b"]) >= threshold for row in quic_rows]
            )

        primary_values = primary_eps_hi[primary_mask]
        quic_values = quic_eps_hi[quic_mask]
        assert len(primary_values) == comparison["primary"]["pair_count"]
        assert len(quic_values) == comparison["quic22"]["pair_count"]

        primary_point = float(primary_values.mean())
        quic_point = float(quic_values.mean())
        assert_close(f"{label} primary upper fraction", primary_point, comparison["primary"]["upper_fraction"])
        assert_close(f"{label} QUIC22 upper fraction", quic_point, comparison["quic22"]["upper_fraction"])

        # Independent resampling of the two corpus-specific matched subsets.
        primary_sample = rng.integers(0, len(primary_values), size=(REPLICATES, len(primary_values)))
        quic_sample = rng.integers(0, len(quic_values), size=(REPLICATES, len(quic_values)))
        primary_bootstrap = primary_values[primary_sample].mean(axis=1)
        quic_bootstrap = quic_values[quic_sample].mean(axis=1)
        gap_bootstrap = quic_bootstrap - primary_bootstrap
        gap = quic_point - primary_point
        ci_lo, ci_hi = np.percentile(gap_bootstrap, [2.5, 97.5])

        gap_ci.append(
            {
                "threshold": label,
                "n_quic22": len(quic_values),
                "n_primary": len(primary_values),
                "gap": float(gap),
                "ci_lo": float(ci_lo),
                "ci_hi": float(ci_hi),
            }
        )

    runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = {
        "method": "nonparametric bootstrap, percentile CI",
        "resampling_unit": "service pairs",
        "seed": SEED,
        "replicates": REPLICATES,
        "runner_sha256": runner_sha256,
        "lower_side_ci": lower_side_ci,
        "stratum_matched_gap_ci": gap_ci,
        "primary_eps_hi_source": "q1_lower_side_full_n.json rows[*].upper_recomputed.eps_hi",
        "limitations": "None for the requested quantities; primary eps_hi was present in upper_recomputed.",
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
