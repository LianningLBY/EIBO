#!/usr/bin/env python3
"""Freeze the IF-E1 follow-up models and evaluate them on later capture days."""

from __future__ import annotations

import argparse
import datetime as dt
import itertools
import json
from pathlib import Path

import numpy as np

from if_e1_fusion_probe import (
    ALPHA, DAY, HOLDOUTS, K, METHODS, ROUNDING_SECONDS, FixedPrefixEncoder,
    FlowSource, PairScores, ScoreQuantizer, bounds, experiment_windows, fit_pair,
    iid_flow_budget, measure, pair_sample, scan, sha256, utc,
)

BUDGET = 8
PRIMARY = (0, 1)
CONTROL_APPS = (1, 2, 3, 4, 14, 16, 51)
CONTROLS = tuple(itertools.combinations(CONTROL_APPS, 2))
PAIRS = (PRIMARY, *CONTROLS)
DEVELOPMENT = ("fit", "stack", "calibration")
SCENARIOS = ("separated_24h", "iid_flow")


def read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path, result):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")


def file_state(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def capture_day(value):
    day = dt.date.fromisoformat(value)
    return int(dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc).timestamp())


def windows_json(windows):
    return {name: [utc(start), utc(stop)] for name, (start, stop) in windows.items()}


def require_samples(samples, apps):
    for name, sample in samples.items():
        missing = [app for app in apps if sample.eligible[app] < 2]
        if missing:
            raise ValueError(f"{name}: fewer than two eligible flows for APP codes {missing}")


def freeze(args):
    discovery = read_json(args.discovery)
    if tuple(discovery["apps"]) != (0, *CONTROL_APPS) or BUDGET not in discovery["output_budgets"]:
        raise ValueError("expected the original IF-E1 APP panel with an 8-bin comparison")
    args.max_per_app = discovery["max_per_app_per_window"]
    args.seed = discovery["seed"]
    if discovery["rounding_seconds"] != ROUNDING_SECONDS:
        raise ValueError("discovery and follow-up must use the same timestamp envelope")
    reference = {tuple(pair["apps"]): pair for pair in discovery["pairs"]}
    initial_state = file_state(args.h5)
    source_hash = sha256(args.h5)
    original = discovery["source"]
    if initial_state[0] != original["bytes"] or original["sha256"] not in (None, source_hash):
        raise ValueError("development H5 does not match the discovery source")
    encoder = FixedPrefixEncoder(K, 2)
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        windows = experiment_windows(tables)
        if len(tables) != original["daily_tables"] or windows_json(windows) != discovery["windows_utc"]:
            raise ValueError("development H5 dates do not match the discovery source")
        samples, _, _ = scan(source, tables, {name: windows[name] for name in DEVELOPMENT}, encoder, args)
    finally:
        source.close()
    if file_state(args.h5) != initial_state:
        raise RuntimeError("development H5 changed during the scan")
    require_samples(samples, (0, *CONTROL_APPS))

    frozen_pairs = []
    for pair in PAIRS:
        model, scores, y = fit_pair(pair, samples, encoder.alphabet)
        maps = {method: ScoreQuantizer.fit(scores[method], y, BUDGET) for method in METHODS}
        strongest = max(METHODS[:2], key=lambda method: maps[method].calibration_accuracy)
        previous = reference[pair]["budgets"][str(BUDGET)]
        if strongest != previous["strongest_single_calibration"]:
            raise ValueError(f"APP {pair}: rebuilt strongest single differs from the discovery run")
        np.testing.assert_allclose(model.stack_parameters, reference[pair]["stack_coefficients_and_intercept"],
                                   rtol=1e-5, atol=1e-7, err_msg=f"APP {pair}: stack parameters differ")
        for method, quantizer in maps.items():
            recorded = previous["maps"][method]
            np.testing.assert_allclose(quantizer.cuts, recorded["cuts"], rtol=1e-5, atol=1e-7,
                                       err_msg=f"APP {pair}, {method}: calibration cuts differ")
            np.testing.assert_array_equal(quantizer.decision, recorded["decision"],
                                          err_msg=f"APP {pair}, {method}: calibrated decisions differ")
            np.testing.assert_allclose(quantizer.calibration_accuracy, recorded["calibration_accuracy"],
                                       rtol=0, atol=1e-10,
                                       err_msg=f"APP {pair}, {method}: calibration accuracy differs")
        frozen_pairs.append({
            "apps": pair, "strongest_single_calibration": strongest,
            "base_parameters": [p.tolist() for p in model.base_parameters],
            "late_base_parameters": [p.tolist() for p in model.late_base_parameters],
            "stack_parameters": model.stack_parameters.tolist(),
            "maps": {method: {"cuts": q.cuts.tolist(), "decision": q.decision.tolist(),
                              "calibration_accuracy": q.calibration_accuracy}
                     for method, q in maps.items()},
        })
    write_json(args.out, {
        "budget": BUDGET, "primary_pair": PRIMARY, "control_pairs": CONTROLS,
        "discovery_sha256": sha256(args.discovery), "development_h5_sha256": source_hash,
        "discovery_windows_utc": discovery["windows_utc"], "rounding_seconds": ROUNDING_SECONDS,
        "max_per_app": args.max_per_app, "seed": args.seed, "pairs": frozen_pairs,
    })
    print(f"Froze 1 primary pair and {len(CONTROLS)} controls: {args.out}", flush=True)


