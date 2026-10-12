#!/usr/bin/env python3
"""Run fixed log-grid counts and temporal evaluation from a completed audit."""

from __future__ import annotations

import argparse
import collections
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
from eibo.realdata import FlowSource  # noqa: E402
from eibo.realexperiment import PERIODS, RealExperimentCounts, analyze_counts  # noqa: E402
from methodology_real_prepare import save, sha256  # noqa: E402


def read_preparation(directory):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete" or run["plan_status"] != "prepared":
        raise ValueError("preparation is not complete/prepared")
    manifest = {item["path"]: item["sha256"] for item in run["outputs"]}
    names = ("experiment_plan.json", "tables.json", "audit.json", "period_service_counts.csv", "time_unit_diagnostics.json")
    for name in names:
        if sha256(directory / name) != manifest[name]:
            raise ValueError(f"preparation artifact hash mismatch: {name}")
    plan = json.loads((directory / "experiment_plan.json").read_text())
    if plan["source"] != run["source"]:
        raise ValueError("source metadata differs between plan and run")
    if not run["source"].get("sha256"):
        raise ValueError("a source SHA256 is required; rerun preparation with hashing")
    expected = {p: collections.Counter() for p in PERIODS}
    with (directory / "period_service_counts.csv").open(newline="") as handle:
        for row in csv.DictReader(handle):
            expected[row["period"]][int(row["service_code"])] += int(row["whole_interval_usable_flows"])
    return run, plan, json.loads((directory / "tables.json").read_text()), expected


