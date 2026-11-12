#!/usr/bin/env python3
"""Evaluate frozen QUICEXT-25 fusion scores on a chronological QUIC22 split."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from if_e1_fusion_validate import (
    BUDGET, CONTROLS, DAY, K, PAIRS, PRIMARY, FixedPrefixEncoder, FlowSource,
    PairScores, ScoreQuantizer, capture_day, file_state, pair_sample,
    read_json, scan, sha256, utc, windows_json, write_json,
)

# Source and target APP enums in CESNET DataZoo datasets_constants.py.
SERVICES = {
    0: ("default-background", 0),
    1: ("google-www", 1),
    2: ("google-play", 2),
    3: ("google-services", 3),
    4: ("google-gstatic", 4),
    14: ("youtube", 15),
    16: ("google-ads", 17),
    51: ("google-background", 109),
}
WINDOWS = {
    "calibration": (capture_day("2022-10-31"), capture_day("2022-11-14")),
    "holdout": (capture_day("2022-11-14"), capture_day("2022-11-28")),
}
SINGLES = ("prefix", "phist")
METHODS = (*SINGLES, "late")
REPETITIONS = 20_000
BLOCK_LENGTHS = (3, 2, 4)
TIE_TOLERANCE = 1e-12


def daily_laws(sample, mapped_pair, window, model, maps):
    rows, labels = pair_sample(sample, mapped_pair)
    scores = model.predict(rows)
    start, stop = window
    days = (stop - start) // DAY
    date_class = 2 * ((rows["first"] - start) // DAY).astype(int) + labels
    totals = np.bincount(date_class, minlength=2 * days).reshape(days, 2)
    valid = (totals > 0).all(axis=1)
    laws = {}
    for method in METHODS:
        indices = BUDGET * date_class + maps[method].encode(scores[method])
        counts = np.bincount(indices, minlength=days * 2 * BUDGET).reshape(days, 2, BUDGET)
        laws[method] = np.full(counts.shape, np.nan)
        laws[method][valid] = counts[valid] / totals[valid, :, None]
    return laws, valid


def evaluate_pair(pair, record, samples, encoder):
    labels, mapped_pair = zip(*(SERVICES[app] for app in pair))
    summary = {
        "source_apps": list(pair), "target_apps": list(mapped_pair),
        "service_names": list(labels),
        "eligible_flows": {name: [sample.eligible[app] for app in mapped_pair]
                           for name, sample in samples.items()},
        "sampled_flows": {name: [len(sample.rows.get(app, ())) for app in mapped_pair]
                          for name, sample in samples.items()},
    }
    if any(min(counts) == 0 for counts in summary["sampled_flows"].values()):
        return {**summary, "status": "missing_class_in_window"}, None

    model = PairScores(encoder.alphabet, tuple(map(np.asarray, record["base_parameters"])),
                       tuple(map(np.asarray, record["late_base_parameters"])),
                       np.asarray(record["stack_parameters"]))
    maps = {name: ScoreQuantizer(np.asarray(q["cuts"]), np.asarray(q["decision"]),
                                 q["calibration_accuracy"]) for name, q in record["maps"].items()}
    cal, cal_valid = daily_laws(samples["calibration"], mapped_pair, WINDOWS["calibration"], model, maps)
    holdout, holdout_valid = daily_laws(samples["holdout"], mapped_pair, WINDOWS["holdout"], model, maps)
    summary["days_with_both_classes"] = {
        "calibration": int(cal_valid.sum()), "holdout": int(holdout_valid.sum()),
    }
    if not (cal_valid.any() and holdout_valid.any()):
        return {**summary, "status": "no_day_with_both_classes"}, None

    # A tie takes class 0, as in the earlier APP 0 vs 1 run.
    rules = {method: law[cal_valid].mean(axis=0).argmax(axis=0) for method, law in cal.items()}
    daily_ba = {method: 0.5 * holdout[method][:, rule, np.arange(BUDGET)].sum(axis=1)
                for method, rule in rules.items()}
    means = {method: float(scores[holdout_valid].mean()) for method, scores in daily_ba.items()}
    best_single = max(SINGLES, key=means.get)
    gaps = np.column_stack([daily_ba["late"] - daily_ba[method] for method in SINGLES])
    return {
        **summary, "status": "scored",
        "calibrated_rules": {method: rule.tolist() for method, rule in rules.items()},
        "holdout_ba": means, "strongest_single_on_holdout": best_single,
        "late_gain_vs_strongest_single_pp": 100 * (means["late"] - means[best_single]),
        "daily_holdout_ba": {method: [float(ba) if valid else None for ba, valid in zip(scores, holdout_valid)]
                             for method, scores in daily_ba.items()},
    }, gaps


def summarize_panel(gaps):
    if not gaps:
        return {"scored_pairs": 0, "planned_pairs": len(CONTROLS)}
    gaps = np.stack(gaps, axis=1)
    valid = np.isfinite(gaps[:, :, 0])
    observed = np.nanmean(gaps, axis=0)
    gains = observed.min(axis=1)
    mean = float(gains.mean())
    rng = np.random.default_rng(20261111)
    days, pairs, _ = gaps.shape
    intervals = {}
    for block in BLOCK_LENGTHS:
        starts = rng.integers(0, days, size=(REPETITIONS, (days + block - 1) // block))
        indices = (starts[:, :, None] + np.arange(block)) % days
        indices = indices.reshape(REPETITIONS, -1)[:, :days]
        weights = np.zeros((REPETITIONS, days))
        np.add.at(weights, (np.arange(REPETITIONS)[:, None], indices), 1)
        counts = weights @ valid
        sums = (weights @ np.nan_to_num(gaps).reshape(days, -1)).reshape(REPETITIONS, pairs, len(SINGLES))
        boot = sums / np.maximum(counts[:, :, None], 1)
        errors = np.abs(boot - observed)
        # A missing pair in a draw can range over the entire [-1, 1] contrast.
        errors = np.where(counts[:, :, None] > 0, errors, 1 + np.abs(observed))
        # The error of a pair's minimum contrast is bounded by its larger contrast error.
        radius = float(np.quantile(errors.max(axis=2).mean(axis=1), 0.95))
        intervals[str(block)] = {
            "lower_pp": 100 * (mean - radius), "upper_pp": 100 * (mean + radius),
            "draws_missing_a_pair": int((counts == 0).any(axis=1).sum()),
        }
    return {
        "scored_pairs": pairs, "planned_pairs": len(CONTROLS),
        "wins": int((gains > TIE_TOLERANCE).sum()),
        "ties": int((np.abs(gains) <= TIE_TOLERANCE).sum()),
        "losses": int((gains < -TIE_TOLERANCE).sum()),
        "mean_gain_pp": 100 * mean, "median_gain_pp": 100 * float(np.median(gains)),
        "mean_gain_approx_95_ci_by_block_days": intervals,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--frozen", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new file")

    frozen = read_json(args.frozen)
    records = {tuple(row["apps"]): row for row in frozen["pairs"]}
    if (frozen["budget"] != BUDGET or tuple(frozen["primary_pair"]) != PRIMARY
            or set(records) != set(PAIRS)):
        raise ValueError("Expected the frozen 8-bin IF-E1 panel")
    args.seed = frozen["seed"]
    args.max_per_app = frozen["max_per_app"]
    args.chunk_rows = 20_000
    state = file_state(args.h5)
    encoder = FixedPrefixEncoder(K, 2)
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        observed_days = {table["day_seconds"] for table in tables}
        scheduled_days = set(range(WINDOWS["calibration"][0], WINDOWS["holdout"][1], DAY))
        if not observed_days or not observed_days <= scheduled_days:
            raise ValueError("Expected QUIC22 daily tables dated 2022-10-31 to 2022-11-27")
        samples, _, audit = scan(source, tables, WINDOWS, encoder, args)
        backend = source.backend
    finally:
        source.close()
    if file_state(args.h5) != state:
        raise RuntimeError("QUIC22 H5 changed during the scan")

    results, control_gaps = [], []
    for pair in PAIRS:
        result, gaps = evaluate_pair(pair, records[pair], samples, encoder)
        results.append(result)
        if gaps is None:
            print(f"{pair} {result['status']}  sampled={result['sampled_flows']}")
        else:
            if pair != PRIMARY:
                control_gaps.append(gaps)
            best = result["strongest_single_on_holdout"]
            print(f"{pair} {' vs '.join(result['service_names'])}: "
                  f"late vs {best} = {result['late_gain_vs_strongest_single_pp']:+.2f} pp")

    panel = summarize_panel(control_gaps)
    write_json(args.out, {
        "design": "Retrospective cross-dataset calibration and chronological holdout",
        "source": str(args.h5), "source_size_bytes": state[0], "backend": backend,
        "frozen_sha256": sha256(args.frozen), "budget": BUDGET,
        "windows_utc": windows_json(WINDOWS),
        "missing_date_tables_utc": [utc(day)[:10] for day in sorted(scheduled_days - observed_days)],
        "seed": args.seed, "max_per_app_per_window": args.max_per_app, "scan_audit": audit,
        "bootstrap": {
            "method": "Shared circular UTC-date blocks; confidence interval conditional on calibrated rules",
            "repetitions": REPETITIONS, "seed": 20261111, "primary_block_days": BLOCK_LENGTHS[0],
        },
        "reference_pair": results[0], "control_pairs": results[1:], "control_summary": panel,
    })
    print(f"Controls scored: {panel['scored_pairs']}/{panel['planned_pairs']}")
    if control_gaps:
        print(f"Wins/ties/losses: {panel['wins']}/{panel['ties']}/{panel['losses']} | "
              f"mean={panel['mean_gain_pp']:+.2f} pp | median={panel['median_gain_pp']:+.2f} pp")
        for block, interval in panel["mean_gain_approx_95_ci_by_block_days"].items():
            print(f"block={block} days | mean approx. 95% CI "
                  f"[{interval['lower_pp']:+.2f}, {interval['upper_pp']:+.2f}] pp")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