def batch_indices(first, window):
    return ((first - window[0]) // (2 * DAY)).astype(int)


def separated_day_mask(first, last, window):
    end = window[0] + (2 * batch_indices(first, window) + 1) * DAY
    return (end <= window[1]) & (last + ROUNDING_SECONDS <= end)


def app_mapping(args):
    codes = (0, *CONTROL_APPS)
    mapping = ({code: code for code in codes} if args.same_app_codes
               else {int(code): mapped for code, mapped in read_json(args.app_map).items()})
    if set(mapping) != set(codes) or any(type(code) is not int or code < 0 for code in mapping.values()):
        raise ValueError("provide one nonnegative H5 APP code for each of the eight discovery APP codes")
    if len(set(mapping.values())) != len(codes):
        raise ValueError("holdout APP codes must be distinct")
    return mapping


def assess_window(model, maps, strongest, sample, pair, window, tail_alpha):
    rows, y = pair_sample(sample, pair)
    scores = model.predict(rows)
    measured = measure(scores, y, maps, BUDGET, strongest)
    n_by_app = np.bincount(y, minlength=2)
    indices = batch_indices(rows["first"], window)
    mass = np.bincount(indices, weights=(0.5 / n_by_app)[y])
    scenarios = {
        "separated_24h": {"blocks": int(np.count_nonzero(mass)), "squared_mass": float(mass @ mass)},
        "iid_flow": iid_flow_budget(y),
    }
    per_batch = []
    for index in np.flatnonzero(mass):
        keep = indices == index
        counts = np.bincount(y[keep], minlength=2)
        row = {"start_utc": utc(window[0] + 2 * int(index) * DAY), "n_by_app": counts.tolist(),
               "mass": float(mass[index]), "sample_oracle_gap": None, "frozen_accuracy_gain": None}
        if counts.min() > 0:
            batch = measure({name: value[keep] for name, value in scores.items()},
                            y[keep], maps, BUDGET, strongest)
            row["sample_oracle_gap"] = batch["fusion_minus_best_single_sample_oracle"]["late"]
            row["frozen_accuracy_gain"] = batch["frozen_accuracy_gains"]["late"]
        per_batch.append(row)
    measured["n_by_app"] = n_by_app.tolist()
    measured["batches"] = per_batch
    measured["bounds"] = {}
    for name, scenario in scenarios.items():
        interval = bounds(measured, scenario["squared_mass"], tail_alpha)
        measured["bounds"][name] = {
            **scenario, "effective_blocks": 1 / scenario["squared_mass"],
            "radius": interval["radius"], "bayes_gain_lower": interval["bayes_gain_lower_vs_best_single"]["late"],
        }
    return measured


def evaluate(args):
    frozen = read_json(args.frozen)
    if (frozen["budget"] != BUDGET or frozen["rounding_seconds"] != ROUNDING_SECONDS
            or tuple(tuple(record["apps"]) for record in frozen["pairs"]) != PAIRS):
        raise ValueError("model artifact does not contain the fixed IF-E1 follow-up panel")
    codes = app_mapping(args)
    windows = dict(zip(HOLDOUTS, (tuple(args.certificate), tuple(args.evaluation))))
    discovery_end = int(dt.datetime.fromisoformat(frozen["discovery_windows_utc"]["evaluation"][1]).timestamp())
    previous_end = discovery_end
    for name, (start, stop) in windows.items():
        if start < previous_end + DAY or stop - start < DAY:
            raise ValueError(f"{name} must start at least one day after the previous window and last at least a day")
        previous_end = stop
    initial_state = file_state(args.h5)
    source_hash = sha256(args.h5)
    if source_hash == frozen["development_h5_sha256"]:
        raise ValueError("use a new capture H5 for the follow-up")
    args.max_per_app = frozen["max_per_app"]
    args.seed = frozen["seed"]
    encoder = FixedPrefixEncoder(K, 2)
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        if (args.certificate[0] < tables[0]["day_seconds"]
                or args.evaluation[1] > tables[-1]["day_seconds"] + DAY):
            raise ValueError("requested holdout windows extend outside the H5 calendar")
        samples, _, audit = scan(source, tables, windows, encoder, args, batch_mask=separated_day_mask)
        backend = source.backend
    finally:
        source.close()
    if file_state(args.h5) != initial_state:
        raise RuntimeError("holdout H5 changed during the scan")
    require_samples(samples, codes.values())

    records = []
    for record in frozen["pairs"]:
        pair = tuple(record["apps"])
        model = PairScores(encoder.alphabet, tuple(map(np.asarray, record["base_parameters"])),
                           tuple(map(np.asarray, record["late_base_parameters"])),
                           np.asarray(record["stack_parameters"]))
        maps = {name: ScoreQuantizer(np.asarray(q["cuts"]), np.asarray(q["decision"]), q["calibration_accuracy"])
                for name, q in record["maps"].items()}
        mapped_pair = tuple(codes[code] for code in pair)
        family_size = len(HOLDOUTS) * (1 if pair == PRIMARY else len(CONTROLS))
        tail_alpha = ALPHA / family_size
        results = {name: assess_window(model, maps, record["strongest_single_calibration"],
                                       samples[name], mapped_pair, windows[name], tail_alpha)
                   for name in HOLDOUTS}
        records.append({
            "apps": pair, "holdout_apps": mapped_pair, "tail_alpha": tail_alpha, "holdouts": results,
            "positive_sample_gap_in_both": all(r["fusion_minus_best_single_sample_oracle"]["late"] > 0
                                               for r in results.values()),
            "positive_lower_bound_in_both": {
                scenario: all(r["bounds"][scenario]["bayes_gain_lower"] > 0 for r in results.values())
                for scenario in SCENARIOS
            },
        })
    primary = records[0]
    write_json(args.out, {
        "budget": BUDGET, "primary_pair": PRIMARY, "control_pairs": CONTROLS, "alpha": ALPHA,
        "primary_scenario": SCENARIOS[0], "sensitivity_scenario": SCENARIOS[1],
        "frozen_sha256": sha256(args.frozen), "h5_sha256": source_hash, "backend": backend,
        "windows_utc": windows_json(windows), "holdout_app_mapping": codes,
        "eligible_counts_by_window": {name: dict(sample.eligible) for name, sample in samples.items()},
        "audit": audit, "pairs": records,
        "primary_pass": primary["positive_lower_bound_in_both"][SCENARIOS[0]],
    })
    for name, result in primary["holdouts"].items():
        gap = result["fusion_minus_best_single_sample_oracle"]["late"]
        separated = result["bounds"]["separated_24h"]
        iid = result["bounds"]["iid_flow"]
        print(f"APP 0 vs 1, {name}: sample gap {100 * gap:+.2f} pp; "
              f"separated lower {100 * separated['bayes_gain_lower']:+.2f} pp "
              f"(effective batches {separated['effective_blocks']:.1f}); "
              f"iid lower {100 * iid['bayes_gain_lower']:+.2f} pp", flush=True)
    control_overlap = sum(record["positive_sample_gap_in_both"] for record in records[1:])
    print(f"Controls positive on both samples: {control_overlap}/{len(CONTROLS)}", flush=True)
    print(f"Results: {args.out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    training = commands.add_parser("freeze", help="rebuild models from the discovery training windows")
    training.add_argument("--discovery", type=Path, required=True)
    testing = commands.add_parser("evaluate", help="score frozen models on two new UTC holdouts")
    testing.add_argument("--frozen", type=Path, required=True)
    testing.add_argument("--certificate", type=capture_day, nargs=2, required=True, metavar=("START", "STOP"))
    testing.add_argument("--evaluation", type=capture_day, nargs=2, required=True, metavar=("START", "STOP"))
    mapping = testing.add_mutually_exclusive_group(required=True)
    mapping.add_argument("--same-app-codes", action="store_true")
    mapping.add_argument("--app-map", type=Path, help="JSON object mapping discovery APP codes to holdout codes")
    for command in (training, testing):
        command.add_argument("--h5", type=Path, required=True)
        command.add_argument("--out", type=Path, required=True)
        command.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
        command.add_argument("--chunk-rows", type=int, default=20_000)
    args = parser.parse_args()
    if args.chunk_rows < 1 or args.out.exists():
        parser.error("use a positive chunk size and a new output file")
    (freeze if args.command == "freeze" else evaluate)(args)


if __name__ == "__main__":
    main()
