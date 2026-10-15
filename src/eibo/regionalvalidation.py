"""Full-past outside predictions with frozen, separately validated local rules."""

from __future__ import annotations

import itertools

import numpy as np

from .jointdiagnostic import budget_audit
from .jointrefinement import FOCAL_APPS, MATCHED_GROUPS, low_marginals, root_model, rule_evaluation, time_children
from .monthlydrift import optional, weighted_range
from .refinement import refine_counts

BACKGROUNDS = ("fit_subset", "full_past")


def splice_background(local, full, alphabet, symbol):
    """Only original symbols outside the local cell inherit the full-past model."""
    if local.shape != full.shape or len(local) != alphabet + 2:
        raise ValueError("matching three-child root representations required")
    outside = np.arange(alphabet) != symbol
    combined = local.copy()
    combined[:alphabet][outside] = full[:alphabet][outside]
    inside = np.concatenate(([symbol], np.arange(alphabet, len(local))))
    if not np.array_equal(combined[inside], local[inside]) or not np.array_equal(combined[:alphabet][outside], full[:alphabet][outside]):
        raise RuntimeError("background splice changed a local root prediction")
    return combined


def collapse_role(role, positions, pairs):
    return {**role, "single": role["single"].sum(axis=3), "joint": role["joint"].sum(axis=4), "positions": positions, "pairs": pairs}


def matrix_result(matrix, ns, priors):
    if not np.array_equal(matrix.sum(axis=1), ns):
        raise RuntimeError("regional classifier changed the target class population")
    wrong = ns - np.diag(matrix)
    errors = np.divide(wrong, ns, out=np.full(len(ns), np.nan), where=ns > 0)
    return {"confusion": matrix, "wrong_counts": wrong, "errors": errors,
            "summary": {"weighted_error": weighted_range(errors, priors)}}


def signed_rates(delta, ns):
    return np.divide(delta, ns, out=np.full(len(ns), np.nan), where=ns > 0)


def same_matrix_delta(a, root_a, b, root_b, message):
    if not np.array_equal(a["confusion"] - root_a["confusion"], b["confusion"] - root_b["confusion"]):
        raise RuntimeError(message)


