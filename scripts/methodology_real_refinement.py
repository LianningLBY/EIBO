#!/usr/bin/env python3
"""Compare four past-selected refinements of symbol 479 under fixed class priors."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.refinement import GROUPS, IPT_CUTS, SIZE_CUTS, RefinementCounts, run_refinements, validate_grid  # noqa: E402
from eibo.realdata import FlowSource  # noqa: E402
from eibo.rolling import MODELS, symbol_dictionary  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_monthly import number, save, write_csv  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, read_rolling, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402


def check_original(result, baseline):
    for row in result["confusions"]:
        if row["group"] == "original":
            token = (row["target"], 2, row["model"])
            if not np.array_equal(np.asarray(row["counts_true_by_predicted"]), baseline[token]):
                raise ValueError("original-representation result differs from stage 6")


def report_text(result, *, cache, protocol):
    lines = ["# Four past-selected cell-refinement comparisons", "",
             f"Canonical cell {protocol['symbol_id']}: `{protocol['decoded']}`. All {len(cache['known'])} original known APPs compete under unchanged priors; unknown-class error is excluded.",
             "The original log M=2 baseline reproduces every saved stage 6 confusion matrix. All groups share the same training and target flows in each window, and every refined histogram projects exactly to the original histogram.", "",
             "## Selection protocol", "",
             "original leaves the observable unchanged; size_split chooses one size position and one binary threshold; ipt_split chooses one binary threshold on the second packet's IPT; size_ipt_split reuses both selected main-effect cuts as a crossed partition. Outside the chosen cell, predictions remain identical to the same-window original model.",
             "Cut candidates and allowed size positions are fixed in selection_protocol.json before the H5 scan. Each window selects cuts by the full-known-class training empirical-risk improvement, using pi_i / n_i where n_i includes all training flows of class i, not only its cell flows.",
             f"Each valid low/high training child must contain at least {protocol['minimum_leaf_flows']} pooled flows. This is a complexity rule, not an independent-sample count. No eligible split gives an explicit identity fallback; a combined group may then retain only its available component.",
             "Invalid/nonfinite/negative IPT2 values have an explicit invalid atom/child and do not remove flows. A child absent from all training classes backs off to its original parent prediction. Raw size atoms retain values above the old codec's saturation.", "",
             "## Chosen past-only thresholds", "",
             "| Target | Model | Last training end | Target start | Size packet | Size threshold B | IPT2 threshold ms |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for row in result["selections"]:
        size, ipt = row.get("size"), row.get("ipt")
        lines.append(f"| {row['target']} | {row['model']} | {row.get('last_training_end_epoch','NA')} | {row.get('target_start_epoch','NA')} | {size['position'] if size else 'NA'} | {number(size['threshold'] if size else None)} | {number(ipt['threshold'] if ipt else None)} |")
    lines += ["", "## Monthly comparisons", "",
              "Negative error change means improvement over the same-window original model. Positive empirical representation gain means a lower target-sample Bayes functional; it does not guarantee that the past-trained classifier improves.", "",
              "| Target | Model | Group | Error % | Error change pp | Empirical F % | Empirical gain pp | APP2 error % | APP34 error % | Children | Unseen-child target flows |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in result["monthly"]:
        lines.append(f"| {row['target']} | {row['model']} | {row['group']} | {number((row.get('weighted_error') or {}).get('value'),100)} | {number((row.get('error_change') or {}).get('value'),100)} | {number(row.get('empirical_F'),100)} | {number(row.get('empirical_representation_gain'),100)} | {number(row.get('APP2_error'),100)} | {number(row.get('APP34_error'),100)} | {row.get('cell_children','NA')} | {row.get('unseen_child_target_flows','NA')} |")
    lines += ["", "## Period classifier comparison", "",
              "Period error pools wrong counts within each class before applying the fixed priors. It is not a mean of monthly macro errors. No pooled empirical F is reported: rolling cuts may differ across months, so their child columns cannot be pooled as one common observable.", "",
              "| Period | Model | Group | Error % | Error change pp | Positive class changes pp | Negative class changes pp | APP2 error % | APP34 error % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for row in result["periods"]:
        lines.append(f"| {row['period']} | {row['model']} | {row['group']} | {number((row.get('weighted_error') or {}).get('value'),100)} | {number((row.get('error_change') or {}).get('value'),100)} | {number(row.get('positive_class_changes'),100)} | {number(row.get('negative_class_changes'),100)} | {number(row.get('APP2_error'),100)} | {number(row.get('APP34_error'),100)} |")
    lines += ["", "## Evaluation-period class improvements and harms", "",
              "| Model | Group | Direction | APP | n | Status | Conditional change pp | Weighted change pp |",
              "|---|---|---|---:|---:|---|---:|---:|"]
    for model in protocol["models"]:
        for group in GROUPS[1:]:
            rows = [row for row in result["period_classes"] if row["period"] == "evaluation" and row["model"] == model and row["group"] == group and row["weighted_error_change"] is not None]
            for sign, direction in ((-1, "improvement"), (1, "harm")):
                ranked = sorted((row for row in rows if sign * row["weighted_error_change"] > 0), key=lambda row: -sign * row["weighted_error_change"])
                for row in ranked[:3]:
                    lines.append(f"| {model} | {group} | {direction} | {row['APP']} | {row['target_n']} | {row['status']} | {number(row['conditional_error_change'],100)} | {number(row['weighted_error_change'],100)} |")
    lines += ["", "## Interpretation and evidence files", "",
              "The cell, the timing feature and this experiment family were motivated by earlier views of the same months. Actual cuts use past training labels only, but results remain exploratory rather than a fresh confirmatory holdout. No significance test, validated population risk floor or claim of independent time units is produced.",
              "Size, timing and combined groups use identical training samples within each window; no new matched-sample randomization across windows is run. Temporal window comparisons retain their original different training amounts.",
              "The monthly sample identity is error_change = -empirical_representation_gain + empirical_gap_change. The gap is classifier error minus the target empirical Bayes functional; its change is descriptive, not a causal effect.",
              "Missing training classes make all four models unavailable; no class/prior is dropped. Missing target classes retain classification identification ranges, while the complete-class empirical F/gain stays NA. Per-class empirical representation-gain contributions are signed and can be negative; their complete-class sum equals the nonnegative total gain.",
              "threshold_selections.csv and threshold_candidates.csv record all past-only choices and candidate scores. class_metrics.csv, period_class_metrics.csv and cell_children.csv retain all classes, errors/transfers and child competitors. confusion_matrices.json retains full prediction counts; monthly_atomic_counts.json supports deterministic replay without individual flows. Input/code/output hashes are in run.json.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    cache = read_cache(args.monthly_dir)
    _, _, _, baseline = read_rolling(args.rolling_dir, cache, args.monthly_dir)
    prepare_run, plan, prepared_tables, expected = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("preparation and monthly cache use different fixed plans")
    before = args.h5.stat()
    print("Verifying raw H5 SHA256, completed inputs and original rolling baselines...", flush=True)
    if sha256(args.h5) != plan["source"]["sha256"] or before.st_size != plan["source"]["bytes"]:
        raise ValueError("H5 source bytes differ from preparation")
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        if tables != prepared_tables:
            raise ValueError("H5 table/schema metadata differs from preparation")
        scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[prepare_run["parameters"]["time_unit"]]
        counts = RefinementCounts(plan, tables, time_scale=scale, symbol=args.symbol_id,
                                  size_cuts=args.size_cuts, ipt_cuts=args.ipt_cuts, positions=args.size_positions)
        decoded = symbol_dictionary(counts.k, 2)[1][args.symbol_id]
        protocol = {"symbol_id": args.symbol_id, "decoded": decoded, "size_positions": list(counts.positions),
                    "size_candidates_bytes": counts.size_cuts.tolist(), "IPT2_candidates_ms": counts.ipt_cuts.tolist(),
                    "groups": list(GROUPS), "models": args.models, "minimum_leaf_flows": args.min_leaf_flows,
                    "selection": "maximize full-known-class training empirical risk improvement; no target labels",
                    "tie_break": "ascending packet position then ascending cut, tolerance 1e-12",
                    "combined": "reuse independently selected main-effect cuts; no additional joint search",
                    "invalid_IPT": "explicit invalid atom; no flow filtering", "unseen_child": "back off to parent prediction",
                    "status": "exploratory family chosen after previous result inspection"}
        inputs = [directory / name for directory, names in ((args.monthly_dir, ("run.json", "monthly_symbol_counts.json", "summary.json", "plan_snapshot.json")),
                  (args.rolling_dir, ("run.json", "summary.json", "plan_snapshot.json", "confusion_matrices.json")),
                  (args.prepare_dir, ("run.json", "experiment_plan.json", "tables.json", "audit.json", "period_service_counts.csv", "time_unit_diagnostics.json"))) for name in names]
        code = [Path(__file__), ROOT / "src/eibo/refinement.py", ROOT / "src/eibo/monthlydrift.py", ROOT / "src/eibo/rolling.py",
                ROOT / "src/eibo/realexperiment.py", ROOT / "src/eibo/realdata.py", ROOT / "src/eibo/riskcert.py", ROOT / "src/eibo/statcore.py",
                ROOT / "scripts/methodology_real_reallocation.py", ROOT / "scripts/methodology_real_rolling.py", ROOT / "scripts/methodology_real_monthly.py",
                ROOT / "scripts/methodology_real_experiment.py", ROOT / "scripts/methodology_real_prepare.py"]
        metadata = start_run(args, inputs=inputs, code=code, source=plan["source"])
        metadata.update({"backend": source.backend, "reader_version": source.module.__version__, "selection_protocol": protocol})
        (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
        save(args.out_dir / "selection_protocol.json", protocol)
        save(args.out_dir / "plan_snapshot.json", plan)
        total = sum(table["rows"] for table in tables)
        for index, table in enumerate(tables, 1):
            for start in range(0, table["rows"], args.chunk_rows):
                counts.add(source.read(table["path"], start, min(start + args.chunk_rows, table["rows"])), table["ppi_capacity"])
            print(f"[{index}/{len(tables)}] {table['path']}: rows={counts.rows_read}/{total}", flush=True)
        after = args.h5.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or counts.rows_read != total or total != cache["run"]["rows_read"]:
            raise RuntimeError("source changed or full scan is incomplete")
        counts.reconcile(expected)
        counts.reconcile_cache(cache)
        invalid = int(sum(values[0, :, :, -1].sum() for values in counts.atoms.values()))
        save(args.out_dir / "monthly_atomic_counts.json", {"known_service_codes": counts.known.tolist(), "symbol_id": counts.symbol,
             "size_positions": list(counts.positions), "size_candidates_bytes": counts.size_cuts.tolist(), "IPT2_candidates_ms": counts.ipt_cuts.tolist(),
             "axis_order": ["size_position", "fixed_APP_order", "size_atom", "IPT2_atom_with_invalid_last"],
             "counts": {key: values.tolist() for key, values in counts.atoms.items()}}, compact=True)
        print("Every monthly base symbol and all-class cell atom count reconciled. Selecting past-only cuts...", flush=True)
        result = run_refinements(cache, counts.atoms, symbol=counts.symbol, positions=counts.positions,
                                 size_cuts=counts.size_cuts, ipt_cuts=counts.ipt_cuts, min_leaf=args.min_leaf_flows,
                                 small_n=args.small_n, models=args.models, progress=lambda key: print(f"Scored four groups: {key}", flush=True))
        check_original(result, baseline)
        save(args.out_dir / "summary.json", {"status": "exploratory past-only representation comparisons", "known_service_codes": counts.known.tolist(),
             "known_priors": counts.priors.tolist(), "unknown_prior": plan["unknown_prior"], "protocol": protocol, "rows_read": counts.rows_read,
             "counts_reconciled": True, "original_models_reproduced": True, "invalid_IPT2_cell_flows": invalid,
             "monthly": result["monthly"], "periods": result["periods"], "selections": result["selections"]})
        save(args.out_dir / "confusion_matrices.json", {"known_service_codes": counts.known.tolist(), "matrices": result["confusions"]}, compact=True)
        for name, key in (("class_metrics", "classes"), ("period_class_metrics", "period_classes"), ("cell_children", "children"), ("threshold_candidates", "candidates")):
            if result[key]:
                write_csv(args.out_dir / (name + ".csv"), result[key])
        selection_rows = []
        for row in result["selections"]:
            size, ipt = row.get("size"), row.get("ipt")
            selection_rows.append({"target": row["target"], "model": row["model"], "status": row["status"], "training_slices": ";".join(row["training_slices"]),
                 "last_training_end_epoch": row.get("last_training_end_epoch"), "target_start_epoch": row.get("target_start_epoch"),
                 "size_position": size["position"] if size else None, "size_threshold_bytes": size["threshold"] if size else None,
                 "size_training_gain": size["training_empirical_gain"] if size else None, "IPT2_threshold_ms": ipt["threshold"] if ipt else None,
                 "IPT_training_gain": ipt["training_empirical_gain"] if ipt else None})
        write_csv(args.out_dir / "threshold_selections.csv", selection_rows)
        for name, key in (("monthly_summary", "monthly"), ("period_summary", "periods")):
            rows = []
            for row in result[key]:
                error, delta = row.get("weighted_error") or {}, row.get("error_change") or {}
                rows.append({"target": row.get("target", row["period"]), "model": row["model"], "group": row["group"], "status": row["status"],
                     "weighted_error": error.get("value"), "error_change": delta.get("value"),
                     "error_change_range_min": delta.get("range_from_unobserved_values", [None, None])[0],
                     "error_change_range_max": delta.get("range_from_unobserved_values", [None, None])[1],
                     "empirical_F": row.get("empirical_F"), "empirical_representation_gain": row.get("empirical_representation_gain"),
                     "empirical_gap_change": row.get("empirical_gap_change"),
                     "training_empirical_gain": row.get("training_empirical_gain"), "APP2_error": row.get("APP2_error"), "APP34_error": row.get("APP34_error"),
                     "effective_size_split": row.get("effective_size_split"), "effective_IPT_split": row.get("effective_IPT_split"),
                     "unseen_child_target_flows": row.get("unseen_child_target_flows")})
            write_csv(args.out_dir / (name + ".csv"), rows)
        (args.out_dir / "report.md").write_text(report_text(result, cache=cache, protocol=protocol))
        metadata.update({"rows_read": counts.rows_read, "invalid_IPT2_cell_flows": invalid})
        finish_run(args.out_dir, metadata, started)
        for row in result["selections"]:
            size, ipt = row.get("size"), row.get("ipt")
            print(f"CUT {row['target']} {row['model']} status={row['status']} size_packet={size['position'] if size else 'NA'} size_B={size['threshold'] if size else 'NA'} IPT2_ms={ipt['threshold'] if ipt else 'NA'}")
        print("Complete. Period errors: fixed-prior weighted fractions; delta_pp compares the same-window original representation.")
        for row in result["periods"]:
            print(f"PERIOD {row['period']} {row['model']} {row['group']} error={number((row.get('weighted_error') or {}).get('value'))} delta_pp={number((row.get('error_change') or {}).get('value'),100)} APP2={number(row.get('APP2_error'))} APP34={number(row.get('APP34_error'))}")
        print(f"Invalid IPT2 values inside the cell (retained): {invalid}")
        print(f"Report: {(args.out_dir / 'report.md').resolve()}")
    finally:
        source.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("h5", "prepare-dir", "monthly-dir", "rolling-dir", "out-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--symbol-id", type=int, default=479)
    parser.add_argument("--size-positions", nargs="+", type=int)
    parser.add_argument("--size-cuts", nargs="+", type=int, default=list(SIZE_CUTS))
    parser.add_argument("--ipt-cuts", nargs="+", type=float, default=list(IPT_CUTS))
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--min-leaf-flows", type=int, default=200)
    parser.add_argument("--small-n", type=int, default=200)
    parser.add_argument("--chunk-rows", type=int, default=20000)
    args = parser.parse_args()
    if not args.h5.is_file() or not all(directory.is_dir() for directory in (args.prepare_dir, args.monthly_dir, args.rolling_dir)) or args.out_dir.exists():
        parser.error("existing H5/completed inputs and a fresh output directory required")
    if min(args.min_leaf_flows, args.small_n, args.chunk_rows) < 1 or len(set(args.models)) != len(args.models):
        parser.error("positive leaf/small-n/chunk budgets and distinct models required")
    try:
        validate_grid(args.size_cuts, integer=True)
        validate_grid(args.ipt_cuts)
    except ValueError as error:
        parser.error(str(error))
    run(args)


if __name__ == "__main__":
    main()
