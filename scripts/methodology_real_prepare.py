#!/usr/bin/env python3
"""Prepare a time-isolated CESNET experiment and audit connection candidates."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.realdata import DAY, FlowSource, PreparationAudit, utc  # noqa: E402

SOURCES = ["https://zenodo.org/records/17249078", "https://cesnet.github.io/cesnet-datazoo/features/"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, payload):
    with path.open("x") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def run(args):
    started = time.monotonic()
    before = args.h5.stat()
    input_hash = None
    if args.sha256 or args.expected_sha256:
        print("Hashing source H5...", flush=True)
        input_hash = sha256(args.h5)
        if args.expected_sha256 and input_hash != args.expected_sha256.lower():
            raise ValueError(f"input SHA256 differs from the declared source: {input_hash}")
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[args.time_unit]
        audit = PreparationAudit(tables, k=args.k, time_scale=scale, gap_seconds=args.gap_seconds,
                                 rounding_seconds=args.rounding_seconds, sample_size=args.identifier_sample,
                                 seed=args.seed, salt=os.urandom(32), block_seconds=args.block_seconds)
        if any(args.k > table["ppi_capacity"] for table in tables):
            raise ValueError("k exceeds PPI capacity")
        total = sum(table["rows"] for table in tables)
        args.out_dir.mkdir(parents=True, exist_ok=False)
        metadata = {"status": "running", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "parameters": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                    "source": {"path": str(args.h5.resolve()), "bytes": before.st_size, "sha256": input_hash},
                    "backend": source.backend, "reader_version": source.module.__version__,
                    "python": platform.python_version(), "numpy": np.__version__, "table_rows": total,
                    "code": [{"path": str(path), "sha256": sha256(path)} for path in
                             (Path(__file__), ROOT / "src/eibo/realdata.py", ROOT / "src/eibo/riskcert.py", ROOT / "src/eibo/statcore.py")],
                    "privacy": "only aggregates and schema; no raw CID/IP values or keyed digests are exported"}
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        save(args.out_dir / "tables.json", tables)
        budget = min(total, args.max_rows) if args.max_rows is not None else total
        for index, table in enumerate(tables, 1):
            for start in range(0, table["rows"], args.chunk_rows):
                remaining = budget - audit.counts["rows_read"]
                if remaining <= 0:
                    break
                stop = min(table["rows"], start + args.chunk_rows, start + remaining)
                audit.add(source.read(table["path"], start, stop), table["ppi_capacity"])
            print(f"[{index}/{len(tables)}] {table['path']}: scanned={audit.counts['rows_read']}/{total}", flush=True)
            if audit.counts["rows_read"] >= budget:
                break
        after = args.h5.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise RuntimeError("input changed while auditing")
        full_scan = audit.counts["rows_read"] == total
        plan = audit.plan(min_pilot_flows=args.min_pilot_flows, alpha=args.alpha, full_scan=full_scan)
        plan["source"] = metadata["source"]
        present_dates = {table["day_seconds"] for table in tables}
        missing_dates = [utc(day)[:10] for day in range(audit.begin, audit.end, DAY) if day not in present_dates]
        valid_n = audit.counts["valid_timestamp_records"]
        result = {"status": "complete" if full_scan else "partial", "record_counts": dict(audit.counts),
                  "time_start_min_utc": utc(audit.min_time) if audit.min_time is not None else None,
                  "time_start_max_utc": utc(audit.max_time) if audit.max_time is not None else None,
                  "hour_aligned_start_fraction": audit.counts["starts_exactly_on_hour"] / valid_n if valid_n else None,
                  "missing_table_dates": missing_dates, "identifier_audit": audit.sample.summary(),
                  "sources": SOURCES,
                  "interpretation": ["ID is documented as a unique flow-record identifier, not a multi-flow session ID.",
                                     "CID repetitions are candidates only; absence of sampled repeats proves neither uniqueness nor independence.",
                                     "Hourly start-time clipping limits chronological resolution; table order is not subhour chronology.",
                                     "Time separation, gaps and candidate grouping do not establish independence or stationarity."]}
        diagnostics = audit.unit_diagnostics(plan)
        save(args.out_dir / "audit.json", result)
        save(args.out_dir / "experiment_plan.json", plan)
        save(args.out_dir / "time_unit_diagnostics.json", diagnostics)
        with (args.out_dir / "daily_service_counts.csv").open("x", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date_utc", "service_code", "usable_flows"])
            writer.writerows((utc(day * DAY)[:10], service, n) for (day, service), n in sorted(audit.daily.items()))
        with (args.out_dir / "period_service_counts.csv").open("x", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["period", "service_code", "whole_interval_usable_flows", "selected_from_pilot"])
            for period, counts in audit.period.items():
                writer.writerows((period, service, n, service in plan["known_service_codes"]) for service, n in sorted(counts.items()))
        lines = ["# Real-data preparation audit", "", f"Scan: {result['status']}; plan: {plan['status']}; rows: {audit.counts['rows_read']}/{total}.",
                 f"Known APP codes selected only on pilot: {len(plan['known_service_codes'])}.",
                 f"Hour-aligned flow starts: {result['hour_aligned_start_fraction']}.", "",
                 "## Fixed chronological windows", "", "| Period | Start UTC | End UTC (exclusive) |",
                 "|---|---|---|"]
        lines += [f"| {name} | {window['start_utc']} | {window['end_utc_exclusive']} |" for name, window in plan["windows"].items()]
        lines += ["", f"Entire stored intervals plus a {args.rounding_seconds}s end margin must fit the window. The target excludes short prefixes, invalid timestamps, gaps and boundary-crossing flows. The resulting law is a filtered population, not all original traffic.",
                  "", "## Identifier sample", "", "| Field | Sample rows | Empty/zero-like | Repeated keys | Keys across services | Keys across days |",
                  "|---|---:|---:|---:|---:|---:|"]
        for field, values in result["identifier_audit"]["field_statistics"].items():
            lines.append(f"| {field} | {values['sample_rows']} | {values['missing_or_zero_like_rows']} | {values['repeated_keys']} | {values['keys_across_services']} | {values['keys_across_days']} |")
        lines += ["", "These sampled candidate keys are not validated session assignments. Destination endpoint alone groups multiple clients; source endpoint fields are absent in this dataset.",
                  "", "## Global time-unit sensitivity (conditional diagnostic only)", "",
                  "| Block seconds | Nonempty blocks | Squared-change budget | Radius if independent and conditionally unbiased |",
                  "|---:|---:|---:|---:|"]
        for item in diagnostics:
            lines.append(f"| {item['block_seconds']} | {item['nonempty_global_blocks']} | {item['squared_change_budget']:.6g} | {item['radius_if_units_independent_and_conditionally_unbiased']:.6g} |")
        lines += ["", "No real-data risk floor or coverage estimate is produced. Independence, conditional unbiasedness and stationarity remain unverified. Missing pilot-selected classes in certificate/evaluation are reported without silently removing them.",
                  "", "Sources: " + ", ".join(SOURCES), ""]
        (args.out_dir / "report.md").write_text("\n".join(lines))
        metadata.update({"status": result["status"], "plan_status": plan["status"], "elapsed_seconds": time.monotonic() - started,
                         "outputs": [{"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
                                     for path in sorted(args.out_dir.iterdir()) if path.name != "run.json"]})
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"Complete: scan={result['status']}, plan={plan['status']}, pilot-selected APP codes={len(plan['known_service_codes'])}")
        print(f"Report: {(args.out_dir / 'report.md').resolve()}")
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=["auto", "tables", "h5py"], default="auto")
    parser.add_argument("--time-unit", choices=["seconds", "milliseconds", "microseconds", "nanoseconds"], default="seconds")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--gap-seconds", type=int, default=DAY)
    parser.add_argument("--rounding-seconds", type=int, default=3600)
    parser.add_argument("--block-seconds", type=int, nargs="+", default=[3600, 21600, DAY])
    parser.add_argument("--chunk-rows", type=int, default=20000)
    parser.add_argument("--identifier-sample", type=int, default=50000)
    parser.add_argument("--min-pilot-flows", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--max-rows", type=int, help="smoke check only unless the entire source is scanned")
    parser.add_argument("--sha256", action="store_true")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    if not args.h5.is_file() or args.out_dir.exists():
        parser.error("input H5 must exist and output directory must be fresh")
    if min(args.k, args.chunk_rows, args.min_pilot_flows) < 1 or min(args.gap_seconds, args.rounding_seconds, args.identifier_sample, args.seed) < 0:
        parser.error("invalid positive/nonnegative argument")
    if args.max_rows is not None and args.max_rows < 1:
        parser.error("max-rows must be positive")
    if not 0 < args.alpha < 1 or len(set(args.block_seconds)) != len(args.block_seconds):
        parser.error("alpha must lie in (0,1); block sizes must be distinct")
    if any(width < max(3600, args.rounding_seconds) or width % 3600 for width in args.block_seconds):
        parser.error("time blocks must be whole hours, at least one hour and at least the rounding envelope")
    if args.expected_sha256 and not re.fullmatch(r"[0-9a-fA-F]{64}", args.expected_sha256):
        parser.error("expected-sha256 must be 64 hexadecimal characters")
    run(args)


if __name__ == "__main__":
    main()
