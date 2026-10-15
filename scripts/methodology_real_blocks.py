#!/usr/bin/env python3
"""Compare pooled and multiple-past-block empirical local constraints."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.blockvalidation import GROUPS, block_windows, evaluate_rules, reconcile_blocks, select_rules  # noqa: E402
from eibo.jointrefinement import JointCounts  # noqa: E402
from eibo.realdata import FlowSource  # noqa: E402
from methodology_real_atomic import flat_metrics, read_hierarchy  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_hierarchy import read_refinement, write_table  # noqa: E402
from methodology_real_joint import save_counts  # noqa: E402
from methodology_real_joint_diagnostic import CODE as DIAGNOSTIC_CODE, read_joint  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

CODE = DIAGNOSTIC_CODE + ("scripts/methodology_real_joint_diagnostic.py", "src/eibo/regionalvalidation.py", "src/eibo/blockvalidation.py")


def report_text(result, selected, boundary, cache, protocol):
    lines = ["# Multiple past blocks for local refinement validation", "",
        f"All {len(cache['known'])} original known classes, fixed priors and original target flows are retained. Unknown-class error is excluded. The outside model uses the full original past window. All predictions inside the original cell use the original fitting subset; the timing threshold, candidate grid, leaf support and budgets are inherited.", "",
        "## Protocol and interpretation", "",
        "Each original validation interval is split into equal-duration contiguous blocks using timestamps only. Each flow must lie wholly within its block with the original timestamp-rounding guard; internal-boundary flows are excluded from block validation only. Fitting samples and target samples do not change. Blocks may be dependent and do not represent independent trials.",
        "time_baseline is the shared hybrid baseline. original_pooled exactly reproduces the old pooled constrained selection. block_pooled uses the union of retained blocks, so it controls for boundary exclusions. block_constraints applies the APP21 and raw-error constraints in EVERY block and maximizes pooled gain. block_minimax uses the same constraints and maximizes the minimum block gain, requiring strictly positive gain in every block. Identity is always available; missing fitting classes make a model unavailable, while any missing validation class in any block makes both block selectors fall back to identity without dropping classes or renormalizing priors.",
        "All local labels and eligibility are fitted once on the old fitting subset. frozen_selections.json is written and hashed before scoring the new models on targets. The outside model can use the validation period, so validation reports only paired local increments; identical outside predictions cancel. No absolute outside validation accuracy is presented.",
        "These empirical checks do not guarantee future budgets. The historical targets have already been inspected; this round remains exploratory. Model-month violations are descriptive, not independent binomial trials. Confirmatory claims require a genuinely uninspected later time period under a frozen protocol.", "",
        "## Evaluation-period comparison", "",
        "Negative changes mean fewer errors. The reference for local changes is the same time_baseline. Periods pool integer wrong counts within each original class before weighting.", "",
        "| Model | Group | Error % | Local pp | Gain retained % | Raw local | APP2 % | APP21 % | APP34 % | Budget met / checked | Identity / available |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    budgets = {(r["period"], r["model"], r["group"]): r for r in result["budget_summary"]}
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation":
            b = budgets[r["period"], r["model"], r["group"]]
            lines.append(f"| {r['model']} | {r['group']} | {number((r['weighted_error'] or {}).get('value'),100)} | {number((r['change_vs_time_baseline'] or {}).get('value'),100)} | {number(r['gain_retained_vs_original'],100)} | {r['raw_change_vs_time_baseline']} | {number(r['APP2_error'],100)} | {number(r['APP21_error'],100)} | {number(r['APP34_error'],100)} | {b['both_met']}/{b['checked_model_months']} | {b['identity_months']}/{b['available_model_months']} |")
    lines += ["", "## Evaluation-month budgets", "",
        f"APP21 conditional increment budget: {protocol['APP21_validation_budget_pp']:g} pp; raw wrong-count increment budget: {protocol['maximum_validation_raw_wrong_increase']}. All are relative to the same background baseline, not absolute error limits.", "",
        "| Target | Model | Group | Identity | APP21 pp | Raw change | APP21 met | Raw met |",
        "|---|---|---|---|---:|---:|---|---|"]
    for r in result["budget_monthly"]:
        if r["period"] == "evaluation" and r["group"] != "time_baseline":
            lines.append(f"| {r['target']} | {r['model']} | {r['group']} | {r['identity']} | {number(r['target_APP21_change'],100)} | {r['target_raw_wrong_change']} | {r['target_APP21_budget_met']} | {r['target_raw_budget_met']} |")
    lines += ["", "## Frozen choices and validation coverage", "",
        "| Target | Model | Group | Status | Candidate | Kind |",
        "|---|---|---|---|---:|---|"]
    for r in selected["selections"]:
        if r["period"] == "evaluation" and r["group"] != "time_baseline":
            rule = r["rule"] or {}
            lines.append(f"| {r['target']} | {r['model']} | {r['group']} | {r['status']} | {rule.get('candidate_id','NA')} | {rule.get('kind','identity')} |")
    lines += ["", "## Block coverage and boundary exclusions", "",
        "| Target | Model | Parent flows | Block-union flows | Boundary excluded | Minimum block class n | Missing class/block cells |",
        "|---|---|---:|---:|---:|---:|---:|"]
    for r in boundary:
        cells = [c for c in selected["coverage"] if c["target"] == r["target"] and c["model"] == r["model"] and c["view"] not in ("original_validation", "block_union")]
        lines.append(f"| {r['target']} | {r['model']} | {sum(r['parent_n'])} | {sum(r['union_n'])} | {sum(r['boundary_excluded_n'])} | {min((c['n'] for c in cells),default='NA')} | {sum(c['missing'] for c in cells)} |")
    lines += ["", "## Files and next decision", "",
        "candidate_scores.csv retains every past-only candidate and its block pass/fail diagnostics. selected_validation.csv retains every selected rule's paired increments on the original validation interval, union and each block. validation_coverage.csv and boundary_counts.json retain all original classes and excluded counts. New block labels never alter the fitting labels.",
        "monthly_summary.csv, period_summary.csv, class_metrics.csv, confusion_matrices.json and budget CSVs retain all controls, exact local rescue/harm, missing-class identification ranges and all observed target violations. A high budget pass rate achieved only by identity is not evidence of useful adaptation; report retained gain and identity frequency together. block_pooled separates changed validation population from all-block constraints; block_constraints versus block_minimax separates the constraint from its objective.",
        "joint_counts.npz stores aggregate counts only. --reuse-counts-dir permits a hash-verified replay without H5 for the identical geometry, source, code and original inputs. No target-label-based choice among models or groups is made. The next confirmation must use new data that did not motivate these controls; this run does not provide a future-risk certificate or establish methodological novelty.", ""]
    return "\n".join(lines)


def load_reused(directory, collection, cache, inputs):
    metadata = json.loads((directory / "run.json").read_text())
    if metadata["status"] != "complete" or metadata.get("counts_reconciled") is not True or metadata["source_lineage"] != cache["plan"]["source"]:
        raise ValueError("completed reconciled block cache with identical source required")
    manifest = {r["path"]: r["sha256"] for r in metadata["outputs"]}
    for filename in ("joint_counts.npz", "collection_protocol.json", "plan_snapshot.json"):
        if manifest.get(filename) != sha256(directory / filename):
            raise ValueError("block cache artifact hash mismatch: " + filename)
    if json.loads((directory / "collection_protocol.json").read_text()) != collection or json.loads((directory / "plan_snapshot.json").read_text()) != cache["plan"]:
        raise ValueError("block cache geometry or plan differs")
    for path in [Path(__file__)] + [ROOT / name for name in CODE]:
        matches = [r for r in metadata["code"] if Path(r["path"]).name == path.name]
        if len(matches) != 1 or matches[0]["sha256"] != sha256(path):
            raise ValueError("block cache code lineage differs")
    for path in inputs:
        matches = [r for r in metadata["input_artifacts"] if Path(r["path"]).name == path.name and Path(r["path"]).parent.name == path.parent.name]
        if len(matches) != 1 or matches[0]["sha256"] != sha256(path):
            raise ValueError("block cache input lineage differs")
    return metadata


def run(args):
    started = time.monotonic()
    cache = read_cache(args.monthly_dir)
    atoms, prior, stage8 = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    stage9 = read_hierarchy(args.hierarchy_dir, cache, atoms, prior, args.monthly_dir, args.refinement_dir)
    prepared, plan, tables, expected = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("identical prepared plan required")
    original_run, old_collection, protocol, joints, old_roles, replay, inputs = read_joint(args, cache, atoms, prior, stage8, stage9)
    windows = block_windows(old_collection["window_spec"], blocks=args.blocks, rounding=plan["time_rounding_envelope_seconds"])
    collection = {**old_collection, "window_spec": windows}
    selection_protocol = {**protocol, "groups": list(GROUPS), "validation_blocks": args.blocks,
        "outside_training": "full original past window", "local_fit_unchanged": True, "refit_after_validation": False,
        "minimum_block_class_n": 1, "missing_block_class_action": "identity", "future_budget_guarantee": False,
        "status": "exploratory multiple-past-block empirical validation"}
    reuse_run = load_reused(args.reuse_counts_dir, collection, cache, inputs) if args.reuse_counts_dir is not None else None
    reuse_inputs = [args.reuse_counts_dir / name for name in ("run.json", "joint_counts.npz", "collection_protocol.json", "plan_snapshot.json")] if reuse_run else []
    metadata = start_run(args, inputs=inputs + reuse_inputs, code=[Path(__file__)] + [ROOT / name for name in CODE], source=plan["source"])
    save(args.out_dir / "collection_protocol.json", collection)
    save(args.out_dir / "selection_protocol.json", selection_protocol)
    save(args.out_dir / "plan_snapshot.json", plan)
    scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[prepared["parameters"]["time_unit"]]
    counter = JointCounts(plan, tables, time_scale=scale, previous_protocol=prior, windows=windows, threshold=collection["fixed_IPT2_threshold_ms"])
    if reuse_run:
        print("Verifying and reusing multiple-block aggregate counts; no H5 read...", flush=True)
        with np.load(args.reuse_counts_dir / "joint_counts.npz", allow_pickle=False) as archive:
            expected_arrays = {f"m{i}_joint": a for i, a in enumerate(counter.joints.values())}
            expected_arrays.update({token + "_" + field: a for token, role in counter.roles.items() for field, a in role.items()})
            if set(archive.files) != set(expected_arrays):
                raise ValueError("block cache array names differ")
            arrays = {}
            for name, template in expected_arrays.items():
                a = archive[name]
                if a.shape != template.shape or a.dtype.kind not in "iu" or np.any(a < 0) or np.any(a > cache["run"]["rows_read"]):
                    raise ValueError("invalid block cache counts")
                arrays[name] = a.astype(np.int64)
            new_joints = {key: arrays[f"m{i}_joint"] for i, key in enumerate(counter.joints)}
            roles = {token: {field: arrays[token + "_" + field] for field in role} for token, role in counter.roles.items()}
        rows_read = 0
    else:
        print("Verifying raw H5, then scanning once for timestamp-defined validation blocks...", flush=True)
        before = args.h5.stat()
        if before.st_size != plan["source"]["bytes"] or sha256(args.h5) != plan["source"]["sha256"]:
            raise ValueError("raw H5 differs from prepared source")
        source = FlowSource(args.h5, args.backend)
        try:
            if source.tables() != tables:
                raise ValueError("raw schema differs from preparation")
            total = sum(table["rows"] for table in tables)
            for index, table in enumerate(tables, 1):
                for start in range(0, table["rows"], args.chunk_rows):
                    counter.add(source.read(table["path"], start, min(start + args.chunk_rows, table["rows"])), table["ppi_capacity"])
                print(f"[{index}/{len(tables)}] rows={counter.rows_read}/{total}", flush=True)
            after = args.h5.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or counter.rows_read != total or total != cache["run"]["rows_read"]:
                raise RuntimeError("raw source changed or scan is incomplete")
            counter.reconcile(expected)
            counter.reconcile_joint(cache, atoms)
            new_joints, roles, rows_read = counter.joints, counter.roles, counter.rows_read
            metadata.update(backend=source.backend, reader_version=source.module.__version__)
        finally:
            source.close()
    for key in joints:
        if not np.array_equal(new_joints[key], joints[key]):
            raise ValueError("rescanned monthly pair counts differ from stage 11")
    # On cache replay, validate all new role projections as well as their old-role subset.
    from eibo.jointrefinement import check_joint
    for role in roles.values():
        check_joint(role["joint"], role["single"], tuple(map(tuple, collection["size_pairs"])), tuple(collection["size_positions"]))
        if not np.array_equal(role["children"].sum(axis=1), role["base"][:, collection["symbol_id"]]) or not np.all(role["single"].sum(axis=(2, 3)) == role["children"][:, 0][None, :]):
            raise ValueError("block role counts do not conserve local flows")
    boundary = reconcile_blocks(roles, old_roles, windows)
    save_counts(args.out_dir, collection, new_joints, roles)
    save(args.out_dir / "boundary_counts.json", boundary)
    print("All old roles and targets reconciled. Selecting from past blocks only...", flush=True)
    selected = select_rules(roles, collection, protocol, replay["selections"])
    save(args.out_dir / "frozen_selections.json", selected["selections"])
    frozen_hash = sha256(args.out_dir / "frozen_selections.json")
    save(args.out_dir / "selection_lock.json", {"sha256": frozen_hash, "new_target_scoring_started": False, "selection_uses_target_histograms": False})
    print("Selections saved and hashed. Scoring original target months...", flush=True)
    result = evaluate_rules(cache, roles, new_joints, atoms, collection, protocol, selected, replay, small_n=args.small_n)
    for filename, rows in (("monthly_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "monthly"])),
        ("period_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "period"])), ("class_metrics", result["classes"]),
        ("budget_monthly", result["budget_monthly"]), ("budget_summary", result["budget_summary"]),
        ("selected_validation", selected["validation"]), ("validation_coverage", selected["coverage"]), ("candidate_scores", selected["candidates"])):
        write_table(args.out_dir / (filename + ".csv"), [{k: json.dumps(v, separators=(",", ":")) if isinstance(v, list) else v for k, v in r.items()} for r in rows], ("target", "model", "status"))
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(),
        "unknown_prior": plan["unknown_prior"], "protocol": selection_protocol, "monthly": [r for r in result["metrics"] if r["scope"] == "monthly"],
        "periods": [r for r in result["metrics"] if r["scope"] == "period"], "budget_summary": result["budget_summary"]})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    save(args.out_dir / "invariants.json", result["invariants"])
    (args.out_dir / "report.md").write_text(report_text(result, selected, boundary, cache, protocol))
    if sha256(args.out_dir / "frozen_selections.json") != frozen_hash:
        raise RuntimeError("frozen choices changed during target scoring")
    metadata.update(rows_read=rows_read, cached_source_rows=original_run["cached_source_rows"], counts_reconciled=True,
                    original_pooled_reproduced=True, frozen_selection_sha256=frozen_hash)
    finish_run(args.out_dir, metadata, started)
    budgets = {(r["model"], r["group"]): r for r in result["budget_summary"] if r["period"] == "evaluation"}
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation":
            b = budgets[r["model"], r["group"]]
            print(f"PERIOD {r['model']} {r['group']} error={number((r['weighted_error'] or {}).get('value'))} local_pp={number((r['change_vs_time_baseline'] or {}).get('value'),100)} retained_pct={number(r['gain_retained_vs_original'],100)} raw_local={r['raw_change_vs_time_baseline']} APP2={number(r['APP2_error'])} APP21={number(r['APP21_error'])} APP34={number(r['APP34_error'])} budget={b['both_met']}/{b['checked_model_months']} identity={b['identity_months']}/{b['available_model_months']}")
    for r in selected["selections"]:
        if r["period"] == "evaluation" and r["group"] == "block_minimax":
            cells = [c for c in selected["coverage"] if c["target"] == r["target"] and c["model"] == r["model"] and c["view"] not in ("original_validation", "block_union")]
            print(f"SELECT {r['target']} {r['model']} status={r['status']} candidate={(r['rule'] or {}).get('candidate_id','identity')} min_block_class_n={min((c['n'] for c in cells),default='NA')} missing_class_blocks={sum(c['missing'] for c in cells)}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepare-dir", "monthly-dir", "refinement-dir", "hierarchy-dir", "joint-dir", "out-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--h5", type=Path)
    source.add_argument("--reuse-counts-dir", type=Path)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--blocks", type=int, default=3)
    parser.add_argument("--chunk-rows", type=int, default=20000)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if args.blocks < 2 or min(args.chunk_rows, args.small_n) < 1:
        parser.error("at least two blocks and positive chunk/small-n required")
    if not all(d.is_dir() for d in (args.prepare_dir, args.monthly_dir, args.refinement_dir, args.hierarchy_dir, args.joint_dir)) or args.out_dir.exists():
        parser.error("completed input artifacts and a fresh output directory required")
    if args.h5 is not None and not args.h5.is_file() or args.reuse_counts_dir is not None and not args.reuse_counts_dir.is_dir():
        parser.error("an existing H5 or block-count cache is required")
    run(args)


if __name__ == "__main__":
    main()
