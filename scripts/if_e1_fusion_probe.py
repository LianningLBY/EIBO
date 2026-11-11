#!/usr/bin/env python3
"""Compare prefix and PHIST score fusion at a fixed output budget on a local H5."""

from __future__ import annotations

import argparse
import itertools
import json
from collections import Counter
from pathlib import Path

import numpy as np

from methodology_real_prepare import sha256

from eibo.fusion import BUDGETS, METHODS, TAILS_PER_COMPARISON, PairScores, ScoreQuantizer, bounds, measure
from eibo.realdata import DAY, FlowSource, chronological_windows, utc, whole_interval_mask
from eibo.realexperiment import FixedPrefixEncoder, TimeUnitGeometry

PHIST_FIELDS = ("PHIST_SRC_SIZES", "PHIST_DST_SIZES", "PHIST_SRC_IPT", "PHIST_DST_IPT")
HOLDOUTS = ("certificate", "evaluation")
BLOCK_SECONDS = (3600, 6 * 3600, DAY, 2 * DAY)
ROUNDING_SECONDS = 3600
K = 5
ALPHA = 0.05
ROW = np.dtype([("priority", "f8"), ("first", "f8"), ("prefix", "u2"), ("phist", "f4", (32,))])


def experiment_windows(tables):
    windows = chronological_windows(tables, gap_seconds=DAY, end_margin_seconds=ROUNDING_SECONDS)
    start, end = windows.pop("pilot")
    days = (end - start) // DAY
    half, three_quarters = start + (days // 2) * DAY, start + (3 * days // 4) * DAY
    development = {"fit": (start, half), "stack": (half + DAY, three_quarters),
                   "calibration": (three_quarters + DAY, end)}
    if any(stop - start <= ROUNDING_SECONDS for start, stop in development.values()):
        raise ValueError("capture period is too short for separate fitting, stacking and calibration windows")
    return {**development, **windows}


class AppReservoir:
    """Keep the lowest independent random priorities per APP in each window."""

    def __init__(self, cap, rng):
        self.cap, self.rng = cap, rng
        self.rows, self.eligible = {}, Counter()

    def add(self, labels, first, prefix, phist):
        candidates = np.empty(len(labels), dtype=ROW)
        candidates["priority"] = self.rng.random(len(labels))
        candidates["first"], candidates["prefix"], candidates["phist"] = first, prefix, phist
        for code, count in zip(*np.unique(labels, return_counts=True)):
            app = int(code)
            self.eligible[app] += int(count)
            rows = candidates[labels == code]
            if app in self.rows:
                rows = np.concatenate((self.rows[app], rows))
            if len(rows) > self.cap:
                index = np.argpartition(rows["priority"], self.cap - 1)[:self.cap]
                rows = rows[index]
            self.rows[app] = rows


def scan(source, tables, windows, encoder, args):
    seeds = np.random.SeedSequence(args.seed).spawn(len(windows))
    samples = {name: AppReservoir(args.max_per_app, np.random.default_rng(seed))
               for name, seed in zip(windows, seeds)}
    geometry = {name: TimeUnitGeometry(windows[name], 1, BLOCK_SECONDS, ROUNDING_SECONDS) for name in HOLDOUTS}
    empty = np.empty(0)
    audit = Counter()
    for index, table in enumerate(tables, 1):
        if table["ppi_capacity"] < K or set(PHIST_FIELDS).difference(table["fields"]):
            raise ValueError(f"{table['path']} lacks the required prefix capacity or PHIST fields")
        for start in range(0, table["rows"], args.chunk_rows):
            records = source.read(table["path"], start, min(start + args.chunk_rows, table["rows"]))
            audit["rows_read"] += len(records)
            first, last, lengths = (np.asarray(records[name], dtype=float)
                                    for name in ("TIME_FIRST", "TIME_LAST", "PPI_LEN"))
            apps = records["APP"]
            if apps.dtype.kind not in "iu" or any(a.shape != (len(records),) for a in (first, last, lengths, apps)):
                raise ValueError("expected scalar epoch seconds, prefix lengths and integer APP codes")
            ppi = records["PPI"][:, :, :K]
            sizes = ppi[:, 2]
            valid_prefix = ((lengths >= K) & (lengths <= table["ppi_capacity"]) & (lengths == np.floor(lengths))
                            & np.isin(ppi[:, 1], (-1, 1)).all(axis=1)
                            & (np.isfinite(sizes) & (sizes > 0) & (sizes == np.floor(sizes))).all(axis=1))
            fields = [np.asarray(records[field], dtype=float) for field in PHIST_FIELDS]
            if any(field.shape != (len(records), 8) for field in fields):
                raise ValueError(f"expected four PHIST arrays of length eight in {table['path']}")
            phist = np.concatenate(fields, axis=1)
            totals = phist.sum(axis=1)
            valid_phist = (np.isfinite(phist) & (phist >= 0)).all(axis=1) & np.isfinite(totals) & (totals > 0)
            valid_time = np.isfinite(first) & np.isfinite(last) & (last >= first)
            audit["invalid_prefix"] += int((~valid_prefix).sum())
            audit["invalid_phist"] += int((~valid_phist).sum())
            audit["invalid_time"] += int((~valid_time).sum())
            valid = valid_prefix & valid_phist & valid_time
            audit["jointly_valid_rows"] += int(valid.sum())
            assigned = np.zeros(len(records), dtype=bool)
            for name, window in windows.items():
                use = valid & whole_interval_mask(first, last, window, ROUNDING_SECONDS)
                if use.any():
                    if np.any(assigned & use):
                        raise RuntimeError("one flow was assigned to multiple windows")
                    assigned |= use
                    samples[name].add(apps[use], first[use], encoder.encode(ppi[use]),
                                      phist[use] / totals[use, None])
                    if name in geometry:
                        # Every eligible flow can bridge blocks, even if it was not retained in the sample.
                        geometry[name].add(first[use], last[use], empty, empty)
            audit["valid_but_outside_windows"] += int((valid & ~assigned).sum())
        if index % 30 == 0 or index == len(tables):
            print(f"Scanned {index}/{len(tables)} daily tables ({audit['rows_read']:,} rows)", flush=True)
    if audit["rows_read"] != sum(table["rows"] for table in tables):
        raise RuntimeError("H5 scan did not read the expected row count")
    assigned_count = sum(sum(sample.eligible.values()) for sample in samples.values())
    if assigned_count + audit["valid_but_outside_windows"] != audit["jointly_valid_rows"]:
        raise RuntimeError("window counts do not reconcile with eligible rows")
    return samples, geometry, dict(audit)


def pair_sample(sample, pair):
    left, right = (sample.rows[app] for app in pair)
    # Priority order makes results independent of the partition order of argpartition.
    parts = [rows[np.argsort(rows["priority"])] for rows in (left, right)]
    return np.concatenate(parts), np.repeat([0, 1], [len(left), len(right)])


def block_budgets(geometry, rows, y):
    ns = np.bincount(y, minlength=2)
    weight = 0.5 / ns
    budgets = {"iid_flow": {"blocks": len(y), "squared_mass": float(np.dot(ns, weight ** 2))}}
    pair_geometry = TimeUnitGeometry(geometry.window, 2, BLOCK_SECONDS, ROUNDING_SECONDS)
    pair_geometry.bridges = geometry.bridges
    pair_geometry.add(np.empty(0), np.empty(0), rows["first"], y)
    for info in pair_geometry.diagnostics(np.array([0.5, 0.5]), ALPHA):
        suffix = f"{info['block_seconds'] // 3600}h"
        budgets[f"start_{suffix}"] = {"blocks": info["start_assigned_nonempty_blocks"],
                                      "squared_mass": info["start_assigned_squared_change_budget"]}
        budgets[f"span_merged_{suffix}"] = {"blocks": info["span_merged_nonempty_units"],
                                            "squared_mass": info["span_merged_squared_change_budget"],
                                            "merged_boundary_edges": info["merged_boundary_edges"]}
    return budgets


def analyze_pair(pair, samples, geometry, alphabet, panel_tail):
    fit, fit_y = pair_sample(samples["fit"], pair)
    stack, stack_y = pair_sample(samples["stack"], pair)
    cal, cal_y = pair_sample(samples["calibration"], pair)
    model = PairScores.fit(alphabet, fit, fit_y, stack, stack_y)
    cal_scores = model.predict(cal)
    holdouts = {}
    for name in HOLDOUTS:
        rows, y = pair_sample(samples[name], pair)
        holdouts[name] = model.predict(rows), y, block_budgets(geometry[name], rows, y)
    result = {"apps": list(pair), "stack_coefficients_and_intercept": model.stack_parameters.tolist(), "budgets": {}}
    for budget in BUDGETS:
        maps = {m: ScoreQuantizer.fit(cal_scores[m], cal_y, budget) for m in METHODS}
        strongest = max(METHODS[:2], key=lambda method: maps[method].calibration_accuracy)
        record = {"strongest_single_calibration": strongest,
                  "maps": {m: {"cuts": q.cuts.tolist(), "decision": q.decision.tolist(),
                               "calibration_accuracy": q.calibration_accuracy} for m, q in maps.items()}, "holdouts": {}}
        for name, (scores, y, scenarios) in holdouts.items():
            measured = measure(scores, y, maps, budget, strongest)
            measured["n_by_app"] = np.bincount(y, minlength=2).tolist()
            measured["bounds"] = {
                scenario: {**stats, "effective_blocks": 1 / stats["squared_mass"],
                           "pointwise": bounds(measured, stats["squared_mass"], ALPHA / 2),
                           "simultaneous_panel": bounds(measured, stats["squared_mass"], panel_tail)}
                for scenario, stats in scenarios.items()
            }
            record["holdouts"][name] = measured
        result["budgets"][str(budget)] = record
    return result


def summarize(rows):
    """Descriptive pair averages and counts of individually certified gains."""
    summary = {}
    for budget in BUDGETS:
        summary[str(budget)] = {}
        for name in HOLDOUTS:
            results = [row["budgets"][str(budget)]["holdouts"][name] for row in rows]
            gains = {m: float(np.mean([v["frozen_accuracy_gains"][m] for v in results]))
                     for m in ("early", "late", "late_minus_early")}
            counts = {}
            for scenario in results[0]["bounds"]:
                counts[scenario] = {}
                for level in ("pointwise", "simultaneous_panel"):
                    values = [v["bounds"][scenario][level] for v in results]
                    counts[scenario][level] = {
                        m: {"positive_frozen_gain_pairs": sum(v["frozen_gain_intervals"][m][0] > 0 for v in values),
                            "positive_bayes_gain_pairs": sum(v["bayes_gain_lower_vs_best_single"][m] > 0 for v in values),
                            "tv_upper_below_half_pairs": sum(v["tv_intervals"][m][1] < 0.5 for v in values)}
                        for m in ("early", "late")
                    }
            summary[str(budget)][name] = {"pairs": len(results), "mean_frozen_accuracy_gains": gains,
                                          "pair_counts_by_block_scenario": counts}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new JSON output path")
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    parser.add_argument("--top-apps", type=int, default=8)
    parser.add_argument("--max-per-app", type=int, default=6000, help="uniform sample cap per APP per window")
    parser.add_argument("--seed", type=int, default=20261111)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    if args.out.exists() or args.top_apps < 2 or args.max_per_app < 2 or args.chunk_rows < 1 or args.seed < 0:
        parser.error("use a new output, at least two APPs and rows per APP, a positive chunk size and nonnegative seed")

    before = args.h5.stat()
    source_hash = sha256(args.h5) if args.expected_sha256 else None
    if source_hash is not None and source_hash != args.expected_sha256.lower():
        raise ValueError(f"H5 SHA-256 mismatch: got {source_hash}")
    encoder = FixedPrefixEncoder(K, 2)
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        windows = experiment_windows(tables)
        samples, geometry, audit = scan(source, tables, windows, encoder, args)
    finally:
        source.close()
    after = args.h5.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError("H5 changed during the scan")

    ranked = sorted(samples["fit"].eligible, key=lambda app: (-samples["fit"].eligible[app], app))
    if len(ranked) < args.top_apps:
        raise ValueError(f"fitting window has {len(ranked)} eligible APPs; requested {args.top_apps}")
    apps = sorted(ranked[:args.top_apps])
    for name, sample in samples.items():
        missing = [app for app in apps if sample.eligible[app] < 2]
        if missing:
            raise ValueError(f"fixed fitting-period APP codes with fewer than two rows in {name}: {missing}")
    pairs = list(itertools.combinations(apps, 2))
    tails = len(pairs) * len(BUDGETS) * len(HOLDOUTS) * TAILS_PER_COMPARISON
    print(f"Fitting {len(pairs)} pairwise probes for APPs {apps}", flush=True)
    rows = []
    for index, pair in enumerate(pairs, 1):
        rows.append(analyze_pair(pair, samples, geometry, encoder.alphabet, ALPHA / tails))
        print(f"Scored pair {index}/{len(pairs)} {pair}", flush=True)

    summary = summarize(rows)
    output = {"source": {"path": str(args.h5.resolve()), "bytes": before.st_size, "sha256": source_hash,
                         "backend": source.backend, "daily_tables": len(tables)},
              "windows_utc": {name: [utc(start), utc(stop)] for name, (start, stop) in windows.items()},
              "eligible_counts_by_window": {name: dict(sample.eligible) for name, sample in samples.items()},
              "selected_counts_by_window": {name: {app: len(sample.rows[app]) for app in apps}
                                            for name, sample in samples.items()},
              "audit": audit, "apps": apps, "max_per_app_per_window": args.max_per_app, "seed": args.seed,
              "representations": {"prefix": "EIBO log M=2, first five packets", "phist_fields": PHIST_FIELDS,
                                  "phist_transform": "normalize concatenated vector to unit sum, then square root",
                                  "early": "logistic score from concatenated prefix one-hot and transformed PHIST",
                                  "late": "logistic stack of the two single-view logits"},
              "output_budgets": BUDGETS, "rounding_seconds": ROUNDING_SECONDS, "alpha": ALPHA,
              "panel_tails_per_scenario": tails,
              "interpretation": "Pairwise equal-prior results for quantized score outputs. Holdout bounds condition on fitting, geometry and block class counts, allow arbitrary dependence within blocks, and assume independence across blocks. Start-assigned and span-merged groupings are separate assumptions. Pointwise intervals use alpha/2 per tail. The Bonferroni panel covers all pairs, budgets, holdouts and reported endpoints within one scenario. Pair averages are descriptive.",
              "summary": summary, "pairs": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")
    for budget, periods in summary.items():
        for name, result in periods.items():
            gains = result["mean_frozen_accuracy_gains"]
            certified = result["pair_counts_by_block_scenario"]["span_merged_24h"]["simultaneous_panel"]
            print(f"B={budget}, {name}: early {gains['early']:+.2%}, late {gains['late']:+.2%} vs frozen best single; "
                  f"positive Bayes gain (merged 24h) early {certified['early']['positive_bayes_gain_pairs']}/{len(pairs)}, "
                  f"late {certified['late']['positive_bayes_gain_pairs']}/{len(pairs)}")
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
