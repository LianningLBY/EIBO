#!/usr/bin/env python3
"""Refine only the low-IPT branch using verified stage 8 aggregate caches."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.hierarchy import FOCAL_APPS, GROUPS, run_hierarchy  # noqa: E402
from eibo.refinement import GROUPS as OLD_GROUPS, run_refinements, validate_grid  # noqa: E402
from eibo.rolling import MODELS, symbol_dictionary  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run, write_rows  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402

REFINEMENT_FILES = ("run.json", "plan_snapshot.json", "selection_protocol.json", "summary.json",
                    "monthly_atomic_counts.json", "confusion_matrices.json")
MONTHLY_FILES = ("run.json", "monthly_symbol_counts.json", "summary.json", "plan_snapshot.json")
OLD_CODE = ("scripts/methodology_real_refinement.py", "src/eibo/refinement.py", "src/eibo/monthlydrift.py",
            "src/eibo/rolling.py", "src/eibo/realexperiment.py", "src/eibo/realdata.py", "src/eibo/riskcert.py",
            "src/eibo/statcore.py", "scripts/methodology_real_reallocation.py", "scripts/methodology_real_rolling.py",
            "scripts/methodology_real_monthly.py", "scripts/methodology_real_experiment.py", "scripts/methodology_real_prepare.py")


def compare_replay(actual, expected, path="replay"):
    """Counts and schema match exactly; metric floats tolerate 1e-12 roundoff."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"stage 8 replay schema mismatch: {path}")
        for key in expected:
            compare_replay(actual[key], expected[key], path + "." + key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"stage 8 replay length mismatch: {path}")
        for index, value in enumerate(expected):
            compare_replay(actual[index], value, path + f"[{index}]")
    elif isinstance(expected, float):
        if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not np.isfinite(actual) or abs(actual - expected) > 1e-12:
            raise ValueError(f"stage 8 replay metric mismatch: {path}")
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(f"stage 8 replay value mismatch: {path}")


def validate_atoms(payload, protocol, cache):
    fields = ("symbol_id", "size_positions", "size_candidates_bytes", "IPT2_candidates_ms")
    if any(payload[field] != protocol[field] for field in fields) or payload["known_service_codes"] != cache["known"].tolist():
        raise ValueError("atomic cache protocol or fixed APP order differs")
    if payload["axis_order"] != ["size_position", "fixed_APP_order", "size_atom", "IPT2_atom_with_invalid_last"]:
        raise ValueError("unexpected atomic axis order")
    positions = tuple(protocol["size_positions"])
    shape = (len(positions), len(cache["known"]), len(protocol["size_candidates_bytes"]) + 1,
             len(protocol["IPT2_candidates_ms"]) + 2)
    if np.prod(shape) > 1000000 or set(payload["counts"]) != {item["key"] for item in cache["slices"]}:
        raise ValueError("atomic cache memory budget or monthly keys differ")
    result = {}
    for key, stored in payload["counts"].items():
        values = np.asarray(stored)
        if values.shape != shape or values.dtype.kind not in "iu" or np.any(values < 0) or np.any(values > cache["run"]["rows_read"]):
            raise ValueError(f"invalid integer atomic counts: {key}")
        values = values.astype(np.int64)
        expected = cache["counts"][key][2][:, protocol["symbol_id"]]
        if not np.all(values.sum(axis=(2, 3)) == expected[None, :]):
            raise ValueError(f"atomic counts do not conserve original cell population: {key}")
        if not np.all(values.sum(axis=2) == values[0].sum(axis=1)[None, :, :]):
            raise ValueError(f"IPT2 marginal differs across position views: {key}")
        result[key] = values
    return result


