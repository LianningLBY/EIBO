"""Past-only block checks for frozen local refinements of a common baseline."""

from __future__ import annotations

import copy
import itertools

import numpy as np

from .jointrefinement import choose_rule, fit_candidates, low_marginals, root_model, rule_evaluation, time_children
from .monthlydrift import optional, weighted_range
from .regionalvalidation import collapse_role, matrix_result, signed_rates, splice_background

GROUPS = ("time_baseline", "original_pooled", "block_pooled", "block_constraints", "block_minimax")
FIELDS = ("base", "children", "single", "joint")


def block_windows(windows, *, blocks=3, rounding=3600):
    """Split each old validation interval by dates, never by labels or counts."""
    if blocks < 2 or rounding < 0:
        raise ValueError("at least two blocks and nonnegative timestamp rounding required")
    result = copy.deepcopy(windows)
    bounds_to_id = {(r["start_epoch"], r["end_epoch"]): r["id"] for r in result["ranges"]}
    for context in result["contexts"]:
        if "validation_id" not in context:
            continue
        begin, end = context["validation_start_epoch"], context["validation_end_epoch"]
        edges = [begin + (end - begin) * i // blocks for i in range(blocks + 1)]
        if min(np.diff(edges)) <= rounding:
            raise ValueError("validation blocks must exceed the timestamp rounding guard")
        if context["fit_end_epoch"] > begin or end > context["target_start_epoch"]:
            raise ValueError("fit, validation and target chronology overlaps")
        ids = []
        for left, right in zip(edges[:-1], edges[1:]):
            if (left, right) not in bounds_to_id:
                token = "b" + str(len(bounds_to_id))
                bounds_to_id[left, right] = token
                result["ranges"].append({"id": token, "start_epoch": left, "end_epoch": right})
            ids.append(bounds_to_id[left, right])
        context["block_ids"] = ids
    result.update(validation_blocks=blocks, block_boundary_rule="equal duration; whole-flow containment with inherited rounding guard")
    return result


def sum_roles(roles):
    return {field: sum((r[field] for r in roles), np.zeros_like(roles[0][field])) for field in FIELDS}


def reconcile_blocks(roles, previous_roles, windows):
    """Verify unchanged old roles and disjoint-block subsets in every atom."""
    for token, previous in previous_roles.items():
        for field in FIELDS:
            if not np.array_equal(roles[token][field], previous[field]):
                raise ValueError("new scan differs from an original fit/validation role")
    rows = []
    for context in windows["contexts"]:
        if "block_ids" not in context:
            continue
        parent = roles[context["validation_id"]]
        union = sum_roles([roles[token] for token in context["block_ids"]])
        for field in FIELDS:
            if np.any(union[field] > parent[field]):
                raise ValueError("validation blocks overlap or escape the parent population")
        rows.append({"target": context["target"], "model": context["model"],
                     "parent_n": parent["base"].sum(axis=1).tolist(), "union_n": union["base"].sum(axis=1).tolist(),
                     "boundary_excluded_n": (parent["base"] - union["base"]).sum(axis=1).tolist()})
    return rows


def budget_ok(row, app21_present, app21_budget, raw_budget):
    value = row["APP21_validation_conditional_change"]
    return bool(row["validation_complete"] and row["validation_raw_wrong_change"] <= raw_budget
                and (not app21_present or value is not None and value <= app21_budget + 1e-12))


def choose_block_rule(candidates, block_scores, mode, *, protected_parent=False, app21_present=True, app21_budget=.001, raw_budget=0):
    """All-block constraints are empirical checks, not a future-risk guarantee."""
    if mode not in ("block_constraints", "block_minimax") or not block_scores:
        raise ValueError("a known block selector and nonempty block scores required")
    if protected_parent:
        return None, "identity_APP34_parent_protection"
    if any(not rows or not rows[0]["validation_complete"] for rows in block_scores):
        return None, "identity_missing_block_classes"
    best, gain = None, 0.
    for index, candidate in enumerate(candidates):
        if not candidate["eligible"]:
            continue
        checks = [rows[index] for rows in block_scores]
        if not all(budget_ok(row, app21_present, app21_budget, raw_budget) for row in checks):
            continue
        # Equal block consideration avoids letting the largest block hide a bad block.
        value = -candidate["validation_weighted_change"] if mode == "block_constraints" else min(-row["validation_weighted_change"] for row in checks)
        if value > gain + 1e-12 or (best is not None and value > 1e-12 and abs(value - gain) <= 1e-12
                and (candidate["observed_fit_leaves"], candidate["candidate_id"]) < (best["observed_fit_leaves"], best["candidate_id"])):
            best, gain = candidate, value
    return best, "selected" if best is not None else "identity_no_positive_block_qualified_gain"


def select_rules(roles, collection, protocol, original_selections):
    """No target histograms or target errors are accepted by this interface."""
    known, priors = np.asarray(collection["known_service_codes"]), np.asarray(collection["known_priors"])
    positions, pairs = tuple(collection["size_positions"]), tuple(map(tuple, collection["size_pairs"]))
    symbol, cuts = collection["symbol_id"], collection["size_candidates_bytes"]
    minimum = protocol["minimum_fit_leaf_flows"]
    kwargs = {"app21_present": bool(21 in known), "app21_budget": protocol["APP21_validation_budget_pp"] / 100,
              "raw_budget": protocol["maximum_validation_raw_wrong_increase"]}
    original = {(r["target"], r["model"]): r for r in original_selections if r["group"] == "validation_constrained"}
    selections, candidates, validation, coverage, reused = [], [], [], [], {}
    for context in collection["window_spec"]["contexts"]:
        common = {key: context[key] for key in ("target", "period", "model")}
        if context["status"] != "ready" or "fit_id" not in context or np.any(roles[context["fit_id"]]["base"].sum(axis=1) == 0):
            selections.extend({**common, "group": group, "status": "unavailable_fit_model", "rule": None} for group in GROUPS)
            continue
        fit = collapse_role(roles[context["fit_id"]], positions, pairs)
        prediction, leaves = root_model(fit["base"], fit["children"], priors, symbol)
        old = int(prediction[leaves[0]])
        protected = int(known[old]) == 34
        token = (context["fit_id"], context["validation_id"], tuple(context["block_ids"]))
        if token not in reused:
            raw_blocks = [roles[key] for key in context["block_ids"]]
            views = [roles[context["validation_id"]], sum_roles(raw_blocks)] + raw_blocks
            scores = [fit_candidates(fit, collapse_role(view, positions, pairs), priors, known, old, positions, pairs, cuts, minimum=minimum) for view in views]
            for rows in scores[1:]:
                if len(rows) != len(scores[0]) or any((r["candidate_id"], r["prediction_indices"], r["eligible"]) !=
                        (s["candidate_id"], s["prediction_indices"], s["eligible"]) for r, s in zip(rows, scores[0])):
                    raise RuntimeError("validation data altered fitting labels or eligibility")
            reused[token] = views, scores
        views, scores = reused[token]
        original_rows, union_rows, block_rows = scores[0], scores[1], scores[2:]
        names = ["original_validation", "block_union"] + context["block_ids"]
        for name, view in zip(names, views):
            ns = view["base"].sum(axis=1)
            coverage.extend({**common, "view": name, "APP": int(app), "n": int(ns[i]), "prior": float(priors[i]), "missing": bool(ns[i] == 0)} for i, app in enumerate(known))
        choices = {"time_baseline": (None, "identity_baseline")}
        for group, rows in (("original_pooled", original_rows), ("block_pooled", union_rows)):
            choices[group] = choose_rule(rows, "validation_constrained", protected_parent=protected, **kwargs)
        prior = original.get((context["target"], context["model"]))
        if prior is None or choices["original_pooled"][0] != prior["rule"]:
            raise RuntimeError("original pooled choice does not replay stage 11")
        for group in GROUPS[3:]:
            choices[group] = choose_block_rule(union_rows, block_rows, group, protected_parent=protected, **kwargs)
        for index, candidate in enumerate(union_rows):
            checks = [rows[index] for rows in block_rows]
            candidates.append({**common, **candidate,
                "all_blocks_complete": all(row["validation_complete"] for row in checks),
                "all_blocks_budget_met": all(budget_ok(row, **kwargs) for row in checks),
                "worst_block_weighted_change": max(r["validation_weighted_change"] for r in checks) if all(r["validation_complete"] for r in checks) else None,
                "block_weighted_changes": [row["validation_weighted_change"] for row in checks],
                "block_APP21_changes": [row["APP21_validation_conditional_change"] for row in checks],
                "block_raw_changes": [row["validation_raw_wrong_change"] for row in checks]})
        for group, (rule, status) in choices.items():
            selections.append({**common, "group": group, "status": status, "rule": rule, "low_parent_APP": int(known[old]),
                "fit_id": context["fit_id"], "validation_id": context["validation_id"], "block_ids": context["block_ids"],
                "fit_end_epoch": context["fit_end_epoch"], "validation_end_epoch": context["validation_end_epoch"], "target_start_epoch": context["target_start_epoch"]})
            for name, rows in zip(names, scores):
                row = rows[rule["candidate_id"]] if rule is not None else None
                validation.append({**common, "group": group, "view": name, "identity": rule is None,
                    "complete": rows[0]["validation_complete"] if rows else False,
                    "weighted_change": row["validation_weighted_change"] if row else 0.,
                    "raw_wrong_change": row["validation_raw_wrong_change"] if row else 0,
                    "APP21_change": row["APP21_validation_conditional_change"] if row else 0. if 21 in known else None})
    return {"selections": selections, "candidates": candidates, "validation": validation, "coverage": coverage}


def evaluate_rules(cache, roles, joints, atoms, collection, protocol, selected, original_replay, *, small_n=200):
    known, priors = cache["known"], cache["priors"]
    positions, pairs = tuple(collection["size_positions"]), tuple(map(tuple, collection["size_pairs"]))
    symbol, cuts, threshold = collection["symbol_id"], collection["IPT2_candidates_ms"], collection["fixed_IPT2_threshold_ms"]
    choices = {(r["target"], r["model"], r["group"]): r for r in selected["selections"]}
    previous = {(r["target"], r["model"], r["group"]): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in original_replay["confusions"]}
    evaluations, transfers, confusions, budget_rows, checks = {}, {}, [], [], []
    for context in collection["window_spec"]["contexts"]:
        key, model = context["target"], context["model"]
        if choices[key, model, "time_baseline"]["status"] == "unavailable_fit_model":
            continue
        fit = collapse_role(roles[context["fit_id"]], positions, pairs)
        prediction, leaves = root_model(fit["base"], fit["children"], priors, symbol)
        full_base = sum(cache["counts"][name][2] for name in context["training_slices"])
        full_children = sum(time_children(atoms[name], cuts, threshold) for name in context["training_slices"])
        full_prediction, _ = root_model(full_base, full_children, priors, symbol)
        background = splice_background(prediction, full_prediction, full_base.shape[1], symbol)
        target = {"base": cache["counts"][key][2], "children": time_children(atoms[key], cuts, threshold),
                  "single": low_marginals(atoms[key], cuts, threshold), "joint": joints[key].sum(axis=4), "positions": positions, "pairs": pairs}
        ns = target["base"].sum(axis=1)
        for group in GROUPS:
            rule = choices[key, model, group]["rule"]
            value, transfer = rule_evaluation(target, rule, background, leaves, priors, symbol)
            evaluations[key, model, group], transfers[key, model, group] = value, transfer
            delta = value["wrong_counts"] - evaluations[key, model, "time_baseline"]["wrong_counts"]
            for i, (rescued, harmed) in enumerate(transfer):
                if harmed - rescued != delta[i] or int(known[i]) == 34 and harmed:
                    raise RuntimeError("local transfers or APP34 protection changed")
            if group == "original_pooled":
                expected = previous[key, model, "validation_constrained"] - previous[key, model, "time_fit"]
                if not np.array_equal(value["confusion"] - evaluations[key, model, "time_baseline"]["confusion"], expected):
                    raise RuntimeError("original local confusion increment differs from stages 11/13")
            rates = signed_rates(delta, ns)
            app21 = optional(rates[np.flatnonzero(known == 21)[0]]) if 21 in known else None
            app21_met = app21 <= protocol["APP21_validation_budget_pp"] / 100 + 1e-12 if app21 is not None else None
            raw_met = int(delta.sum()) <= protocol["maximum_validation_raw_wrong_increase"]
            budget_rows.append({"target": key, "period": context["period"], "model": model, "group": group,
                "target_APP21_change": app21, "target_raw_wrong_change": int(delta.sum()), "target_APP21_budget_met": app21_met,
                "target_raw_budget_met": raw_met, "both_met": app21_met and raw_met if app21_met is not None else None,
                "identity": rule is None, "selection_status": choices[key, model, group]["status"]})
            confusions.append({"target": key, "model": model, "group": group, "counts_true_by_predicted": value["confusion"].tolist()})
            checks.append({"target": key, "model": model, "group": group, "all_original_target_flows_retained": True, "APP34_local_no_harm": True})
    metrics, classes = [], []
    for scope in ("monthly", "period"):
        targets = [(s["key"], s["period"], [s["key"]]) for s in cache["slices"] if s["period"] != "pilot"] if scope == "monthly" else [
            (period, period, [s["key"] for s in cache["slices"] if s["period"] == period]) for period in ("certificate", "evaluation")]
        for target, period, keys in targets:
            ns = sum(cache["counts"][key][2].sum(axis=1) for key in keys)
            for model, group in itertools.product(protocol["models"], GROUPS):
                common = {"scope": scope, "target": target, "period": period, "model": model, "group": group}
                available = all((key, model, group) in evaluations for key in keys)
                value, rates, deltas = None, {}, {}
                if available:
                    matrix = sum(evaluations[key, model, group]["confusion"] for key in keys)
                    value = matrix_result(matrix, ns, priors)
                    for reference in ("time_baseline", "original_pooled"):
                        deltas[reference] = value["wrong_counts"] - sum(evaluations[key, model, reference]["wrong_counts"] for key in keys)
                        rates[reference] = signed_rates(deltas[reference], ns)
                row = {**common, "status": "complete" if available else "unavailable_fit_model", "weighted_error": value["summary"]["weighted_error"] if value else None,
                       "raw_wrong": int(value["wrong_counts"].sum()) if value else None}
                for reference in ("time_baseline", "original_pooled"):
                    row["change_vs_" + reference] = weighted_range(rates[reference], priors, signed=True) if available else None
                    row["raw_change_vs_" + reference] = int(deltas[reference].sum()) if available else None
                old_local = weighted_range(signed_rates(sum(evaluations[key, model, "original_pooled"]["wrong_counts"] -
                    evaluations[key, model, "time_baseline"]["wrong_counts"] for key in keys), ns), priors, signed=True)["value"] if available else None
                local = (row["change_vs_time_baseline"] or {}).get("value")
                row["gain_retained_vs_original"] = local / old_local if local is not None and old_local is not None and old_local < -1e-12 else None
                for app in (2, 21, 34):
                    row[f"APP{app}_error"] = optional(value["errors"][np.flatnonzero(known == app)[0]]) if available and app in known else None
                metrics.append(row)
                for i, app in enumerate(known):
                    r = {**common, "APP": int(app), "n": int(ns[i]), "prior": float(priors[i]),
                         "status": "unavailable_model" if not available else "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                         "wrong": int(value["wrong_counts"][i]) if available else None, "error": optional(value["errors"][i]) if available else None,
                         "rescued": sum(transfers[key, model, group][i][0] for key in keys) if available else None,
                         "harmed": sum(transfers[key, model, group][i][1] for key in keys) if available else None}
                    for reference in ("time_baseline", "original_pooled"):
                        r["wrong_change_vs_" + reference] = int(deltas[reference][i]) if available else None
                        r["conditional_change_vs_" + reference] = optional(rates[reference][i]) if available else None
                        r["weighted_change_vs_" + reference] = optional(priors[i] * rates[reference][i]) if available else None
                    classes.append(r)
    budget_summary = []
    for period, model, group in itertools.product(("certificate", "evaluation"), protocol["models"], GROUPS):
        rows = [r for r in budget_rows if (r["period"], r["model"], r["group"]) == (period, model, group)]
        checked = [r for r in rows if r["both_met"] is not None]
        expected = sum(s["period"] == period for s in cache["slices"])
        budget_summary.append({"period": period, "model": model, "group": group, "expected_model_months": expected,
            "available_model_months": len(rows), "checked_model_months": len(checked), "both_met": sum(r["both_met"] for r in checked),
            "APP21_violations": sum(r["target_APP21_budget_met"] is False for r in rows), "raw_violations": sum(not r["target_raw_budget_met"] for r in rows),
            "identity_months": sum(r["identity"] for r in rows)})
    return {"metrics": metrics, "classes": classes, "budget_monthly": budget_rows, "budget_summary": budget_summary, "confusions": confusions, "invariants": checks}
