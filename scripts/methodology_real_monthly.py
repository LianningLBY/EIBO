#!/usr/bin/env python3
"""Decompose fixed-observable drift by UTC month and APP code."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.monthlydrift import MonthlyDriftCounts, analyze_months  # noqa: E402
from eibo.realdata import FlowSource  # noqa: E402
from eibo.realexperiment import PERIODS  # noqa: E402
from eibo.riskcert import validate_counts  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402


def save(path, payload, *, compact=False):
    with path.open("x") as handle:
        json.dump(payload, handle, allow_nan=False, indent=None if compact else 2,
                  separators=(",", ":") if compact else None)
        handle.write("\n")


def write_csv(path, rows):
    if not rows:
        raise ValueError(f"empty output table: {path.name}")
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_previous(directory, plan):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete":
        raise ValueError("previous temporal experiment is incomplete")
    manifest = {item["path"]: item["sha256"] for item in run["outputs"]}
    for name in ("plan_snapshot.json", "symbol_counts.json", "summary.json"):
        if sha256(directory / name) != manifest[name]:
            raise ValueError(f"previous experiment artifact hash mismatch: {name}")
    snapshot = json.loads((directory / "plan_snapshot.json").read_text())
    if snapshot != plan or any(run["source"][field] != plan["source"][field] for field in ("sha256", "bytes")):
        raise ValueError("previous experiment and preparation have different plans/sources")
    payload = json.loads((directory / "symbol_counts.json").read_text())
    if payload["known_service_codes"] != plan["known_service_codes"]:
        raise ValueError("previous APP order differs from the fixed plan")
    counts = {p: {rung: validate_counts(payload["counts"][p][str(rung)]).astype(np.int64)
                  for rung in (1, 2)} for p in PERIODS}
    for period in PERIODS:
        for spec in plan["fixed_representations"]:
            if counts[period][spec["M"]].shape != (len(plan["known_service_codes"]), spec["alphabet_size"]):
                raise ValueError("previous count shape differs from the declared representation")
    return run, counts, json.loads((directory / "summary.json").read_text())


def reconcile_previous_summary(analysis, previous):
    for representation in previous["representations"]:
        rung = representation["M"]
        for period in PERIODS:
            actual = analysis["metrics"][(period, rung)]
            expected = representation["periods"][period]
            if actual["n"].tolist() != expected["sample_counts"]:
                raise ValueError("period sample counts differ from previous summary")
            values = [(actual["empirical_F"], expected["empirical_known_bayes_risk"]),
                      (float(np.dot(analysis["summary"]["known_priors"], actual["pilot_error"])), expected["pilot_classifier"]["known_weighted_error"])]
            if period == "evaluation":
                values.append((float(np.dot(analysis["summary"]["known_priors"], actual["recent_error"])), expected["certificate_classifier"]["known_weighted_error"]))
            if any(abs(left - right) > 1e-12 for left, right in values):
                raise ValueError("period metrics differ from the previous temporal experiment")


def number(value, scale=1):
    return "NA" if value is None else f"{value * scale:.5f}"


def report_text(analysis):
    summary = analysis["summary"]
    lines = ["# Monthly and per-class temporal drift", "",
             "Descriptive decomposition of the same audited population. No sampling confidence intervals or real-data coverage claims are produced.",
             f"Fixed known APP codes: {len(summary['known_service_codes'])}; report-only small-n threshold: {summary['small_n_threshold_report_only']}.",
             "Calendar slices use stored UTC start time and preserve the original whole-period interval guards. No extra monthly end filter is applied.", "",
             "## Monthly overview, canonical log M=2", "",
             "Error, F, TV and coarsening loss are percentages of fixed known-prior mass contributions. Unknown-class error is discarded.",
             "| Slice | Known flows | Min class n | Missing / small-n classes | Empirical F % | Pilot error % | Recent error % | TV from pilot % | TV from previous slice % | M1-M2 empirical loss pp |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for item in summary["monthly"]:
        if item["log_M"] != 2:
            continue
        recent = item.get("recent_classifier", {}).get("value")
        previous_tv = item["previous_slice_comparison"]["empirical_tv"]["value"] if item["previous_slice_comparison"] is not None else None
        lines.append(f"| {item['slice']} | {item['sample_count']} | {item['minimum_class_n']} | {len(item['missing_service_codes'])} / {len(item['small_n_service_codes'])} | {number(item['empirical_F'],100)} | {number(item['pilot_classifier']['value'],100)} | {number(recent,100)} | {number(item['empirical_TV_from_pilot']['value'],100)} | {number(previous_tv,100)} | {number(item['empirical_coarsening_loss_M1_minus_M2'],100)} |")
    lines += ["", "Within-pilot monthly errors reuse pilot training data. The recent classifier is fixed on the entire certificate period and evaluated only in evaluation slices.",
              "NA means a complete fixed-prior mixture is not identifiable because one or more selected classes are absent. Partial error/TV contributions and missing-value identification ranges are retained in summary.json; no present-class renormalization is used.",
              "", "## Period error decomposition", "",
              "Delta error = delta empirical F + delta empirical gap, using the same pilot classifier on both periods. These are sample identities, not causal effects.",
              "| Log M | Comparison | Error delta pp | F delta pp | Gap delta pp | Positive class contributions pp | Negative class contributions pp |",
              "|---:|---|---:|---:|---:|---:|---:|"]
    for item in summary["comparisons"]:
        if item["scope"] == "period":
            lines.append(f"| {item['log_M']} | {item['source']} -> {item['target']} | {number(item['pilot_error_change']['value'],100)} | {number(item['empirical_F_change']['value'],100)} | {number(item['empirical_gap_change']['value'],100)} | {number(item['positive_error_contributions'],100)} | {number(item['negative_error_contributions'],100)} |")
    lines += ["", "## Classes with increased error: certificate -> evaluation", "",
              "Both models use the fixed pilot classifier. Contributions include the class prior; rankings retain small-n flags.",
              "| Log M | APP | Certificate n | Evaluation n | Sample status | Error change pp | Empirical TV % | F change pp | Gap change pp |",
              "|---:|---:|---:|---:|---|---:|---:|---:|---:|"]
    for ranking in analysis["rankings"]:
        if ranking["scope"] == "period" and ranking["source"] == "certificate" and ranking["target"] == "evaluation":
            for row in ranking["largest_error_increases"]:
                lines.append(f"| {ranking['log_M']} | {row['service_code']} | {row['source_n']} | {row['target_n']} | {row['sample_status']} | {number(row['weighted_error_change'],100)} | {number(row['empirical_TV'],100)} | {number(row['weighted_empirical_F_change'],100)} | {number(row['weighted_empirical_gap_change'],100)} |")
    lines += ["", "## Classes with decreased empirical coarsening contribution: pilot -> evaluation", "",
              "Per-class Fhat(M1)-Fhat(M2) contributions are signed. A class can have a negative contribution because the empirical optimum allocates errors differently across classes; the complete-class sum remains nonnegative.",
              "| APP | Evaluation n | Signed contribution pp | Contribution change from pilot pp | Pilot-model M2 gain pp |",
              "|---:|---:|---:|---:|---:|"]
    for row in summary["coarsening_contribution_decrease_rankings"]["evaluation"]:
        lines.append(f"| {row['service_code']} | {row['n']} | {number(row['signed_empirical_coarsening_contribution'],100)} | {number(row['coarsening_contribution_change_from_pilot'],100)} | {number(row['weighted_pilot_model_M2_gain'],100)} |")
    lines += ["", "## Monthly decreases in signed coarsening contribution relative to pilot", "",
              "| Slice | APP | Slice n | Status | Contribution change pp | Pilot-model M2 gain pp |",
              "|---|---:|---:|---|---:|---:|"]
    for key, ranking in summary["coarsening_contribution_decrease_rankings"].items():
        if "/" not in key:
            continue
        for row in ranking[:3]:
            lines.append(f"| {key} | {row['service_code']} | {row['n']} | {row['sample_status']} | {number(row['coarsening_contribution_change_from_pilot'],100)} | {number(row['weighted_pilot_model_M2_gain'],100)} |")
    lines += ["", "## Monthly classes with largest error increases relative to pilot, log M=2", "",
              "| Slice | APP | Slice n | Status | Error change pp | Empirical TV % | Class-specific unseen mass % |",
              "|---|---:|---:|---|---:|---:|---:|"]
    lookup = {(row["slice"], row["log_M"], row["service_code"]): row for row in analysis["class_rows"]}
    for ranking in analysis["rankings"]:
        if ranking["scope"] != "monthly_pilot_reference" or ranking["log_M"] != 2 or ranking["target"].startswith("pilot/"):
            continue
        for row in ranking["largest_error_increases"][:3]:
            metric = lookup[(ranking["target"], 2, row["service_code"])]
            lines.append(f"| {ranking['target']} | {row['service_code']} | {row['target_n']} | {row['sample_status']} | {number(row['weighted_error_change'],100)} | {number(row['empirical_TV'],100)} | {number(metric['pilot_class_specific_unseen_mass'],100)} |")
    lines += ["", "## Coverage and limitations", ""]
    for item in summary["monthly"]:
        if item["log_M"] == 2:
            lines.append(f"- {item['slice']}: {item['available_table_days']}/{item['calendar_days']} calendar days have tables; {item['days_with_selected_flows']} days have selected flows; missing APP={item['missing_service_codes']}; small-n APP={item['small_n_service_codes']}.")
    lines += ["", "The small-n threshold only marks rows; no classes or priors are removed. Global unseen symbols and per-class unseen symbols use different dictionaries and are reported separately. Adjacent slices are compared even when empty; an empty month is never silently skipped. Rankings and empirical TV include sampling noise and temporal dependence, and do not establish statistical significance.",
              "", "The existing log grid is unchanged; log M=2 differs from the legacy 1200-byte representation. No new risk floor, effective sample size or representation is selected by this analysis.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    prepare_run, plan, prepared_tables, expected = read_preparation(args.prepare_dir)
    previous_run, baseline_counts, previous_summary = read_previous(args.experiment_dir, plan)
    before = args.h5.stat()
    print("Verifying H5 SHA256 and completed experiment artifacts...", flush=True)
    input_hash = sha256(args.h5)
    if input_hash != plan["source"]["sha256"] or before.st_size != plan["source"]["bytes"]:
        raise ValueError("source bytes differ from the audited input")
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        if tables != prepared_tables:
            raise ValueError("source table/schema metadata differs from preparation")
        scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[prepare_run["parameters"]["time_unit"]]
        counts = MonthlyDriftCounts(plan, tables, time_scale=scale)
        args.out_dir.mkdir(parents=True, exist_ok=False)
        code = [Path(__file__), ROOT / "src/eibo/monthlydrift.py", ROOT / "src/eibo/realexperiment.py",
                ROOT / "src/eibo/realdata.py", ROOT / "src/eibo/riskcert.py", ROOT / "src/eibo/statcore.py",
                ROOT / "scripts/methodology_real_experiment.py", ROOT / "scripts/methodology_real_prepare.py"]
        metadata = {"status": "running", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "parameters": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                    "source": {"path": str(args.h5.resolve()), "bytes": before.st_size, "sha256": input_hash},
                    "python": platform.python_version(), "numpy": np.__version__, "backend": source.backend,
                    "reader_version": source.module.__version__, "previous_rows_read": previous_run["rows_read"],
                    "input_artifacts": [{"path": str(p.resolve()), "sha256": sha256(p)} for directory in (args.prepare_dir, args.experiment_dir) for p in sorted(directory.iterdir()) if p.is_file()],
                    "code": [{"path": str(p), "sha256": sha256(p)} for p in code],
                    "privacy": "schema and aggregated counts/metrics only; no raw IP/CID, keyed digests or per-flow output"}
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        save(args.out_dir / "plan_snapshot.json", plan)
        total = sum(table["rows"] for table in tables)
        for index, table in enumerate(tables, 1):
            for start in range(0, table["rows"], args.chunk_rows):
                counts.add(source.read(table["path"], start, min(start + args.chunk_rows, table["rows"])), table["ppi_capacity"])
            print(f"[{index}/{len(tables)}] {table['path']}: counted={counts.rows_read}/{total}", flush=True)
        after = args.h5.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or counts.rows_read != total:
            raise RuntimeError("source changed or scan is incomplete")
        counts.reconcile(expected)
        counts.reconcile_months(baseline_counts)
        analysis = analyze_months(counts, small_n=args.small_n, top=args.top)
        reconcile_previous_summary(analysis, previous_summary)
        save(args.out_dir / "summary.json", analysis["summary"])
        save(args.out_dir / "rankings.json", analysis["rankings"])
        save(args.out_dir / "monthly_symbol_counts.json", {"known_service_codes": counts.known.tolist(), "slices": counts.slices,
            "counts": {key: {str(rung): matrix.tolist() for rung, matrix in values.items()} for key, values in counts.monthly.items()}}, compact=True)
        write_csv(args.out_dir / "class_metrics.csv", analysis["class_rows"])
        write_csv(args.out_dir / "class_drift_decomposition.csv", analysis["comparison_rows"])
        write_csv(args.out_dir / "representation_contributions.csv", analysis["representation_rows"])
        monthly_rows = []
        for item in analysis["summary"]["monthly"]:
            error_range = item["pilot_classifier"]["range_from_unobserved_values"]
            previous = item["previous_slice_comparison"]
            monthly_rows.append({"slice": item["slice"], "period": item["period"], "month_utc": item["month_utc"], "log_M": item["log_M"],
                "n": item["sample_count"], "min_class_n": item["minimum_class_n"],
                "missing_APP": ";".join(map(str, item["missing_service_codes"])), "small_n_APP": ";".join(map(str, item["small_n_service_codes"])),
                "available_table_days": item["available_table_days"], "calendar_days": item["calendar_days"],
                "empirical_F": item["empirical_F"], "pilot_weighted_error": item["pilot_classifier"]["value"],
                "error_missing_values_min": error_range[0], "error_missing_values_max": error_range[1],
                "recent_weighted_error": item.get("recent_classifier", {}).get("value"),
                "empirical_TV_from_pilot": item["empirical_TV_from_pilot"]["value"],
                "previous_slice": item["previous_slice"],
                "empirical_TV_from_previous_slice": previous["empirical_tv"]["value"] if previous is not None else None,
                "error_change_from_previous_slice": previous["pilot_error_change"]["value"] if previous is not None else None,
                "empirical_F_change_from_previous_slice": previous["empirical_F_change"]["value"] if previous is not None else None,
                "empirical_gap_change_from_previous_slice": previous["empirical_gap_change"]["value"] if previous is not None else None,
                "global_unseen_mass": item["global_unseen_mass"]["value"], "class_specific_unseen_mass": item["class_specific_unseen_mass"]["value"],
                "empirical_coarsening_loss_M1_minus_M2": item["empirical_coarsening_loss_M1_minus_M2"]})
        write_csv(args.out_dir / "monthly_summary.csv", monthly_rows)
        (args.out_dir / "report.md").write_text(report_text(analysis))
        metadata.update({"status": "complete", "rows_read": total, "elapsed_seconds": time.monotonic() - started,
                         "reconciliation": "audited APP counts, prior experiment symbol matrices/metrics, monthly pooling, deterministic refinement and decomposition identities passed",
                         "outputs": [{"path": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in sorted(args.out_dir.iterdir()) if p.name != "run.json"]})
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"Complete: {total} rows; {len(counts.known)} fixed APP codes; {len(counts.slices)} calendar/period slices; all reconciliations passed.")
        print("Monthly log M=2: fixed-prior weighted fractions; NA retains missing classes.")
        for item in analysis["summary"]["monthly"]:
            if item["log_M"] == 2:
                previous = item["previous_slice_comparison"]
                previous_tv = previous["empirical_tv"]["value"] if previous is not None else None
                print(f"MONTH {item['slice']} n={item['sample_count']} min_n={item['minimum_class_n']} missing={len(item['missing_service_codes'])} small_n={len(item['small_n_service_codes'])} error={number(item['pilot_classifier']['value'])} F={number(item['empirical_F'])} TVpilot={number(item['empirical_TV_from_pilot']['value'])} TVprev={number(previous_tv)} loss={number(item['empirical_coarsening_loss_M1_minus_M2'])}")
        for item in analysis["summary"]["comparisons"]:
            if item["scope"] == "period" and item["source"] == "certificate" and item["target"] == "evaluation":
                print(f"PERIOD log M={item['log_M']} cert->eval delta_error_pp={number(item['pilot_error_change']['value'],100)} delta_F_pp={number(item['empirical_F_change']['value'],100)} delta_gap_pp={number(item['empirical_gap_change']['value'],100)} positive_pp={number(item['positive_error_contributions'],100)} negative_pp={number(item['negative_error_contributions'],100)}")
        print("Largest log M=2 error increases, certificate->evaluation (weighted percentage points):")
        ranking = next(item for item in analysis["rankings"] if item["scope"] == "period" and item["source"] == "certificate" and item["target"] == "evaluation" and item["log_M"] == 2)
        for row in ranking["largest_error_increases"]:
            print(f"APP={row['service_code']} cert_n={row['source_n']} eval_n={row['target_n']} status={row['sample_status']} delta_error_pp={number(row['weighted_error_change'],100)} TV={number(row['empirical_TV'])} delta_F_pp={number(row['weighted_empirical_F_change'],100)} delta_gap_pp={number(row['weighted_empirical_gap_change'],100)}")
        print(f"Report: {(args.out_dir / 'report.md').resolve()}")
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--prepare-dir", type=Path, required=True)
    parser.add_argument("--experiment-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=["auto", "tables", "h5py"], default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20000)
    parser.add_argument("--small-n", type=int, default=200, help="report-only flag; never a selection threshold")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    if not args.h5.is_file() or not args.prepare_dir.is_dir() or not args.experiment_dir.is_dir() or args.out_dir.exists():
        parser.error("H5 and both completed input directories must exist; output directory must be fresh")
    if min(args.chunk_rows, args.small_n, args.top) < 1:
        parser.error("chunk rows, report-only small-n threshold and top must be positive")
    run(args)


if __name__ == "__main__":
    main()
