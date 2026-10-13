#!/usr/bin/env python3
"""Scan true size-pair joints and validate bounded local rules on past periods."""

from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.jointrefinement import GROUPS, JointCounts, check_joint, run_joint, validation_windows  # noqa: E402
from eibo.realdata import DAY, FlowSource  # noqa: E402
from methodology_real_atomic import HIERARCHY_CODE, HIERARCHY_FILES, flat_metrics, read_hierarchy  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_hierarchy import MONTHLY_FILES, REFINEMENT_FILES, read_refinement, write_table  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

CODE = HIERARCHY_CODE + ("scripts/methodology_real_atomic.py", "src/eibo/atomicdiagnostic.py", "src/eibo/jointrefinement.py")


def collection_protocol(cache, prior, windows, threshold):
    return {"symbol_id": prior["symbol_id"], "size_positions": prior["size_positions"], "size_candidates_bytes": prior["size_candidates_bytes"],
            "IPT2_candidates_ms": prior["IPT2_candidates_ms"], "fixed_IPT2_threshold_ms": threshold,
            "low_time_atoms": int(np.flatnonzero(np.asarray(prior["IPT2_candidates_ms"]) == threshold)[0]) + 1,
            "size_pairs": [list(p) for p in itertools.combinations(prior["size_positions"], 2)], "window_spec": windows,
            "known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": cache["plan"]["unknown_prior"],
            "month_keys": [s["key"] for s in cache["slices"]],
            "joint_axes": ["size_pair", "fixed_APP_order", "left_size_atom", "right_size_atom", "valid_low_IPT_atom"]}


def save_counts(directory, collection, joints, roles):
    payload = {f"m{i}_joint": joints[key] for i, key in enumerate(collection["month_keys"])}
    for token, role in roles.items():
        for field in ("base", "children", "single", "joint"):
            payload[token + "_" + field] = role[field]
    with (directory / "joint_counts.npz").open("xb") as handle:
        np.savez_compressed(handle, **payload)


def load_counts(directory, cache, prior, collection, old_atoms, inputs):
    metadata = json.loads((directory / "run.json").read_text())
    if metadata["status"] != "complete" or metadata["source_lineage"] != cache["plan"]["source"] or metadata["counts_reconciled"] is not True:
        raise ValueError("completed reconciled joint run with identical source required")
    manifests = {row["path"]: row["sha256"] for row in metadata["outputs"]}
    for filename in ("joint_counts.npz", "collection_protocol.json", "plan_snapshot.json"):
        if manifests.get(filename) != sha256(directory / filename):
            raise ValueError(f"joint cache artifact hash mismatch: {filename}")
    if json.loads((directory / "collection_protocol.json").read_text()) != collection or json.loads((directory / "plan_snapshot.json").read_text()) != cache["plan"]:
        raise ValueError("joint collection geometry, grid or plan differs")
    for relative in CODE + ("scripts/methodology_real_joint.py",):
        records = [r for r in metadata["code"] if Path(r["path"]).name == Path(relative).name]
        if len(records) != 1 or records[0]["sha256"] != sha256(ROOT / relative):
            raise ValueError(f"joint collection code lineage differs: {relative}")
    for path in inputs:
        previous = [r for r in metadata["input_artifacts"] if Path(r["path"]).name == path.name and Path(r["path"]).parent.name == path.parent.name]
        if len(previous) != 1 or previous[0]["sha256"] != sha256(path):
            raise ValueError("joint collection used different source artifacts")
    k, alphabet, bins, times = len(cache["known"]), cache["period_counts"]["pilot"][2].shape[1], len(prior["size_candidates_bytes"]) + 1, collection["low_time_atoms"]
    pairs, positions = tuple(map(tuple, collection["size_pairs"])), tuple(prior["size_positions"])
    shapes = {"base": (k, alphabet), "children": (k, 3), "single": (len(positions), k, bins, times), "joint": (len(pairs), k, bins, bins, times)}
    expected = {f"m{i}_joint": shapes["joint"] for i in range(len(collection["month_keys"]))}
    expected.update({r["id"] + "_" + field: shape for r in collection["window_spec"]["ranges"] for field, shape in shapes.items()})
    arrays = {}
    with np.load(directory / "joint_counts.npz", allow_pickle=False) as archive:
        if set(archive.files) != set(expected):
            raise ValueError("joint cache array members differ")
        for name, shape in expected.items():
            a = archive[name]
            if a.shape != shape or a.dtype.kind not in "iu" or np.any(a < 0) or np.any(a > cache["run"]["rows_read"]):
                raise ValueError("invalid joint cache integer counts")
            arrays[name] = a.astype(np.int64)
    joints = {key: arrays[f"m{i}_joint"] for i, key in enumerate(collection["month_keys"])}
    roles = {r["id"]: {field: arrays[r["id"] + "_" + field] for field in shapes} for r in collection["window_spec"]["ranges"]}
    for key, joint in joints.items():
        check_joint(joint, old_atoms[key][:, :, :, :times], pairs, positions)
    for role in roles.values():
        check_joint(role["joint"], role["single"], pairs, positions)
        if not np.array_equal(role["children"].sum(axis=1), role["base"][:, prior["symbol_id"]]) or not np.all(role["single"].sum(axis=(2, 3)) == role["children"][:, 0][None, :]):
            raise ValueError("joint role population differs from timing children")
    return joints, roles


