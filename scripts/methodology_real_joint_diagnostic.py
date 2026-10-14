#!/usr/bin/env python3
"""Replay stage 11, attribute all-class changes and audit focal opportunities."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.jointdiagnostic import attribution, budget_audit, focal_candidate_audit, training_split_regions  # noqa: E402
from eibo.jointrefinement import GROUPS, run_joint, validation_windows  # noqa: E402
from methodology_real_atomic import HIERARCHY_FILES, flat_metrics, read_hierarchy  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_hierarchy import MONTHLY_FILES, REFINEMENT_FILES, compare_replay, read_refinement, write_table  # noqa: E402
from methodology_real_joint import CODE as JOINT_CODE, collection_protocol, load_counts  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

JOINT_FILES = ("collection_protocol.json", "selection_protocol.json", "plan_snapshot.json", "joint_counts.npz", "summary.json", "confusion_matrices.json",
               "monthly_summary.csv", "period_summary.csv", "monthly_classes.csv", "period_classes.csv", "candidate_scores.csv", "selections.csv", "report.md")
PREPARE_FILES = ("run.json", "experiment_plan.json", "tables.json", "audit.json", "period_service_counts.csv", "time_unit_diagnostics.json")
CODE = JOINT_CODE + ("scripts/methodology_real_joint.py", "src/eibo/jointdiagnostic.py")


def read_joint(args, cache, atoms, prior, stage8, stage9):
    directory = args.joint_dir
    metadata = json.loads((directory / "run.json").read_text())
    if metadata["status"] != "complete" or metadata["source_lineage"] != cache["plan"]["source"] or metadata["counts_reconciled"] is not True:
        raise ValueError("completed reconciled stage 11 with identical source required")
    manifest = {r["path"]: r["sha256"] for r in metadata["outputs"]}
    if len(manifest) != len(metadata["outputs"]) or not set(JOINT_FILES).issubset(manifest):
        raise ValueError("stage 11 output manifest is incomplete or duplicated")
    for filename in JOINT_FILES:
        if sha256(directory / filename) != manifest[filename]:
            raise ValueError(f"stage 11 artifact hash mismatch: {filename}")
    parameters = metadata["parameters"]
    threshold = parameters["ipt_threshold_ms"]
    windows = validation_windows(cache, prior["models"], gap=parameters["validation_gap_seconds"], validation_day=parameters["validation_day"])
    collection = collection_protocol(cache, prior, windows, threshold)
    protocol = {"groups": list(GROUPS), "models": prior["models"], "fixed_IPT2_threshold_ms": threshold,
                "minimum_fit_leaf_flows": parameters["min_leaf_flows"], "APP21_validation_budget_pp": parameters["app21_budget_pp"],
                "maximum_validation_raw_wrong_increase": parameters["max_validation_raw_increase"], "maximum_low_leaves": 4, "maximum_low_tree_depth": 2,
                "refit_after_validation": False, "status": "exploratory chronologically validated local refinement"}
    compare_replay(json.loads((directory / "selection_protocol.json").read_text()), protocol, "stage11.protocol")
    inputs = [directory0 / name for directory0, names in ((args.monthly_dir, MONTHLY_FILES), (args.refinement_dir, REFINEMENT_FILES),
              (args.hierarchy_dir, HIERARCHY_FILES), (args.prepare_dir, PREPARE_FILES)) for name in names]
    joints, roles = load_counts(directory, cache, prior, collection, atoms, inputs)
    legacy = {(r["target"], r["model"], "legacy_time_full"): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in stage8["confusions"] if r["group"] == "ipt_split"}
    legacy.update({(r["target"], r["model"], "legacy_hierarchy_full"): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in stage9["confusions"] if r["group"] == "low_size_split"})
    replay = run_joint(cache, roles, joints, atoms, windows, prior, legacy, threshold=threshold, minimum=parameters["min_leaf_flows"],
                       app21_budget=parameters["app21_budget_pp"] / 100, raw_budget=parameters["max_validation_raw_increase"], small_n=parameters["small_n"])
    summary = {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": cache["plan"]["unknown_prior"],
               "protocol": protocol, "counts_reconciled": True, "legacy_models_reproduced": True,
               "monthly": replay["monthly"], "periods": replay["periods"], "selections": replay["selections"]}
    compare_replay(summary, json.loads((directory / "summary.json").read_text()), "stage11.summary")
    compare_replay({"known_service_codes": cache["known"].tolist(), "matrices": replay["confusions"]},
                   json.loads((directory / "confusion_matrices.json").read_text()), "stage11.confusions")
    return metadata, collection, protocol, joints, roles, replay, inputs + [directory / name for name in ("run.json",) + JOINT_FILES]


def report_text(result, cache, original_protocol, top):
    lines = ["# Joint refinement diagnostic audit", "",
        f"Stage 11 has been replayed before this audit. All {len(cache['known'])} original known classes and priors are retained. Unknown-class error is excluded. No H5 read and no new deployed model selection.",
        "Positive error changes mean harm. All class denominators are full-role class counts, never local-cell counts. Periods pool integers within each class before weighting. Candidate/atomic target results below are hindsight diagnostics and never modify the frozen stage 11 models.", "",
        "## Budget transfer by model month", "",
        f"Original APP21 validation budget: {original_protocol['APP21_validation_budget_pp']:g} pp; raw wrong-count budget: {original_protocol['maximum_validation_raw_wrong_increase']}. Validation missing classes can trigger identity. These are empirical constraints; model-month counts are not independent trials.", "",
        "| Target | Model | Validation APP21 pp | Target APP21 pp | Validation raw | Target raw | APP21 met | Raw met |",
        "|---|---|---:|---:|---:|---:|---|---|"]
    for r in result["budget_monthly"]:
        if r["period"] == "evaluation" and r["group"] == "validation_constrained":
            lines.append(f"| {r['target']} | {r['model']} | {number(r['validation_APP21_change'],100)} | {number(r['target_APP21_change'],100)} | {r['validation_raw_wrong_change']} | {r['target_raw_wrong_change']} | {r['target_APP21_budget_met']} | {r['target_raw_budget_met']} |")
    lines += ["", "## APP2 candidate opportunity", "",
        "A raw positive candidate uses its original fitted leaf labels even when its pooled leaf support is ineligible. Allowed candidates also satisfy the original leaf budget and APP34-parent protection. The maximum target gain evaluates past-fitted candidates after the fact; it is not a valid new selection or a population bound.", "",
        "| Target | Model | Family | Candidates / allowed | Raw positive APP2 | Allowed positive APP2 | Validation-qualified positive | Best allowed fit correct gain | Candidate | Selected by | Max target correct gain hindsight |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    for r in result["focal"]["candidate_summary"]:
        if r["period"] == "evaluation":
            lines.append(f"| {r['target']} | {r['model']} | {r['kind']} | {r.get('candidate_count','NA')} / {r.get('allowed_candidates','NA')} | {r.get('raw_positive_APP2_candidates','NA')} | {r.get('allowed_positive_APP2_candidates','NA')} | {r.get('validation_qualified_positive_APP2_candidates','NA')} | {r.get('best_allowed_fit_APP2_correct_gain','NA')} | {r.get('best_allowed_candidate_id','NA')} | {r.get('best_allowed_selected_by','')} | {r.get('maximum_allowed_target_APP2_correct_gain_hindsight','NA')} |")
    lines += ["", "## APP2 fine pair atoms", "",
        "These full size-pair grids are finer than two crossed cuts and are not deployed models. IPT is collapsed inside the fixed low branch. Raw atom winners use all fixed classes; guarded atom labels back off below the original support threshold and respect APP34 protection. Different position pairs are views of the same flows and their counts must not be added.", "",
        "| Target | Model | Pair | Fit APP2 winning atoms | Guarded winning atoms | APP2 flows lost to support | Target empirical winning atoms | Target APP2 flows in winning atoms |",
        "|---|---|---|---:|---:|---:|---:|---:|"]
    for r in result["focal"]["pair_summary"]:
        if r["period"] == "evaluation":
            lines.append(f"| {r['target']} | {r['model']} | {r['left_packet']},{r['right_packet']} | {r['fit_APP2_winning_atoms']} | {r['guarded_fit_APP2_winning_atoms']} | {r['fit_APP2_flows_lost_to_leaf_budget']} | {r['target_empirical_APP2_winning_atoms']} | {r['target_empirical_APP2_flows_in_winning_atoms']} |")
    lines += ["", "## Evaluation-period class contributions", "",
        "Each comparison lists its largest positive and negative fixed-prior contributions. Full CSVs retain every class, including missing and small-n classes. Non-root comparisons have integer net changes only; paired rescue/harm is not inferred from separate confusion matrices.", "",
        "| Model | Model / reference | APP | n | Status | Wrong change | Conditional pp | Weighted pp |",
        "|---|---|---:|---:|---|---:|---:|---:|"]
    groups = sorted({(r["model"], r["group"], r["reference"]) for r in result["attribution"]})
    for model, group, reference in groups:
        rows = [r for r in result["attribution"] if (r["scope"], r["period"], r["model"], r["group"], r["reference"]) == ("period", "evaluation", model, group, reference) and r["weighted_change"] is not None]
        improved = sorted((r for r in rows if r["wrong_change"] < 0), key=lambda r: (r["weighted_change"], r["APP"]))[:top]
        harmed = sorted((r for r in rows if r["wrong_change"] > 0), key=lambda r: (-r["weighted_change"], r["APP"]))[:top]
        for r in improved + harmed:
            lines.append(f"| {model} | {group} / {reference} | {r['APP']} | {r['n']} | {r['status']} | {r['wrong_change']} | {number(r['conditional_change'],100)} | {number(r['weighted_change'],100)} |")
    lines += ["", "## APP2 training-split regions", "",
        "Fit-subset and full-past models use the same fixed IPT root and original target population. Positive changes are extra errors from the fitting subset. Regions sum exactly to the class error change. This data-usage comparison cannot separately identify sample-size effects, recency effects or estimation noise. The actual legacy model comparison is also retained in class attribution and can differ if its learned timing threshold differs.", "",
        "| Model | Region | Wrong full past | Wrong fit subset | Wrong change | APP2 conditional pp |",
        "|---|---|---:|---:|---:|---:|"]
    for r in result["split_regions"]:
        if r["scope"] == "period" and r["period"] == "evaluation" and r["APP"] == 2:
            lines.append(f"| {r['model']} | {r['region']} | {r['wrong_full_past']} | {r['wrong_fit_subset']} | {r['wrong_change']} | {number(r['conditional_change'],100)} |")
    lines += ["", "## Interpretation and files", "",
        "APP2_candidates.csv covers every original single/joint candidate, its validation rejection reasons and the actual selecting groups; APP2_candidate_leaves.csv expands deployed choices and the best allowed fit-APP2 candidate per family. The best positive gain includes identity at zero; candidate ID is absent when no allowed candidate has positive focal gain. APP2_pair_atoms.csv contains atoms with APP2 mass in fitting, validation or target; pair summaries cover every position pair. Empty-focal atoms cannot contribute APP2 correct flows. Atom indices denote (previous cut, current cut], with unbounded outer intervals.",
        "budget_monthly.csv and budget_summary.csv report validation-to-target violations. class_attribution.csv and attribution_summary.csv retain full class comparisons. training_split_regions.csv separates outside-cell and low/high/invalid changes. All original rules and budgets stay frozen. No significance claim, population-risk guarantee or validated session independence is introduced; missing target classes make complete-class atom-oracle diagnostics unavailable.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    if min(args.small_n, args.top) < 1:
        raise ValueError("positive small-n and report limits required")
    print("Verifying stage 5/8/9/11 hashes and replaying original joint models; no H5 read...", flush=True)
    cache = read_cache(args.monthly_dir)
    atoms, prior, stage8 = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    stage9 = read_hierarchy(args.hierarchy_dir, cache, atoms, prior, args.monthly_dir, args.refinement_dir)
    _, plan, _, _ = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("identical preparation plan required")
    metadata0, collection, protocol, joints, roles, replay, inputs = read_joint(args, cache, atoms, prior, stage8, stage9)
    metadata = start_run(args, inputs=inputs, code=[Path(__file__)] + [ROOT / path for path in CODE], source=plan["source"])
    save(args.out_dir / "plan_snapshot.json", plan)
    save(args.out_dir / "collection_protocol.json", collection)
    save(args.out_dir / "audit_protocol.json", {"original_selection_protocol": protocol, "deployed_rules_changed": False, "raw_H5_rescan": False,
        "APP2_atomic_diagnostic": "full inherited size-pair atoms, IPT collapsed in the low branch, no deployment or target-label selection",
        "training_split_reference": "full past fitted at the same fixed IPT root; sample size and recency are not separately identified"})
    attr, attr_summary = attribution(cache, replay, protocol["models"], small_n=args.small_n)
    budgets, budget_summary = budget_audit(cache, replay, protocol)
    print("Original models reproduced. Auditing all candidate APP2 winners and fine size-pair atoms...", flush=True)
    focal = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=protocol["minimum_fit_leaf_flows"],
                                  app21_budget=protocol["APP21_validation_budget_pp"] / 100, raw_budget=protocol["maximum_validation_raw_wrong_increase"])
    split = training_split_regions(cache, roles, atoms, collection)
    result = {"attribution": attr, "attribution_summary": attr_summary, "budget_monthly": budgets, "budget_summary": budget_summary, "focal": focal, "split_regions": split}
    for filename, rows in (("class_attribution", attr), ("attribution_summary", flat_metrics(attr_summary)), ("budget_monthly", flat_metrics(budgets)),
        ("budget_summary", budget_summary), ("APP2_candidates", focal["candidates"]), ("APP2_candidate_summary", focal["candidate_summary"]),
        ("APP2_candidate_leaves", focal["leaves"]), ("APP2_pair_atoms", focal["pair_atoms"]), ("APP2_pair_summary", focal["pair_summary"]), ("training_split_regions", split)):
        write_table(args.out_dir / (filename + ".csv"), [{k: json.dumps(v, separators=(",", ":")) if isinstance(v, list) else v for k, v in r.items()} for r in rows], ("target", "model", "status"))
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": plan["unknown_prior"],
        "stage11_reproduced": True, "raw_H5_rescan": False, "original_selection_protocol": protocol,
        "attribution_summary": attr_summary, "budget_summary": budget_summary, "APP2_candidate_summary": focal["candidate_summary"], "APP2_pair_summary": focal["pair_summary"]})
    (args.out_dir / "report.md").write_text(report_text(result, cache, protocol, args.top))
    metadata.update(rows_read=0, cached_source_rows=metadata0["cached_source_rows"], stage11_reproduced=True, deployed_rules_changed=False)
    finish_run(args.out_dir, metadata, started)
    for r in budget_summary:
        if r["period"] == "evaluation" and r["group"] == "validation_constrained":
            print(f"BUDGET {r['model']} checked={r['checked_model_months']} both_met={r['both_met']} APP21_violations={r['APP21_violations']} raw_violations={r['raw_wrong_violations']}")
    for r in focal["candidate_summary"]:
        if r["period"] == "evaluation" and r["kind"] == "joint":
            print(f"APP2 {r['target']} {r['model']} raw_positive={r.get('raw_positive_APP2_candidates','NA')} allowed_positive={r.get('allowed_positive_APP2_candidates','NA')} best_fit_correct_gain={r.get('best_allowed_fit_APP2_correct_gain','NA')} max_target_correct_gain_hindsight={r.get('maximum_allowed_target_APP2_correct_gain_hindsight','NA')}")
            pairs = [v for v in focal["pair_summary"] if (v["target"], v["model"]) == (r["target"], r["model"])]
            empirical = [v["target_empirical_APP2_flows_in_winning_atoms"] for v in pairs if v["target_empirical_APP2_flows_in_winning_atoms"] is not None]
            print(f"ATOMS {r['target']} {r['model']} max_fit_winners={max((v['fit_APP2_winning_atoms'] for v in pairs),default=0)} max_guarded_winners={max((v['guarded_fit_APP2_winning_atoms'] for v in pairs),default=0)} max_target_empirical_correct_hindsight={max(empirical,default='NA')}")
    for model in protocol["models"]:
        for group, reference in (("joint_fit", "single_fit"), ("validation_constrained", "time_fit")):
            values = [r for r in attr if (r["scope"], r["period"], r["model"], r["group"], r["reference"]) == ("period", "evaluation", model, group, reference) and r["weighted_change"] is not None]
            improved = sorted((r for r in values if r["wrong_change"] < 0), key=lambda r: r["weighted_change"])[:3]
            harmed = sorted((r for r in values if r["wrong_change"] > 0), key=lambda r: -r["weighted_change"])[:3]
            def display(rows):
                return ";".join(f"APP{r['APP']}:n={r['n']},raw={r['wrong_change']},pp={number(r['weighted_change'],100)}" for r in rows) or "none"
            print(f"CLASS {model} {group}/{reference} improve=[{display(improved)}] harm=[{display(harmed)}]")
        parts = [r for r in split if (r["scope"], r["period"], r["model"], r["APP"]) == ("period", "evaluation", model, 2)]
        if parts:
            print(f"SPLIT_APP2 {model} " + " ".join(f"{r['region']}:raw={r['wrong_change']},pp={number(r['conditional_change'],100)}" for r in parts))
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepare-dir", "monthly-dir", "refinement-dir", "hierarchy-dir", "joint-dir", "out-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--small-n", type=int, default=200)
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    if not all(path.is_dir() for path in (args.prepare_dir, args.monthly_dir, args.refinement_dir, args.hierarchy_dir, args.joint_dir)) or args.out_dir.exists():
        parser.error("completed source artifacts and a fresh output directory required")
    if min(args.small_n, args.top) < 1:
        parser.error("positive small-n and top required")
    run(args)


if __name__ == "__main__":
    main()
