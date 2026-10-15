#!/usr/bin/env python3
"""Audit past exclusions and compare matched temporal objectives from cached counts."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.forwardvalidation import GROUPS as FORWARD_GROUPS, check_roles, evaluate_forward, forward_windows, select_forward  # noqa: E402
from eibo.recencyaudit import MATCHED, evaluate_matched, recency_weights, select_and_audit  # noqa: E402
from methodology_real_atomic import flat_metrics, read_hierarchy  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_forward import CODE as FORWARD_CODE, cache_roles, fixed_audit, read_blocks  # noqa: E402
from methodology_real_hierarchy import compare_replay, read_refinement, write_table  # noqa: E402
from methodology_real_joint_diagnostic import read_joint  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

CODE = FORWARD_CODE + ("scripts/methodology_real_forward.py", "src/eibo/recencyaudit.py")
FORWARD_FILES = ("role_counts.npz", "collection_protocol.json", "plan_snapshot.json", "selection_protocol.json", "selection_lock.json", "frozen_selections.json",
    "summary.json", "confusion_matrices.json", "candidate_scores.csv", "historical_selected_scores.csv", "class_metrics.csv", "monthly_summary.csv", "period_summary.csv",
    "budget_monthly.csv", "budget_summary.csv", "fixed_pilot_past_audit.csv", "fixed_pilot_past_classes.csv", "validation_coverage.csv", "report.md")


def read_forward(args, cache, atoms, prior, stage8, stage9):
    directory = args.forward_dir
    metadata = json.loads((directory / "run.json").read_text())
    manifest = {r["path"]: r["sha256"] for r in metadata["outputs"]}
    if len(manifest) != len(metadata["outputs"]) or not set(FORWARD_FILES).issubset(manifest):
        raise ValueError("forward manifest is incomplete or duplicated")
    for name in FORWARD_FILES:
        if sha256(directory / name) != manifest[name]:
            raise ValueError("forward artifact hash mismatch: " + name)
    _, old_collection, protocol, joints, old_roles, _, inputs = read_joint(args, cache, atoms, prior, stage8, stage9)
    block_collection, block_choices, previous, block_inputs = read_blocks(args.blocks_dir, cache, old_collection, inputs)
    inputs += block_inputs
    audit, _ = fixed_audit(args.blocks_dir, block_collection, block_choices, old_roles, cache["priors"])
    parameters = metadata["parameters"]
    windows = forward_windows(cache["slices"], old_collection["window_spec"], history=parameters["history_months"], gap=old_collection["window_spec"]["gap_seconds"])
    collection = {**old_collection, "window_spec": windows, "role_axes": "low-IPT collapsed; family labels refitted per origin"}
    original_protocol = {**protocol, "groups": list(FORWARD_GROUPS), "history_months": parameters["history_months"], "refit_after_validation": True,
        "validation_target": "split family fitting procedure; historical fitted labels differ from current labels", "outside_training": "original full past window",
        "labels_available_by_next_origin_assumed": True, "future_budget_guarantee": False}
    compare_replay(original_protocol, json.loads((directory / "selection_protocol.json").read_text()), "forward.protocol")
    roles = cache_roles(directory, collection, cache, inputs)
    check_roles(roles, collection)
    print("Forward cache and source hashes verified. Replaying all original frozen choices...", flush=True)
    selected = select_forward(roles, collection, protocol)
    compare_replay(selected["selections"], json.loads((directory / "frozen_selections.json").read_text()), "forward.selections")
    lock = json.loads((directory / "selection_lock.json").read_text())
    frozen_hash = sha256(directory / "frozen_selections.json")
    if lock["sha256"] != frozen_hash or metadata["frozen_selection_sha256"] != frozen_hash:
        raise ValueError("forward frozen selection lock differs")
    result = evaluate_forward(cache, roles, joints, atoms, collection, protocol, selected, previous, small_n=parameters["small_n"])
    expected = {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": cache["plan"]["unknown_prior"],
        "protocol": original_protocol, "monthly": [r for r in result["metrics"] if r["scope"] == "monthly"], "periods": [r for r in result["metrics"] if r["scope"] == "period"],
        "budget_summary": result["budget_summary"], "fixed_pilot_past_audit": audit}
    compare_replay(expected, json.loads((directory / "summary.json").read_text()), "forward.summary")
    compare_replay({"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]},
                   json.loads((directory / "confusion_matrices.json").read_text()), "forward.confusions")
    return metadata, collection, protocol, joints, roles, previous, selected, result, inputs + [directory / name for name in ("run.json",) + FORWARD_FILES]


def class_extremes(result, model, group, *, top=3):
    rows = [r for r in result["classes"] if (r["scope"], r["period"], r["model"], r["group"]) == ("period", "evaluation", model, group) and r["weighted_change_vs_source_latest"] is not None]
    improve = sorted((r for r in rows if r["wrong_change_vs_source_latest"] < 0), key=lambda r: r["weighted_change_vs_source_latest"])[:top]
    harm = sorted((r for r in rows if r["wrong_change_vs_source_latest"] > 0), key=lambda r: -r["weighted_change_vs_source_latest"])[:top]
    return improve, harm


def report_text(result, selected, collection, protocol, ratio):
    weights = recency_weights(collection["window_spec"]["history_months"], ratio).tolist()
    lines = ["# Common-support temporal objectives and exclusion audit", "",
        "The original forward run is hash-verified and replayed before this analysis. All original classes, priors, target flows, current fitting labels, historical origin fitting labels, candidate grid, leaf guards, outside predictions and timing baseline remain unchanged. No H5 read and no new dependencies.", "",
        "## Controlled comparisons", "",
        "Every new group requires the SAME candidate support: complete current and historical fitting populations, the original leaf guard and APP34-parent protection at every origin, and complete original validation classes in every required month. shared groups check only the latest historical month's APP21/raw budgets. strict groups check every month AND the original pooled budgets. These two budget rows deliberately have different feasible sets; within either row, only the objective changes.",
        "latest maximizes the latest month's gain. pooled retains the original class-count pooling before fixed-prior weighting. uniform averages the fixed-prior monthly gains equally. recent averages the SAME monthly gains using the declared geometric weights. Thus uniform versus recent isolates recency; pooled versus uniform also changes how month-specific class sample sizes enter the objective.",
        f"Geometric ratio is {ratio:g}; oldest-to-newest normalized weights are {weights}. This single illustrative ratio is declared before new target scoring. There is no target-driven weight search or automatic winner selection.",
        "source_latest uses the old latest-only support. source_pooled and source_all are actual replayed old controls. source_latest versus shared_latest diagnoses added older support/coverage requirements with the same latest budget and objective. strict_pooled must reproduce source_all's exact current rule. shared versus strict for the same objective isolates extra historical budgets. These interventions can interact; exclusion flags overlap and do not form an additive causal decomposition.", "",
        "## Evaluation-period controls", "",
        "Negative changes mean fewer errors. All local budgets use the unchanged time_baseline. Periods pool integer wrong counts within each original class before applying fixed priors.", "",
        "| Model | Group | Error % | Local pp | Vs source latest pp | Raw local | Budget met/checked | Identity/available |",
        "|---|---|---:|---:|---:|---:|---|---|"]
    bs = {(r["model"], r["group"]): r for r in result["budget_summary"] if r["period"] == "evaluation"}
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation":
            b = bs[r["model"], r["group"]]
            lines.append(f"| {r['model']} | {r['group']} | {number((r['weighted_error'] or {}).get('value'),100)} | {number((r['change_vs_time_baseline'] or {}).get('value'),100)} | {number((r['change_vs_source_latest'] or {}).get('value'),100)} | {r['raw_change_vs_time_baseline']} | {b['both_met']}/{b['checked']} | {b['identity']}/{b['available']} |")
    lines += ["", "## Why the source latest choice is excluded or outranked", "",
        "Support, budget and ranking are recorded separately. A candidate can fail several checks. A positive objective gap is meaningful only alongside its support/budget flags. Unavailable history is never silently dropped.", "",
        "| Target | Model | Latest ID | Common support | Latest cap | Strict caps | Shared latest ID | Strict pooled ID |",
        "|---|---|---:|---|---|---|---:|---:|"]
    choice = {(r["target"], r["model"], r["group"]): r for r in selected["selections"]}
    for r in selected["focal"]:
        if r["period"] == "evaluation":
            def identity(group):
                return (choice[r["target"], r["model"], group]["rule"] or {}).get("candidate_id", "identity")
            lines.append(f"| {r['target']} | {r['model']} | {r['source_latest_candidate']} | {r.get('common_support','NA')} | {r.get('latest_budget_ok','NA')} | {r.get('strict_budget_ok','NA')} | {identity('shared_latest')} | {identity('strict_pooled')} |")
    lines += ["", "## Class reallocation from source latest to source all", "",
        "These are net differences between classifiers, not paired rescue/harm. Rescue/harm columns in the full class CSV still refer only to each classifier versus its shared root. Fixed-prior class weighting can disagree with raw flow-count changes.", "",
        "| Model | APP | n | Wrong change | Weighted pp |",
        "|---|---:|---:|---:|---:|"]
    for model in protocol["models"]:
        improve, harm = class_extremes(result, model, "source_all")
        for r in improve + harm:
            lines.append(f"| {model} | {r['APP']} | {r['n']} | {r['wrong_change_vs_source_latest']} | {number(r['weighted_change_vs_source_latest'],100)} |")
    lines += ["", "## Files and limits", "",
        "candidate_audit.csv retains every candidate's common support, individual-month support and budget flags, pooled budgets and four objective scores. latest_choice_audit.csv focuses on the actual old latest choice; latest_choice_exclusions.csv adds per-control feasibility and objective gaps. selected_monthly_scores.csv retains the actual old/new selected candidate families at each historical origin, with historical fitted labels separate from current fitted labels and no target scores.",
        "frozen_selections.json and selection_lock.json are written and hashed before evaluating the new controls. monthly_summary.csv, period_summary.csv, class_metrics.csv, budget_monthly.csv, budget_summary.csv and confusion_matrices.json retain every source/control outcome. Missing current models, missing target classes and small-n flags remain explicit. Original prior identification ranges are retained; classes and priors are never dropped or renormalized.",
        "This is exploratory analysis motivated by inspected targets. Historical fold scores validate a fitting procedure, not exact current leaves; annotation availability and all temporal assumptions are inherited. Repeated model-months are not independent trials. Neither the fixed recency weights nor observed budget pass rates provide a future-risk guarantee or a novelty claim. New uninspected time periods are needed for confirmation.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    if args.small_n < 1 or not np.isfinite(args.recency_ratio) or args.recency_ratio < 1:
        raise ValueError("positive small-n and finite recency ratio >= 1 required")
    print("Verifying source artifacts and replaying forward models; no H5 read...", flush=True)
    cache = read_cache(args.monthly_dir)
    atoms, prior, stage8 = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    stage9 = read_hierarchy(args.hierarchy_dir, cache, atoms, prior, args.monthly_dir, args.refinement_dir)
    _, plan, _, _ = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("identical preparation plan required")
    metadata0, collection, protocol, joints, roles, previous, source_selected, source_result, inputs = read_forward(args, cache, atoms, prior, stage8, stage9)
    metadata = start_run(args, inputs=inputs, code=[Path(__file__)] + [ROOT / name for name in CODE], source=plan["source"])
    save(args.out_dir / "plan_snapshot.json", plan)
    save(args.out_dir / "collection_protocol.json", collection)
    save(args.out_dir / "selection_protocol.json", {"matched_groups": list(MATCHED), "original_protocol": protocol,
        "recency_ratio": args.recency_ratio, "oldest_to_newest_weights": recency_weights(collection["window_spec"]["history_months"], args.recency_ratio).tolist(),
        "candidate_support_shared_across_objectives": True, "shared_budget": "latest month", "strict_budget": "all months and original pooled budgets",
        "raw_H5_rescan": False, "target_weight_search": False, "status": "exploratory matched temporal objectives"})
    print("Source choices and confusion matrices reproduced. Auditing past-only exclusions...", flush=True)
    selected = select_and_audit(roles, collection, protocol, source_selected, ratio=args.recency_ratio)
    save(args.out_dir / "frozen_selections.json", selected["selections"])
    frozen_hash = sha256(args.out_dir / "frozen_selections.json")
    save(args.out_dir / "selection_lock.json", {"sha256": frozen_hash, "new_target_scoring_started": False, "target_weight_search": False})
    print("All control rules frozen. Evaluating the fixed target population...", flush=True)
    result = evaluate_matched(cache, roles, joints, atoms, collection, protocol, selected, source_selected, source_result, previous, small_n=args.small_n)
    for name, rows in (("monthly_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "monthly"])),
        ("period_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "period"])), ("class_metrics", result["classes"]),
        ("budget_monthly", result["budget_monthly"]), ("budget_summary", result["budget_summary"]), ("candidate_audit", selected["candidates"]),
        ("latest_choice_audit", selected["focal"]), ("latest_choice_exclusions", selected["exclusions"]), ("selected_monthly_scores", selected["months"])):
        write_table(args.out_dir / (name + ".csv"), [{k: json.dumps(v, separators=(",", ":")) if isinstance(v, list) else v for k, v in r.items()} for r in rows], ("target", "model", "status"))
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": plan["unknown_prior"],
        "source_forward_reproduced": True, "raw_H5_rescan": False, "monthly": [r for r in result["metrics"] if r["scope"] == "monthly"],
        "periods": [r for r in result["metrics"] if r["scope"] == "period"], "budget_summary": result["budget_summary"]})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    save(args.out_dir / "invariants.json", {"source_forward_reproduced": True, "strict_pooled_rule_equals_source_all": True,
        "common_baseline_unchanged": True, "current_and_historical_labels_unchanged": True, "fixed_target_population": True})
    (args.out_dir / "report.md").write_text(report_text(result, selected, collection, protocol, args.recency_ratio))
    if sha256(args.out_dir / "frozen_selections.json") != frozen_hash:
        raise RuntimeError("frozen controls changed during target evaluation")
    metadata.update(rows_read=0, cached_source_rows=metadata0["cached_source_rows"], source_forward_reproduced=True, frozen_selection_sha256=frozen_hash)
    finish_run(args.out_dir, metadata, started)
    bs = {(r["model"], r["group"]): r for r in result["budget_summary"] if r["period"] == "evaluation"}
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation" and r["group"] in MATCHED:
            b = bs[r["model"], r["group"]]
            print(f"PERIOD {r['model']} {r['group']} error={number((r['weighted_error'] or {}).get('value'))} local_pp={number((r['change_vs_time_baseline'] or {}).get('value'),100)} latest_pp={number((r['change_vs_source_latest'] or {}).get('value'),100)} raw={r['raw_change_vs_time_baseline']} budget={b['both_met']}/{b['checked']} identity={b['identity']}/{b['available']}")
    for r in selected["focal"]:
        if r["period"] == "evaluation":
            print(f"AUDIT {r['target']} {r['model']} latest={r['source_latest_candidate']} common_support={r.get('common_support','NA')} past_support={r.get('historical_fit_support',[])} APP21_ok={r.get('month_APP21_ok',[])} raw_ok={r.get('month_raw_ok',[])} pooled_gain_pp={number(r.get('pooled_gain'),100)} latest_gain_pp={number(r.get('latest_gain'),100)}")
    for model in protocol["models"]:
        improve, harm = class_extremes(result, model, "source_all")
        def display(rows):
            return ";".join(f"APP{r['APP']}:raw={r['wrong_change_vs_source_latest']},pp={number(r['weighted_change_vs_source_latest'],100)}" for r in rows) or "none"
        print(f"CLASSES {model} all_vs_latest improve=[{display(improve)}] harm=[{display(harm)}]")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepare-dir", "monthly-dir", "refinement-dir", "hierarchy-dir", "joint-dir", "blocks-dir", "forward-dir", "out-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--recency-ratio", type=float, default=2.)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if args.small_n < 1 or not np.isfinite(args.recency_ratio) or args.recency_ratio < 1:
        parser.error("positive small-n and finite recency ratio >= 1 required")
    if not all(d.is_dir() for d in (args.prepare_dir, args.monthly_dir, args.refinement_dir, args.hierarchy_dir, args.joint_dir, args.blocks_dir, args.forward_dir)) or args.out_dir.exists():
        parser.error("completed source artifacts and a fresh output directory required")
    run(args)


if __name__ == "__main__":
    main()