def read_refinement(directory, cache, monthly_dir):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete" or run["source_lineage"] != cache["plan"]["source"] or run["rows_read"] != cache["run"]["rows_read"]:
        raise ValueError("completed stage 8 output with identical full-scan source required")
    manifest = {item["path"]: item["sha256"] for item in run["outputs"]}
    if len(manifest) != len(run["outputs"]):
        raise ValueError("duplicate stage 8 output manifest paths")
    for name in REFINEMENT_FILES[1:]:
        if manifest.get(name) != sha256(directory / name):
            raise ValueError(f"stage 8 artifact hash mismatch: {name}")
    for relative in OLD_CODE:
        matches = [item for item in run["code"] if Path(item["path"]).name == Path(relative).name]
        if len(matches) != 1 or matches[0]["sha256"] != sha256(ROOT / relative):
            raise ValueError(f"stage 8 code lineage differs: {relative}")
    # Several stages save summary.json/run.json. Basenames alone are ambiguous.
    for name in MONTHLY_FILES:
        matches = [item for item in run["input_artifacts"]
                   if Path(item["path"]).name == name and Path(item["path"]).parent.name == monthly_dir.name]
        if len(matches) != 1 or matches[0]["sha256"] != sha256(monthly_dir / name):
            raise ValueError(f"stage 8 used different monthly inputs: {name}")
    protocol = json.loads((directory / "selection_protocol.json").read_text())
    summary = json.loads((directory / "summary.json").read_text())
    if (json.loads((directory / "plan_snapshot.json").read_text()) != cache["plan"]
            or summary["known_service_codes"] != cache["known"].tolist()
            or summary["known_priors"] != cache["priors"].tolist()
            or summary["unknown_prior"] != cache["plan"]["unknown_prior"]
            or summary["protocol"] != protocol or run["selection_protocol"] != protocol
            or summary["rows_read"] != cache["run"]["rows_read"]
            or summary["counts_reconciled"] is not True or summary["original_models_reproduced"] is not True):
        raise ValueError("stage 8 fixed plan, prior, scan or protocol differs")
    size_cuts = validate_grid(protocol["size_candidates_bytes"], integer=True)
    ipt_cuts = validate_grid(protocol["IPT2_candidates_ms"])
    positions, models = tuple(protocol["size_positions"]), protocol["models"]
    k = cache["plan"]["k"]
    if (k < 2 or not positions or any(type(p) is not int for p in positions)
            or positions != tuple(sorted(set(positions))) or min(positions) < 1 or max(positions) > k
            or not models or len(set(models)) != len(models) or any(model not in MODELS for model in models)
            or protocol["groups"] != list(OLD_GROUPS) or type(protocol["minimum_leaf_flows"]) is not int
            or protocol["minimum_leaf_flows"] < 1 or type(protocol["symbol_id"]) is not int
            or not 0 <= protocol["symbol_id"] < cache["period_counts"]["pilot"][2].shape[1]):
        raise ValueError("invalid stage 8 candidate/position/model protocol")
    if protocol["decoded"] != symbol_dictionary(k, 2)[1][protocol["symbol_id"]]:
        raise ValueError("stage 8 canonical symbol decoding differs")
    atoms = validate_atoms(json.loads((directory / "monthly_atomic_counts.json").read_text()), protocol, cache)
    invalid = int(sum(values[0, :, :, -1].sum() for values in atoms.values()))
    if invalid != summary["invalid_IPT2_cell_flows"] or invalid != run["invalid_IPT2_cell_flows"]:
        raise ValueError("stage 8 invalid-IPT count differs")
    replay = run_refinements(cache, atoms, symbol=protocol["symbol_id"], positions=positions,
                            size_cuts=size_cuts, ipt_cuts=ipt_cuts, models=models,
                            min_leaf=protocol["minimum_leaf_flows"], small_n=run["parameters"]["small_n"])
    for name in ("monthly", "periods", "selections"):
        compare_replay(summary[name], replay[name], name)
    compare_replay(json.loads((directory / "confusion_matrices.json").read_text()),
                   {"known_service_codes": cache["known"].tolist(), "matrices": replay["confusions"]}, "confusions")
    return atoms, protocol, replay


