#!/usr/bin/env python3
"""Compare positive cell-product contributions in the two XS windows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


DEFAULT_SWEEP = (Path(__file__).resolve().parents[1] / "artifacts/methodology"
                 / "if_e1_timing_service_sweep_xs_20261112_125904.json")


def describe(cohort):
    if "status" in cohort:
        return {key: cohort[key] for key in ("status", "missing_holdout_classes") if key in cohort}
    rows = {}
    for width, row in cohort["results_by_block_width"].items():
        bounds = row["certificate_comparison"]
        cell_lower = bounds["cell_product"]["lower"]
        pooled_lower = bounds["pooled_product"]["lower"]
        cells = sorted(
            (cell for cell in row["cells"] if cell["bayes_gain_lower_contribution"] > 0),
            key=lambda cell: (-cell["bayes_gain_lower_contribution"], cell["coarse_symbol"]),
        )
        positive = [
            {
                "symbol": cell["coarse_symbol"],
                "contribution_pp": 100 * cell["bayes_gain_lower_contribution"],
                "share_of_cell_product": cell["bayes_gain_lower_contribution"] / cell_lower,
                "mutable_units": cell["mutable_units"],
                "flow_count": cell["flow_count"],
            }
            for cell in cells
        ]
        rows[width] = {
            "family_alpha": row["family_alpha"],
            "sampling_units": row["sampling_units"],
            "occupied_cells": row["occupied_coarse_cells"],
            "sample_bayes_gain_pp": 100 * row["sample_bayes_gain"],
            "pooled_product_pp": 100 * pooled_lower,
            "cell_product_pp": 100 * cell_lower,
            "cell_minus_pooled_product_pp": 100 * (cell_lower - pooled_lower),
            "top_1_share": positive[0]["share_of_cell_product"] if positive else None,
            "top_3_share": sum(cell["share_of_cell_product"] for cell in positive[:3]) if positive else None,
            "positive_cells": positive,
        }
    return rows


def compare_windows(sweep_path, temporal_path):
    sweep_bytes = sweep_path.read_bytes()
    sweep = json.loads(sweep_bytes)
    sweep_hash = hashlib.sha256(sweep_bytes).hexdigest()
    original = sweep["service_sweep"]["expanded_cohorts"]
    output = {
        "sweep_sha256": sweep_hash,
        "windows_utc": {"original": sweep["windows_utc"]["evaluation"]},
        "cohorts": {name: {"original": describe(original[key])} for name, key in (("16", "16"), ("44", "all"))},
    }
    if temporal_path is None:
        return output

    temporal_bytes = temporal_path.read_bytes()
    temporal = json.loads(temporal_bytes)
    if (temporal["reference_sweep_sha256"] != sweep_hash
            or temporal["pilot_h5_sha256"] != sweep["h5_sha256"]
            or temporal["pilot_utc"] != sweep["windows_utc"]["pilot"]):
        raise ValueError("the temporal JSON does not identify this sweep and its fitting window")
    output["temporal_sha256"] = hashlib.sha256(temporal_bytes).hexdigest()
    output["windows_utc"]["temporal"] = temporal["holdout_utc"]
    for name, key in (("16", "16"), ("44", "all")):
        check = temporal["cohorts"][name]
        if any(check[field] != original[key][field] for field in ("classes_in_count_order", "fit_counts")):
            raise ValueError(f"the {name}-class cohort differs from the fitted cohort in the sweep")
        summary = output["cohorts"][name]
        summary["temporal"] = describe(check)
        if "status" not in summary["original"] and "status" not in summary["temporal"]:
            summary["common_positive_symbols"] = {
                width: sorted(
                    {cell["symbol"] for cell in row["positive_cells"]}
                    & {cell["symbol"] for cell in summary["temporal"][width]["positive_cells"]}
                )
                for width, row in summary["original"].items()
            }
    return output


def add_leave_one_cell_out(result):
    for cohort in result["cohorts"].values():
        original = cohort["original"]
        if "status" in original or not original["1d"]["positive_cells"]:
            cohort["leave_one_cell_out"] = {"status": "no_positive_original_daily_cell"}
            continue
        symbol = original["1d"]["positive_cells"][0]["symbol"]
        cohort["leave_one_cell_out"] = {
            "omitted_symbol": symbol,
            "remaining_bound_pp": {
                window: {
                    width: sum(cell["contribution_pp"] for cell in row["positive_cells"]
                               if cell["symbol"] != symbol)
                    for width, row in cohort[window].items()
                }
                for window in result["windows_utc"] if "status" not in cohort[window]
            },
        }
    result["leave_one_cell_out_design"] = (
        "Omit the largest original daily cell-product contributor in every width and window. "
        "Sum the remaining simultaneous bounds under the original weights and error allocation."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    parser.add_argument("--temporal", type=Path, help="XS temporal check JSON; omit for the original window only")
    parser.add_argument("--leave-one-cell-out", action="store_true", help="omit the largest original daily contributor")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new file")
    result = compare_windows(args.sweep, args.temporal)
    if args.leave_one_cell_out:
        add_leave_one_cell_out(result)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")

    for cohort, windows in result["cohorts"].items():
        for name in result["windows_utc"]:
            print(f"{cohort} classes, {name}")
            if "status" in windows[name]:
                print(f"  {windows[name]['status']}")
                continue
            for width, row in windows[name].items():
                cells = row["positive_cells"]
                print(f"  {width} (alpha {row['family_alpha']:.3f}): "
                      f"{len(cells)}/{row['occupied_cells']} positive cells, "
                      f"cell minus pooled {row['cell_minus_pooled_product_pp']:+.5f} pp")
                if cells:
                    top = cells[0]
                    print(f"    symbol {top['symbol']}: {top['share_of_cell_product']:.1%}, "
                          f"{top['mutable_units']}/{row['sampling_units']} mutable blocks; "
                          f"top 3 share {row['top_3_share']:.1%}")
        if "common_positive_symbols" in windows:
            print(f"  Common positive symbols by width: {windows['common_positive_symbols']}")
        if args.leave_one_cell_out:
            check = windows["leave_one_cell_out"]
            if "omitted_symbol" in check:
                for window, bounds in check["remaining_bound_pp"].items():
                    print(f"  {window} without symbol {check['omitted_symbol']}: " + " | ".join(
                        f"{width} {value:+.5f} pp" for width, value in bounds.items()))
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
