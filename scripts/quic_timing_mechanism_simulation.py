#!/usr/bin/env python3
"""Vary the concentration of a known Bayes gain under the timing block model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from quic_timing_cell_certificate import ALPHA, joint_radius_from_change_budget, product_lower


CELLS = 32
OCCUPIED_CELL_COUNTS = (CELLS, 88, 199)
GROUPS_PER_CELL_BLOCK = 8
BLOCK_COUNTS = (20, 40, 80, 160)
ACTIVE_CELL_COUNTS = (0, 4, 8, 16, 32)
POSITIVE_GAIN = 0.04
TRIALS = 10_000
SEED = 20261112
METHODS = ("pooled_hoeffding", "pooled_product", "cell_hoeffding", "cell_product")


def bounds(scores, num_blocks, *, occupied_cells=CELLS):
    cell_alpha = ALPHA / occupied_cells
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


def simulate(num_blocks, active_cells, occupied_cell_counts):
    rng = np.random.default_rng([SEED, num_blocks, active_cells])
    gain = POSITIVE_GAIN if active_cells else 0.0
    p = np.full(CELLS, 0.5)
    if active_cells:
        p[:active_cells] += gain * CELLS / active_cells
    # Each group contains equal mass from both classes. A shared bit sets
    # whether the added binary feature agrees with or flips every label.
    score_per_group = 1 / (num_blocks * CELLS * GROUPS_PER_CELL_BLOCK)
    lower = {cells: np.empty((TRIALS, len(METHODS))) for cells in occupied_cell_counts}
    for start in range(0, TRIALS, 128):
        batch_size = min(TRIALS - start, 128)
        scores = rng.binomial(GROUPS_PER_CELL_BLOCK, p[None, :, None],
                              size=(batch_size, CELLS, num_blocks)) * score_per_group
        for cells, values in lower.items():
            # Split only null cells. Each child receives a proportional
            # share of its parent's score, range, and coarse optimum. The
            # child bounds sum to the parent bound at the new alpha/M.
            values[start:start + batch_size] = bounds(scores, num_blocks, occupied_cells=cells)
    pooled = lower[occupied_cell_counts[0]][:, :2]
    if not all(np.array_equal(values[:, :2], pooled) for values in lower.values()):
        raise RuntimeError("splitting null cells changed a pooled bound")
    return {cells: summarize(values, num_blocks, active_cells, gain, p[0]) for cells, values in lower.items()}


def summarize(lower, num_blocks, active_cells, gain, signal_probability):
    gap = lower[:, 3] - lower[:, 1]
    return {
        "blocks": num_blocks,
        "signal_cells": active_cells,
        "true_bayes_gain": gain,
        "signal_cell_agreement_probability": float(signal_probability),
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
    parser.add_argument("--cell-count-sweep", action="store_true", help="split zero-gain cells to compare 32, 88 and 199 cells")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new file")
    cell_counts = OCCUPIED_CELL_COUNTS if args.cell_count_sweep else (CELLS,)
    active_counts = ACTIVE_CELL_COUNTS[:-1] if args.cell_count_sweep else ACTIVE_CELL_COUNTS
    scenarios = []
    for blocks in BLOCK_COUNTS:
        for active in active_counts:
            for cells, row in simulate(blocks, active, cell_counts).items():
                if args.cell_count_sweep:
                    row["occupied_cells"] = cells
                    row["alpha_per_cell"] = ALPHA / cells
                scenarios.append(row)
                print(f"{blocks:3d} blocks, {active:2d}/{cells} signal cells | " + " | ".join(
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
    if args.cell_count_sweep:
        output["occupied_cell_counts"] = list(cell_counts)
        output["base_cells"] = output.pop("coarse_cells")
        output["base_synthetic_flow_count"] = output.pop("synthetic_flow_count")
        output["design"] += (
            " Split zero-gain cells into proportional children sharing the parent block draws. "
            "This preserves the true gain, total mass, and pooled block scores. "
            "Use the total number of occupied children and unsplit cells in the Bonferroni allocation."
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
