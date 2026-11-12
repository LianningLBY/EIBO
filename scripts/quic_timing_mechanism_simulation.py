#!/usr/bin/env python3
"""Vary the concentration of a known Bayes gain under the timing block model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from quic_timing_cell_certificate import ALPHA, joint_radius_from_change_budget, product_lower


CELLS = 32
GROUPS_PER_CELL_BLOCK = 8
BLOCK_COUNTS = (20, 40, 80, 160)
ACTIVE_CELL_COUNTS = (0, 4, 8, 16, 32)
POSITIVE_GAIN = 0.04
TRIALS = 10_000
SEED = 20261112
METHODS = ("pooled_hoeffding", "pooled_product", "cell_hoeffding", "cell_product")


def bounds(scores, num_blocks):
    cell_alpha = ALPHA / CELLS
    cell_mass = 1 / (CELLS * num_blocks)
    pooled_mass = 1 / num_blocks
    cell_coarse = 0.5 / CELLS
    pooled_scores = scores.sum(axis=1)
    cell_radius = joint_radius_from_change_budget([num_blocks * cell_mass**2], alpha=cell_alpha)[0]
    pooled_radius = joint_radius_from_change_budget([num_blocks * pooled_mass**2], alpha=ALPHA)[0]
    return np.column_stack((
        np.maximum(0, pooled_scores.sum(axis=-1) - pooled_radius - 0.5),
        np.maximum(0, product_lower(pooled_scores, ALPHA) - 0.5),
        np.maximum(0, scores.sum(axis=-1) - cell_radius - cell_coarse).sum(axis=-1),
        np.maximum(0, product_lower(scores, cell_alpha) - cell_coarse).sum(axis=-1),
    ))


def simulate(num_blocks, active_cells):
    rng = np.random.default_rng([SEED, num_blocks, active_cells])
    gain = POSITIVE_GAIN if active_cells else 0.0
    p = np.full(CELLS, 0.5)
    if active_cells:
        p[:active_cells] += gain * CELLS / active_cells
    # Each group contains equal mass from both classes. A shared bit sets
    # whether the added binary feature agrees with or flips every label.
    score_per_group = 1 / (num_blocks * CELLS * GROUPS_PER_CELL_BLOCK)
    lower = np.empty((TRIALS, len(METHODS)))
    for start in range(0, TRIALS, 128):
        batch = lower[start:start + 128]
        scores = rng.binomial(GROUPS_PER_CELL_BLOCK, p[None, :, None],
                              size=(len(batch), CELLS, num_blocks)) * score_per_group
        batch[:] = bounds(scores, num_blocks)
    gap = lower[:, 3] - lower[:, 1]
    return {
        "blocks": num_blocks,
        "signal_cells": active_cells,
        "true_bayes_gain": gain,
        "signal_cell_agreement_probability": float(p[0]),
        "methods": {
            name: {
                "positive_rate": float((values > 1e-12).mean()),
                "mean_lower": float(values.mean()),
                "median_lower": float(np.median(values)),
                "undercoverage_rate": float((values > gain + 1e-12).mean()),
            }
            for name, values in zip(METHODS, lower.T)
        },
        "cell_product_larger_rate": float((gap > 1e-12).mean()),
        "pooled_product_larger_rate": float((gap < -1e-12).mean()),
        "mean_cell_minus_pooled_product": float(gap.mean()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new file")
    scenarios = []
    for blocks in BLOCK_COUNTS:
        for active in ACTIVE_CELL_COUNTS:
            row = simulate(blocks, active)
            scenarios.append(row)
            print(f"{blocks:3d} blocks, {active:2d} signal cells | " + " | ".join(
                f"{name} {values['positive_rate']:.1%} positive, median {100 * values['median_lower']:+.3f} pp"
                for name, values in row["methods"].items()), flush=True)
    output = {
        "alpha_per_method": ALPHA,
        "seed": SEED,
        "trials_per_scenario": TRIALS,
        "coarse_cells": CELLS,
        "groups_per_cell_block": GROUPS_PER_CELL_BLOCK,
        "equal_class_priors": [0.5, 0.5],
        "synthetic_flow_count": 2 * CELLS * GROUPS_PER_CELL_BLOCK * max(BLOCK_COUNTS),
        "design": "Independent agreement bits across groups, cells and blocks. "
                  "Each group repeats its balanced class pair to keep the total flow count fixed. "
                  "The frozen decision predicts the added binary feature.",
        "scenarios": scenarios,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
