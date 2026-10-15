#!/usr/bin/env python3
"""Past-only gain / class-cost frontiers over the existing frozen grid."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.costfrontier import GROUPS, evaluate_tradeoffs, select_tradeoffs  # noqa: E402
from eibo.recencyaudit import MATCHED, evaluate_matched, recency_weights, select_and_audit  # noqa: E402
from methodology_real_atomic import flat_metrics, read_hierarchy  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_hierarchy import compare_replay, read_refinement, write_table  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_recency import CODE as RECENCY_CODE, read_forward  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

CODE = RECENCY_CODE + ("scripts/methodology_real_recency.py", "src/eibo/costfrontier.py")


def replay_recency(directory, cache, roles, joints, atoms, collection, protocol, source_selected, source_result, previous, inputs):
    """Verify manifests and reproduce stage 16 before constructing new policies."""
    metadata = json.loads((directory / "run.json").read_text())
    manifest = {r["path"]: r["sha256"] for r in metadata["outputs"]}
    required = {"summary.json", "confusion_matrices.json", "frozen_selections.json", "selection_lock.json",
        "collection_protocol.json", "selection_protocol.json", "plan_snapshot.json", "invariants.json"}
    if metadata["status"] != "complete" or metadata["source_lineage"] != cache["plan"]["source"] or metadata["rows_read"] != 0:
        raise ValueError("completed recency cache with identical source required")
    if len(manifest) != len(metadata["outputs"]) or not required.issubset(manifest):
        raise ValueError("recency manifest incomplete or duplicated")
    for name, digest in manifest.items():
        if Path(name).name != name or sha256(directory / name) != digest:
            raise ValueError("recency artifact hash mismatch: " + name)
    for path in [ROOT / "scripts/methodology_real_recency.py"] + [ROOT / name for name in RECENCY_CODE]:
        saved = [r for r in metadata["code"] if Path(r["path"]).name == path.name]
        if len(saved) != 1 or saved[0]["sha256"] != sha256(path):
            raise ValueError("recency code lineage differs")
    for path in inputs:
        saved = [r for r in metadata["input_artifacts"] if Path(r["path"]).name == path.name and Path(r["path"]).parent.name == path.parent.name]
        if len(saved) != 1 or saved[0]["sha256"] != sha256(path):
            raise ValueError("recency input lineage differs")
    compare_replay(collection, json.loads((directory / "collection_protocol.json").read_text()), "recency.collection")
    compare_replay(cache["plan"], json.loads((directory / "plan_snapshot.json").read_text()), "recency.plan")
    ratio = metadata["parameters"]["recency_ratio"]
    expected_protocol = {"matched_groups": list(MATCHED), "original_protocol": protocol, "recency_ratio": ratio,
        "oldest_to_newest_weights": recency_weights(collection["window_spec"]["history_months"], ratio).tolist(),
        "candidate_support_shared_across_objectives": True, "shared_budget": "latest month",
        "strict_budget": "all months and original pooled budgets", "raw_H5_rescan": False,
        "target_weight_search": False, "status": "exploratory matched temporal objectives"}
    compare_replay(expected_protocol, json.loads((directory / "selection_protocol.json").read_text()), "recency.protocol")
    selected = select_and_audit(roles, collection, protocol, source_selected, ratio=ratio)
    compare_replay(selected["selections"], json.loads((directory / "frozen_selections.json").read_text()), "recency.selections")
    lock = json.loads((directory / "selection_lock.json").read_text())
    digest = sha256(directory / "frozen_selections.json")
    if lock["sha256"] != digest or metadata["frozen_selection_sha256"] != digest:
        raise ValueError("recency frozen lock differs")
    result = evaluate_matched(cache, roles, joints, atoms, collection, protocol, selected, source_selected, source_result,
        previous, small_n=metadata["parameters"]["small_n"])
    expected = {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(),
        "unknown_prior": cache["plan"]["unknown_prior"], "source_forward_reproduced": True, "raw_H5_rescan": False,
        "monthly": [r for r in result["metrics"] if r["scope"] == "monthly"],
        "periods": [r for r in result["metrics"] if r["scope"] == "period"], "budget_summary": result["budget_summary"]}
    compare_replay(expected, json.loads((directory / "summary.json").read_text()), "recency.summary")
    compare_replay({"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]},
        json.loads((directory / "confusion_matrices.json").read_text()), "recency.confusions")
    return result, [directory / name for name in ("run.json",) + tuple(sorted(manifest))]


def counts(result, model, group):
    rows = [r for r in result["compatibility"] if r["period"] == "evaluation" and (r["model"], r["group"]) == (model, group)]
    return [sum(r[key] is True for r in rows) for key in ("legacy_met", "root_joint_met", "keep_joint_met")] + [
        sum(r["root_joint_met"] is not None for r in rows)]


def report_text(result, selected, protocol):
    lines = ["# Existing-candidate gain and class-cost tradeoffs", "",
        "All original classes and priors, candidate thresholds, current and historical fitted labels, target population, outside predictions and the timing baseline are unchanged. Stages 15 and 16 are hash-verified and replayed. No H5 scan and no new dependencies.", "",
        "## Past-only policies", "",
        "Every new policy requires the same current/historical leaf support and full historical class coverage as stage 16. latest policies use only the latest historical validation month's budgets and gain. all policies require every historical month AND class-count pooled budgets, and maximize pooled gain. All preserve the original APP21 and raw-error budgets.",
        "no_harm adds zero raw wrong-count increases for APP22 and APP15 relative to the shared root. keep_gains instead bounds each of those classes by min(0, the source-latest family's historical increment), preserving its improvements without allowing its harms. The reference family is the actual old source_latest choice for this target origin; each historical fold uses that family's own past fitted labels. It is a past-data comparator selected using past scores, not an independent held-out guarantee for exact current leaves.",
        "Only positive weighted past gain is deployed. Identity is included explicitly in feasibility/frontier analysis. Identity can FAIL keep_gains when the reference rescued past flows. No feasible rule, no positive feasible gain, incomplete history and unavailable current model have distinct statuses; fallback is evaluated without claiming that retention constraints were met.", "",
        "## Evaluation-period comparisons", "",
        "Local and latest changes are error changes in percentage points: negative is better. Joint/root checks APP21, raw error, APP22 and APP15; joint/keep additionally retains actual target source_latest improvements for APP22/15. These are descriptive target checks, never policy-selection inputs.", "",
        "| Model | Group | Local pp | Vs latest pp | Raw local | Legacy / root / keep / checked | Identity/available |",
        "|---|---|---:|---:|---:|---|---|"]
    budgets = {(r["model"], r["group"]): r for r in result["budget_summary"] if r["period"] == "evaluation"}
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation" and r["group"] in ("shared_latest", "strict_pooled") + GROUPS:
            b = budgets[r["model"], r["group"]]
            lines.append(f"| {r['model']} | {r['group']} | {number((r['change_vs_time_baseline'] or {}).get('value'),100)} | {number((r['change_vs_source_latest'] or {}).get('value'),100)} | {r['raw_change_vs_time_baseline']} | {' / '.join(map(str,counts(result,r['model'],r['group'])))} | {b['identity']}/{b['available']} |")
    lines += ["", "## Past feasibility and choices", "",
        "| Target | Model | Group | Rule | Feasible incl identity | Identity feasible | Deployed feasible | Status |",
        "|---|---|---|---:|---:|---|---|---|"]
    for r in selected["selections"]:
        if r["period"] == "evaluation":
            lines.append(f"| {r['target']} | {r['model']} | {r['group']} | {(r['rule'] or {}).get('candidate_id','identity')} | {r.get('past_feasible_count','NA')} | {r.get('past_identity_feasible','NA')} | {r.get('past_selected_feasible','NA')} | {r['status']} |")
    lines += ["", "## Evaluation focal classes", "",
        "All class changes below are integer NET differences between classifiers. Paired rescued/harmed columns in class_metrics.csv refer only to each policy versus its common root.", "",
        "| Model | Group | APP | n | Wrong | Vs root | Vs latest | Latest weighted pp |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in result["classes"]:
        if r["scope"] == "period" and r["period"] == "evaluation" and r["group"] in GROUPS and r["APP"] in (2, 15, 21, 22, 34):
            lines.append(f"| {r['model']} | {r['group']} | {r['APP']} | {r['n']} | {r['wrong']} | {r['wrong_change_vs_time_baseline']} | {r['wrong_change_vs_source_latest']} | {number(r['weighted_change_vs_source_latest'],100)} |")
    lines += ["", "## Other class improvements and harms", "",
        "| Model | Group | APP | n | Vs latest wrong | Weighted pp |",
        "|---|---|---:|---:|---:|---:|"]
    for model in protocol["models"]:
        for group in GROUPS:
            rows = [r for r in result["classes"] if (r["scope"],r["period"],r["model"],r["group"]) == ("period","evaluation",model,group) and r["weighted_change_vs_source_latest"] is not None]
            for direction in (-1, 1):
                top = sorted((r for r in rows if direction * r["wrong_change_vs_source_latest"] > 0),
                    key=lambda r: -direction*r["weighted_change_vs_source_latest"])[:3]
                for r in top:
                    lines.append(f"| {model} | {group} | {r['APP']} | {r['n']} | {r['wrong_change_vs_source_latest']} | {number(r['weighted_change_vs_source_latest'],100)} |")
    lines += ["", "## Past frontiers and full candidate records", "",
        "Frontiers minimize [-gain, APP21 conditional cost, APP22 conditional cost, APP15 conditional cost, raw cost]. latest uses the last historical month; all uses pooled gain and the maximum of each cost across all historical months AND pooled data (maxima may come from different months). Exact numerical dominance keeps all equivalent points. The full-support frontier and the frontier after original APP21/raw budgets are both retained. Frontiers use ROOT-relative costs; retention feasibility is a separate flag, not another dominance claim. They are past-only opportunity diagnostics, not target oracles or evidence of optimality beyond this finite grid.",
        "past_candidate_classes.npz retains every candidate plus identity, every historical class delta and original denominator, support/availability, all cost vectors and feasibility/frontier masks; candidate_index.json maps contexts, candidate IDs, class/prior order and origins. frontier_candidates.csv contains both frontiers plus the actual selected points; frontier_summary.csv includes feasible counts. selected_past_classes.csv retains selected policies' exact per-class monthly and pooled increments. No class is dropped, reweighted or resampled.",
        "class_metrics.csv, monthly_summary.csv, period_summary.csv, compatibility_monthly.csv, budget_monthly.csv, budget_summary.csv and confusion_matrices.json retain every new policy and every stage-16 control. Missing classes retain NA and their original prior identification ranges; small classes stay explicitly marked. Different policies can have different off-diagonal confusions despite equal error.",
        "All new rules and protocol are hashed before any new target scoring. No target thresholds, budget sweeps, target-driven winner selection or new feature search are performed. These are exploratory results on already inspected months; empirical compatibility is not a future-budget or independence guarantee. Further confirmation requires uninspected time periods.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    if args.small_n < 1:
        raise ValueError("positive small-n required")
    print("Verifying forward and recency sources; replaying old rules and matrices; no H5 read...", flush=True)
    cache = read_cache(args.monthly_dir)
    atoms, prior, stage8 = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    stage9 = read_hierarchy(args.hierarchy_dir, cache, atoms, prior, args.monthly_dir, args.refinement_dir)
    _, plan, _, _ = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("identical preparation plan required")
    metadata0, collection, protocol, joints, roles, previous, source_selected, source_result, inputs = read_forward(args, cache, atoms, prior, stage8, stage9)
    replayed, old_inputs = replay_recency(args.recency_dir, cache, roles, joints, atoms, collection, protocol, source_selected, source_result, previous, inputs)
    metadata = start_run(args, inputs=inputs + old_inputs, code=[Path(__file__)] + [ROOT / n for n in CODE], source=plan["source"])
    save(args.out_dir / "plan_snapshot.json", plan)
    save(args.out_dir / "collection_protocol.json", collection)
    save(args.out_dir / "selection_protocol.json", {"groups": list(GROUPS), "original_protocol": protocol,
        "no_harm_APPs": [22,15], "no_harm_budget_raw": 0, "retention_limit": "min(0,source_latest_family_historical_delta)",
        "latest_objective": "latest historical gain", "all_objective": "class-count pooled gain",
        "all_budgets": "every historical month and pooled", "common_support": True,
        "target_oracle": False, "target_budget_search": False, "raw_H5_rescan": False})
    print("Sources reproduced. Constructing past-only frontiers and four frozen policies...", flush=True)
    selected = select_tradeoffs(roles, collection, protocol, source_selected)
    save(args.out_dir / "frozen_selections.json", selected["selections"])
    digest = sha256(args.out_dir / "frozen_selections.json")
    protocol_digest = sha256(args.out_dir / "selection_protocol.json")
    save(args.out_dir / "selection_lock.json", {"sha256": digest, "protocol_sha256": protocol_digest, "new_target_scoring_started": False})
    np.savez_compressed(args.out_dir / "past_candidate_classes.npz", **selected["arrays"])
    save(args.out_dir / "candidate_index.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(),
        "unknown_prior": plan["unknown_prior"], "point_columns": ["negative_gain","APP21_cost","APP22_cost","APP15_cost","raw_cost"],
        "delta_axes": ["historical_origin","candidate_including_identity_first","original_class"],
        "contexts": selected["array_index"], "frontiers_use_target_counts": False})
    print("Rules and protocol locked. Scoring only frozen policies on fixed target flows...", flush=True)
    result = evaluate_tradeoffs(cache, roles, joints, atoms, collection, protocol, selected, source_selected, replayed, previous, small_n=args.small_n)
    for name, rows in (("frontier_candidates", selected["frontiers"]), ("frontier_summary", selected["frontier_summary"]),
        ("selected_past_classes", selected["past_classes"]), ("monthly_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "monthly"])),
        ("period_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "period"])), ("class_metrics", result["classes"]),
        ("compatibility_monthly", result["compatibility"]), ("budget_monthly", result["budget_monthly"]), ("budget_summary", result["budget_summary"])):
        write_table(args.out_dir / (name + ".csv"), rows, ("target","model","status"))
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(),
        "unknown_prior": plan["unknown_prior"], "periods": [r for r in result["metrics"] if r["scope"] == "period"],
        "monthly": [r for r in result["metrics"] if r["scope"] == "monthly"], "compatibility": result["compatibility"],
        "source_recency_reproduced": True, "target_oracle": False})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    save(args.out_dir / "invariants.json", {"source_recency_reproduced": True, "common_baseline_unchanged": True,
        "current_and_historical_labels_unchanged": True, "fixed_target_population": True, "all_original_classes_and_priors": True})
    (args.out_dir / "report.md").write_text(report_text(result, selected, protocol))
    if sha256(args.out_dir / "frozen_selections.json") != digest or sha256(args.out_dir / "selection_protocol.json") != protocol_digest:
        raise RuntimeError("frozen policy or protocol changed during target evaluation")
    metadata.update(rows_read=0, cached_source_rows=metadata0["cached_source_rows"], source_recency_reproduced=True, frozen_selection_sha256=digest)
    finish_run(args.out_dir, metadata, started)
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation" and r["group"] in GROUPS:
            rows = {c["APP"]: c for c in result["classes"] if (c["scope"],c["target"],c["model"],c["group"]) == ("period","evaluation",r["model"],r["group"])}
            delta = "/".join(str(rows[a]["wrong_change_vs_source_latest"]) for a in (21,22,15))
            focal = "/".join(str(rows[a]["wrong_change_vs_time_baseline"]) for a in (2,34))
            print(f"PERIOD {r['model']} {r['group']} local_pp={number((r['change_vs_time_baseline'] or {}).get('value'),100)} latest_pp={number((r['change_vs_source_latest'] or {}).get('value'),100)} raw={r['raw_change_vs_time_baseline']} d21/22/15_vs_latest={delta} d2/34_vs_root={focal} caps={'/'.join(map(str,counts(result,r['model'],r['group'])))}")
    for c in collection["window_spec"]["contexts"]:
        if c["period"] == "evaluation":
            rows = [r for r in selected["selections"] if (r["target"],r["model"]) == (c["target"],c["model"])]
            choices = ",".join(str((r["rule"] or {}).get("candidate_id","identity")) for r in rows)
            feasible = ",".join(str(r.get("past_feasible_count","NA")) for r in rows)
            print(f"PAST {c['target']} {c['model']} order={','.join(GROUPS)} rules={choices} feasible={feasible}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepare-dir","monthly-dir","refinement-dir","hierarchy-dir","joint-dir","blocks-dir","forward-dir","recency-dir","out-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if args.small_n < 1 or args.out_dir.exists() or not all(getattr(args, name).is_dir() for name in
            ("prepare_dir","monthly_dir","refinement_dir","hierarchy_dir","joint_dir","blocks_dir","forward_dir","recency_dir")):
        parser.error("completed source directories, positive small-n and a fresh output directory required")
    run(args)


if __name__ == "__main__":
    main()
