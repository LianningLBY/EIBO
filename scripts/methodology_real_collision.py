#!/usr/bin/env python3
"""Rescan raw CESNET PPI for exact size/IPT distributions in canonical cell 479."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.collisionaudit import CollisionCounts, collision_analysis  # noqa: E402
from eibo.realdata import FlowSource  # noqa: E402
from eibo.rolling import symbol_dictionary  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_monthly import number, save, write_csv  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run, write_rows  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

FEATURE_SOURCE = "https://cesnet.github.io/cesnet-datazoo/features/"
CHANNEL_SOURCE = "https://github.com/CESNET/cesnet-datazoo/blob/main/cesnet_datazoo/constants.py"


def report_text(result, *, apps, symbol, decoded, reference_months):
    lines = [f"# Raw PPI diagnostics inside symbol {symbol}", "", f"Canonical cell: `{decoded}`. Detail APPs: {apps[0]}, {apps[1]}.",
             "All monthly counts, for every fixed known class and both original representations, were reconciled against the completed monthly cache.",
             f"PPI channels and units follow [CESNET feature documentation]({FEATURE_SOURCE}) and [channel constants]({CHANNEL_SOURCE}): row 0 is IPT in milliseconds, row 1 direction, row 2 transport-payload size in bytes. These are stored exporter observables; wire size and sub-millisecond timing cannot be recovered here.",
             "Exact observed size values are retained even above the old codec's 1500-byte saturation. No per-flow identifiers or raw sequences are exported.", "",
             "## Cell occupancy for the two detail classes", "",
             "| Scope | Target | APP | All class flows | Cell flows | Class probability of cell % | Known-only posterior in cell % |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for row in result["occupancy"]:
        if row["APP"] in apps:
            lines.append(f"| {row['scope']} | {row['target']} | {row['APP']} | {row['class_n']} | {row['symbol_n']} | {number(row['class_probability_of_symbol'],100)} | {number(row['known_only_posterior_in_symbol'],100)} |")
    lines += ["", "Posteriors use every fixed known competitor under the unchanged class priors, rather than the observed two-class flow mixture. Unknown classes are excluded.",
              "", "## Monthly strongest cell competitors", "", "| Target | APP | Cell flows | Fixed-prior mass | Known-only posterior % |", "|---|---:|---:|---:|---:|"]
    for key in sorted({row["target"] for row in result["occupancy"] if row["scope"] == "monthly"}):
        rows = [row for row in result["occupancy"] if row["scope"] == "monthly" and row["target"] == key]
        for row in sorted(rows, key=lambda item: -(item["fixed_prior_symbol_mass"] or 0))[:3]:
            lines.append(f"| {key} | {row['APP']} | {row['symbol_n']} | {number(row['fixed_prior_symbol_mass'])} | {number(row['known_only_posterior_in_symbol'],100)} |")
    lines += ["", "## Monthly size/IPT summaries", "", "Quantiles use the exact empirical inverse CDF. Values use the feature's unit. Invalid values are excluded only from that marginal and remain in the cell-flow counts.",
              "", "| Target | APP | Feature | Packet | Cell flows | Valid / invalid | Median | q05 | q95 | Max | Zero % |", "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in result["features"]:
        if row["scope"] == "monthly" and not row["target"].startswith("pilot/"):
            lines.append(f"| {row['target']} | {row['APP']} | {row['feature']} | {row['position']} | {row['flows']} | {row['valid_values']} / {row['invalid_values']} | {number(row['median'])} | {number(row['q05'])} | {number(row['q95'])} | {number(row['max'])} | {number(row['zero_fraction'],100)} |")
    lines += ["", "## Largest between-class marginal differences by month", "", "| Target | Feature | Packet | APP left n | APP right n | Empirical TV % | CDF sup distance % |", "|---|---|---:|---:|---:|---:|---:|"]
    for key in sorted({row["target"] for row in result["comparisons"] if row["scope"] == "monthly" and not row["target"].startswith("pilot/")}):
        rows = [row for row in result["comparisons"] if row["target"] == key and row["comparison"] == "within_symbol_between_classes" and not row["structural_first_IPT"] and row["empirical_TV"] is not None]
        for row in sorted(rows, key=lambda item: -item["empirical_TV"])[:5]:
            lines.append(f"| {key} | {row['feature']} | {row['position']} | {row['source_valid_n']} | {row['target_valid_n']} | {number(row['empirical_TV'],100)} | {number(row['empirical_CDF_sup_distance'],100)} |")
    lines += ["", "## Largest within-class marginal drifts from the reference", "", "Reference: " + ", ".join(reference_months) + ".", "",
              "| Target | APP | Feature | Packet | Reference n | Target n | Empirical TV % |", "|---|---:|---|---:|---:|---:|---:|"]
    for key in sorted({row["target"] for row in result["comparisons"] if row["comparison"] == "within_class_reference_to_month"}):
        for app in apps:
            rows = [row for row in result["comparisons"] if row["comparison"] == "within_class_reference_to_month" and row["target"] == key and row["target_APP"] == app and not row["structural_first_IPT"] and row["empirical_TV"] is not None]
            for row in sorted(rows, key=lambda item: -item["empirical_TV"])[:3]:
                lines.append(f"| {key} | {app} | {row['feature']} | {row['position']} | {row['source_valid_n']} | {row['target_valid_n']} | {number(row['empirical_TV'],100)} |")
    lines += ["", "## Interpretation", "",
              "The first IPT is structurally zero according to the exporter. It remains in the summaries for checking and is excluded from difference rankings; zero values at later positions remain valid observations.",
              "Marginal TVs and CDF distances are descriptive, without p-values or population uncertainty. Large exact-support TV can reflect sparse support and sampling noise. These marginal comparisons do not quantify joint-prefix separability, causal drift or achievable held-out multiclass gains.",
              "distributions.csv contains exact observed-value histograms; feature_summary.csv contains quantiles and invalid-value counts; marginal_comparisons.csv contains between-class differences and reference-to-month drift; cell_occupancy.csv retains every fixed known competitor. Whole-period interval guards and start-month assignment are unchanged.",
              "The cell and classes were selected after inspecting previous results. Subsequent representation selection needs separate past-only training and future evaluation; no new representation is chosen or fitted here.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    cache = read_cache(args.monthly_dir)
    prepare_run, plan, prepared_tables, expected = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("monthly cache and preparation use different plans")
    if len(set(args.apps)) != 2 or not set(args.apps).issubset(cache["known"]) or not 0 <= args.symbol_id < cache["counts"][cache["slices"][0]["key"]][2].shape[1]:
        raise ValueError("two distinct fixed known classes and an in-alphabet cell required")
    if len(set(args.reference_months)) != len(args.reference_months) or not set(args.reference_months).issubset({item["month_utc"] for item in cache["slices"]}):
        raise ValueError("reference months must be distinct and present")
    before = args.h5.stat()
    print("Hashing raw H5 and validating prepared schema...", flush=True)
    input_hash = sha256(args.h5)
    if input_hash != plan["source"]["sha256"] or before.st_size != plan["source"]["bytes"]:
        raise ValueError("H5 bytes differ from the audited source")
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        if tables != prepared_tables:
            raise ValueError("H5 table/schema metadata differs from preparation")
        scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[prepare_run["parameters"]["time_unit"]]
        counts = CollisionCounts(plan, tables, time_scale=scale, symbol=args.symbol_id, apps=args.apps)
        inputs = [directory / name for directory, names in ((args.monthly_dir, ("run.json", "monthly_symbol_counts.json", "summary.json", "plan_snapshot.json")),
                  (args.prepare_dir, ("run.json", "experiment_plan.json", "tables.json", "audit.json", "period_service_counts.csv", "time_unit_diagnostics.json"))) for name in names]
        code = [Path(__file__), ROOT / "src/eibo/collisionaudit.py", ROOT / "src/eibo/monthlydrift.py", ROOT / "src/eibo/rolling.py",
                ROOT / "src/eibo/realdata.py", ROOT / "src/eibo/realexperiment.py", ROOT / "src/eibo/statcore.py", ROOT / "src/eibo/riskcert.py",
                ROOT / "scripts/methodology_real_rolling.py", ROOT / "scripts/methodology_real_monthly.py", ROOT / "scripts/methodology_real_prepare.py",
                ROOT / "scripts/methodology_real_experiment.py", ROOT / "scripts/methodology_real_reallocation.py"]
        metadata = start_run(args, inputs=inputs, code=code, source=plan["source"])
        metadata.update({"backend": source.backend, "reader_version": source.module.__version__, "IPT_unit": "milliseconds",
                         "size_unit": "transport_payload_bytes", "PPI_channels": {"IPT": 0, "DIR": 1, "SIZE": 2},
                         "feature_sources": [FEATURE_SOURCE, CHANNEL_SOURCE]})
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        total = sum(table["rows"] for table in tables)
        for index, table in enumerate(tables, 1):
            for start in range(0, table["rows"], args.chunk_rows):
                counts.add(source.read(table["path"], start, min(start + args.chunk_rows, table["rows"])), table["ppi_capacity"])
            print(f"[{index}/{len(tables)}] {table['path']}: rows={counts.rows_read}/{total}", flush=True)
        after = args.h5.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or counts.rows_read != total or total != cache["run"]["rows_read"]:
            raise RuntimeError("source changed or raw scan is incomplete")
        counts.reconcile(expected)
        counts.reconcile_cache(cache)
        result = collision_analysis(counts, reference_months=args.reference_months, small_n=args.small_n)
        decoded = symbol_dictionary(counts.k, 2)[1][args.symbol_id]
        invalid = sum(row["invalid_values"] for row in result["features"] if row["scope"] == "monthly")
        first_nonzero = sum(sum(marginal.values.values()) - marginal.values[0.0]
                            for details in counts.details.values() for app in args.apps
                            for marginal in [details[app][("IPT_ms", 1)]])
        for name, key in (("feature_summary", "features"), ("cell_occupancy", "occupancy"), ("marginal_comparisons", "comparisons")):
            write_csv(args.out_dir / (name + ".csv"), result[key])
        write_rows(args.out_dir / "distributions.csv", result["distributions"],
                   ["scope", "target", "APP", "feature", "position", "value", "count", "valid_values", "probability"])
        save(args.out_dir / "summary.json", {"symbol_id": args.symbol_id, "decoded": decoded, "apps": args.apps,
             "known_service_codes": counts.known.tolist(), "known_priors": counts.priors.tolist(),
             "reference_months": args.reference_months, "rows_read": counts.rows_read, "counts_reconciled": True,
             "invalid_feature_values": invalid, "first_IPT_nonzero_valid_values": first_nonzero,
             "feature_summary": result["features"], "cell_occupancy": result["occupancy"], "marginal_comparisons": result["comparisons"],
             "status": "retrospective descriptive marginals; no fitted representation or risk certificate"})
        save(args.out_dir / "plan_snapshot.json", plan)
        (args.out_dir / "report.md").write_text(report_text(result, apps=args.apps, symbol=args.symbol_id, decoded=decoded, reference_months=args.reference_months))
        metadata["rows_read"] = counts.rows_read
        finish_run(args.out_dir, metadata, started)
        print(f"Complete. Canonical symbol {args.symbol_id}: {decoded}; every monthly symbol count reconciled.")
        for key in sorted({row["target"] for row in result["occupancy"] if row["scope"] == "monthly" and not row["target"].startswith("pilot/")}):
            for row in result["occupancy"]:
                if row["scope"] == "monthly" and row["target"] == key and row["APP"] in args.apps:
                    print(f"CELL {key} APP={row['APP']} n={row['symbol_n']}/{row['class_n']} class_mass={number(row['class_probability_of_symbol'])} posterior_known={number(row['known_only_posterior_in_symbol'])}")
            rows = [row for row in result["comparisons"] if row["comparison"] == "within_symbol_between_classes" and row["target"] == key and not row["structural_first_IPT"] and row["empirical_TV"] is not None]
            for row in sorted(rows, key=lambda item: -item["empirical_TV"])[:3]:
                print(f"  DIFFERENCE {row['feature']} packet={row['position']} n={row['source_valid_n']}/{row['target_valid_n']} TV={number(row['empirical_TV'])} CDF={number(row['empirical_CDF_sup_distance'])}")
        print(f"Invalid detailed feature values (kept in cell-flow counts): {invalid}")
        print(f"First-IPT nonzero valid values: {first_nonzero}")
        print(f"Report: {(args.out_dir / 'report.md').resolve()}")
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--prepare-dir", type=Path, required=True)
    parser.add_argument("--monthly-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--symbol-id", type=int, default=479)
    parser.add_argument("--apps", nargs=2, type=int, default=[2, 34])
    parser.add_argument("--reference-months", nargs="+", default=["2024-12", "2025-01"])
    parser.add_argument("--chunk-rows", type=int, default=50000)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if not args.h5.is_file() or not args.prepare_dir.is_dir() or not args.monthly_dir.is_dir() or args.out_dir.exists() or min(args.chunk_rows, args.small_n) < 1:
        parser.error("existing H5/completed inputs, a fresh output directory and positive chunk-rows/small-n required")
    run(args)


if __name__ == "__main__":
    main()