def report_text(result, cache, protocol):
    lines = ["# Chronologically validated two-size local refinement", "",
             f"All {len(cache['known'])} fixed known APPs and original priors are retained; unknown-class error is excluded. Target months keep every original audited flow. Genuine pair-size x low-IPT atom counts project to the previous single-size counts.", "",
             "## Collection and temporal validation", "",
             "IPT2 <= the fixed protocol threshold is the only editable region. The threshold was motivated by earlier experiments and is declared before this scan. All position pairs use the inherited fixed size grid. The archive retains low-IPT atom details for future cache-only analysis; current rules split size axes only.",
             "Fixed pilot and rolling_3m reserve the final past calendar month for validation. rolling_1m uses days before the protocol cut for fitting and days after the gap for validation. Stored whole-flow intervals plus the original hourly rounding guard must fit entirely inside their role window. Boundary/gap flows are excluded from fitting/validation and counted as unused past flows; these exclusions do not alter any original target-month population.",
             "Models and leaf labels freeze after fitting. Validation chooses among those models; no refit occurs after validation, so the measured constraint applies to the actual frozen classifier on that past validation slice. This is empirical past validation, not a future-risk guarantee or an independent-unit certificate.", "",
             "## Model groups and constraints", "",
             "time_fit is the matching fitting-subset timing baseline; single_fit selects one size cut by fit gain; joint_fit selects two crossed size cuts by fit gain, at most four low leaves (tree depth at most two). Exhaustive pair search can find interactions when neither single main effect helps.",
             f"Observed fitting leaves require at least {protocol['minimum_fit_leaf_flows']} pooled flows. Empty fitting leaves back off to the low parent, with no target-flow removal. All class scores use original pi_i / full_fit_class_n_i; all fixed classes compete. High/invalid branches and other original cells keep the same time_fit predictions. If the low parent predicts APP34, refinements are disabled; otherwise APP34 cannot acquire a new error relative to time_fit.",
             "validation_weighted selects the best positive weighted validation gain from the same fitted single/joint candidate pool. validation_constrained adds the class-cost and raw-error constraints below. Identity is available in every family and wins zero-gain ties. Ties favor fewer observed leaves, then the fixed candidate order.",
             f"validation_constrained requires positive fixed-prior validation improvement, raw wrong-count increase <= {protocol['maximum_validation_raw_wrong_increase']}, and APP21 conditional error increase <= {protocol['APP21_validation_budget_pp']:g} percentage points. Validation missing any fixed class forces identity; classes/priors are never dropped. The APP21 condition is inactive only when APP21 is not in the original fixed plan.",
             "legacy_time_full and legacy_hierarchy_full reproduce previous full-past models. They use more fitting data, so they are context references; method comparisons use the matching time_fit baseline and shared fit/validation data.", "",
             "## Frozen past-only selections", "",
             "| Target | Model | Group | Status | Kind | Packets | Size thresholds B | Fit gain pp | Validation gain pp | Validation raw change | APP21 validation change pp | Low parent APP |",
             "|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|"]
    for r in result["selections"]:
        rule = r.get("rule") or {}
        lines.append(f"| {r['target']} | {r['model']} | {r['group']} | {r['status']} | {rule.get('kind','identity')} | {','.join(map(str,rule.get('positions',[])))} | {','.join(map(str,rule.get('thresholds_bytes',[])))} | {number(rule.get('fit_gain'),100)} | {number(-rule['validation_weighted_change'] if rule.get('validation_weighted_change') is not None else None,100)} | {rule.get('validation_raw_wrong_change','NA')} | {number(rule.get('APP21_validation_conditional_change'),100)} | {r.get('low_parent_APP','NA')} |")
    lines += ["", "## Monthly target results", "",
              "Negative changes mean improvement relative to the matching time_fit model. Target labels evaluate frozen models only.", "",
              "| Target | Model | Group | Error % | Weighted change pp | Raw wrong change | APP2 error % | APP21 error % | APP34 error % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in result["monthly"]:
        lines.append(f"| {r['target']} | {r['model']} | {r['group']} | {number((r.get('weighted_error') or {}).get('value'),100)} | {number((r.get('change_vs_time_fit') or {}).get('value'),100)} | {r.get('raw_wrong_change_vs_time_fit','NA')} | {number(r.get('APP2_error'),100)} | {number(r.get('APP21_error'),100)} | {number(r.get('APP34_error'),100)} |")
    lines += ["", "## Period target results", "",
              "Period errors pool wrong counts within each fixed class before weighting. No pooled empirical Bayes functional is reported for changing rules.", "",
              "| Period | Model | Group | Error % | Weighted change pp | Raw wrong change | APP2 error % | APP21 error % | APP34 error % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in result["periods"]:
        lines.append(f"| {r['period']} | {r['model']} | {r['group']} | {number((r.get('weighted_error') or {}).get('value'),100)} | {number((r.get('change_vs_time_fit') or {}).get('value'),100)} | {r.get('raw_wrong_change_vs_time_fit','NA')} | {number(r.get('APP2_error'),100)} | {number(r.get('APP21_error'),100)} | {number(r.get('APP34_error'),100)} |")
    lines += ["", "## Scope and files", "",
              "candidate_scores.csv contains all fitting/validation candidates, without target scores. selections.csv and summary.json retain exact frozen rules, class sample counts and unused past flows. monthly_classes.csv and period_classes.csv retain every fixed class; matched-model rescued/harmed counts must account for every target error change. Fit/validation dates are in collection_protocol.json.",
              "joint_counts.npz contains aggregate integer histograms, not individual flows or identities. Reuse it through --reuse-counts-dir to change empirical selection budgets without a second H5 scan; geometry, source, old code and grid must remain identical. Every input/code/output hash is in run.json.",
              "Past validation selection can itself be optimistic; the future months have also been inspected in previous rounds. This remains exploratory. Constraints are measured on past validation and may fail in the target under drift. Missing fit classes make matched models unavailable; missing target classes retain original prior mass and classification identification ranges. Small-n is a flag only. No iid significance test, population-risk guarantee or validated session independence is claimed.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    if min(args.min_leaf_flows, args.small_n, args.chunk_rows) < 1 or args.app21_budget_pp < 0 or args.max_validation_raw_increase < 0:
        raise ValueError("positive leaf/small-n/chunk budgets and nonnegative validation loss budgets required")
    cache = read_cache(args.monthly_dir)
    old_atoms, prior, stage8 = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    stage9 = read_hierarchy(args.hierarchy_dir, cache, old_atoms, prior, args.monthly_dir, args.refinement_dir)
    prepare_run, plan, tables, expected = read_preparation(args.prepare_dir)
    if plan != cache["plan"] or args.ipt_threshold_ms not in prior["IPT2_candidates_ms"]:
        raise ValueError("identical preparation and an inherited timing threshold required")
    windows = validation_windows(cache, prior["models"], gap=args.validation_gap_seconds, validation_day=args.validation_day)
    collection = collection_protocol(cache, prior, windows, args.ipt_threshold_ms)
    protocol = {"groups": list(GROUPS), "models": prior["models"], "fixed_IPT2_threshold_ms": args.ipt_threshold_ms,
                "minimum_fit_leaf_flows": args.min_leaf_flows, "APP21_validation_budget_pp": args.app21_budget_pp,
                "maximum_validation_raw_wrong_increase": args.max_validation_raw_increase, "maximum_low_leaves": 4, "maximum_low_tree_depth": 2,
                "refit_after_validation": False, "status": "exploratory chronologically validated local refinement"}
    inputs = [directory / name for directory, names in ((args.monthly_dir, MONTHLY_FILES), (args.refinement_dir, REFINEMENT_FILES), (args.hierarchy_dir, HIERARCHY_FILES),
              (args.prepare_dir, ("run.json", "experiment_plan.json", "tables.json", "audit.json", "period_service_counts.csv", "time_unit_diagnostics.json"))) for name in names]
    if args.reuse_counts_dir is not None:
        print("Verifying and reusing genuine joint-count archive; no H5 read...", flush=True)
        joints, roles = load_counts(args.reuse_counts_dir, cache, prior, collection, old_atoms, inputs)
        source_rows_read = 0
    else:
        print("Verifying raw H5 SHA256 and schema before one joint-count scan...", flush=True)
        before = args.h5.stat()
        if sha256(args.h5) != plan["source"]["sha256"] or before.st_size != plan["source"]["bytes"]:
            raise ValueError("raw H5 differs from the prepared source")
        source = FlowSource(args.h5, args.backend)
        try:
            if source.tables() != tables:
                raise ValueError("H5 table/schema metadata differs from preparation")
            scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[prepare_run["parameters"]["time_unit"]]
            counter = JointCounts(plan, tables, time_scale=scale, previous_protocol=prior, windows=windows, threshold=args.ipt_threshold_ms)
            # Save the protocol before scanning; output directories never overwrite.
            metadata = start_run(args, inputs=inputs, code=[Path(__file__)] + [ROOT / path for path in CODE], source=plan["source"])
            save(args.out_dir / "collection_protocol.json", collection)
            save(args.out_dir / "selection_protocol.json", protocol)
            save(args.out_dir / "plan_snapshot.json", plan)
            total = sum(table["rows"] for table in tables)
            for index, table in enumerate(tables, 1):
                for start in range(0, table["rows"], args.chunk_rows):
                    counter.add(source.read(table["path"], start, min(start + args.chunk_rows, table["rows"])), table["ppi_capacity"])
                print(f"[{index}/{len(tables)}] {table['path']}: rows={counter.rows_read}/{total}", flush=True)
            after = args.h5.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or counter.rows_read != total or total != cache["run"]["rows_read"]:
                raise RuntimeError("raw source changed or joint scan is incomplete")
            counter.reconcile(expected)
            counter.reconcile_joint(cache, old_atoms)
            joints, roles, source_rows_read = counter.joints, counter.roles, counter.rows_read
            metadata.update({"backend": source.backend, "reader_version": source.module.__version__})
        finally:
            source.close()
    if args.reuse_counts_dir is not None:
        reuse_inputs = inputs + [args.reuse_counts_dir / name for name in ("run.json", "collection_protocol.json", "joint_counts.npz", "plan_snapshot.json")]
        metadata = start_run(args, inputs=reuse_inputs, code=[Path(__file__)] + [ROOT / path for path in CODE], source=plan["source"])
        save(args.out_dir / "collection_protocol.json", collection)
        save(args.out_dir / "selection_protocol.json", protocol)
        save(args.out_dir / "plan_snapshot.json", plan)
    save_counts(args.out_dir, collection, joints, roles)
    legacy = {(r["target"], r["model"], "legacy_time_full"): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in stage8["confusions"] if r["group"] == "ipt_split"}
    legacy.update({(r["target"], r["model"], "legacy_hierarchy_full"): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in stage9["confusions"] if r["group"] == "low_size_split"})
    print("All old monthly counts and true pair projections verified. Selecting frozen rules from fit/validation periods...", flush=True)
    result = run_joint(cache, roles, joints, old_atoms, windows, prior, legacy, threshold=args.ipt_threshold_ms, minimum=args.min_leaf_flows,
                       app21_budget=args.app21_budget_pp / 100, raw_budget=args.max_validation_raw_increase, small_n=args.small_n,
                       progress=lambda key, model: print(f"Scored local rules: {key} {model}", flush=True))
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": plan["unknown_prior"],
         "protocol": protocol, "counts_reconciled": True, "legacy_models_reproduced": True, "monthly": result["monthly"], "periods": result["periods"], "selections": result["selections"]})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    for filename, rows in (("monthly_summary", flat_metrics(result["monthly"])), ("period_summary", flat_metrics(result["periods"])),
                           ("monthly_classes", result["classes"]), ("period_classes", result["period_classes"])):
        write_table(args.out_dir / (filename + ".csv"), rows, ("target", "model", "group", "status"))
    candidate_rows = []
    for r in result["candidates"]:
        candidate_rows.append({**{key: value for key, value in r.items() if key not in ("positions", "indices", "thresholds_bytes", "prediction_indices", "prediction_APPs", "fit_leaf_flows")},
                               **{key: ";".join(map(str, r[key])) for key in ("positions", "indices", "thresholds_bytes", "prediction_APPs", "fit_leaf_flows")}})
    write_table(args.out_dir / "candidate_scores.csv", candidate_rows, ("target", "model", "candidate_id", "eligible"))
    write_table(args.out_dir / "selections.csv", [{**{key: value for key, value in r.items() if not isinstance(value, (dict, list))},
                "rule": json.dumps(r["rule"], separators=(",", ":")) if r.get("rule") else "identity",
                **{key: ";".join(map(str, r.get(key, []))) for key in ("fit_sample_counts", "validation_sample_counts", "unused_past_sample_counts")}} for r in result["selections"]], ("target", "model", "status"))
    (args.out_dir / "report.md").write_text(report_text(result, cache, protocol))
    metadata.update({"rows_read": source_rows_read, "cached_source_rows": cache["run"]["rows_read"], "counts_reconciled": True, "selection_protocol": protocol})
    finish_run(args.out_dir, metadata, started)
    for r in result["selections"]:
        if r["group"] == "validation_constrained":
            rule = r.get("rule") or {}
            print(f"SELECT {r['target']} {r['model']} status={r['status']} kind={rule.get('kind','identity')} packets={rule.get('positions',[])} sizes_B={rule.get('thresholds_bytes',[])} val_weighted_change_pp={number(rule.get('validation_weighted_change'),100)} val_raw_change={rule.get('validation_raw_wrong_change','NA')} val_APP21_change_pp={number(rule.get('APP21_validation_conditional_change'),100)}")
    for r in result["periods"]:
        if r["period"] == "evaluation":
            print(f"PERIOD {r['model']} {r['group']} error={number((r.get('weighted_error') or {}).get('value'))} delta_time_fit_pp={number((r.get('change_vs_time_fit') or {}).get('value'),100)} raw_delta={r.get('raw_wrong_change_vs_time_fit','NA')} APP2={number(r.get('APP2_error'))} APP21={number(r.get('APP21_error'))} APP34={number(r.get('APP34_error'))}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("prepare-dir", "monthly-dir", "refinement-dir", "hierarchy-dir", "out-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--h5", type=Path)
    source.add_argument("--reuse-counts-dir", type=Path)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--ipt-threshold-ms", type=float, default=4.)
    parser.add_argument("--validation-day", type=int, default=21)
    parser.add_argument("--validation-gap-seconds", type=int, default=DAY)
    parser.add_argument("--min-leaf-flows", type=int, default=200)
    parser.add_argument("--app21-budget-pp", type=float, default=.1)
    parser.add_argument("--max-validation-raw-increase", type=int, default=0)
    parser.add_argument("--small-n", type=int, default=200)
    parser.add_argument("--chunk-rows", type=int, default=20000)
    args = parser.parse_args()
    if not all(d.is_dir() for d in (args.prepare_dir, args.monthly_dir, args.refinement_dir, args.hierarchy_dir)) or args.out_dir.exists():
        parser.error("completed source artifacts and a fresh output directory required")
    if (args.h5 is not None and not args.h5.is_file()) or (args.reuse_counts_dir is not None and not args.reuse_counts_dir.is_dir()):
        parser.error("existing raw H5 or joint-count artifact required")
    if (min(args.min_leaf_flows, args.small_n, args.chunk_rows) < 1 or args.validation_gap_seconds < 0 or not 2 <= args.validation_day <= 27
            or not np.isfinite(args.app21_budget_pp) or args.app21_budget_pp < 0 or args.max_validation_raw_increase < 0
            or not np.isfinite(args.ipt_threshold_ms) or args.ipt_threshold_ms < 0):
        parser.error("invalid training/validation protocol budgets")
    run(args)


if __name__ == "__main__":
    main()
