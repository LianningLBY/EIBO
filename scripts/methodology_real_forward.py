#!/usr/bin/env python3
"""Replay monthly forward validation of locally fitted split families."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.blockvalidation import block_windows  # noqa: E402
from eibo.forwardvalidation import FIELDS, GROUPS, ForwardCounts, check_roles, evaluate_forward, forward_windows, select_forward  # noqa: E402
from eibo.jointrefinement import root_model, rule_evaluation  # noqa: E402
from eibo.regionalvalidation import collapse_role  # noqa: E402
from eibo.realdata import FlowSource  # noqa: E402
from methodology_real_atomic import flat_metrics, read_hierarchy  # noqa: E402
from methodology_real_blocks import CODE as BLOCK_CODE, load_reused  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_hierarchy import read_refinement, write_table  # noqa: E402
from methodology_real_joint_diagnostic import read_joint  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

CODE = BLOCK_CODE + ("scripts/methodology_real_blocks.py", "src/eibo/forwardvalidation.py")


def read_blocks(directory, cache, old_collection, inputs):
    metadata0 = json.loads((directory / "run.json").read_text())
    collection = {**old_collection, "window_spec": block_windows(old_collection["window_spec"], blocks=metadata0["parameters"]["blocks"], rounding=cache["plan"]["time_rounding_envelope_seconds"])}
    metadata = load_reused(directory, collection, cache, inputs)
    names = ("frozen_selections.json", "selected_validation.csv", "confusion_matrices.json", "summary.json")
    manifest = {r["path"]: r["sha256"] for r in metadata["outputs"]}
    for name in names:
        if manifest.get(name) != sha256(directory / name):
            raise ValueError("block audit output hash mismatch: " + name)
    choices = json.loads((directory / "frozen_selections.json").read_text())
    matrices = json.loads((directory / "confusion_matrices.json").read_text())
    if matrices["known_service_codes"] != cache["known"].tolist():
        raise ValueError("previous block class order differs")
    previous = {(r["target"], r["model"], "previous_time" if r["group"] == "time_baseline" else "previous_blocks"):
                np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in matrices["matrices"] if r["group"] in ("time_baseline", "block_constraints")}
    return collection, choices, previous, [directory / n for n in ("run.json", "joint_counts.npz", "collection_protocol.json", "plan_snapshot.json") + names]


def fixed_audit(directory, collection, choices, old_roles, priors):
    contexts = [c for c in collection["window_spec"]["contexts"] if c["model"] == "fixed_pilot" and "fit_id" in c]
    c = contexts[0]
    if any((x["fit_id"], x["validation_id"], x["block_ids"]) != (c["fit_id"], c["validation_id"], c["block_ids"]) for x in contexts):
        raise ValueError("fixed pilot roles unexpectedly vary")
    positions, pairs = tuple(collection["size_positions"]), tuple(map(tuple, collection["size_pairs"]))
    fit = collapse_role(old_roles[c["fit_id"]], positions, pairs)
    prediction, leaves = root_model(fit["base"], fit["children"], priors, collection["symbol_id"])
    with np.load(directory / "joint_counts.npz", allow_pickle=False) as archive:
        blocks = [{field: archive[token + "_" + field] for field in FIELDS} for token in c["block_ids"]]
    union = {field: sum(b[field] for b in blocks) for field in FIELDS}
    views = [("original_validation", old_roles[c["validation_id"]]), ("block_union", union)] + list(zip(c["block_ids"], blocks))
    with (directory / "selected_validation.csv").open() as handle:
        saved = {(r["target"], r["model"], r["group"], r["view"]): r for r in csv.DictReader(handle)}
    rows, class_rows = [], []
    for group in ("original_pooled", "block_constraints", "block_minimax"):
        chosen = [r for r in choices if r["model"] == "fixed_pilot" and r["group"] == group]
        rule = chosen[0]["rule"]
        if any(r["rule"] != rule for r in chosen):
            raise ValueError("fixed pilot frozen choices unexpectedly vary")
        for name, raw in views:
            data = collapse_role(raw, positions, pairs)
            value, transfer = rule_evaluation(data, rule, prediction, leaves, priors, collection["symbol_id"])
            baseline, _ = rule_evaluation(data, None, prediction, leaves, priors, collection["symbol_id"])
            change = value["wrong_counts"] - baseline["wrong_counts"]
            ns = raw["base"].sum(axis=1)
            rates = np.divide(change, ns, out=np.full(len(ns), np.nan), where=ns > 0)
            weighted = float(np.dot(priors, rates)) if np.all(ns > 0) else None
            previous = saved[c["target"], "fixed_pilot", group, name]
            if int(previous["raw_wrong_change"]) != int(change.sum()) or weighted is not None and abs(float(previous["weighted_change"]) - weighted) > 1e-12:
                raise ValueError("fixed audit does not reproduce original past increments")
            rows.append({"group": group, "view": name, "candidate_id": rule["candidate_id"] if rule else None,
                "weighted_change": weighted, "raw_change": int(change.sum()), "rescued": sum(t[0] for t in transfer), "harmed": sum(t[1] for t in transfer),
                "minimum_class_n": int(ns.min()), "current_fit_gain": rule["fit_gain"] if rule else 0.})
            class_rows.extend({"group": group, "view": name, "APP": int(app), "n": int(ns[i]), "prior": float(priors[i]),
                "rescued": transfer[i][0], "harmed": transfer[i][1], "raw_change": int(change[i])} for i, app in enumerate(collection["known_service_codes"]))
    return rows, class_rows


def cache_roles(directory, collection, cache, inputs):
    metadata = json.loads((directory / "run.json").read_text())
    if metadata["status"] != "complete" or metadata.get("counts_reconciled") is not True or metadata["source_lineage"] != cache["plan"]["source"]:
        raise ValueError("completed forward cache with identical source required")
    manifests = {r["path"]: r["sha256"] for r in metadata["outputs"]}
    for name in ("role_counts.npz", "collection_protocol.json", "plan_snapshot.json"):
        if manifests.get(name) != sha256(directory / name):
            raise ValueError("forward cache hash mismatch: " + name)
    if json.loads((directory / "collection_protocol.json").read_text()) != collection or json.loads((directory / "plan_snapshot.json").read_text()) != cache["plan"]:
        raise ValueError("forward cache calendar or plan differs")
    for path in [Path(__file__)] + [ROOT / p for p in CODE]:
        r = [x for x in metadata["code"] if Path(x["path"]).name == path.name]
        if len(r) != 1 or r[0]["sha256"] != sha256(path):
            raise ValueError("forward cache code lineage differs")
    for path in inputs:
        r = [x for x in metadata["input_artifacts"] if Path(x["path"]).name == path.name and Path(x["path"]).parent.name == path.parent.name]
        if len(r) != 1 or r[0]["sha256"] != sha256(path):
            raise ValueError("forward cache input lineage differs")
    k, bins = len(cache["known"]), len(collection["size_candidates_bytes"]) + 1
    shapes = {"base": (k, cache["period_counts"]["pilot"][2].shape[1]), "children": (k, 3),
              "single": (len(collection["size_positions"]), k, bins), "joint": (len(collection["size_pairs"]), k, bins, bins)}
    expected = {r["id"] + "_" + field: shape for r in collection["window_spec"]["ranges"] for field, shape in shapes.items()}
    arrays = {}
    with np.load(directory / "role_counts.npz", allow_pickle=False) as archive:
        if set(archive.files) != set(expected):
            raise ValueError("forward cache arrays differ")
        for name, shape in expected.items():
            a = archive[name]
            if a.shape != shape or a.dtype.kind not in "iu" or np.any(a < 0) or np.any(a > cache["run"]["rows_read"]):
                raise ValueError("invalid forward cache counts")
            arrays[name] = a.astype(np.int64)
    return {r["id"]: {field: arrays[r["id"] + "_" + field] for field in FIELDS} for r in collection["window_spec"]["ranges"]}


def report_text(result, audit, collection, protocol):
    lines = ["# Forward monthly validation of local split families", "",
        "All original known classes, fixed priors and target flows are retained. Outside the refined cell the original full-past model is unchanged. Current local labels use the new full earlier fitting window with the declared gap; previous_time and previous_blocks retain the actual previous hybrid controls so refitting and family selection are reported separately.", "",
        "Each historical fold fits on dates strictly before its validation month with a 24-hour gap (or the declared inherited gap). Validation flows must lie wholly within the audited monthly slice, including timestamp rounding. Capture and original split gaps can clip calendar months. No missing days are invented. All required calendar months must exist.",
        "Historical leaf labels are refitted at each origin. Their scores validate a split FAMILY and its fitting procedure, not the exact current leaf labels. The current family is fitted using only the current past window, then frozen before its target is scored. Previous-month labels are assumed available; operational annotation delays are not modeled. Overlapping training windows and calendar folds are not independent trials.",
        "fit_only uses current training gain. latest_month uses the last eligible past origin. pooled_months pools integer historical error changes within each class before applying fixed priors. all_months uses the identical family support and pooled objective but also requires APP21/raw budgets in EACH historical month. Both pooled_months and all_months require the family to satisfy the fit-leaf guard in every required historical fold and the current fit. Missing historical classes or unavailable dates cause identity; missing current fit classes make new models unavailable. APP34-parent protection applies to every fit origin.",
        "No target labels enter family selection. Current rules and historical fitted labels are stored separately. frozen_selections.json is hashed before new target scoring. These inspected historical targets remain exploratory; empirical monthly checks provide no guarantee of future budgets or methodological novelty.", "",
        "## Evaluation-period comparison", "",
        "Local changes and target budgets use the new shared time_baseline. Previous controls have different local fitting data; differences against them include refitting and must not be called pure validation effects.", "",
        "| Model | Group | Error % | Local pp | Vs previous blocks pp | Raw local | APP2 % | APP21 % | APP34 % | Budget met/checked | Identity/available |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|"]
    bs = {(r["model"], r["group"]): r for r in result["budget_summary"] if r["period"] == "evaluation"}
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation":
            b = bs.get((r["model"], r["group"]))
            lines.append(f"| {r['model']} | {r['group']} | {number((r['weighted_error'] or {}).get('value'),100)} | {number((r['change_vs_time_baseline'] or {}).get('value'),100)} | {number((r['change_vs_previous_blocks'] or {}).get('value'),100)} | {r['raw_change_vs_time_baseline']} | {number(r['APP2_error'],100)} | {number(r['APP21_error'],100)} | {number(r['APP34_error'],100)} | {str(b['both_met'])+'/'+str(b['checked']) if b else 'reference'} | {str(b['identity'])+'/'+str(b['available']) if b else 'reference'} |")
    lines += ["", "## Fixed pilot past-gain audit", "",
        "These are actual past-validation transfers for the old frozen choices, not target-selected minimum-gain cutoffs. A tiny past gain can motivate a later prespecified practical threshold, but no such threshold is tuned on these target outcomes here.", "",
        "| Group | View | Candidate | Weighted pp | Rescued | Harmed | Raw change | Min class n |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in audit:
        lines.append(f"| {r['group']} | {r['view']} | {r['candidate_id']} | {number(r['weighted_change'],100)} | {r['rescued']} | {r['harmed']} | {r['raw_change']} | {r['minimum_class_n']} |")
    lines += ["", "## Files and interpretation", "",
        "historical_selected_scores.csv retains the historical predictions, parent label, eligibility and increments at EACH past origin; frozen_selections.json contains separate CURRENT fitted labels. candidate_scores.csv contains no target scores. validation_coverage.csv retains all classes and priors, including low and zero sample counts. fixed_pilot_past_audit.csv and fixed_pilot_past_classes.csv retain exact old-rule past transfers.",
        "monthly_summary.csv, period_summary.csv, class_metrics.csv, budget_monthly.csv, budget_summary.csv and confusion_matrices.json retain all controls, unchanged original target class counts, exact local transfers, all observed violations and unavailable/missing cases. Missing target classes retain NA and original-prior identification ranges. Priors are never renormalized. Absolute errors and budget reference must be read together.",
        "role_counts.npz contains only aggregate role counts. Source, old outputs, role geometry and code hashes are verified before reuse. This round changes local fitting data as well as validation geometry; compare the matched current-fit groups to isolate the historical selector. A high pass rate achieved by identity must be reported with gain and identity frequency. Unseen later data are still required for confirmation.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    cache = read_cache(args.monthly_dir)
    atoms, prior, stage8 = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    stage9 = read_hierarchy(args.hierarchy_dir, cache, atoms, prior, args.monthly_dir, args.refinement_dir)
    prepared, plan, tables, expected = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("identical preparation plan required")
    original_run, old_collection, protocol, joints, old_roles, replay, inputs = read_joint(args, cache, atoms, prior, stage8, stage9)
    block_collection, block_choices, previous, block_inputs = read_blocks(args.blocks_dir, cache, old_collection, inputs)
    inputs += block_inputs
    audit, audit_classes = fixed_audit(args.blocks_dir, block_collection, block_choices, old_roles, cache["priors"])
    windows = forward_windows(cache["slices"], old_collection["window_spec"], history=args.history_months, gap=old_collection["window_spec"]["gap_seconds"])
    collection = {**old_collection, "window_spec": windows, "role_axes": "low-IPT collapsed; family labels refitted per origin"}
    selection_protocol = {**protocol, "groups": list(GROUPS), "history_months": args.history_months, "refit_after_validation": True,
        "validation_target": "split family fitting procedure; historical fitted labels differ from current labels", "outside_training": "original full past window",
        "labels_available_by_next_origin_assumed": True, "future_budget_guarantee": False}
    if args.reuse_counts_dir is not None:
        roles = cache_roles(args.reuse_counts_dir, collection, cache, inputs)
        reuse_inputs = [args.reuse_counts_dir / n for n in ("run.json", "role_counts.npz", "collection_protocol.json", "plan_snapshot.json")]
        rows_read = 0
    else:
        roles, reuse_inputs = None, []
    metadata = start_run(args, inputs=inputs + reuse_inputs, code=[Path(__file__)] + [ROOT / p for p in CODE], source=plan["source"])
    save(args.out_dir / "collection_protocol.json", collection)
    save(args.out_dir / "selection_protocol.json", selection_protocol)
    save(args.out_dir / "plan_snapshot.json", plan)
    if roles is None:
        print("Verifying raw H5 and scanning whole-flow monthly roles once...", flush=True)
        before = args.h5.stat()
        if before.st_size != plan["source"]["bytes"] or sha256(args.h5) != plan["source"]["sha256"]:
            raise ValueError("raw H5 differs from prepared source")
        scale = {"seconds": 1, "milliseconds": 1000, "microseconds": 1000000, "nanoseconds": 1000000000}[prepared["parameters"]["time_unit"]]
        source = FlowSource(args.h5, args.backend)
        try:
            if source.tables() != tables:
                raise ValueError("raw table/schema differs from preparation")
            counter = ForwardCounts(plan, tables, time_scale=scale, previous_protocol=prior, windows=windows, threshold=collection["fixed_IPT2_threshold_ms"])
            total = sum(t["rows"] for t in tables)
            for index, table in enumerate(tables, 1):
                for start in range(0, table["rows"], args.chunk_rows):
                    counter.add(source.read(table["path"], start, min(start + args.chunk_rows, table["rows"])), table["ppi_capacity"])
                print(f"[{index}/{len(tables)}] rows={counter.rows_read}/{total}", flush=True)
            after = args.h5.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or counter.rows_read != total or total != cache["run"]["rows_read"]:
                raise RuntimeError("raw source changed or scan is incomplete")
            counter.reconcile(expected)
            counter.reconcile_cache(cache)
            if any(not np.array_equal(counter.atoms[key], atoms[key]) for key in atoms):
                raise ValueError("rescanned original monthly atoms differ")
            roles, rows_read = counter.roles, counter.rows_read
            metadata.update(backend=source.backend, reader_version=source.module.__version__)
        finally:
            source.close()
    check_roles(roles, collection)
    fixed_context = next(c for c in old_collection["window_spec"]["contexts"] if c["model"] == "fixed_pilot" and "fit_id" in c)
    fixed_fit = collapse_role(old_roles[fixed_context["fit_id"]], tuple(collection["size_positions"]), tuple(map(tuple, collection["size_pairs"])))
    for node in windows["nodes"]:
        if np.any(roles[node["validation_id"]]["base"] > cache["counts"][node["month_key"]][2]):
            raise ValueError("whole-month validation exceeds original month counts")
        if "fit_id" in node and np.any(roles[node["fit_id"]]["base"] > sum(cache["counts"][k][2] for k in node["training_slices"])):
            raise ValueError("forward fit exceeds its earlier audited months")
        if node["model"] == "fixed_pilot" and "fit_id" in node and any(not np.array_equal(roles[node["fit_id"]][field], fixed_fit[field]) for field in FIELDS):
            raise ValueError("fixed pilot fitting population changed")
    with (args.out_dir / "role_counts.npz").open("xb") as handle:
        np.savez_compressed(handle, **{token + "_" + field: value for token, role in roles.items() for field, value in role.items()})
    print("Original counts reconciled. Selecting families using earlier month folds...", flush=True)
    selected = select_forward(roles, collection, protocol)
    save(args.out_dir / "frozen_selections.json", selected["selections"])
    frozen_hash = sha256(args.out_dir / "frozen_selections.json")
    save(args.out_dir / "selection_lock.json", {"sha256": frozen_hash, "new_target_scoring_started": False, "validation_is_for_family_not_current_leaf_labels": True})
    print("Current fitted rules frozen. Scoring original target months...", flush=True)
    result = evaluate_forward(cache, roles, joints, atoms, collection, protocol, selected, previous, small_n=args.small_n)
    for name, rows in (("monthly_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "monthly"])),
        ("period_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "period"])), ("class_metrics", result["classes"]),
        ("budget_monthly", result["budget_monthly"]), ("budget_summary", result["budget_summary"]),
        ("historical_selected_scores", selected["folds"]), ("candidate_scores", selected["candidates"]), ("validation_coverage", selected["coverage"]),
        ("fixed_pilot_past_audit", audit), ("fixed_pilot_past_classes", audit_classes)):
        write_table(args.out_dir / (name + ".csv"), [{k: json.dumps(v, separators=(",", ":")) if isinstance(v, list) else v for k, v in r.items()} for r in rows], ("target", "model", "status"))
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": plan["unknown_prior"],
        "protocol": selection_protocol, "monthly": [r for r in result["metrics"] if r["scope"] == "monthly"], "periods": [r for r in result["metrics"] if r["scope"] == "period"],
        "budget_summary": result["budget_summary"], "fixed_pilot_past_audit": audit})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    (args.out_dir / "report.md").write_text(report_text(result, audit, collection, protocol))
    if sha256(args.out_dir / "frozen_selections.json") != frozen_hash:
        raise RuntimeError("frozen choices changed during target scoring")
    metadata.update(rows_read=rows_read, cached_source_rows=original_run["cached_source_rows"], counts_reconciled=True, frozen_selection_sha256=frozen_hash)
    finish_run(args.out_dir, metadata, started)
    bs = {(r["model"], r["group"]): r for r in result["budget_summary"] if r["period"] == "evaluation"}
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation":
            b = bs.get((r["model"], r["group"]))
            print(f"PERIOD {r['model']} {r['group']} error={number((r['weighted_error'] or {}).get('value'))} local_pp={number((r['change_vs_time_baseline'] or {}).get('value'),100)} prev_blocks_pp={number((r['change_vs_previous_blocks'] or {}).get('value'),100)} raw_local={r['raw_change_vs_time_baseline']} APP2={number(r['APP2_error'])} APP21={number(r['APP21_error'])} APP34={number(r['APP34_error'])} budget={str(b['both_met'])+'/'+str(b['checked']) if b else 'ref'} identity={str(b['identity'])+'/'+str(b['available']) if b else 'ref'}")
    for r in selected["selections"]:
        if r["period"] == "evaluation" and r["group"] == "all_months":
            cells = [x for x in selected["coverage"] if x["target"] == r["target"] and x["model"] == r["model"]]
            print(f"SELECT {r['target']} {r['model']} status={r['status']} family={(r['rule'] or {}).get('candidate_id','identity')} min_month_class_n={min((x['n'] for x in cells),default='NA')}")
    for r in audit:
        if r["view"] == ("original_validation" if r["group"] == "original_pooled" else "block_union"):
            print(f"FIXED_PAST {r['group']} candidate={r['candidate_id']} gain_pp={number(-r['weighted_change'] if r['weighted_change'] is not None else None,100)} rescued={r['rescued']} harmed={r['harmed']} raw={r['raw_change']}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepare-dir", "monthly-dir", "refinement-dir", "hierarchy-dir", "joint-dir", "blocks-dir", "out-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--h5", type=Path)
    source.add_argument("--reuse-counts-dir", type=Path)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--history-months", type=int, default=3)
    parser.add_argument("--chunk-rows", type=int, default=20000)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if args.history_months < 2 or min(args.chunk_rows, args.small_n) < 1:
        parser.error("at least two validation months and positive chunk/small-n required")
    if not all(d.is_dir() for d in (args.prepare_dir, args.monthly_dir, args.refinement_dir, args.hierarchy_dir, args.joint_dir, args.blocks_dir)) or args.out_dir.exists():
        parser.error("completed source artifacts and a fresh output directory required")
    if args.h5 is not None and not args.h5.is_file() or args.reuse_counts_dir is not None and not args.reuse_counts_dir.is_dir():
        parser.error("an existing H5 or forward-role cache is required")
    run(args)


if __name__ == "__main__":
    main()
