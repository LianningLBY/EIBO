#!/usr/bin/env python3
"""Compare outside training data while preserving every validated local rule."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.regionalvalidation import BACKGROUNDS, run_regional  # noqa: E402
from eibo.jointrefinement import MATCHED_GROUPS  # noqa: E402
from methodology_real_atomic import flat_metrics, read_hierarchy  # noqa: E402
from methodology_real_experiment import read_preparation  # noqa: E402
from methodology_real_hierarchy import read_refinement, write_table  # noqa: E402
from methodology_real_joint_diagnostic import CODE as DIAGNOSTIC_CODE, read_joint  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

CODE = DIAGNOSTIC_CODE + ("scripts/methodology_real_joint_diagnostic.py", "src/eibo/regionalvalidation.py")


def report_text(result, cache, protocol):
    lines = ["# Regional validation with a full-past outside baseline", "",
        f"All {len(cache['known'])} original known APPs, priors and target flows remain fixed. Unknown-class error is excluded. Stage 11 is replayed first; all local selections, labels, training/validation roles, support thresholds and budgets stay frozen. No H5 read.", "",
        "## Data usage and validation scope", "",
        "fit_subset reproduces the original model. full_past replaces only original symbols outside the refined cell with predictions fitted on the full original past window. The low/high/invalid predictions inside the refined cell still come from the original fitting subset. Each background has its own matching time_fit baseline.",
        "The full outside model may use flows from the local validation period. Absolute validation accuracy is therefore not held out and is not reported. Local validation uses only the paired error increment against the identical outside baseline; the outside predictions cancel pointwise. Full confusion-matrix increments, not just aggregate risks, must agree between backgrounds on validation and target data.",
        "full_past_time is a separate full-window model with the same fixed timing threshold in every region. legacy_time_full is the actual previous learned-threshold model. Neither is silently equated to the hybrid baseline. A change from fit_subset to full_past can help or harm classes; no background is chosen from target labels.", "",
        "## Period controls", "",
        "Negative changes mean fewer errors. Local change is relative to the matching background's time_fit; total change compares against full_past_time. Periods pool integer errors within each fixed class before applying its prior.", "",
        "| Period | Model | Outside training | Local group | Error % | Local change pp | Total vs full-past time pp | Raw local | Raw total | APP2 % | APP21 % | APP34 % |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in result["metrics"]:
        if r["scope"] == "period" and r["group"] in ("time_fit", "validation_constrained"):
            lines.append(f"| {r['period']} | {r['model']} | {r['background']} | {r['group']} | {number((r.get('weighted_error') or {}).get('value'),100)} | {number((r.get('change_vs_same_background_time') or {}).get('value'),100)} | {number((r.get('change_vs_full_past_time') or {}).get('value'),100)} | {r.get('raw_change_vs_same_background_time','NA')} | {r.get('raw_change_vs_full_past_time','NA')} | {number(r.get('APP2_error'),100)} | {number(r.get('APP21_error'),100)} | {number(r.get('APP34_error'),100)} |")
    lines += ["", "## Full-past reference models", "",
        "| Period | Model | Reference | Error % | Raw wrong | APP2 % | APP21 % | APP34 % |",
        "|---|---|---|---:|---:|---:|---:|---:|"]
    for r in result["reference_metrics"]:
        if r["scope"] == "period":
            lines.append(f"| {r['period']} | {r['model']} | {r['reference']} | {number((r.get('weighted_error') or {}).get('value'),100)} | {r.get('raw_wrong','NA')} | {number(r.get('APP2_error'),100)} | {number(r.get('APP21_error'),100)} | {number(r.get('APP34_error'),100)} |")
    lines += ["", "## Evaluation months with full-past outside predictions", "",
        "| Target | Model | Error % | Local change pp | Total vs full-past time pp | APP2 % | APP21 % | APP34 % |",
        "|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in result["metrics"]:
        if (r["scope"], r["period"], r["background"], r["group"]) == ("monthly", "evaluation", "full_past", "validation_constrained"):
            lines.append(f"| {r['target']} | {r['model']} | {number((r.get('weighted_error') or {}).get('value'),100)} | {number((r.get('change_vs_same_background_time') or {}).get('value'),100)} | {number((r.get('change_vs_full_past_time') or {}).get('value'),100)} | {number(r.get('APP2_error'),100)} | {number(r.get('APP21_error'),100)} | {number(r.get('APP34_error'),100)} |")
    lines += ["", "## Budget increments remain unchanged", "",
        f"Original APP21 increment budget is {protocol['APP21_validation_budget_pp']:g} pp; original raw increment budget is {protocol['maximum_validation_raw_wrong_increase']}. These are local increments against the matching time baseline, not constraints on absolute class errors or on total differences against another baseline.",
        "Changing the outside baseline does not repair temporal budget violations. APP34 protection also refers to each background's local refinement increment; outside-data effects and differences against the full-past timing reference are reported separately.", "",
        "| Target | Model | APP21 validation pp | APP21 target pp | Validation raw | Target raw | APP21 met | Raw met |",
        "|---|---|---:|---:|---:|---:|---|---|"]
    for r in result["budget_monthly"]:
        if r["period"] == "evaluation" and r["group"] == "validation_constrained":
            lines.append(f"| {r['target']} | {r['model']} | {number(r['validation_APP21_change'],100)} | {number(r['target_APP21_change'],100)} | {r['validation_raw_wrong_change']} | {r['target_raw_wrong_change']} | {r['target_APP21_budget_met']} | {r['target_raw_budget_met']} |")
    lines += ["", "## Outside-data class effects", "",
        "Each row changes only the outside training data, keeping the same frozen local rule. These class changes are identical for all five local groups. Largest evaluation-period improvements and harms are shown below; CSVs retain every class.", "",
        "| Model | APP | n | Raw wrong change | Conditional pp | Weighted pp |",
        "|---|---:|---:|---:|---:|---:|"]
    for model in protocol["models"]:
        values = [r for r in result["classes"] if (r["scope"], r["period"], r["model"], r["background"], r["group"]) == ("period", "evaluation", model, "full_past", "time_fit") and r["weighted_change_vs_subset_same_group"] is not None]
        improve = sorted((r for r in values if r["wrong_change_vs_subset_same_group"] < 0), key=lambda r: r["weighted_change_vs_subset_same_group"])[:5]
        harm = sorted((r for r in values if r["wrong_change_vs_subset_same_group"] > 0), key=lambda r: -r["weighted_change_vs_subset_same_group"])[:5]
        for r in improve + harm:
            lines.append(f"| {model} | {r['APP']} | {r['n']} | {r['wrong_change_vs_subset_same_group']} | {number(r['conditional_change_vs_subset_same_group'],100)} | {number(r['weighted_change_vs_subset_same_group'],100)} |")
    lines += ["", "## Scope and output files", "",
        "monthly_summary.csv and period_summary.csv retain all five frozen local groups under both outside baselines. reference_summary.csv retains the full-past fixed-root and actual legacy reference. class_metrics.csv retains all fixed classes, original priors, exact local rescue/harm and integer changes against each reference. Missing target classes keep NA and prior identification ranges; small-n is only a flag.",
        "outside_class_effects.csv records outside changes and past-role class counts; APP2_outside_symbols.csv decomposes every nonzero outside APP2 error change by original symbol. These symbol changes must sum to the exact class effect. validation_local_increments.csv contains paired class increments only, without absolute validation accuracy. invariants.json records the full-matrix cancellation and APP34 local-protection checks.",
        "This is an exploratory control motivated by previously inspected targets. It separates global data usage from local refinement effects; it does not introduce a new drift-robust budget, validated independent units, a future-risk guarantee or a claim of methodological novelty. New multiple-time-block selection remains a separate experiment.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    if args.small_n < 1:
        raise ValueError("positive small-n flag required")
    print("Verifying and replaying original joint models; no H5 read...", flush=True)
    cache = read_cache(args.monthly_dir)
    atoms, prior, stage8 = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    stage9 = read_hierarchy(args.hierarchy_dir, cache, atoms, prior, args.monthly_dir, args.refinement_dir)
    _, plan, _, _ = read_preparation(args.prepare_dir)
    if plan != cache["plan"]:
        raise ValueError("identical preparation plan required")
    original_run, collection, protocol, joints, roles, replay, inputs = read_joint(args, cache, atoms, prior, stage8, stage9)
    metadata = start_run(args, inputs=inputs, code=[Path(__file__)] + [ROOT / path for path in CODE], source=plan["source"])
    save(args.out_dir / "plan_snapshot.json", plan)
    save(args.out_dir / "collection_protocol.json", collection)
    save(args.out_dir / "frozen_selections.json", replay["selections"])
    save(args.out_dir / "regional_protocol.json", {"backgrounds": list(BACKGROUNDS), "local_groups": list(MATCHED_GROUPS), "original_local_protocol": protocol,
        "local_rules_reselected": False, "outside_full_past_includes_local_validation": True, "absolute_validation_accuracy_reported": False,
        "validation_objective": "paired local increments against identical outside predictions; full confusion deltas must cancel",
        "full_past_reference": "full window fitted at the same fixed timing root, separately from actual legacy learned-threshold reference",
        "target_population_changed": False, "raw_H5_rescan": False})
    print("Comparing outside data usage and checking exact local cancellation...", flush=True)
    result = run_regional(cache, roles, joints, atoms, collection, protocol, replay, small_n=args.small_n)
    for filename, rows in (("monthly_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "monthly"])),
        ("period_summary", flat_metrics([r for r in result["metrics"] if r["scope"] == "period"])), ("reference_summary", flat_metrics(result["reference_metrics"])),
        ("class_metrics", result["classes"]), ("outside_class_effects", result["outside_effects"]), ("APP2_outside_symbols", result["APP2_outside_symbols"]),
        ("validation_local_increments", result["validation_increments"]), ("budget_monthly", flat_metrics(result["budget_monthly"])), ("budget_summary", result["budget_summary"])):
        write_table(args.out_dir / (filename + ".csv"), rows, ("target", "model", "status"))
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": plan["unknown_prior"],
        "stage11_reproduced": True, "raw_H5_rescan": False, "local_selection_unchanged": True,
        "monthly": [r for r in result["metrics"] if r["scope"] == "monthly"], "periods": [r for r in result["metrics"] if r["scope"] == "period"],
        "references": result["reference_metrics"], "budget_summary": result["budget_summary"], "contexts": result["contexts"]})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    save(args.out_dir / "invariants.json", result["invariants"])
    (args.out_dir / "report.md").write_text(report_text(result, cache, protocol))
    metadata.update(rows_read=0, cached_source_rows=original_run["cached_source_rows"], stage11_reproduced=True, local_selection_unchanged=True,
                    target_local_cancellation_checks=len(result["invariants"]), validation_local_cancellation_checks=len(result["invariants"]))
    finish_run(args.out_dir, metadata, started)
    print(f"INVARIANTS target_and_validation_checks={len(result['invariants'])} local_selections_unchanged=True")
    for r in result["metrics"]:
        if r["scope"] == "period" and r["period"] == "evaluation" and r["group"] in ("time_fit", "validation_constrained"):
            print(f"PERIOD {r['model']} {r['background']} {r['group']} error={number((r.get('weighted_error') or {}).get('value'))} local_pp={number((r.get('change_vs_same_background_time') or {}).get('value'),100)} total_full_time_pp={number((r.get('change_vs_full_past_time') or {}).get('value'),100)} raw_local={r.get('raw_change_vs_same_background_time','NA')} APP2={number(r.get('APP2_error'))} APP21={number(r.get('APP21_error'))} APP34={number(r.get('APP34_error'))}")
    for r in result["classes"]:
        if (r["scope"], r["period"], r["background"], r["group"], r["APP"]) == ("period", "evaluation", "full_past", "time_fit", 2):
            print(f"OUTSIDE_APP2 {r['model']} raw_change={r['wrong_change_vs_subset_same_group']} conditional_pp={number(r['conditional_change_vs_subset_same_group'],100)} vs_full_time_pp={number(r['conditional_change_vs_full_past_time'],100)}")
    for r in result["budget_summary"]:
        if r["period"] == "evaluation" and r["group"] == "validation_constrained":
            print(f"LOCAL_BUDGET {r['model']} checked={r['checked_model_months']} both_met={r['both_met']} APP21_violations={r['APP21_violations']} raw_violations={r['raw_wrong_violations']}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("prepare-dir", "monthly-dir", "refinement-dir", "hierarchy-dir", "joint-dir", "out-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if not all(path.is_dir() for path in (args.prepare_dir, args.monthly_dir, args.refinement_dir, args.hierarchy_dir, args.joint_dir)) or args.out_dir.exists():
        parser.error("completed source artifacts and a fresh output directory required")
    if args.small_n < 1:
        parser.error("positive small-n required")
    run(args)


if __name__ == "__main__":
    main()
