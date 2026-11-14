#!/usr/bin/env python3
"""Reproduce or validate a coarse-cell certificate for conditional timing gain."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import beta

import quic_timing_pilot as timing
import quic_timing_pilot_h5 as h5_pilot
from eibo.realdata import DAY, FlowSource, chronological_windows, utc
from eibo.riskcert import joint_radius_from_change_budget


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_SUMMARY = ROOT / "artifacts/quic_timing_pilot_20261111/summary.json"
ALPHA = 0.05
BLOCK_DAYS = (1, 2, 4)
ROUNDING_SECONDS = 3600
MIN_SWEEP_PILOT_FLOWS = 2_000
QUIC22_S_ROWS = 25_000_000
# CESNET DataZoo APP enum for QUIC22.
QUIC22_BACKGROUND = (0, 109, 110)
TRIALS = 100_000
SEED = 20261112


def product_lower(scores, alpha):
    """Lower bound for the sum of expectations of independent nonnegative scores."""
    units = scores.shape[-1]
    if units == 0:
        return np.zeros(scores.shape[:-1])
    with np.errstate(divide="ignore"):
        return units * np.exp((math.log(alpha) + np.log(scores).sum(axis=-1)) / units)


def cell_certificate(labels, coarse, fine, groups, priors, fine_rule, *, compare=False, alpha=ALPHA,
                     pooled_omit_symbol=None, report_pooled_blocks=False, weighted_cells=False,
                     added_bins=timing.TIMING_BINS):
    """Condition on labels, coarse symbols, block membership, and the fitted rule."""
    alphabet = len(fine_rule) // added_bins
    coarse_counts = timing.hist(labels, coarse, len(priors), alphabet)
    class_counts = coarse_counts.sum(axis=1)
    if np.any(class_counts == 0):
        raise ValueError("every fitted class must be present in the eligible holdout")
    class_weights = priors / class_counts
    coarse_mass = class_weights[:, None] * coarse_counts
    active = np.flatnonzero(coarse_counts.sum(axis=0))
    cell_alpha = alpha / len(active)
    coarse_optimum = coarse_mass.max(axis=0)
    fine_mass = class_weights[:, None] * timing.hist(labels, fine, len(priors), len(fine_rule))
    fine_optimum = fine_mass.max(axis=0).reshape(alphabet, added_bins).sum(axis=1)

    candidates = fine_rule.reshape(alphabet, added_bins)
    correct_by_bin = candidates[None, :, :] == np.arange(len(priors))[:, None, None]
    always_correct = correct_by_bin.all(axis=2)
    can_change = correct_by_bin.any(axis=2) & ~always_correct
    deterministic = (coarse_mass * always_correct).sum(axis=0)
    mutable = can_change[labels, coarse]
    unique_units, unit = np.unique(groups, return_inverse=True)
    num_units = len(unique_units)
    cell_unit = coarse[mutable].astype(np.int64) * num_units + unit[mutable]
    block_sizes = np.bincount(cell_unit, minlength=alphabet * num_units).reshape(alphabet, num_units)
    mutable_labels = labels[mutable]
    correct_weights = class_weights[mutable_labels] * (fine_rule[fine[mutable]] == mutable_labels)
    block_scores = np.bincount(cell_unit, weights=correct_weights, minlength=alphabet * num_units)
    block_scores = block_scores.reshape(alphabet, num_units)

    cells = []
    for symbol in active:
        scores = block_scores[symbol, block_sizes[symbol] > 0]
        lower = deterministic[symbol] + product_lower(scores, cell_alpha) - coarse_optimum[symbol]
        cells.append({
            "coarse_symbol": int(symbol),
            "flow_count": int(coarse_counts[:, symbol].sum()),
            "mutable_units": len(scores),
            "sample_bayes_gain_contribution": float(fine_optimum[symbol] - coarse_optimum[symbol]),
            "frozen_gain_contribution": float(deterministic[symbol] + scores.sum() - coarse_optimum[symbol]),
            "bayes_gain_lower_contribution": float(max(0, lower)),
        })
    result = {
        "flows": len(labels),
        "class_counts": class_counts.tolist(),
        "sampling_units": num_units,
        "family_alpha": alpha,
        "occupied_coarse_cells": len(active),
        "per_cell_alpha": cell_alpha,
        "positive_cells": sum(row["bayes_gain_lower_contribution"] > 0 for row in cells),
        "sample_bayes_gain": sum(row["sample_bayes_gain_contribution"] for row in cells),
        "frozen_rule_minus_sample_coarse_optimum": sum(row["frozen_gain_contribution"] for row in cells),
        "conditional_bayes_gain_lower": sum(row["bayes_gain_lower_contribution"] for row in cells),
        "cells": cells,
    }
    if compare:
        # Conditional on the coarse inputs and labels, the correct score of
        # the mutable rows in a cell and block lies in [0, mutable mass].
        block_masses = np.bincount(cell_unit, weights=class_weights[mutable_labels],
                                   minlength=alphabet * num_units).reshape(alphabet, num_units)
        pooled_masses = block_masses.sum(axis=0)
        pooled_scores = block_scores.sum(axis=0)
        if report_pooled_blocks:
            result["pooled_blocks"] = {
                "groups": unique_units.tolist(),
                "scores": pooled_scores.tolist(),
                "mutable_masses": pooled_masses.tolist(),
                "fixed_correct_minus_coarse_optimum": float(deterministic.sum() - coarse_optimum.sum()),
            }
        pooled_radius = float(joint_radius_from_change_budget([pooled_masses @ pooled_masses], alpha=alpha)[0])
        pooled_scores = pooled_scores[pooled_masses > 0]
        pooled_product = float(deterministic.sum() + product_lower(pooled_scores, alpha) - coarse_optimum.sum())
        cell_radii = joint_radius_from_change_budget(np.square(block_masses[active]).sum(axis=1), alpha=cell_alpha)
        for row, radius in zip(cells, cell_radii):
            row["hoeffding_radius"] = float(radius)
            row["hoeffding_lower_contribution"] = max(0.0, row["frozen_gain_contribution"] - float(radius))
        result["certificate_comparison"] = {
            "pooled_hoeffding": {
                "alpha": alpha,
                "radius": pooled_radius,
                "lower": max(0.0, result["frozen_rule_minus_sample_coarse_optimum"] - pooled_radius),
            },
            "pooled_product": {
                "alpha": alpha,
                "mutable_units": len(pooled_scores),
                "untruncated_lower": pooled_product,
                "lower": max(0.0, pooled_product),
            },
            "cell_hoeffding": {
                "alpha": cell_alpha,
                "positive_cells": sum(row["hoeffding_lower_contribution"] > 0 for row in cells),
                "lower": sum(row["hoeffding_lower_contribution"] for row in cells),
            },
            "cell_product": {
                "alpha": cell_alpha,
                "positive_cells": result["positive_cells"],
                "lower": result["conditional_bayes_gain_lower"],
            },
        }
        if weighted_cells:
            # Correctness can change for these records given the fixed rule,
            # label, and coarse symbol. Their mass is fixed by conditioning.
            mutable_mass = (coarse_mass * can_change).sum(axis=0)
            total_mass = float(mutable_mass.sum())
            allocated = alpha * mutable_mass / total_mass if total_mass > 0 else mutable_mass
            weighted_rows = []
            for symbol in active:
                tail = float(allocated[symbol])
                product, hoeffding = 0.0, 0.0
                if tail > 0:
                    ranges = block_masses[symbol]
                    scores = block_scores[symbol, ranges > 0]
                    fixed = float(deterministic[symbol] - coarse_optimum[symbol])
                    radius = float(joint_radius_from_change_budget([ranges @ ranges], alpha=tail)[0])
                    product = max(0.0, fixed + float(product_lower(scores, tail)))
                    hoeffding = max(0.0, fixed + float(scores.sum()) - radius)
                weighted_rows.append({
                    "coarse_symbol": int(symbol),
                    "mutable_mass": float(mutable_mass[symbol]),
                    "alpha": tail,
                    "product_lower_contribution": product,
                    "hoeffding_lower_contribution": hoeffding,
                })
            result["mutable_mass_weighted_cells"] = {
                "family_alpha": alpha,
                "cell_product_lower": sum(row["product_lower_contribution"] for row in weighted_rows),
                "cell_hoeffding_lower": sum(row["hoeffding_lower_contribution"] for row in weighted_rows),
                "cells": weighted_rows,
            }
        if pooled_omit_symbol is not None:
            if pooled_omit_symbol not in active:
                raise ValueError(f"coarse symbol {pooled_omit_symbol} is absent from the holdout")
            retained = active[active != pooled_omit_symbol]
            retained_units = block_masses[retained].sum(axis=0) > 0
            retained_scores = block_scores[retained].sum(axis=0)[retained_units]
            fixed_gap = float(deterministic[retained].sum() - coarse_optimum[retained].sum())
            pointwise = fixed_gap + product_lower(retained_scores, alpha)
            simultaneous = fixed_gap + product_lower(retained_scores, cell_alpha)
            result["pooled_product_ablation"] = {
                "omitted_symbol": int(pooled_omit_symbol),
                "omitted_flows": int(coarse_counts[:, pooled_omit_symbol].sum()),
                "omitted_class_weight": float(coarse_mass[:, pooled_omit_symbol].sum()),
                "retained_mutable_units": len(retained_scores),
                "retained_sample_bayes_gain": float((fine_optimum - coarse_optimum)[retained].sum()),
                "retained_frozen_gain": float(fixed_gap + retained_scores.sum()),
                "pointwise_alpha": alpha,
                "pointwise_lower": float(max(0, pointwise)),
                "singleton_family_alpha": alpha,
                "singleton_per_symbol_alpha": cell_alpha,
                "singleton_simultaneous_lower": float(max(0, simultaneous)),
            }
    return result


def evaluate_days(labels, coarse, fine, day, priors, fine_rule, *, compare=False, alpha=ALPHA,
                  pooled_omit_symbol=None, weighted_cells=False):
    return {f"{width}d": cell_certificate(labels, coarse, fine, day // width, priors, fine_rule,
                                          compare=compare, alpha=alpha, pooled_omit_symbol=pooled_omit_symbol,
                                          weighted_cells=weighted_cells)
            for width in BLOCK_DAYS}


def run_quic22(prefix_dir, *, compare=False, weighted_cells=False):
    manifest_bytes = ARCHIVE_SUMMARY.read_bytes()
    summary = json.loads(manifest_bytes)
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    offsets = timing.archive_members(prefix_dir / "quic22-tail.bin")
    days = {}
    for date, expected in summary["files"].items():
        data, manifest = timing.read_day(prefix_dir / f"{date}.prefix", date, encoder, offsets)
        if manifest != expected:
            raise ValueError(f"QUIC22 archive segment does not match its manifest: {date}")
        days[date] = data
    fit_dates = summary["fit_dates"]
    evaluation_dates = summary["results"]["all"]["dates"]
    if max(summary["files"][date]["latest_end"] for date in fit_dates) >= min(
            summary["files"][date]["earliest_start"] for date in evaluation_dates):
        raise ValueError("QUIC22 fit and evaluation intervals overlap")
    classes = np.asarray(summary["classes_in_count_order"])
    priors = np.asarray(summary["priors"])
    fit = timing.combine([days[date] for date in fit_dates], classes)
    _, fine_rule, fit_counts = timing.fit_rules(*fit[:3], priors, encoder.alphabet)
    labels, coarse, fine, hour = timing.combine([days[date] for date in evaluation_dates], classes)
    results = evaluate_days(labels, coarse, fine, hour // 24, priors, fine_rule, compare=compare,
                            weighted_cells=weighted_cells)
    archived = summary["results"]["all"]
    primary = results["1d"]
    archived_keys = {"flows": "flows", "sample_bayes_gain": "sample_ceiling_gain",
                     "frozen_rule_minus_sample_coarse_optimum": "fused_minus_coarse_sample_optimum"}
    if (fit_counts.tolist() != summary["fit_counts"]
            or not all(np.isclose(primary[key], archived[original], atol=1e-11, rtol=0)
                       for key, original in archived_keys.items())):
        raise RuntimeError("the QUIC22 reproduction disagrees with the archived pilot")
    return {
        "source": "QUIC22 archived daily prefixes",
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "fit_archive_dates": fit_dates,
        "evaluation_archive_dates": evaluation_dates,
        "classes_in_count_order": classes.tolist(),
        "fit_counts": fit_counts.tolist(),
        "results_by_block_width": results,
    }


def evaluate_cohort(pilot, evaluation, day, within_day, alphabet, classes, *, compare=False):
    classes, priors, _, fine_rule, fit_counts = h5_pilot.fit(pilot, alphabet, classes=classes)
    cohort = evaluate_frozen_cohort(evaluation, day, within_day, classes, priors, fine_rule, compare=compare)
    return {**cohort, "fit_counts": fit_counts.tolist()}


def evaluate_frozen_cohort(evaluation, day, within_day, classes, priors, fine_rule, *, compare=False, alpha=ALPHA,
                           pooled_omit_symbol=None):
    apps, coarse, fine, _, _ = evaluation
    fitted_class = np.isin(apps, classes)
    keep = fitted_class & within_day
    labels = np.searchsorted(classes, apps[keep])
    cohort = {
        "classes_in_count_order": classes.tolist(),
        "evaluation_fitted_class_flows_before_daily_guard": int(fitted_class.sum()),
        "excluded_fitted_class_flows_crossing_day_boundary": int((fitted_class & ~within_day).sum()),
    }
    holdout_counts = np.bincount(labels, minlength=len(classes))
    if np.any(holdout_counts == 0):
        return {**cohort, "status": "missing_holdout_classes", "holdout_counts": holdout_counts.tolist(),
                "missing_holdout_classes": classes[holdout_counts == 0].tolist()}
    return {**cohort, "results_by_block_width": evaluate_days(labels, coarse[keep], fine[keep], day[keep],
                                                             priors, fine_rule, compare=compare, alpha=alpha,
                                                             pooled_omit_symbol=pooled_omit_symbol)}


def run_quic22_s(args):
    start = (date(2022, 10, 31) - date(1970, 1, 1)).days * DAY
    windows = {"pilot": (start, start + 7 * DAY), "evaluation": (start + 8 * DAY, start + 28 * DAY)}
    initial = args.h5.stat()
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        if ({table["day_seconds"] for table in tables} != set(range(start, start + 28 * DAY, DAY))
                or sum(table["rows"] for table in tables) != QUIC22_S_ROWS):
            raise ValueError("expected the 28 daily tables and 25 million rows of CESNET-QUIC22-S")
        sha256 = h5_pilot.sha256(args.h5)
        periods, rows = h5_pilot.scan(source, tables, windows, encoder, args.chunk_rows, ROUNDING_SECONDS)
    finally:
        source.close()
    after = args.h5.stat()
    if (initial.st_size, initial.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError("H5 changed during hashing or scanning")
    if not periods["pilot"] or not periods["evaluation"]:
        raise ValueError("pilot and evaluation each need eligible rows")

    pilot, evaluation = periods["pilot"], periods["evaluation"]
    ranked, counts = h5_pilot.rank_pilot_services(pilot[0])
    eligible = ranked[(counts >= MIN_SWEEP_PILOT_FLOWS) & ~np.isin(ranked, QUIC22_BACKGROUND)]
    _, _, _, first, last = evaluation
    day = (first // DAY).astype(np.int64)
    within_day = last + ROUNDING_SECONDS <= (day + 1) * DAY
    cohorts = {}
    for name, requested in (("8", 8), ("16", 16), ("all", len(eligible))):
        if requested < 2 or len(eligible) < requested:
            cohorts[name] = {"status": "insufficient_pilot_classes", "requested_classes": requested,
                             "eligible_pilot_classes": len(eligible)}
            continue
        cohorts[name] = evaluate_cohort(pilot, evaluation, day, within_day, encoder.alphabet,
                                        eligible[:requested], compare=True)
    return {
        "source": "CESNET-QUIC22-S",
        "h5_sha256": sha256,
        "backend": source.backend,
        "rows_scanned": rows,
        "windows_utc": {name: [utc(begin), utc(end)] for name, (begin, end) in windows.items()},
        "timestamp_end_margin_seconds": ROUNDING_SECONDS,
        "excluded_background_app_codes": list(QUIC22_BACKGROUND),
        "min_pilot_flows_per_service": MIN_SWEEP_PILOT_FLOWS,
        "eligible_app_codes_ranked_by_pilot_count": eligible.tolist(),
        "cohorts": cohorts,
    }


def run_xs(args, *, compare=False, service_sweep=False):
    initial = args.h5.stat()
    sha256 = h5_pilot.sha256(args.h5)
    if sha256 != args.expected_sha256.lower():
        raise ValueError(f"H5 SHA-256 mismatch: got {sha256}")
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        split = chronological_windows(tables, end_margin_seconds=ROUNDING_SECONDS)
        windows = {name: split[name] for name in ("pilot", "evaluation")}
        periods, rows = h5_pilot.scan(source, tables, windows, encoder, args.chunk_rows, ROUNDING_SECONDS)
    finally:
        source.close()
    after = args.h5.stat()
    if (initial.st_size, initial.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError("H5 changed during hashing or scanning")
    if not periods["pilot"] or not periods["evaluation"]:
        raise ValueError("pilot and evaluation each need eligible rows")
    pilot = periods.pop("pilot")
    evaluation = periods["evaluation"]
    _, _, _, first, last = evaluation
    day = (first // DAY).astype(np.int64)
    within_day = last + ROUNDING_SECONDS <= (day + 1) * DAY
    ranked, counts = h5_pilot.rank_pilot_services(pilot[0])
    if len(ranked) < 8:
        raise ValueError("the pilot window has fewer than eight usable APP codes")
    baseline = evaluate_cohort(pilot, evaluation, day, within_day, encoder.alphabet, ranked[:8], compare=compare)
    if "status" in baseline and not service_sweep:
        raise ValueError(f"baseline classes absent from the eligible holdout: {baseline['missing_holdout_classes']}")
    result = {
        "source": "CESNET-QUICEXT-25 XS",
        "h5_sha256": sha256,
        "backend": source.backend,
        "rows_scanned": rows,
        "windows_utc": {name: [utc(start), utc(stop)] for name, (start, stop) in windows.items()},
        "timestamp_end_margin_seconds": ROUNDING_SECONDS,
        **baseline,
    }
    if service_sweep:
        eligible = ranked[counts >= MIN_SWEEP_PILOT_FLOWS]
        cohorts = {}
        for name, requested in (("16", 16), ("all", len(eligible))):
            if requested < 2 or len(eligible) < requested:
                cohorts[name] = {"status": "insufficient_pilot_classes", "requested_classes": requested,
                                 "eligible_pilot_classes": len(eligible)}
                continue
            cohorts[name] = evaluate_cohort(pilot, evaluation, day, within_day, encoder.alphabet,
                                            eligible[:requested], compare=compare)
        result["service_sweep"] = {
            "baseline_top_pilot_classes": 8,
            "min_pilot_flows_per_service": MIN_SWEEP_PILOT_FLOWS,
            "eligible_app_codes_ranked_by_pilot_count": eligible.tolist(),
            "expanded_cohorts": cohorts,
        }
    return result


def run_simulation():
    rng = np.random.default_rng(SEED)
    num_cells, num_units = 36, 10
    cell_alpha = ALPHA / num_cells
    mass = 1 / (num_cells * num_units)
    coarse_optimum = 0.5 / num_cells
    scenarios = []
    for shared, probabilities in (
        (False, np.full(num_units, 0.5)),
        (True, np.full(num_units, 0.5)),
        (False, np.tile([0.1, 0.9], num_units // 2)),
    ):
        failures = 0
        for start in range(0, TRIALS, 1_000):
            batch_size = min(TRIALS - start, 1_000)
            bits = rng.random((batch_size, 1 if shared else num_cells, num_units)) < probabilities
            # Each bit jointly sets timing equal to the label or flips it for
            # every record in its balanced cell and block.
            lower = product_lower(bits * mass, cell_alpha)
            failures += int((lower > coarse_optimum).any(axis=1).sum())
        all_correct = float(probabilities.prod())
        exact_cell_error = all_correct if product_lower(np.full(num_units, mass), cell_alpha) > coarse_optimum else 0.0
        exact_family_error = exact_cell_error if shared else -math.expm1(num_cells * math.log1p(-exact_cell_error))
        scenarios.append({
            "shared_bits_across_cells": shared,
            "unit_success_probabilities": probabilities.tolist(),
            "true_bayes_gain": abs(float(probabilities.mean()) - 0.5),
            "families_with_false_positive": failures,
            "estimated_family_false_positive_rate": failures / TRIALS,
            "monte_carlo_one_sided_95pct_upper": float(beta.ppf(0.95, failures + 1, TRIALS - failures)),
            "exact_family_false_positive_rate": exact_family_error,
        })
    return {"seed": SEED, "trials_per_scenario": TRIALS, "cells": num_cells, "units": num_units,
            "family_alpha": ALPHA, "scenarios": scenarios}


def print_block_results(cohort, *, compare):
    if "status" in cohort:
        print(f"  {cohort['status']}: {cohort.get('missing_holdout_classes', cohort.get('eligible_pilot_classes'))}")
        return
    for width, row in cohort["results_by_block_width"].items():
        if compare:
            bounds = row["certificate_comparison"]
            print(f"{width}: " + " | ".join(f"{name} {100 * bound['lower']:+.5f} pp"
                                            for name, bound in bounds.items()))
            if "mutable_mass_weighted_cells" in row:
                weighted = row["mutable_mass_weighted_cells"]
                print(f"  Mutable-mass weights: cell product {100 * weighted['cell_product_lower']:+.5f} pp | "
                      f"cell Hoeffding {100 * weighted['cell_hoeffding_lower']:+.5f} pp")
        else:
            print(f"{width}: {row['positive_cells']}/{row['occupied_coarse_cells']} positive cells, "
                  f"gain lower {100 * row['conditional_bayes_gain_lower']:+.5f} pp")


def print_cohorts(cohorts, *, compare):
    for name, cohort in cohorts.items():
        selected = len(cohort.get("classes_in_count_order", ()))
        print(f"Service cohort {name} ({selected} selected APP codes)")
        if "results_by_block_width" in cohort:
            daily = cohort["results_by_block_width"]["1d"]
            print(f"  Retained {daily['flows']:,} flows, {daily['sampling_units']} days, "
                  f"{daily['occupied_coarse_cells']} coarse cells, "
                  f"sample Bayes gain {100 * daily['sample_bayes_gain']:+.5f} pp")
        print_block_results(cohort, compare=compare)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    quic22 = modes.add_parser("quic22")
    quic22.add_argument("--prefix-dir", type=Path, default=ROOT / "data/quic_timing_pilot")
    quic22.add_argument("--weighted-cells", action="store_true",
                        help="compare uniform and mutable-mass-weighted cell error allocations")
    quic22_s = modes.add_parser("quic22-s")
    xs = modes.add_parser("xs")
    for mode in (xs, quic22_s):
        mode.add_argument("--h5", type=Path, required=True)
        mode.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
        mode.add_argument("--chunk-rows", type=int, default=20_000)
    xs.add_argument("--expected-sha256", required=True)
    xs.add_argument("--service-sweep", action="store_true", help="also evaluate 16 and all eligible pilot APP codes")
    simulation = modes.add_parser("simulate")
    for mode in (quic22, xs):
        mode.add_argument("--compare", action="store_true", help="include four matched pooled and cell bounds")
    for mode in (quic22, quic22_s, xs, simulation):
        mode.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or getattr(args, "chunk_rows", 1) <= 0:
        parser.error("use a new output path and a positive chunk size")
    if args.mode == "simulate":
        result = run_simulation()
    elif args.mode == "quic22":
        args.compare = args.compare or args.weighted_cells
        result = run_quic22(args.prefix_dir, compare=args.compare, weighted_cells=args.weighted_cells)
        if args.weighted_cells:
            result["weighted_allocation_protocol"] = (
                "Exploratory comparison of fixed allocations on the same holdout. "
                "Coverage applies to each allocation and block width under its conditional block model."
            )
    elif args.mode == "quic22-s":
        result = run_quic22_s(args)
    else:
        result = run_xs(args, compare=args.compare, service_sweep=args.service_sweep)
    if args.mode != "simulate":
        result["target"] = "Bayes accuracy gain from adding timing, conditional on coarse inputs, labels and grouping"
        result["block_independence_is_assumed"] = True
        result["primary_block_width"] = "1d"
        if "service_sweep" in result:
            sweep = result["service_sweep"]
            print_cohorts({"8": result, **sweep["expanded_cohorts"]}, compare=args.compare)
        elif args.mode == "quic22-s":
            print_cohorts(result["cohorts"], compare=True)
        else:
            print_block_results(result, compare=args.compare)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