def check_baselines(result, previous):
    reference = {(row["target"], row["model"], row["group"]): row["counts_true_by_predicted"] for row in previous["confusions"]}
    mapping = {"original": "original", "ipt_split": "ipt_split", "crossed_size_ipt": "size_ipt_split"}
    for row in result["confusions"]:
        if row["group"] in mapping:
            expected = reference[(row["target"], row["model"], mapping[row["group"]])]
            if row["counts_true_by_predicted"] != expected:
                raise ValueError("hierarchy baseline confusion differs from replayed stage 8")


def write_table(path, rows, empty_fields):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    write_rows(path, [{key: row.get(key) for key in fields} for row in rows], empty_fields)


def report_text(result, cache, protocol):
    lines = ["# Low-IPT branch size refinement", "",
             f"All {len(cache['known'])} fixed known APPs and their original priors are retained. Unknown-class error is excluded. Stage 8 input hashes, joint-count projections, past-only cuts and every original confusion matrix are verified before this experiment.",
             "Only the low-IPT child is eligible for a new binary size split. High-IPT, invalid-IPT and all other original cells retain exactly their IPT-only trained decisions. No H5 rescan or new per-flow export is needed.", "",
             "## Selection and protection", "",
             "The IPT root and old crossed comparison replay the stage 8 grid, minimum leaf budget and full-class training objective. The secondary size search uses only the same past window's low-IPT flows; scores are pi_i * child_count_i / full_training_class_n_i. Its candidate positions/grid are inherited from the verified joint cache.",
             f"Both new low-branch leaves require at least {protocol['minimum_low_leaf_flows']} pooled training flows and a strictly positive overall training gain. Otherwise the model retains the IPT-only representation and decisions. Ties use ascending packet position/cut within 1e-12. An unseen low child backs off to its IPT-only parent, while high/invalid decisions remain frozen.",
             "A constant parent label can lose correct predictions only for that label's own class. Every other class is pointwise protected relative to the IPT-only model, for any target distribution. APP34 is protected when the low parent label is not 34, or no secondary split is applied. This is a structural classification property, not a population confidence bound; the former low winner may be harmed, so its losses are reported.", "",
             "## Chosen past-only low-branch cuts", "",
             "APP2 ranks/margins in the target month are evaluation diagnostics only; they never enter threshold selection. The best eligible APP2-only candidate gain is a diagnostic of this finite search, not an alternate fitted policy.", "",
             "| Target | Model | IPT2 ms | Low parent APP | Size packet | Size B | Training gain pp | APP2 train / target rank | APP34 protected | Best APP2 candidate gain pp |",
             "|---|---|---:|---:|---:|---:|---:|---|---|---:|"]
    for row in result["selections"]:
        cut = row.get("low_size_cut") or {}
        lines.append(f"| {row['target']} | {row['model']} | {number(row.get('IPT2_threshold_ms'))} | {row.get('low_branch_prediction_APP','NA')} | {cut.get('size_position','NA')} | {number(cut.get('size_threshold_bytes'))} | {number(cut.get('training_empirical_gain'),100)} | {row.get('APP2_training_rank_in_low','NA')} / {row.get('APP2_target_rank_in_low','NA')} | {row.get('APP34_pointwise_no_harm_relative_to_IPT','NA')} | {number(row.get('best_eligible_APP2_training_gain'),100)} |")
    lines += ["", "## Monthly comparisons", "",
              "Negative error changes mean improvement. Positive empirical gain means a lower target-sample Bayes functional; target labels fit only this diagnostic oracle, never a deployed model.", "",
              "| Target | Model | Group | Error % | Change vs original pp | Change vs IPT pp | Empirical gain vs IPT pp | Gap change vs IPT pp | APP2 error % | APP21 error % | APP34 error % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for row in result["monthly"]:
        lines.append(f"| {row['target']} | {row['model']} | {row['group']} | {number((row.get('weighted_error') or {}).get('value'),100)} | {number((row.get('error_change_from_original') or {}).get('value'),100)} | {number((row.get('error_change_from_IPT') or {}).get('value'),100)} | {number(row.get('empirical_gain_from_IPT'),100)} | {number(row.get('empirical_gap_change_from_IPT'),100)} | {number(row.get('APP2_error'),100)} | {number(row.get('APP21_error'),100)} | {number(row.get('APP34_error'),100)} |")
    lines += ["", "## Period classifier comparison", "",
              "Wrong counts are pooled within each class, then original priors are applied. No pooled empirical F is reported because monthly rolling cuts can differ.", "",
              "| Period | Model | Group | Error % | Change vs original pp | Change vs IPT pp | APP2 error % | APP21 error % | APP34 error % |",
              "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in result["periods"]:
        lines.append(f"| {row['period']} | {row['model']} | {row['group']} | {number((row.get('weighted_error') or {}).get('value'),100)} | {number((row.get('error_change_from_original') or {}).get('value'),100)} | {number((row.get('error_change_from_IPT') or {}).get('value'),100)} | {number(row.get('APP2_error'),100)} | {number(row.get('APP21_error'),100)} | {number(row.get('APP34_error'),100)} |")
    lines += ["", "## Low-branch competitors", "",
              "Each row shows a top-three training competitor or APP2/21/34. Scores use full-class denominators, and posteriors are known-only. Full all-class tables, including high/invalid branches, are in branch_competition.csv.", "",
              "| Target | Model | View / child | APP | Train / target child n | Train known posterior % | Target known posterior % | Trained prediction APP | Target empirical winner APP |",
              "|---|---|---|---:|---|---:|---:|---:|---:|"]
    nodes = {}
    for row in result["competition"]:
        if "<=" in row["condition"].split(";")[0]:
            nodes.setdefault((row["target"], row["model"], row["view"], row["child"]), []).append(row)
    for token, rows in nodes.items():
        leaders = sorted(rows, key=lambda r: -(r["training_known_posterior"] or 0))[:3]
        selected = {row["APP"] for row in leaders} | set(FOCAL_APPS)
        for row in rows:
            if row["APP"] in selected:
                lines.append(f"| {token[0]} | {token[1]} | {token[2]} / {token[3]} | {row['APP']} | {row['training_child_n']} / {row['target_child_n']} | {number(row['training_known_posterior'],100)} | {number(row['target_known_posterior'],100)} | {row['trained_prediction_APP']} | {row['target_empirical_winner_APP'] if row['target_empirical_winner_APP'] is not None else 'NA'} |")
    lines += ["", "## Evaluation-period improvements and harms relative to IPT", "",
              "| Model | Direction | APP | n | Status | Conditional change pp | Weighted change pp |",
              "|---|---|---:|---:|---|---:|---:|"]
    for model in protocol["models"]:
        rows = [row for row in result["period_classes"] if row["period"] == "evaluation" and row["model"] == model and row["group"] == "low_size_split" and row["weighted_change_from_IPT"] is not None]
        for sign, direction in ((-1, "improvement"), (1, "harm")):
            selected = sorted((row for row in rows if sign * row["weighted_change_from_IPT"] > 1e-15), key=lambda row: -sign * row["weighted_change_from_IPT"])
            for row in selected[:5]:
                lines.append(f"| {model} | {direction} | {row['APP']} | {row['target_n']} | {row['status']} | {number(row['conditional_change_from_IPT'],100)} | {number(row['weighted_change_from_IPT'],100)} |")
    lines += ["", "## Interpretation and evidence files", "",
              "This architecture was chosen after viewing these months. Past-only threshold fitting prevents direct target-label selection, but this remains exploratory reuse of the same evaluation data. No significance test, independent temporal units, population risk floor or confirmatory claim is produced.",
              "Missing training classes make a window unavailable. Missing target classes retain their original priors and classification identification ranges; complete-class empirical F/gain is NA. Small-n is a reporting flag only. Negative signed class contributions are possible even when the total empirical representation gain is nonnegative.",
              "For the hierarchical model, monthly error_change_from_IPT = -empirical_gain_from_IPT + empirical_gap_change_from_IPT. A zero APP2 improvement may mean the available binary size split cannot make APP2 win against all classes; branch competition and candidate scores should be read before proposing additional features.",
              "low_threshold_selections.csv and low_threshold_candidates.csv record every choice, training month, score and diagnostic. class_metrics.csv records all classes and exact rescued/harmed flow counts; period_class_metrics.csv, monthly_summary.csv and period_summary.csv retain full metrics. confusion_matrices.json preserves full confusion counts. run.json records input/code/output hashes; selection_protocol.json and plan_snapshot.json preserve the experiment definition.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    if min(args.min_leaf_flows, args.small_n) < 1:
        raise ValueError("positive leaf and small-n budgets required")
    print("Verifying stage 5/8 hashes, complete-class atom counts and deterministic stage 8 replay...", flush=True)
    cache = read_cache(args.monthly_dir)
    atoms, previous_protocol, replay = read_refinement(args.refinement_dir, cache, args.monthly_dir)
    protocol = {"symbol_id": previous_protocol["symbol_id"], "decoded": previous_protocol["decoded"],
                "size_positions": previous_protocol["size_positions"], "size_candidates_bytes": previous_protocol["size_candidates_bytes"],
                "IPT2_candidates_ms": previous_protocol["IPT2_candidates_ms"], "models": previous_protocol["models"], "groups": list(GROUPS),
                "minimum_root_leaf_flows": previous_protocol["minimum_leaf_flows"], "minimum_low_leaf_flows": args.min_leaf_flows,
                "selection": "strictly positive full-known-class past training gain within low-IPT branch only",
                "frozen": "high-IPT/invalid-IPT branches and other original cells retain IPT-only decisions",
                "unseen_low_child": "back off to IPT-only parent prediction", "tie_break": "ascending packet position/cut, tolerance 1e-12",
                "status": "exploratory family chosen after earlier evaluation", "raw_H5_rescan": False}
    inputs = ([args.monthly_dir / name for name in MONTHLY_FILES] + [args.refinement_dir / name for name in REFINEMENT_FILES])
    metadata = start_run(args, inputs=inputs, code=[Path(__file__), ROOT / "src/eibo/hierarchy.py"] + [ROOT / name for name in OLD_CODE], source=cache["plan"]["source"])
    save(args.out_dir / "selection_protocol.json", protocol)
    save(args.out_dir / "plan_snapshot.json", cache["plan"])
    print("Stage 8 replay verified. Selecting low-branch size cuts from past months only...", flush=True)
    result = run_hierarchy(cache, atoms, positions=tuple(protocol["size_positions"]), size_cuts=protocol["size_candidates_bytes"],
                           ipt_cuts=protocol["IPT2_candidates_ms"], symbol=protocol["symbol_id"], root_min_leaf=protocol["minimum_root_leaf_flows"],
                           min_leaf=args.min_leaf_flows, small_n=args.small_n, models=protocol["models"],
                           progress=lambda key: print(f"Scored hierarchy and baselines: {key}", flush=True))
    check_baselines(result, replay)
    save(args.out_dir / "summary.json", {"status": protocol["status"], "known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(),
         "unknown_prior": cache["plan"]["unknown_prior"], "protocol": protocol, "stage8_reproduced": True, "baseline_confusions_reproduced": True,
         "counts_reconciled": True, "high_invalid_decisions_frozen": True, "raw_H5_rescan": False,
         "monthly": result["monthly"], "periods": result["periods"], "selections": result["selections"]})
    save(args.out_dir / "confusion_matrices.json", {"known_service_codes": cache["known"].tolist(), "matrices": result["confusions"]}, compact=True)
    for filename, collection in (("class_metrics", "classes"), ("period_class_metrics", "period_classes"), ("branch_competition", "competition"), ("low_threshold_candidates", "candidates")):
        write_table(args.out_dir / (filename + ".csv"), result[collection], ("target", "model", "APP", "status"))
    selections = []
    for row in result["selections"]:
        cut = row.get("low_size_cut") or {}
        selections.append({**{key: value for key, value in row.items() if key not in ("low_size_cut", "training_slices", "pointwise_no_harm_APPs_relative_to_IPT")},
                           "training_slices": ";".join(row["training_slices"]), "size_position": cut.get("size_position"),
                           "size_threshold_bytes": cut.get("size_threshold_bytes"), "training_empirical_gain": cut.get("training_empirical_gain"),
                           "new_child_predictions_APP": ";".join(map(str, cut.get("child_predictions_APP", []))),
                           "pointwise_no_harm_APPs_relative_to_IPT": ";".join(map(str, row.get("pointwise_no_harm_APPs_relative_to_IPT", [])))})
    write_table(args.out_dir / "low_threshold_selections.csv", selections, ("target", "model", "status"))
    for filename, collection in (("monthly_summary", "monthly"), ("period_summary", "periods")):
        rows = []
        for row in result[collection]:
            flat = {key: value for key, value in row.items() if not isinstance(value, dict)}
            for field in ("weighted_error", "error_change_from_original", "error_change_from_IPT"):
                value = row.get(field) or {}
                bounds = value.get("range_from_unobserved_values", [None, None])
                flat.update({field: value.get("value"), field + "_observed": value.get("observed_contribution"),
                             field + "_range_min": bounds[0], field + "_range_max": bounds[1]})
            rows.append(flat)
        write_table(args.out_dir / (filename + ".csv"), rows, ("target", "model", "group", "status"))
    (args.out_dir / "report.md").write_text(report_text(result, cache, protocol))
    metadata.update({"rows_read": 0, "cached_source_rows": cache["run"]["rows_read"], "stage8_reproduced": True,
                     "baseline_confusions_reproduced": True, "high_invalid_decisions_frozen": True, "selection_protocol": protocol})
    finish_run(args.out_dir, metadata, started)
    for row in result["selections"]:
        cut = row.get("low_size_cut") or {}
        print(f"CUT {row['target']} {row['model']} IPT2_ms={row.get('IPT2_threshold_ms','NA')} low_parent_APP={row.get('low_branch_prediction_APP','NA')} size_packet={cut.get('size_position','NA')} size_B={cut.get('size_threshold_bytes','NA')} APP2_rank_train/target={row.get('APP2_training_rank_in_low','NA')}/{row.get('APP2_target_rank_in_low','NA')} APP34_protected={row.get('APP34_pointwise_no_harm_relative_to_IPT','NA')}")
    for row in result["periods"]:
        print(f"PERIOD {row['period']} {row['model']} {row['group']} error={number((row.get('weighted_error') or {}).get('value'))} delta_original_pp={number((row.get('error_change_from_original') or {}).get('value'),100)} delta_IPT_pp={number((row.get('error_change_from_IPT') or {}).get('value'),100)} APP2={number(row.get('APP2_error'))} APP21={number(row.get('APP21_error'))} APP34={number(row.get('APP34_error'))}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("monthly-dir", "refinement-dir", "out-dir"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--min-leaf-flows", type=int, default=200)
    parser.add_argument("--small-n", type=int, default=200)
    args = parser.parse_args()
    if not args.monthly_dir.is_dir() or not args.refinement_dir.is_dir() or args.out_dir.exists():
        parser.error("completed monthly/refinement inputs and a fresh output directory required")
    if min(args.min_leaf_flows, args.small_n) < 1:
        parser.error("positive leaf and small-n budgets required")
    run(args)


if __name__ == "__main__":
    main()
