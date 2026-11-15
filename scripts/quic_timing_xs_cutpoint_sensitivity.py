#!/usr/bin/env python3
"""Compare three timing encodings on the two archived XS 44-class cohorts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

import quic_timing_pilot as timing
import quic_timing_pilot_h5 as h5_pilot
from eibo.realdata import DAY, FlowSource, chronological_windows, utc
from if_e1_fusion_validate import file_state, write_json
from quic_timing_cell_certificate import ROUNDING_SECONDS, cell_certificate, product_lower
from quic_timing_temporal_check import FAMILY_ALPHA, REFERENCE, check_windows


TEMPORAL = REFERENCE.with_name("if_e1_timing_temporal_xs_20261112_150118.json")
QUANTILE_LEVELS = (0.10, 0.25, 0.40, 0.60, 0.75, 0.90)
CANDIDATE_CERTIFICATES = ("pooled_hoeffding", "pooled_product", "cell_hoeffding", "cell_product")


def cutpoint_designs(pilot_ms):
    """Choose distinct cuts from the positive pilot support, preserving the zero bin."""
    support, counts = np.unique(pilot_ms[pilot_ms > 0], return_counts=True)
    if len(support) <= len(QUANTILE_LEVELS):
        raise ValueError("the pilot needs at least seven distinct positive packet intervals")
    cumulative = counts.cumsum() / counts.sum()
    positions = []
    for i, q in enumerate(QUANTILE_LEVELS):
        first = positions[-1] + 1 if positions else 0
        last = len(support) - 1 - (len(QUANTILE_LEVELS) - i)
        positions.append(int(np.clip(np.searchsorted(cumulative, q), first, last)))

    designs = {"registered": {"cuts_ms": list(timing.TIMING_CUTS_MS)}}
    registered = tuple(np.searchsorted(support, timing.TIMING_CUTS_MS[1:], side="right") - 1)
    for grid in ((0, 2, 4), (1, 3, 5), (0, 2, 5)):
        indices = tuple(positions[i] for i in grid)
        if indices == registered:
            continue
        designs[f"pilot_quantile_{len(designs)}"] = {
            "cuts_ms": [0, *[support[i].item() for i in indices]],
            "target_quantiles_of_positive_pilot_intervals": [QUANTILE_LEVELS[i] for i in grid],
            "achieved_pilot_cdf": cumulative[list(indices)].tolist(),
        }
        if len(designs) == 3:
            break
    return designs


def pooled_at_alpha(blocks, alpha):
    scores = np.asarray(blocks["scores"])[np.asarray(blocks["mutable_masses"]) > 0]
    lower = float(blocks["fixed_correct_minus_coarse_optimum"] + product_lower(scores, alpha))
    return {"alpha": alpha, "untruncated_lower": lower, "lower": max(0.0, lower)}


def apply_simultaneous_bounds(report):
    windows = report["windows"]
    family_size = len(CANDIDATE_CERTIFICATES) * sum(len(row["encodings"]) for row in windows.values())
    alpha = FAMILY_ALPHA / family_size
    report["simultaneous_candidate_certificates"] = list(CANDIDATE_CERTIFICATES)
    report["simultaneous_family_size"] = family_size
    report["simultaneous_family_alpha"] = FAMILY_ALPHA
    report["simultaneous_alpha_per_bound"] = alpha
    for window in windows.values():
        for encoding in window["encodings"].values():
            encoding["pooled_product_simultaneous"] = pooled_at_alpha(encoding["pooled_blocks"], alpha)


def verify_baseline(result, archived, period):
    expected = archived["results_by_block_width"]["1d"]
    expected_bound = expected["certificate_comparison"]["pooled_product"]
    for key in ("flows", "class_counts", "sampling_units", "occupied_coarse_cells"):
        if result[key] != expected[key]:
            raise ValueError(f"{period}: registered timing {key} disagrees with the archive")
    actual_bound = pooled_at_alpha(result["pooled_blocks"], expected_bound["alpha"])
    actual = [result["sample_bayes_gain"], result["frozen_rule_minus_sample_coarse_optimum"],
              actual_bound["untruncated_lower"], actual_bound["lower"]]
    reference = [expected["sample_bayes_gain"], expected["frozen_rule_minus_sample_coarse_optimum"],
                 expected_bound["untruncated_lower"], expected_bound["lower"]]
    np.testing.assert_allclose(actual, reference, rtol=0, atol=1e-10, err_msg=period)
    return actual_bound


def evaluate_window(data, classes, priors, designs, archived, period):
    apps, coarse, interval, first, last = data
    day = (first // DAY).astype(np.int64)
    fitted = np.isin(apps, classes)
    within_day = last + ROUNDING_SECONDS <= (day + 1) * DAY
    keep = fitted & within_day
    for key, count in (("evaluation_fitted_class_flows_before_daily_guard", fitted.sum()),
                       ("excluded_fitted_class_flows_crossing_day_boundary", (fitted & ~within_day).sum())):
        if count != archived[key]:
            raise ValueError(f"{period}: {key} disagrees with the archive")
    labels = np.searchsorted(classes, apps[keep])
    coarse, interval, day = coarse[keep], interval[keep], day[keep]

    results = {}
    for name, design in designs.items():
        bins = np.searchsorted(design["cuts_ms"], interval, side="left")
        fine = coarse * timing.TIMING_BINS + bins
        result = cell_certificate(labels, coarse, fine, day, priors, design["fine_rule"], compare=True,
                                  alpha=FAMILY_ALPHA, report_pooled_blocks=True)
        blocks = result["pooled_blocks"]
        results[name] = {
            "bin_counts": np.bincount(bins, minlength=timing.TIMING_BINS).tolist(),
            "sample_bayes_gain": result["sample_bayes_gain"],
            "frozen_rule_minus_sample_coarse_optimum": result["frozen_rule_minus_sample_coarse_optimum"],
            "pooled_product_pointwise": result["certificate_comparison"]["pooled_product"],
            "pooled_blocks": blocks,
        }
        if name == "registered":
            results[name]["reproduced_archived_bound"] = verify_baseline(result, archived, period)

    return {
        "flows": len(labels),
        "class_counts": np.bincount(labels, minlength=len(classes)).tolist(),
        "sampling_units": len(np.unique(day)),
        "encodings": results,
    }


def run(args):
    sweep_bytes, temporal_bytes = REFERENCE.read_bytes(), TEMPORAL.read_bytes()
    sweep, temporal = json.loads(sweep_bytes), json.loads(temporal_bytes)
    sweep_hash = hashlib.sha256(sweep_bytes).hexdigest()
    digest = sweep["h5_sha256"]
    if (temporal["reference_sweep_sha256"] != sweep_hash
            or temporal["pilot_h5_sha256"] != digest or temporal["holdout_h5_sha256"] != digest):
        raise ValueError("the XS sweep and temporal archives do not share the same source")
    original, retrospective = sweep["service_sweep"]["expanded_cohorts"]["all"], temporal["cohorts"]["44"]
    classes = np.asarray(original["classes_in_count_order"])
    if (len(classes) != 44 or np.any(np.diff(classes) <= 0)
            or classes.tolist() != retrospective["classes_in_count_order"]
            or original["fit_counts"] != retrospective["fit_counts"]):
        raise ValueError("the two archived windows do not use the same 44-class fit")

    state = file_state(args.xs_h5)
    if h5_pilot.sha256(args.xs_h5) != digest:
        raise ValueError("the XS H5 does not match the registered sweep")
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    source = FlowSource(args.xs_h5, args.backend)
    try:
        tables = source.tables()
        split = chronological_windows(tables, end_margin_seconds=ROUNDING_SECONDS)
        check_windows(split, sweep)
        windows = {"pilot": split["pilot"], "original": split["evaluation"], "retrospective": split["certificate"]}
        dates = {key: [utc(value) for value in window] for key, window in windows.items()}
        if dates["pilot"] != temporal["pilot_utc"] or dates["retrospective"] != temporal["holdout_utc"]:
            raise ValueError("the retrospective and pilot windows differ from the archive")
        periods, rows = h5_pilot.scan(source, tables, windows, encoder, args.chunk_rows, ROUNDING_SECONDS,
                                      raw_timing=True)
    finally:
        source.close()
    if file_state(args.xs_h5) != state:
        raise RuntimeError("the XS H5 changed during hashing or scanning")
    if rows != sweep["rows_scanned"] or any(not data for data in periods.values()):
        raise ValueError("the scan must match the archive size and populate all three windows")

    apps, coarse, interval, _, _ = periods.pop("pilot")
    keep = np.isin(apps, classes)
    labels, coarse, interval = np.searchsorted(classes, apps[keep]), coarse[keep], interval[keep]
    priors = np.full(len(classes), 1 / len(classes))
    if np.bincount(labels, minlength=len(classes)).tolist() != original["fit_counts"]:
        raise ValueError("the pilot class counts disagree with the archive")
    designs = cutpoint_designs(interval)
    for design in designs.values():
        bins = np.searchsorted(design["cuts_ms"], interval, side="left")
        _, design["fine_rule"], _ = timing.fit_rules(labels, coarse, coarse * timing.TIMING_BINS + bins,
                                                     priors, encoder.alphabet)
        design["pilot_bin_counts"] = np.bincount(bins, minlength=timing.TIMING_BINS).tolist()
    if designs["registered"]["fine_rule"].tolist() != retrospective["fine_rule"]:
        raise ValueError("the registered cuts did not reproduce the archived frequency rule")

    archives = {"original": original, "retrospective": retrospective}
    results = {period: evaluate_window(periods[period], classes, priors, designs, archived, period)
               for period, archived in archives.items()}
    for design in designs.values():
        design["fine_rule"] = design["fine_rule"].tolist()
    return {
        "design": "retrospective XS timing cutpoint sensitivity on the two previously evaluated windows",
        "h5_sha256": digest,
        "archive_sha256": {"sweep": sweep_hash, "temporal": hashlib.sha256(temporal_bytes).hexdigest()},
        "backend": source.backend,
        "rows_scanned": rows,
        "windows_utc": dates,
        "app_codes": classes.tolist(),
        "pilot_class_counts": original["fit_counts"],
        "class_prior": priors.tolist(),
        "block_width_days": 1,
        "block_independence_is_assumed": True,
        "pointwise_alpha_per_bound": FAMILY_ALPHA,
        "encodings": designs,
        "windows": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--xs-h5", type=Path)
    source.add_argument("--from-archive", type=Path, help="recompute the simultaneous bounds from archived block scores")
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.chunk_rows <= 0:
        parser.error("use a new output path and a positive chunk size")
    if args.from_archive is None:
        result = run(args)
        print("PASS: registered cuts reproduced the archived rule and both daily bounds")
    else:
        result = json.loads(args.from_archive.read_text())
    apply_simultaneous_bounds(result)
    write_json(args.out, result)
    print(f"Simultaneous tail probability per bound: {FAMILY_ALPHA:g}/{result['simultaneous_family_size']}")
    for period, row in result["windows"].items():
        print(f"{period}: {row['flows']:,} flows | {row['sampling_units']} daily blocks")
        for name, entry in row["encodings"].items():
            cuts = result["encodings"][name]["cuts_ms"]
            print(f"  {name} {cuts} ms | sample gain {100 * entry['sample_bayes_gain']:+.5f} pp | "
                  f"pointwise lower {100 * entry['pooled_product_pointwise']['lower']:+.5f} pp | "
                  f"simultaneous lower {100 * entry['pooled_product_simultaneous']['lower']:+.5f} pp")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
