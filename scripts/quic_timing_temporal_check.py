#!/usr/bin/env python3
"""Check the fixed XS timing cohorts on a disjoint UTC evaluation window."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import numpy as np

import quic_timing_pilot as timing
import quic_timing_pilot_h5 as h5_pilot
from eibo.realdata import DAY, FlowSource, chronological_windows, utc
from if_e1_fusion_validate import capture_day, file_state, read_json, write_json
from quic_timing_cell_certificate import ROUNDING_SECONDS, evaluate_frozen_cohort, print_block_results


REFERENCE = (Path(__file__).resolve().parents[1]
             / "artifacts/methodology/if_e1_timing_service_sweep_xs_20261112_125904.json")
PRIMARY = {"16": "cell_product", "44": "pooled_product"}
FAMILY_ALPHA = 0.05


def check_windows(split, reference):
    for name in ("pilot", "evaluation"):
        if [utc(value) for value in split[name]] != reference["windows_utc"][name]:
            raise ValueError(f"the registered XS {name} window differs from the service sweep")


def frozen_models(pilot, alphabet, reference):
    cohorts = reference["service_sweep"]["expanded_cohorts"]
    models = {}
    for name, reference_name in (("16", "16"), ("44", "all")):
        expected = cohorts[reference_name]
        classes, priors, _, fine_rule, counts = h5_pilot.fit(
            pilot, alphabet, classes=expected["classes_in_count_order"])
        if len(classes) != int(name) or counts.tolist() != expected["fit_counts"]:
            raise ValueError(f"the {name}-class pilot counts differ from the registered sweep")
        models[name] = (classes, priors, fine_rule, counts)
    return models


def evaluate_holdout(holdout, models):
    if not holdout:
        raise ValueError("the temporal window has no eligible flows")
    _, _, _, first, last = holdout
    day = (first // DAY).astype(np.int64)
    within_day = last + ROUNDING_SECONDS <= (day + 1) * DAY
    per_cohort_alpha = FAMILY_ALPHA / len(PRIMARY)
    results = {}
    for name, (classes, priors, fine_rule, counts) in models.items():
        result = evaluate_frozen_cohort(holdout, day, within_day, classes, priors, fine_rule,
                                        compare=True, alpha=per_cohort_alpha)
        method = PRIMARY[name]
        primary_lower = (result["results_by_block_width"]["1d"]["certificate_comparison"][method]["lower"]
                         if "results_by_block_width" in result else None)
        results[name] = {
            **result,
            "fit_counts": counts.tolist(),
            "fine_rule": fine_rule.tolist(),
            "primary_method": method,
            "primary_daily_lower": primary_lower,
        }
    return results


def scan_later(args, encoder, archive_end, archive_hash):
    start, stop = args.later_window
    if start < archive_end + DAY or stop <= start:
        raise ValueError("the later window must start at least one day after the archived end and have positive length")
    initial = file_state(args.later_h5)
    later_hash = h5_pilot.sha256(args.later_h5)
    if later_hash == archive_hash:
        raise ValueError("the later capture must have a different H5 digest")
    source = FlowSource(args.later_h5, args.backend)
    try:
        tables = source.tables()
        calendar = {row["day_seconds"] for row in tables}
        if start < min(calendar) or stop > max(calendar) + DAY:
            raise ValueError("the requested window extends outside the later H5 calendar")
        missing = sorted(set(range(start, stop, DAY)) - calendar)
        periods, rows = h5_pilot.scan(source, tables, {"holdout": (start, stop)}, encoder, args.chunk_rows,
                                      ROUNDING_SECONDS)
    finally:
        source.close()
    if file_state(args.later_h5) != initial:
        raise RuntimeError("the later H5 changed during hashing or scanning")
    return periods["holdout"], (start, stop), later_hash, rows, missing


def run(args):
    reference = read_json(REFERENCE)
    initial = file_state(args.xs_h5)
    archive_hash = h5_pilot.sha256(args.xs_h5)
    if archive_hash != reference["h5_sha256"]:
        raise ValueError(f"the original XS H5 does not match the registered service sweep: got {archive_hash}")
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    source = FlowSource(args.xs_h5, args.backend)
    try:
        tables = source.tables()
        split = chronological_windows(tables, end_margin_seconds=ROUNDING_SECONDS)
        check_windows(split, reference)
        windows = {"pilot": split["pilot"]}
        if args.later_h5 is None:
            windows["holdout"] = split["certificate"]
        periods, archive_rows = h5_pilot.scan(source, tables, windows, encoder, args.chunk_rows, ROUNDING_SECONDS)
    finally:
        source.close()
    if file_state(args.xs_h5) != initial:
        raise RuntimeError("the original XS H5 changed during hashing or scanning")
    if not periods["pilot"]:
        raise ValueError("the registered pilot has no eligible flows")
    models = frozen_models(periods.pop("pilot"), encoder.alphabet, reference)

    if args.later_h5 is None:
        window = windows["holdout"]
        holdout = periods["holdout"]
        holdout_hash, holdout_rows = archive_hash, archive_rows
        calendar = {row["day_seconds"] for row in tables}
        missing = sorted(set(range(*window, DAY)) - calendar)
        design = "time_disjoint_middle_window_in_existing_xs"
    else:
        holdout, window, holdout_hash, holdout_rows, missing = scan_later(
            args, encoder, split["evaluation"][1], archive_hash)
        design = "later_capture_with_confirmed_xs_app_codes"

    cohorts = evaluate_holdout(holdout, models)
    primary = [result["primary_daily_lower"] for result in cohorts.values()]
    return {
        "design": design,
        "target": "Conditional class-weighted Bayes accuracy gain from adding timing",
        "reference_sweep_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        "pilot_h5_sha256": archive_hash,
        "holdout_h5_sha256": holdout_hash,
        "pilot_rows_scanned": archive_rows,
        "holdout_rows_scanned": holdout_rows,
        "pilot_utc": [utc(value) for value in split["pilot"]],
        "holdout_utc": [utc(value) for value in window],
        "missing_holdout_calendar_days_utc": [utc(value) for value in missing],
        "primary_block_width": "1d",
        "primary_family_alpha": FAMILY_ALPHA,
        "block_independence_is_assumed": True,
        "both_primary_bounds_positive": None if any(value is None for value in primary) else min(primary) > 0,
        "cohorts": cohorts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xs-h5", type=Path, required=True, help="registered XS H5 used for the original fit")
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    parser.add_argument("--later-h5", type=Path, help="optional compatible capture after the XS archive")
    parser.add_argument("--later-window", type=capture_day, nargs=2, metavar=("START", "STOP"))
    parser.add_argument("--same-app-codes", action="store_true", help="confirm the later capture uses the XS APP codes")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.chunk_rows <= 0:
        parser.error("use a new output path and a positive chunk size")
    if args.later_h5 is None and (args.later_window is not None or args.same_app_codes):
        parser.error("the later-window and same-app-codes options require a later H5")
    if args.later_h5 is not None and (args.later_window is None or not args.same_app_codes):
        parser.error("a later H5 requires a preselected window and confirmed XS APP codes")
    result = run(args)
    write_json(args.out, result)
    print(f"UTC holdout [{result['holdout_utc'][0]}, {result['holdout_utc'][1]})")
    for name, cohort in result["cohorts"].items():
        print(f"{name} classes, primary {cohort['primary_method']}")
        print_block_results(cohort, compare=True)
    print(f"Both primary bounds positive: {result['both_primary_bounds_positive']}")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