def report_text(summary, plan):
    lines = ["# Real-data fixed-observable temporal experiment", "",
             "Exploratory results. Population Bayes risk, independence and real-data coverage are unknown.",
             "Floors below are conditional sensitivity calculations, not validated real-traffic certificates.", "",
             f"Known APP codes: {len(summary['known_service_codes'])}; unknown mass: {summary['unknown_prior']:.8f}.",
             "Class selection, priors and windows are copied from the completed pilot plan.",
             "Both representations use the canonical statcore log grid. Log M=2 is not the legacy 1200-byte split.", "",
             "| Period | Start UTC | End UTC (exclusive) |", "|---|---|---|"]
    lines += [f"| {period} | {plan['windows'][period]['start_utc']} | {plan['windows'][period]['end_utc_exclusive']} |" for period in PERIODS]
    lines += ["", "## Empirical risk and temporal classifier evaluation", "",
              "| Log M | Period | Known flows | Empirical F | Pilot-trained known error | Weighted unseen mass |",
              "|---:|---|---:|---:|---:|---:|"]
    for representation in summary["representations"]:
        for period, values in representation["periods"].items():
            classifier = values["pilot_classifier"]
            lines.append(f"| {representation['M']} | {period} | {sum(values['sample_counts'])} | {values['empirical_known_bayes_risk']:.8f} | {classifier['known_weighted_error']:.8f} | {classifier['known_weighted_unseen_symbol_mass']:.8f} |")
    lines.append("")
    for representation in summary["representations"]:
        recent = representation["periods"]["evaluation"]["certificate_classifier"]["known_weighted_error"]
        lines.append(f"Log M={representation['M']}: certificate-trained model's evaluation known error = {recent:.8f}.")
    lines += ["", "Pilot error on pilot is a resubstitution statistic. Certificate-trained error is evaluated only on the later evaluation period. Each error is weighted by fixed known-class priors; unknown error is not measured.",
              "", "## Empirical temporal shift", "",
              "| Log M | Period comparison | Prior-weighted empirical class TV |", "|---:|---|---:|"]
    for representation in summary["representations"]:
        for comparison, values in representation["drift"].items():
            lines.append(f"| {representation['M']} | {comparison} | {values['prior_weighted_empirical_tv']:.8f} |")
    lines += ["", "Empirical TV contains sampling error. No certificate-period floor is transported through this empirical shift to future traffic.",
              "", "## Conditional floors and sampling-unit sensitivity", "",
              "| Log M | Period | Unit assumption | Radius | Floor if assumptions hold |", "|---:|---|---|---:|---:|"]
    for representation in summary["representations"]:
        for period in ("certificate", "evaluation"):
            values = representation["periods"][period]
            for method in ("classwise", "joint"):
                result = values["iid_floors_if_assumptions_hold"][method]
                lines.append(f"| {representation['M']} | {period} | iid {method} | {result['radius']:.8f} | {result['lower_floor']:.8f} |")
            for result in values["time_unit_sensitivity"]:
                lines.append(f"| {representation['M']} | {period} | start-assigned {result['block_seconds']}s blocks | {result['start_assigned_radius_if_assumptions_hold']:.8f} | {result['start_assigned_lower_floor_if_assumptions_hold']:.8f} |")
                lines.append(f"| {representation['M']} | {period} | span-merged {result['block_seconds']}s blocks | {result['span_merged_radius_if_assumptions_hold']:.8f} | {result['span_merged_lower_floor_if_assumptions_hold']:.8f} |")
    lines += ["", "Start-assigned units assume dependence is fully contained by start-time groups. Span-merged units add a pessimistic full-interval safeguard. Neither model's independence or conditional unbiasedness is established. CID sessions and observed constant runs are not assumed. Alpha applies to each fixed comparison; selecting the largest floor across rows has no simultaneous guarantee.",
              "", "## Interval coarsening", "",
              "| Period | Block seconds | Start-assigned blocks | Span-merged units | Merged edges | Start radius | Merged radius |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for period in ("certificate", "evaluation"):
        for result in summary["representations"][0]["periods"][period]["time_unit_sensitivity"]:
            lines.append(f"| {period} | {result['block_seconds']} | {result['start_assigned_nonempty_blocks']} | {result['span_merged_nonempty_units']} | {result['merged_boundary_edges']} | {result['start_assigned_radius_if_assumptions_hold']:.8f} | {result['span_merged_radius_if_assumptions_hold']:.8f} |")
    lines += ["", "Any usable flow whose stored interval plus rounding envelope crosses blocks joins those blocks, across all APP codes. Hour clipping can cause almost all adjacent blocks to merge, making the resulting floor zero. This is a worst-case interval diagnostic; it does not show that all flows are actually dependent or prove independent sampling units.",
              "", "## Empirical coarsening loss", "",
              "The M=2 count table projects exactly to M=1. The differences below concern these two finite empirical observables only; they do not certify information lost relative to richer features."]
    lines += [f"- {period}: Fhat(log M=1) - Fhat(log M=2) = {loss:.8f}." for period, loss in summary["empirical_coarsening_loss_M1_minus_M2"].items()]
    lines.append("")
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    prepare_run, plan, prepared_tables, expected = read_preparation(args.prepare_dir)
    before = args.h5.stat()
    print("Verifying source SHA256 against the completed audit...", flush=True)
    input_hash = sha256(args.h5)
    if input_hash != plan["source"]["sha256"] or before.st_size != plan["source"]["bytes"]:
        raise ValueError("source bytes differ from the preparation audit")
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        if tables != prepared_tables:
            raise ValueError("flow table/schema metadata differs from completed audit")
        scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[prepare_run["parameters"]["time_unit"]]
        experiment = RealExperimentCounts(plan, tables, time_scale=scale, widths=args.block_seconds)
        args.out_dir.mkdir(parents=True, exist_ok=False)
        code = [Path(__file__), ROOT / "scripts/methodology_real_prepare.py", ROOT / "src/eibo/realexperiment.py",
                ROOT / "src/eibo/realdata.py", ROOT / "src/eibo/riskcert.py", ROOT / "src/eibo/statcore.py"]
        metadata = {"status": "running", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "source": {"path": str(args.h5.resolve()), "bytes": before.st_size, "sha256": input_hash},
                    "parameters": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                    "preparation": {"path": str(args.prepare_dir.resolve()), "files": [{"path": p.name, "sha256": sha256(p)} for p in sorted(args.prepare_dir.iterdir()) if p.is_file()]},
                    "python": platform.python_version(), "numpy": np.__version__, "backend": source.backend,
                    "reader_version": source.module.__version__, "code": [{"path": str(p), "sha256": sha256(p)} for p in code],
                    "privacy": "aggregated counts only; no raw IP, CID, keyed digests or per-flow output"}
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        save(args.out_dir / "plan_snapshot.json", plan)
        total = sum(table["rows"] for table in tables)
        for index, table in enumerate(tables, 1):
            for start in range(0, table["rows"], args.chunk_rows):
                experiment.add(source.read(table["path"], start, min(start + args.chunk_rows, table["rows"])), table["ppi_capacity"])
            print(f"[{index}/{len(tables)}] {table['path']}: counted={experiment.rows_read}/{total}", flush=True)
        after = args.h5.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("source changed while counting")
        if experiment.rows_read != total:
            raise RuntimeError("incomplete scan")
        experiment.reconcile(expected)
        summary = analyze_counts(experiment)
        save(args.out_dir / "summary.json", summary)
        save(args.out_dir / "symbol_counts.json", {"known_service_codes": experiment.known.tolist(),
                                                   "representation": "canonical statcore log grid, forward +1 -> direction 0, reverse -1 -> direction 1",
                                                   "counts": {period: {str(rung): matrix.tolist() for rung, matrix in values.items()} for period, values in experiment.counts.items()}})
        save(args.out_dir / "time_unit_diagnostics.json", {p: geometry.diagnostics(experiment.priors, plan["alpha"]) for p, geometry in experiment.geometry.items()})
        with (args.out_dir / "per_service_metrics.csv").open("x", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["log_M", "service_code", "pilot_n", "certificate_n", "evaluation_n", "pilot_model_evaluation_error", "recent_model_evaluation_error", "evaluation_unseen_mass", "empirical_TV_certificate_evaluation"])
            for representation in summary["representations"]:
                periods = representation["periods"]
                for i, service in enumerate(summary["known_service_codes"]):
                    writer.writerow([representation["M"], service, *(periods[p]["sample_counts"][i] for p in PERIODS),
                                     periods["evaluation"]["pilot_classifier"]["per_service_error"][i],
                                     periods["evaluation"]["certificate_classifier"]["per_service_error"][i],
                                     periods["evaluation"]["pilot_classifier"]["per_service_unseen_symbol_mass"][i],
                                     representation["drift"]["certificate_to_evaluation"]["per_service_empirical_tv"][i]])
        (args.out_dir / "report.md").write_text(report_text(summary, plan))
        metadata.update({"status": "complete", "rows_read": total, "elapsed_seconds": time.monotonic() - started,
                         "count_reconciliation": "all audited period/service counts, refinement projection and time-unit counts matched",
                         "outputs": [{"path": p.name, "sha256": sha256(p), "bytes": p.stat().st_size} for p in sorted(args.out_dir.iterdir()) if p.name != "run.json"]})
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"Complete: {total} rows; {len(experiment.known)} fixed known APP codes; all count reconciliations passed.")
        print(f"Report: {(args.out_dir / 'report.md').resolve()}")
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--prepare-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=["auto", "tables", "h5py"], default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20000)
    parser.add_argument("--block-seconds", type=int, nargs="+", default=[3600, 21600, 86400])
    args = parser.parse_args()
    if not args.h5.is_file() or not args.prepare_dir.is_dir() or args.out_dir.exists():
        parser.error("H5 and preparation directory must exist; output directory must be fresh")
    if args.chunk_rows < 1 or len(set(args.block_seconds)) != len(args.block_seconds) or any(width < 3600 or width % 3600 for width in args.block_seconds):
        parser.error("positive chunk size and distinct whole-hour block sizes are required")
    plan = json.loads((args.prepare_dir / "experiment_plan.json").read_text())
    if any(width < plan["time_rounding_envelope_seconds"] for width in args.block_seconds):
        parser.error("blocks must be at least the declared rounding envelope")
    run(args)


if __name__ == "__main__":
    main()