def run_regional(cache, roles, joints, atoms, collection, protocol, replay, *, small_n=200):
    known, priors, symbol = cache["known"], cache["priors"], collection["symbol_id"]
    positions, pairs = tuple(collection["size_positions"]), tuple(map(tuple, collection["size_pairs"]))
    threshold, ipt_cuts = collection["fixed_IPT2_threshold_ms"], collection["IPT2_candidates_ms"]
    matrices = {(r["target"], r["model"], r["group"]): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in replay["confusions"]}
    selections = {(r["target"], r["model"], r["group"]): r for r in replay["selections"]}
    evaluations, references, local_transfers = {}, {}, {}
    outside_effects, focal_symbols, validation_rows, invariants, contexts, stored_confusions = [], [], [], [], [], []
    for context in collection["window_spec"]["contexts"]:
        key, model = context["target"], context["model"]
        common = {"target": key, "period": context["period"], "model": model}
        available = context["status"] == "ready" and "fit_id" in context and np.all(roles[context["fit_id"]]["base"].sum(axis=1) > 0)
        contexts.append({**context, "regional_status": "ready" if available else "unavailable_fit_model"})
        if not available:
            continue
        fit, validation = (collapse_role(roles[context[name + "_id"]], positions, pairs) for name in ("fit", "validation"))
        full_base = sum(cache["counts"][name][2] for name in context["training_slices"])
        full_children = sum(time_children(atoms[name], ipt_cuts, threshold) for name in context["training_slices"])
        local_prediction, leaves = root_model(fit["base"], fit["children"], priors, symbol)
        full_prediction, full_leaves = root_model(full_base, full_children, priors, symbol)
        if not np.array_equal(leaves, full_leaves):
            raise RuntimeError("full-past and fitting-subset root mappings differ")
        alphabet = full_base.shape[1]
        predictions = {"fit_subset": local_prediction, "full_past": splice_background(local_prediction, full_prediction, alphabet, symbol)}
        target = {"base": cache["counts"][key][2], "children": time_children(atoms[key], ipt_cuts, threshold),
                  "single": low_marginals(atoms[key], ipt_cuts, threshold), "joint": joints[key].sum(axis=4), "positions": positions, "pairs": pairs}
        ns, validation_ns = target["base"].sum(axis=1), validation["base"].sum(axis=1)
        full_counts = refine_counts(target["base"], target["children"], symbol)
        full_matrix = np.zeros((len(known), len(known)), dtype=np.int64)
        np.add.at(full_matrix, (np.arange(len(known))[:, None], full_prediction[None, :]), full_counts)
        references[key, model, "full_past_time"] = matrix_result(full_matrix, ns, priors)
        legacy = matrices.get((key, model, "legacy_time_full"))
        if legacy is not None:
            references[key, model, "legacy_time_full"] = matrix_result(legacy, ns, priors)
        validation_evaluations = {}
        for group in MATCHED_GROUPS:
            choice = selections.get((key, model, group)) if group != "time_fit" else None
            if group != "time_fit" and choice is None:
                raise ValueError("original frozen regional selection is missing")
            rule = choice["rule"] if choice else None
            for background in BACKGROUNDS:
                value, transfer = rule_evaluation(target, rule, predictions[background], leaves, priors, symbol)
                evaluations[key, model, background, group] = value
                local_transfers[key, model, background, group] = transfer
                # Only paired validation differences are exported; absolute validation accuracy is not held out for the outside model.
                validation_evaluations[background, group], _ = rule_evaluation(validation, rule, predictions[background], leaves, priors, symbol)
                if background == "fit_subset" and not np.array_equal(value["confusion"], matrices.get((key, model, group))):
                    raise RuntimeError("fitting-subset regional control does not replay stage 11")
                stored_confusions.append({**common, "background": background, "group": group, "counts_true_by_predicted": value["confusion"].tolist()})
            a, b = (evaluations[key, model, name, group] for name in BACKGROUNDS)
            root_a, root_b = (evaluations[key, model, name, "time_fit"] for name in BACKGROUNDS)
            same_matrix_delta(a, root_a, b, root_b, "outside background altered a target local confusion delta")
            va, vb = (validation_evaluations[name, group] for name in BACKGROUNDS)
            vra, vrb = (validation_evaluations[name, "time_fit"] for name in BACKGROUNDS)
            same_matrix_delta(va, vra, vb, vrb, "outside background altered a validation local confusion delta")
            delta = vb["wrong_counts"] - vrb["wrong_counts"]
            rates = signed_rates(delta, validation_ns)
            if rule is not None:
                if int(delta.sum()) != rule["validation_raw_wrong_change"]:
                    raise RuntimeError("local validation raw increment differs from the original frozen rule")
                if 21 in known and validation_ns[np.flatnonzero(known == 21)[0]]:
                    if abs(rates[np.flatnonzero(known == 21)[0]] - rule["APP21_validation_conditional_change"]) > 1e-12:
                        raise RuntimeError("local validation APP21 increment differs from the original frozen rule")
            for i, app in enumerate(known):
                validation_rows.append({**common, "group": group, "APP": int(app), "n": int(validation_ns[i]), "prior": float(priors[i]),
                    "status": "observed" if validation_ns[i] else "missing", "wrong_increment": int(delta[i]),
                    "conditional_increment": optional(rates[i]), "weighted_increment": optional(priors[i] * rates[i]),
                    "both_backgrounds_identical": True, "identity_rule": rule is None})
            for i, (rescued, harmed) in enumerate(local_transfers[key, model, "full_past", group]):
                if harmed - rescued != int(b["wrong_counts"][i] - root_b["wrong_counts"][i]):
                    raise RuntimeError("regional paired transfers do not account for local error increments")
                if int(known[i]) == 34 and harmed:
                    raise RuntimeError("regional local change violated APP34 protection")
            invariants.append({**common, "group": group, "target_local_confusion_increment_identical": True,
                "validation_local_confusion_increment_identical": True, "outside_change_is_shared_across_groups": True, "APP34_local_no_harm": True})
        outside = np.flatnonzero(np.arange(alphabet) != symbol)
        outside_counts = target["base"][:, outside]
        wrong = {name: (outside_counts * (predictions[name][outside][None, :] != np.arange(len(known))[:, None])).sum(axis=1) for name in BACKGROUNDS}
        effect = wrong["full_past"] - wrong["fit_subset"]
        expected = evaluations[key, model, "full_past", "time_fit"]["wrong_counts"] - evaluations[key, model, "fit_subset", "time_fit"]["wrong_counts"]
        if not np.array_equal(effect, expected):
            raise RuntimeError("background error change escaped the outside region")
        full_ns, fit_ns = full_base.sum(axis=1), fit["base"].sum(axis=1)
        for i, app in enumerate(known):
            outside_effects.append({**common, "APP": int(app), "n": int(ns[i]), "prior": float(priors[i]),
                "wrong_outside_fit": int(wrong["fit_subset"][i]), "wrong_outside_full": int(wrong["full_past"][i]), "wrong_change": int(effect[i]),
                "conditional_change": float(effect[i] / ns[i]) if ns[i] else None, "full_past_training_n": int(full_ns[i]),
                "local_fitting_n": int(fit_ns[i]), "local_validation_n": int(validation_ns[i]), "unused_local_past_n": int(full_ns[i] - fit_ns[i] - validation_ns[i])})
        if 2 in known:
            focal = int(np.flatnonzero(known == 2)[0])
            focal_delta = target["base"][focal, outside] * ((predictions["full_past"][outside] != focal).astype(int) - (predictions["fit_subset"][outside] != focal).astype(int))
            if int(focal_delta.sum()) != int(effect[focal]):
                raise RuntimeError("APP2 outside-symbol changes do not reconcile")
            for index in np.flatnonzero(focal_delta):
                cell = int(outside[index])
                focal_symbols.append({**common, "symbol": cell, "APP2_target_flows": int(target["base"][focal, cell]),
                    "prediction_fit_APP": int(known[local_prediction[cell]]), "prediction_full_APP": int(known[full_prediction[cell]]),
                    "APP2_wrong_change": int(focal_delta[index]), "APP2_fit_score": float(priors[focal] * fit["base"][focal, cell] / fit_ns[focal]),
                    "APP2_full_score": float(priors[focal] * full_base[focal, cell] / full_ns[focal])})
        stored_confusions.append({**common, "background": "reference", "group": "full_past_time", "counts_true_by_predicted": full_matrix.tolist()})
    metrics, classes, reference_metrics = [], [], []
    for scope in ("monthly", "period"):
        targets = [(s["key"], s["period"], [s["key"]]) for s in cache["slices"] if s["period"] != "pilot"] if scope == "monthly" else [
            (period, period, [s["key"] for s in cache["slices"] if s["period"] == period]) for period in ("certificate", "evaluation")]
        for target, period, keys in targets:
            ns = sum(cache["counts"][key][2].sum(axis=1) for key in keys)
            for model in protocol["models"]:
                for reference in ("full_past_time", "legacy_time_full"):
                    common_reference = {"scope": scope, "target": target, "period": period, "model": model, "reference": reference}
                    if all((key, model, reference) in references for key in keys):
                        matrix = sum((references[key, model, reference]["confusion"] for key in keys), np.zeros((len(known), len(known)), dtype=np.int64))
                        ref = matrix_result(matrix, ns, priors)
                        r = {**common_reference, "status": "complete", "weighted_error": ref["summary"]["weighted_error"], "raw_wrong": int(ref["wrong_counts"].sum())}
                        for app in FOCAL_APPS:
                            r[f"APP{app}_error"] = optional(ref["errors"][np.flatnonzero(known == app)[0]]) if app in known else None
                        reference_metrics.append(r)
                    else:
                        reference_metrics.append({**common_reference, "status": "unavailable_reference", "weighted_error": None})
                for background in BACKGROUNDS:
                    for group in MATCHED_GROUPS:
                        common = {"scope": scope, "target": target, "period": period, "model": model, "background": background, "group": group}
                        available = all((key, model, background, group) in evaluations for key in keys)
                        if available:
                            total = sum((evaluations[key, model, background, group]["confusion"] for key in keys), np.zeros((len(known), len(known)), dtype=np.int64))
                            value = matrix_result(total, ns, priors)
                            refs = {"same_background_time": sum(evaluations[key, model, background, "time_fit"]["wrong_counts"] for key in keys),
                                    "subset_same_group": sum(evaluations[key, model, "fit_subset", group]["wrong_counts"] for key in keys),
                                    "full_past_time": sum(references[key, model, "full_past_time"]["wrong_counts"] for key in keys)}
                            if all((key, model, "legacy_time_full") in references for key in keys):
                                refs["legacy_time_full"] = sum(references[key, model, "legacy_time_full"]["wrong_counts"] for key in keys)
                            delta = {name: value["wrong_counts"] - ref for name, ref in refs.items()}
                            rates = {name: signed_rates(d, ns) for name, d in delta.items()}
                            row = {**common, "status": "complete", "weighted_error": value["summary"]["weighted_error"], "raw_wrong": int(value["wrong_counts"].sum())}
                            for name in ("same_background_time", "subset_same_group", "full_past_time", "legacy_time_full"):
                                row["change_vs_" + name] = weighted_range(rates[name], priors, signed=True) if name in rates else None
                                row["raw_change_vs_" + name] = int(delta[name].sum()) if name in delta else None
                            for app in FOCAL_APPS:
                                row[f"APP{app}_error"] = optional(value["errors"][np.flatnonzero(known == app)[0]]) if app in known else None
                            metrics.append(row)
                        else:
                            metrics.append({**common, "status": "unavailable_fit_model", "weighted_error": None})
                        for i, app in enumerate(known):
                            r = {**common, "APP": int(app), "n": int(ns[i]), "prior": float(priors[i]),
                                 "status": "unavailable_model" if not available else "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                                 "wrong": int(value["wrong_counts"][i]) if available else None, "error": optional(value["errors"][i]) if available else None,
                                 "local_rescued": None, "local_harmed": None}
                            for name in ("same_background_time", "subset_same_group", "full_past_time", "legacy_time_full"):
                                r["wrong_change_vs_" + name] = int(delta[name][i]) if available and name in delta else None
                                r["conditional_change_vs_" + name] = optional(rates[name][i]) if available and name in rates else None
                                r["weighted_change_vs_" + name] = optional(priors[i] * rates[name][i]) if available and name in rates else None
                            if available:
                                r["local_rescued"] = sum(local_transfers[key, model, background, group][i][0] for key in keys)
                                r["local_harmed"] = sum(local_transfers[key, model, background, group][i][1] for key in keys)
                            classes.append(r)
    budget_rows, budget_summary = budget_audit(cache, replay, protocol)
    return {"metrics": metrics, "classes": classes, "outside_effects": outside_effects, "APP2_outside_symbols": focal_symbols,
            "validation_increments": validation_rows, "invariants": invariants, "contexts": contexts, "confusions": stored_confusions,
            "reference_metrics": reference_metrics, "budget_monthly": budget_rows, "budget_summary": budget_summary}
