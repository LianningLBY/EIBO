#!/usr/bin/env python3
"""Compute exact false-certification rates in a zero-gain block model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import binom

from quic_timing_cell_certificate import ALPHA, joint_radius_from_change_budget, product_lower


BLOCK_COUNTS = (5, 10, 20, 46, 91)
CORRELATIONS = (0.0, 0.1, 0.2, 0.4, 0.6, 0.8, 1.0)
DESIGNS = ("adjacent_pairs", "persistent_markov")


def high_count_law(blocks, rho, design):
    """Track the joint law of the high-score count and the latest block state."""
    law = np.zeros((2, blocks + 1))
    law[0, 0] = law[1, 1] = 0.5
    for block in range(1, blocks):
        # Blocks 0 and 1 share a pair, as do 2 and 3, and so on.
        correlation = 0.0 if design == "adjacent_pairs" and block % 2 == 0 else rho
        same = (1 + correlation) / 2
        flip = 1 - same
        next_law = np.zeros_like(law)
        next_law[0] = same * law[0] + flip * law[1]
        next_law[1, 1:] = flip * law[0, :-1] + same * law[1, :-1]
        law = next_law
    return law.sum(axis=0)


def gain_bounds(blocks):
    # Each row represents all sequences with the same number of high scores.
    high = np.arange(blocks) < np.arange(blocks + 1)[:, None]
    scores = np.where(high, 0.75, 0.25) / blocks
    # A general [0, 1/blocks] range is available from the mutable mass.
    radius = joint_radius_from_change_budget([1 / blocks], alpha=ALPHA)[0]
    return {
        "independent_hoeffding": scores.sum(axis=1) - radius - 0.5,
        "independent_product": product_lower(scores, ALPHA) - 0.5,
        "parity_hoeffding": scores.sum(axis=1) - np.sqrt(2) * radius - 0.5,
        "parity_product": product_lower(scores, ALPHA**2) - 0.5,
    }


def evaluate():
    scenarios = []
    for blocks in BLOCK_COUNTS:
        bounds = gain_bounds(blocks)
        rejects = {method: value > 1e-12 for method, value in bounds.items()}
        for design in DESIGNS:
            for rho in CORRELATIONS:
                law = high_count_law(blocks, rho, design)
                if not np.isclose(law.sum(), 1, atol=1e-13, rtol=0) or not np.allclose(
                        law, law[::-1], atol=1e-13, rtol=0):
                    raise RuntimeError("the null count law must be normalized and symmetric")
                if rho == 0 and not np.allclose(
                        law, binom.pmf(np.arange(blocks + 1), blocks, 0.5), atol=1e-13, rtol=0):
                    raise RuntimeError("the independent count law must match the exact binomial law")
                rates = {method: float(law[positive].sum()) for method, positive in rejects.items()}
                for method, rate in rates.items():
                    valid_model = rho == 0 or (design == "adjacent_pairs" and method.startswith("parity_"))
                    if valid_model and rate > ALPHA + 1e-12:
                        raise RuntimeError("false-certification rate exceeds alpha under a valid model")
                scenarios.append({
                    "blocks": blocks,
                    "dependence": design,
                    "state_correlation_at_linked_transitions": rho,
                    "mean_adjacent_correlation": (
                        rho if design == "persistent_markov" else rho * (blocks // 2) / (blocks - 1)
                    ),
                    "false_certification_rates": rates,
                    "coverage_rates": {method: 1 - rate for method, rate in rates.items()},
                })
    return {
        "alpha_per_method": ALPHA,
        "true_bayes_gain": 0.0,
        "design": (
            "One coarse cell with four equal-mass balanced label pairs per block. "
            "In the high state the added feature agrees with three pairs and flips one. "
            "The low state reverses those outcomes. Each state has marginal probability one half, "
            "so each record's added feature is marginally fair given the cohort. "
            "The frozen rule predicts the added feature. Scores are one-quarter or three-quarters "
            "of the mutable block mass. False certification means a strictly positive lower bound."
        ),
        "assumptions": {
            "adjacent_pairs": "Independent successive pairs of blocks with correlation rho inside each pair. "
                              "An unpaired final block is independent.",
            "persistent_markov": "Stationary symmetric two-state Markov chain with lag-one correlation rho "
                                 "and lag-two correlation rho squared.",
            "range": "[0, 1 / blocks] from the mutable block mass",
            "method_scope": "At rho=0 all methods have their assumed independence. For adjacent pairs, "
                            "the parity methods remain valid at all rho values.",
            "calculation": "Exact recursion over the last state and the number of high scores",
        },
        "scenarios": scenarios,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new file")
    result = evaluate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")
    for row in result["scenarios"]:
        if row["blocks"] in (20, 91):
            rates = " | ".join(f"{name} {value:.3%}"
                               for name, value in row["false_certification_rates"].items())
            print(f"{row['dependence']} | {row['blocks']} blocks | "
                  f"rho={row['state_correlation_at_linked_transitions']:.1f} | {rates}")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
