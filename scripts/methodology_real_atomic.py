#!/usr/bin/env python3
"""Diagnose fine low-IPT atoms and monthly hierarchy tradeoffs from caches."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.atomicdiagnostic import FOCAL_APPS, attribute_hierarchy, run_atomic_diagnostic  # noqa: E402
from eibo.hierarchy import run_hierarchy  # noqa: E402
from eibo.rolling import training_window  # noqa: E402
from methodology_real_hierarchy import (MONTHLY_FILES, OLD_CODE, REFINEMENT_FILES, compare_replay,
                                        read_refinement, write_table)  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

HIERARCHY_FILES = ("run.json", "summary.json", "selection_protocol.json", "plan_snapshot.json", "confusion_matrices.json")
HIERARCHY_CODE = OLD_CODE + ("scripts/methodology_real_hierarchy.py", "src/eibo/hierarchy.py")


def read_hierarchy(directory, cache, atoms, prior_protocol, monthly_dir, refinement_dir):
    run = json.loads((directory / "run.json").read_text())
    if (run["status"] != "complete" or run["source_lineage"] != cache["plan"]["source"]
            or run["rows_read"] != 0 or run["cached_source_rows"] != cache["run"]["rows_read"]):
        raise ValueError("completed cache-only hierarchy with identical source required")
    outputs = {item["path"]: item["sha256"] for item in run["outputs"]}
    if len(outputs) != len(run["outputs"]):
        raise ValueError("duplicate hierarchy output manifest paths")
    for name in HIERARCHY_FILES[1:]:
        if outputs.get(name) != sha256(directory / name):
            raise ValueError(f"hierarchy artifact hash mismatch: {name}")
    for relative in HIERARCHY_CODE:
        matches = [item for item in run["code"] if Path(item["path"]).name == Path(relative).name]
        if len(matches) != 1 or matches[0]["sha256"] != sha256(ROOT / relative):
            raise ValueError(f"hierarchy code lineage differs: {relative}")
    for source, names in ((monthly_dir, MONTHLY_FILES), (refinement_dir, REFINEMENT_FILES)):
        for name in names:
            matches = [item for item in run["input_artifacts"] if Path(item["path"]).name == name and Path(item["path"]).parent.name == source.name]
            if len(matches) != 1 or matches[0]["sha256"] != sha256(source / name):
                raise ValueError(f"hierarchy used different inputs: {source.name}/{name}")
    summary = json.loads((directory / "summary.json").read_text())
    protocol = json.loads((directory / "selection_protocol.json").read_text())
    if (summary["known_service_codes"] != cache["known"].tolist() or summary["known_priors"] != cache["priors"].tolist()
            or summary["unknown_prior"] != cache["plan"]["unknown_prior"] or summary["protocol"] != protocol
            or run["selection_protocol"] != protocol or json.loads((directory / "plan_snapshot.json").read_text()) != cache["plan"]
            or any(summary[field] is not True for field in ("stage8_reproduced", "baseline_confusions_reproduced", "counts_reconciled", "high_invalid_decisions_frozen"))
            or summary["raw_H5_rescan"] is not False):
        raise ValueError("hierarchy plan, class order, prior or completed checks differ")
    for field in ("symbol_id", "decoded", "size_positions", "size_candidates_bytes", "IPT2_candidates_ms", "models"):
        if protocol[field] != prior_protocol[field]:
            raise ValueError("hierarchy/refinement protocols differ")
    if (protocol["minimum_root_leaf_flows"] != prior_protocol["minimum_leaf_flows"]
            or type(protocol["minimum_low_leaf_flows"]) is not int or protocol["minimum_low_leaf_flows"] < 1
            or run["parameters"]["min_leaf_flows"] != protocol["minimum_low_leaf_flows"]):
        raise ValueError("hierarchy leaf protocol differs")
    replay = run_hierarchy(cache, atoms, positions=tuple(protocol["size_positions"]), size_cuts=protocol["size_candidates_bytes"],
                           ipt_cuts=protocol["IPT2_candidates_ms"], symbol=protocol["symbol_id"], root_min_leaf=protocol["minimum_root_leaf_flows"],
                           min_leaf=protocol["minimum_low_leaf_flows"], small_n=run["parameters"]["small_n"], models=protocol["models"])
    for field in ("monthly", "periods", "selections"):
        compare_replay(summary[field], replay[field], "hierarchy." + field)
    compare_replay(json.loads((directory / "confusion_matrices.json").read_text()),
                   {"known_service_codes": cache["known"].tolist(), "matrices": replay["confusions"]}, "hierarchy.confusions")
    return replay


def candidate_precision(cache, previous):
    rows = []
    for selected in previous["selections"]:
        target, model = selected["target"], selected["model"]
        candidates = [r for r in previous["candidates"] if r["target"] == target and r["model"] == model and r["eligible"] and r["APP2_training_weighted_gain"] is not None]
        value = max((r["APP2_training_weighted_gain"] for r in candidates), default=None)
        if value != selected.get("best_eligible_APP2_training_gain"):
            raise RuntimeError("unrounded binary candidate maximum differs from hierarchy selection")
        change = None
        if value is not None:
            item = next(item for item in cache["slices"] if item["key"] == target)
            i = int(np.flatnonzero(cache["known"] == 2)[0])
            ns = training_window(cache, item, model)["sample_counts"][i]
            change = int(round(value * ns / cache["priors"][i]))
        rows.append({"target": target, "model": model, "status": selected["status"], "eligible_candidates": len(candidates),
                     "APP2_positive_candidates": sum(r["APP2_training_weighted_gain"] > 0 for r in candidates),
                     "max_APP2_training_weighted_gain": value, "max_gain_pp_17digits": format(value * 100, ".17g") if value is not None else None,
                     "maximum_is_exact_zero": value == 0 if value is not None else None, "max_APP2_training_correct_change_count": change})
    return rows


def report_text(result, attribution, precision, cache, protocol):
    lines = ["# Fine low-IPT atom diagnostics and monthly hierarchy attribution", "",
             f"All {len(cache['known'])} fixed known APPs and original priors are retained. Unknown-class error is excluded. Completed stage 8 and 9 outputs, input/code hashes, atom projections and deterministic replay are verified. No H5 rescan is used.", "",
             "## Unrounded binary candidate audit", "",
             "Exact-zero flags distinguish an actual zero from a small value hidden by the previous five-decimal percentage-point display. The candidate family and objective are unchanged; these rows fit no alternate APP2 policy.", "",
             "| Target | Model | Eligible candidates | APP2 positive candidates | Maximum APP2 gain pp (17 digits) | Exact zero | Best APP2 correct-count change |",
             "|---|---|---:|---:|---:|---|---:|"]
    for r in precision:
        lines.append(f"| {r['target']} | {r['model']} | {r['eligible_candidates']} | {r['APP2_positive_candidates']} | {r['max_gain_pp_17digits'] if r['max_gain_pp_17digits'] is not None else 'NA'} | {r['maximum_is_exact_zero']} | {r['max_APP2_training_correct_change_count']} |")
    lines += ["", "## Past-only atomic selection", "",
              f"Within each past-selected low-IPT branch, one packet position exposes every saved size x valid-IPT atom. Training atoms with fewer than {protocol['minimum_atom_training_flows']} pooled flows back off to the IPT parent; no target flow is removed. High-IPT, invalid-IPT and other cells keep their IPT-only decisions.",
              "Each position is evaluated for diagnostics. The fitted position maximizes full-class past training gain only, with ascending-position ties and identity on zero gain. Target empirical winners never choose the position. The cache contains single-position size/IPT joints, not joints among several packet lengths.", "",
              "| Target | Model | Training slices | Last training end | Target start | Selected packet | Training gain pp |",
              "|---|---|---|---:|---:|---:|---:|"]
    for r in result["choices"]:
        lines.append(f"| {r['target']} | {r['model']} | {', '.join(r['training_slices'])} | {r.get('last_training_end_epoch','NA')} | {r.get('target_start_epoch','NA')} | {r.get('selected_size_position') if r.get('selected_size_position') is not None else 'identity'} | {number(r.get('training_gain_vs_IPT'),100)} |")
    lines += ["", "## Selected atomic monthly diagnostics", "",
              "The target empirical oracle may change only low-branch decisions. Root adaptation gain changes the coarse low winner; representation gain compares coarse and fine target oracles; regret compares the past-fitted atomic model with the fine oracle. Error change = -(root adaptation gain + representation gain) + regret. Regret = unguarded past regret + signed training-flow guard change; the guard may help or hurt future classification. These are sample diagnostics, not population bounds or independent holdout results.", "",
              "| Target | Model | Packet | Error change vs IPT pp | Raw error-count change | Root adaptation gain pp | Representation gain pp | Atomic regret pp | Guard change pp | APP2 change pp | APP2 oracle change pp | Backoff target flows |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in result["monthly"]:
        if r["group"] == "selected_atomic":
            lines.append(f"| {r['target']} | {r['model']} | {r.get('size_position') if r.get('size_position') is not None else 'identity'} | {number((r.get('error_change_vs_IPT') or {}).get('value'),100)} | {r.get('raw_error_change_count_vs_IPT','NA')} | {number(r.get('root_adaptation_gain'),100)} | {number(r.get('empirical_representation_gain'),100)} | {number(r.get('past_model_regret_to_atomic_oracle'),100)} | {number((r.get('guard_error_change') or {}).get('value'),100)} | {number(r.get('APP2_change_vs_IPT'),100)} | {number(r.get('APP2_atomic_oracle_change_vs_IPT'),100)} | {r.get('backoff_target_flows','NA')} |")
    lines += ["", "## APP2 winning atoms by position", "",
              "Counts distinguish an unconstrained past winner, a prediction retained after the training-flow guard, and a target empirical winner. The same flow appears in each packet-position view; do not sum counts across positions. Full intervals, rivals, unrounded scores and margins are in APP2_atomic_cells.csv.", "",
              "| Target | Model | Packet | APP2 train-winning atoms | Retained APP2 predicted atoms | APP2 target-winning atoms | APP2 target flows in trained APP2 atoms | APP2 target flows in oracle APP2 atoms |",
              "|---|---|---:|---:|---:|---:|---:|---:|"]
    nodes = {}
    for r in result["APP2_cells"]:
        nodes.setdefault((r["target"], r["model"], r["size_position"]), []).append(r)
    for key, rows in nodes.items():
        future = None if not all(r["target_population_complete"] for r in rows) else sum(r["target_APP2_winner"] is True for r in rows)
        lines.append(f"| {key[0]} | {key[1]} | {key[2]} | {sum(r['training_APP2_winner'] for r in rows)} | {sum(r['trained_prediction_APP'] == 2 for r in rows)} | {future if future is not None else 'NA'} | {sum(r['APP2_target_flows'] for r in rows if r['trained_prediction_APP'] == 2)} | {sum(r['APP2_target_flows'] for r in rows if r['target_APP2_winner'] is True) if future is not None else 'NA'} |")
    lines += ["", "## Selected atomic period comparison", "",
              "Period errors pool integer wrong counts within each class before fixed-prior weighting. No pooled oracle/representation gain is reported: root cuts and packet positions can change by month.", "",
              "| Period | Model | Group | Weighted error % | Change vs IPT pp | Raw error-count change | APP2 error % | APP21 error % | APP34 error % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|"]
    for r in result["periods"]:
        lines.append(f"| {r['period']} | {r['model']} | {r['group']} | {number((r.get('weighted_error') or {}).get('value'),100)} | {number((r.get('error_change_vs_IPT') or {}).get('value'),100)} | {r.get('raw_error_change_count_vs_IPT','NA')} | {number(r.get('APP2_error'),100)} | {number(r.get('APP21_error'),100)} | {number(r.get('APP34_error'),100)} |")
    lines += ["", "## Previous hierarchy monthly focal attribution", "",
              "These rows replay stage 9, not the new atomic model. Positive changes mean harm; raw wrong change = harmed - rescued. Small-n is a flag, not a filter.", "",
              "| Target | Model | APP | n | Status | Rescued | Harmed | Raw wrong change | Conditional change pp | Weighted change pp |",
              "|---|---|---:|---:|---|---:|---:|---:|---:|---:|"]
    for r in attribution["classes"]:
        if r["scope"] == "monthly" and r["APP"] in (15, 21, 22):
            lines.append(f"| {r['target']} | {r['model']} | {r['APP']} | {r['n']} | {r['status']} | {r['rescued']} | {r['harmed']} | {r['raw_wrong_change']} | {number(r['conditional_change'],100)} | {number(r['weighted_change'],100)} |")
    lines += ["", "## Previous hierarchy aggregate tradeoffs", "",
              "| Scope | Target | Model | Weighted change pp | Raw wrong change | Rescued | Harmed |",
              "|---|---|---|---:|---:|---:|---:|"]
    for r in attribution["summary"]:
        lines.append(f"| {r['scope']} | {r['target']} | {r['model']} | {number((r.get('weighted_change') or {}).get('value'),100)} | {r['raw_error_change_count']} | {r.get('raw_rescued','NA')} | {r.get('raw_harmed','NA')} |")
    lines += ["", "## Interpretation and scope", "",
              "All positions' metrics remain in atomic_monthly.csv, including choices not selected for fitting. APP2_atomic_cells.csv identifies whether fine atoms can make APP2 win in the past, only in the target, or only below the training-flow budget. Training/backoff and target winners must be distinguished before adding features.",
              "The target oracle is a finite-cache empirical comparator, not an upper bound on achievable population accuracy. Fine sparse cells can make its apparent gain optimistic. No target metrics enter training selection; the family itself is motivated by prior inspection of these evaluation months and remains exploratory.",
              "Missing training classes make a window unavailable. Missing target classes retain their original priors and classification identification ranges; complete-class oracle metrics are NA. All class orders and priors remain fixed. Monthly caches cannot establish daily/session concentration or independent temporal units; those questions require finer aggregates or a new raw-data audit.", ""]
    return "\n".join(lines)


def flat_metrics(rows):
    result = []
    for row in rows:
        flat = {key: value for key, value in row.items() if not isinstance(value, dict)}
        for key, value in row.items():
            if isinstance(value, dict):
                bounds = value.get("range_from_unobserved_values", [None, None])
                flat.update({key: value.get("value"), key + "_observed": value.get("observed_contribution"), key + "_range_min": bounds[0], key + "_range_max": bounds[1]})
        result.append(flat)
    return result


def run(args):
    started = time.monotonic()
    if min(args.min_atom_flows, args.small_n) < 1:
        raise ValueError("positive atomic-flow and small-n budgets required")
    print("Verifying stage 5/8/9 lineage and deterministic cache replay...", flush=True)
    cache = read_cache(args.monthly_dir)
    atoms, prior_protocol, _ = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    previous = read_hierarchy(args.hierarchy_dir, cache, atoms, prior_protocol, args.monthly_dir, args.refinement_dir)
    protocol = {"symbol_id": prior_protocol["symbol_id"], "size_positions": prior_protocol["size_positions"],
                "size_candidates_bytes": prior_protocol["size_candidates_bytes"], "IPT2_candidates_ms": prior_protocol["IPT2_candidates_ms"],
                "minimum_atom_training_flows": args.min_atom_flows, "models": prior_protocol["models"],
                "selection": "positive full-class past training gain; ascending-position ties; identity on zero gain",
                "oracle": "target empirical low-branch decisions only; frozen high/invalid/outside decisions; never selects a model",
                "cache_scope": "one packet-size position x IPT2 atoms; no multi-position joint reconstruction", "status": "exploratory reused-month diagnostics"}
    inputs = [directory / name for directory, names in ((args.monthly_dir, MONTHLY_FILES), (args.refinement_dir, REFINEMENT_FILES), (args.hierarchy_dir, HIERARCHY_FILES)) for name in names]
    metadata = start_run(args, inputs=inputs, code=[Path(__file__), ROOT / "src/eibo/atomicdiagnostic.py"] + [ROOT / path for path in HIERARCHY_CODE], source=cache["plan"]["source"])
    save(args.out_dir / "selection_protocol.json", protocol)
    save(args.out_dir / "plan_snapshot.json", cache["plan"])
    precision = candidate_precision(cache, previous)
    attribution = attribute_hierarchy(cache, previous, small_n=args.small_n)
    result = run_atomic_diagnostic(cache, atoms, prior_protocol, minimum=args.min_atom_flows, small_n=args.small_n,
                                   progress=lambda key: print(f"Scored fine atomic diagnostics: {key}", flush=True))
    old_root = {(r["target"], r["model"]): r["counts_true_by_predicted"] for r in previous["confusions"] if r["group"] == "ipt_split"}
    for row in result["confusions"]:
        if row["group"] == "ipt_split" and row["counts_true_by_predicted"] != old_root[(row["target"], row["model"])]:
            raise RuntimeError("atomic baseline differs from hierarchy replay")
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": cache["plan"]["unknown_prior"],
         "protocol": protocol, "stage8_stage9_reproduced": True, "counts_reconciled": True, "raw_H5_rescan": False,
         "binary_precision": precision, "monthly": result["monthly"], "periods": result["periods"], "choices": result["choices"], "hierarchy_attribution": attribution["summary"]})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    tables = (("binary_candidate_precision", precision), ("atomic_monthly", flat_metrics(result["monthly"])), ("atomic_periods", flat_metrics(result["periods"])),
              ("atomic_monthly_classes", result["monthly_classes"]), ("atomic_period_classes", result["period_classes"]), ("APP2_atomic_cells", result["APP2_cells"]), ("hierarchy_attribution", attribution["classes"]),
              ("hierarchy_attribution_summary", flat_metrics(attribution["summary"])))
    for filename, rows in tables:
        write_table(args.out_dir / (filename + ".csv"), rows, ("target", "model", "status"))
    write_table(args.out_dir / "atomic_selections.csv", [{**row, "training_slices": ";".join(row["training_slices"])} for row in result["choices"]], ("target", "model", "status"))
    (args.out_dir / "report.md").write_text(report_text(result, attribution, precision, cache, protocol))
    metadata.update({"rows_read": 0, "cached_source_rows": cache["run"]["rows_read"], "stage8_stage9_reproduced": True, "selection_protocol": protocol})
    finish_run(args.out_dir, metadata, started)
    for row in precision:
        print(f"BINARY {row['target']} {row['model']} exact_zero={row['maximum_is_exact_zero']} APP2_gain_pp={row['max_gain_pp_17digits']} APP2_positive_candidates={row['APP2_positive_candidates']}")
    for row in result["periods"]:
        if row["group"] == "selected_atomic":
            print(f"ATOMIC {row['period']} {row['model']} error={number((row.get('weighted_error') or {}).get('value'))} delta_IPT_pp={number((row.get('error_change_vs_IPT') or {}).get('value'),100)} raw_wrong_change={row.get('raw_error_change_count_vs_IPT')} APP2={number(row.get('APP2_error'))} APP21={number(row.get('APP21_error'))} APP34={number(row.get('APP34_error'))}")
    for row in attribution["summary"]:
        if row["scope"] == "period":
            print(f"HIERARCHY {row['target']} {row['model']} weighted_delta_pp={number((row.get('weighted_change') or {}).get('value'),100)} raw_wrong_change={row['raw_error_change_count']} rescued={row.get('raw_rescued')} harmed={row.get('raw_harmed')}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("monthly-dir", "refinement-dir", "hierarchy-dir", "out-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--min-atom-flows", type=int, default=200)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if not all(path.is_dir() for path in (args.monthly_dir, args.refinement_dir, args.hierarchy_dir)) or args.out_dir.exists():
        parser.error("completed cache inputs and a fresh output directory required")
    if min(args.min_atom_flows, args.small_n) < 1:
        parser.error("positive budgets required")
    run(args)


if __name__ == "__main__":
    main()
