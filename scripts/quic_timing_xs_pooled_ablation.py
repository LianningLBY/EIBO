#!/usr/bin/env python3
"""Recompute the pooled product certificate after omitting the leading XS cell."""

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
from quic_timing_cell_certificate import ROUNDING_SECONDS, evaluate_frozen_cohort
from quic_timing_temporal_check import REFERENCE, check_windows
from quic_timing_xs_sensitivity import check_archived_bounds


TEMPORAL = REFERENCE.with_name("if_e1_timing_temporal_xs_20261112_150118.json")


def evaluate_window(data, archive, classes, priors, fine_rule, symbol):
    _, _, _, first, last = data
    day = (first // DAY).astype(np.int64)
    within_day = last + ROUNDING_SECONDS <= (day + 1) * DAY
    alpha = archive["results_by_block_width"]["1d"]["family_alpha"]
    result = evaluate_frozen_cohort(data, day, within_day, classes, priors, fine_rule,
                                    compare=True, alpha=alpha, pooled_omit_symbol=symbol)
    if "status" in result:
        raise RuntimeError(f"holdout cannot reproduce the archived cohort: {result['status']}")
    check_archived_bounds(result, archive)
    return {
        width: {
            "flows": row["flows"],
            "sampling_units": row["sampling_units"],
            "occupied_coarse_cells": row["occupied_coarse_cells"],
            "full_pooled_product": row["certificate_comparison"]["pooled_product"],
            "pooled_product_without_symbol": row["pooled_product_ablation"],
        }
        for width, row in result["results_by_block_width"].items()
    }


def run(args):
    reference_bytes = REFERENCE.read_bytes()
    temporal_bytes = TEMPORAL.read_bytes()
    reference = json.loads(reference_bytes)
    temporal = json.loads(temporal_bytes)
    reference_hash = hashlib.sha256(reference_bytes).hexdigest()
    initial = file_state(args.xs_h5)
    digest = h5_pilot.sha256(args.xs_h5)
    if (digest != reference["h5_sha256"] or digest != temporal["pilot_h5_sha256"]
            or digest != temporal["holdout_h5_sha256"]
            or reference_hash != temporal["reference_sweep_sha256"]):
        raise ValueError("the H5 and the two XS archives do not match")

    original_cohort = reference["service_sweep"]["expanded_cohorts"]["all"]
    temporal_cohort = temporal["cohorts"]["44"]
    fields = ("classes_in_count_order", "fit_counts")
    if any(original_cohort[key] != temporal_cohort[key] for key in fields):
        raise ValueError("the archived 44-class fitting cohorts differ")
    original_cells = original_cohort["results_by_block_width"]["1d"]["cells"]
    leading = max(original_cells, key=lambda row: (row["bayes_gain_lower_contribution"], -row["coarse_symbol"]))
    if leading["bayes_gain_lower_contribution"] <= 0:
        raise ValueError("the original daily result has no positive cell contribution")
    symbol = leading["coarse_symbol"]
    classes = np.asarray(temporal_cohort["classes_in_count_order"])
    priors = np.full(len(classes), 1 / len(classes))
    fine_rule = np.asarray(temporal_cohort["fine_rule"])

    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    source = FlowSource(args.xs_h5, args.backend)
    try:
        tables = source.tables()
        split = chronological_windows(tables, end_margin_seconds=ROUNDING_SECONDS)
        check_windows(split, reference)
        windows = {"original": split["evaluation"], "temporal": split["certificate"]}
        window_dates = {name: [utc(value) for value in window] for name, window in windows.items()}
        if window_dates["temporal"] != temporal["holdout_utc"] or temporal["pilot_utc"] != reference["windows_utc"]["pilot"]:
            raise ValueError("the temporal archive does not match the registered XS windows")
        periods, rows = h5_pilot.scan(source, tables, windows, encoder, args.chunk_rows, ROUNDING_SECONDS)
    finally:
        source.close()
    if file_state(args.xs_h5) != initial:
        raise RuntimeError("the XS H5 changed during hashing or scanning")
    if any(not data for data in periods.values()):
        raise ValueError("both registered holdouts must contain usable flows")

    archives = {"original": original_cohort, "temporal": temporal_cohort}
    return {
        "source": "CESNET-QUICEXT-25 XS",
        "h5_sha256": digest,
        "reference_sweep_sha256": reference_hash,
        "temporal_sha256": hashlib.sha256(temporal_bytes).hexdigest(),
        "rows_scanned": rows,
        "windows_utc": window_dates,
        "app_codes": classes.tolist(),
        "omitted_symbol": symbol,
        "selection": "Largest original daily cell-product contribution",
        "target": "Bayes accuracy gain summed over retained symbols with original cohort weights",
        "block_independence_is_assumed": True,
        "results": {name: evaluate_window(data, archives[name], classes, priors, fine_rule, symbol)
                    for name, data in periods.items()},
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
    print(f"Omitted symbol: {result['omitted_symbol']}")
    for name, windows in result["results"].items():
        for width, row in windows.items():
            ablation = row["pooled_product_without_symbol"]
            print(f"{name} {width}: full {100 * row['full_pooled_product']['lower']:+.5f} pp | "
                  f"without symbol, pointwise {100 * ablation['pointwise_lower']:+.5f} pp | "
                  f"without symbol, simultaneous over omissions {100 * ablation['singleton_simultaneous_lower']:+.5f} pp")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
