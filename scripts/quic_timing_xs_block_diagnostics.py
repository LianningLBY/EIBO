#!/usr/bin/env python3
"""Stress-test XS calendar blocks and complete the 44-class prior comparison."""

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
from quic_timing_cell_certificate import BLOCK_DAYS, ROUNDING_SECONDS, cell_certificate, product_lower
from quic_timing_temporal_check import REFERENCE, check_windows
from quic_timing_xs_pooled_ablation import TEMPORAL
from quic_timing_xs_sensitivity import check_archived_bounds


REFIT = REFERENCE.with_name("if_e1_timing_xs_refit_20261112_154300.json")
FROZEN_SCENARIOS = {
    "frequency_equal": ("frequency", "equal"),
    "frequency_sqrt_pilot_prior": ("frequency", "sqrt"),
    "refitted_frequency_equal": ("refitted_frequency_sqrt_pilot_prior", "equal"),
    "refitted_frequency_sqrt_pilot_prior": ("refitted_frequency_sqrt_pilot_prior", "sqrt"),
}


def lag_correlations(rates):
    result = []
    for lag in range(1, 8):
        left, right = rates[:-lag], rates[lag:]
        keep = np.isfinite(left) & np.isfinite(right)
        left, right = left[keep], right[keep]
        correlation = None
        if len(left) >= 3 and np.ptp(left) > 0 and np.ptp(right) > 0:
            correlation = float(np.corrcoef(left, right)[0, 1])
        result.append({"lag_days": lag, "pairs": len(left), "correlation": correlation})
    return result


def daily_score_diagnostics(blocks, window):
    days = np.arange(window[0] // DAY, window[1] // DAY)
    positions = np.asarray(blocks["groups"]) - days[0]
    scores, masses = np.zeros(len(days)), np.zeros(len(days))
    scores[positions], masses[positions] = blocks["scores"], blocks["mutable_masses"]
    rates = np.divide(scores, masses, out=np.full(len(days), np.nan), where=masses > 0)
    return {
        "daily_scores": [
            {"date_utc": utc(int(day) * DAY)[:10], "mutable_correct_weight": float(score),
             "mutable_weight": float(mass), "correct_fraction": float(rate) if mass > 0 else None}
            for day, score, mass, rate in zip(days, scores, masses, rates)
        ],
        "lag_correlations": lag_correlations(rates),
    }


def block_offsets(blocks, archived):
    days = np.asarray(blocks["groups"])
    offset = blocks["fixed_correct_minus_coarse_optimum"]
    results = {}
    for width in BLOCK_DAYS:
        name = f"{width}d"
        expected = archived["results_by_block_width"][name]
        method = expected["certificate_comparison"]["pooled_product"]
        alpha = method["alpha"]
        phases = []
        for phase in range(width):
            units, inverse = np.unique((days - phase) // width, return_inverse=True)
            scores = np.bincount(inverse, weights=blocks["scores"])
            masses = np.bincount(inverse, weights=blocks["mutable_masses"])
            active_scores = scores[masses > 0]
            lower = float(offset + product_lower(active_scores, alpha))
            phases.append({
                "start_day_mod_width": phase,
                "sampling_units": len(units),
                "mutable_units": len(active_scores),
                "alpha_pointwise": alpha,
                "untruncated_lower": lower,
                "lower": max(0.0, lower),
            })
        baseline = phases[0]
        if (baseline["sampling_units"] != expected["sampling_units"]
                or baseline["mutable_units"] != method["mutable_units"]
                or not np.isclose(baseline["untruncated_lower"], method["untruncated_lower"], rtol=0, atol=1e-10)):
            raise RuntimeError(f"the zero-offset {name} result disagrees with the archived pooled product bound")
        results[name] = phases
    return results


def prior_comparison(labels, coarse, fine, day, model, period, alpha):
    old = model["holdouts"][period]
    rules = {name: np.asarray(rule) for name, rule in model["fine_rules"].items()}
    priors = {
        "equal": np.asarray(model["scenario_priors"]["frequency_equal"]),
        "sqrt": np.asarray(model["scenario_priors"]["frequency_sqrt_pilot_prior"]),
    }
    results = {}
    for name, (rule, prior) in FROZEN_SCENARIOS.items():
        widths = {
            f"{width}d": cell_certificate(labels, coarse, fine, day // width, priors[prior], rules[rule],
                                          compare=True, alpha=alpha)
            for width in BLOCK_DAYS
        }
        if name in old:
            check_archived_bounds({"results_by_block_width": widths}, old[name])
        results[name] = {
            "fitted_prior": "equal" if rule == "frequency" else "sqrt",
            "evaluation_prior": prior,
            "results_by_block_width": {
                width: {
                    key: row[key] for key in ("sample_bayes_gain", "frozen_rule_minus_sample_coarse_optimum",
                                              "certificate_comparison")
                } for width, row in widths.items()
            },
        }
    return results


def evaluate_window(data, window, classes, temporal_model, refit_model, archived, period, refit_alpha):
    apps, coarse, fine, first, last = data
    day = (first // DAY).astype(np.int64)
    keep = np.isin(apps, classes) & (last + ROUNDING_SECONDS <= (day + 1) * DAY)
    labels = np.searchsorted(classes, apps[keep])
    coarse, fine, day = coarse[keep], fine[keep], day[keep]
    daily = archived["results_by_block_width"]["1d"]
    pooled = cell_certificate(labels, coarse, fine, day, np.full(len(classes), 1 / len(classes)),
                              np.asarray(temporal_model["fine_rule"]), compare=True,
                              alpha=daily["family_alpha"], report_pooled_blocks=True)
    if pooled["class_counts"] != daily["class_counts"]:
        raise RuntimeError("the daily class counts disagree with the archived cohort")
    blocks = pooled["pooled_blocks"]
    return {
        "flows": pooled["flows"],
        "class_counts": pooled["class_counts"],
        **daily_score_diagnostics(blocks, window),
        "pooled_product_by_block_offset": block_offsets(blocks, archived),
        "prior_comparison": prior_comparison(labels, coarse, fine, day, refit_model, period, refit_alpha),
    }


def run(args):
    archive_bytes = {key: path.read_bytes() for key, path in
                     (("sweep", REFERENCE), ("temporal", TEMPORAL), ("refit", REFIT))}
    hashes = {key: hashlib.sha256(data).hexdigest() for key, data in archive_bytes.items()}
    reference, temporal, refit = (json.loads(archive_bytes[key]) for key in ("sweep", "temporal", "refit"))
    digest = reference["h5_sha256"]
    if (temporal["reference_sweep_sha256"] != hashes["sweep"] or refit["reference_sweep_sha256"] != hashes["sweep"]
            or {temporal["pilot_h5_sha256"], temporal["holdout_h5_sha256"], refit["h5_sha256"]} != {digest}):
        raise ValueError("the XS sweep, temporal, and refit archives do not share the same source")
    original_cohort = reference["service_sweep"]["expanded_cohorts"]["all"]
    temporal_cohort, refit_cohort = temporal["cohorts"]["44"], refit["cohorts"]["44"]
    classes = np.asarray(temporal_cohort["classes_in_count_order"])
    if (classes.tolist() != original_cohort["classes_in_count_order"]
            or classes.tolist() != refit_cohort["app_codes"]
            or temporal_cohort["fit_counts"] != original_cohort["fit_counts"]
            or temporal_cohort["fit_counts"] != refit_cohort["pilot_class_counts"]
            or temporal_cohort["fine_rule"] != refit_cohort["fine_rules"]["frequency"]):
        raise ValueError("the archived 44-class fitting cohorts or frequency rules differ")

    initial = file_state(args.xs_h5)
    if h5_pilot.sha256(args.xs_h5) != digest:
        raise ValueError("the XS H5 does not match the registered sweep")
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    source = FlowSource(args.xs_h5, args.backend)
    try:
        tables = source.tables()
        split = chronological_windows(tables, end_margin_seconds=ROUNDING_SECONDS)
        check_windows(split, reference)
        windows = {"original": split["evaluation"], "temporal": split["certificate"]}
        dates = {key: [utc(value) for value in window] for key, window in windows.items()}
        if (dates["temporal"] != temporal["holdout_utc"]
                or {**dates, "pilot": reference["windows_utc"]["pilot"]} != refit["windows_utc"]):
            raise ValueError("the temporal and refit archives do not match the registered XS windows")
        periods, rows = h5_pilot.scan(source, tables, windows, encoder, args.chunk_rows, ROUNDING_SECONDS)
    finally:
        source.close()
    if file_state(args.xs_h5) != initial:
        raise RuntimeError("the XS H5 changed during hashing or scanning")
    if any(not data for data in periods.values()):
        raise ValueError("both registered holdouts must contain usable flows")

    archived = {"original": original_cohort, "temporal": temporal_cohort}
    return {
        "source": "CESNET-QUICEXT-25 XS",
        "h5_sha256": digest,
        "archive_sha256": hashes,
        "rows_scanned": rows,
        "windows_utc": dates,
        "app_codes": classes.tolist(),
        "scenario_priors": refit_cohort["scenario_priors"],
        "block_offset_definition": "floor((UTC day index since 1970-01-01 minus offset) / width)",
        "diagnostic_only": "Lag correlations are descriptive. Each offset bound is pointwise under "
                           "conditional independence for that partition.",
        "results": {
            key: evaluate_window(data, windows[key], classes, temporal_cohort, refit_cohort, archived[key],
                                 key, refit["alpha_per_fixed_bound"])
            for key, data in periods.items()
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xs-h5", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.chunk_rows <= 0:
        parser.error("use a new output path and a positive chunk size")
    result = run(args)
    write_json(args.out, result)
    for period, row in result["results"].items():
        lag = row["lag_correlations"][0]
        correlation = lag["correlation"]
        text = "undefined" if correlation is None else f"{correlation:+.3f}"
        print(f"{period} | {row['flows']:,} flows | daily lag-1 correlation {text} ({lag['pairs']} pairs)")
        for width, phases in row["pooled_product_by_block_offset"].items():
            bounds = " | ".join(f"offset {p['start_day_mod_width']}: {100 * p['lower']:+.5f} pp" for p in phases)
            print(f"  {width} pooled product: {bounds}")
        for name, scenario in row["prior_comparison"].items():
            daily = scenario["results_by_block_width"]["1d"]["certificate_comparison"]
            print(f"  {name}: cell product {100 * daily['cell_product']['lower']:+.5f} pp | "
                  f"pooled product {100 * daily['pooled_product']['lower']:+.5f} pp")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
