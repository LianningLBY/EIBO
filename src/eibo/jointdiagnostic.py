"""Audit frozen joint models without choosing another rule from target labels."""

from __future__ import annotations

import itertools

import numpy as np

from .jointrefinement import MATCHED_GROUPS, child_counts, root_model, time_children
from .monthlydrift import optional, weighted_range
from .refinement import refine_counts
from .rolling import training_window

COMPARISONS = tuple((group, "time_fit") for group in MATCHED_GROUPS[1:]) + (
    ("joint_fit", "single_fit"), ("validation_weighted", "joint_fit"),
    ("validation_constrained", "validation_weighted"), ("time_fit", "legacy_time_full"))


def rate(delta, ns):
    return np.divide(delta, ns, out=np.full(np.shape(delta), np.nan), where=ns > 0)


def attribution(cache, replay, models, *, small_n=200):
    """Integer net changes; paired rescue/harm only for saved same-root transfers."""
    matrices = {(r["target"], r["model"], r["group"]): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in replay["confusions"]}
    transfer = {(r["target"], r["model"], r["group"], r["APP"]): r for r in replay["classes"]}
    rows, summaries = [], []
    for scope in ("monthly", "period"):
        targets = [(s["key"], s["period"], [s["key"]]) for s in cache["slices"] if s["period"] != "pilot"] if scope == "monthly" else [
            (period, period, [s["key"] for s in cache["slices"] if s["period"] == period]) for period in ("certificate", "evaluation")]
        for target, period, keys in targets:
            ns = sum(cache["counts"][key][2].sum(axis=1) for key in keys)
            for model in models:
                for group, reference in COMPARISONS:
                    common = {"scope": scope, "target": target, "period": period, "model": model, "group": group, "reference": reference}
                    available = all((key, model, name) in matrices for key in keys for name in (group, reference))
                    if available:
                        wrong = {name: sum((ns0 - np.diag(matrices[key, model, name]) for key in keys
                                  for ns0 in [cache["counts"][key][2].sum(axis=1)]), np.zeros(len(ns), dtype=np.int64)) for name in (group, reference)}
                        delta = wrong[group] - wrong[reference]
                        errors = rate(delta, ns)
                        summaries.append({**common, "status": "complete", "weighted_change": weighted_range(errors, cache["priors"], signed=True),
                                          "raw_wrong_change": int(delta.sum()), "harmed_classes": int((delta > 0).sum()), "improved_classes": int((delta < 0).sum())})
                    else:
                        summaries.append({**common, "status": "unavailable_model", "weighted_change": None, "raw_wrong_change": None})
                    for i, app in enumerate(cache["known"]):
                        r = {**common, "APP": int(app), "n": int(ns[i]), "prior": float(cache["priors"][i]),
                             "status": "unavailable_model" if not available else "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                             "wrong_reference": int(wrong[reference][i]) if available else None, "wrong_model": int(wrong[group][i]) if available else None,
                             "wrong_change": int(delta[i]) if available else None, "conditional_change": optional(errors[i]) if available else None,
                             "weighted_change": optional(cache["priors"][i] * errors[i]) if available else None, "rescued": None, "harmed": None}
                        if available and reference == "time_fit":
                            values = [transfer[key, model, group, int(app)] for key in keys]
                            if all(v["rescued"] is not None and v["harmed"] is not None for v in values):
                                r.update(rescued=sum(v["rescued"] for v in values), harmed=sum(v["harmed"] for v in values))
                                if r["harmed"] - r["rescued"] != r["wrong_change"]:
                                    raise RuntimeError("paired transfers do not account for integer class change")
                        rows.append(r)
    return rows, summaries


def budget_audit(cache, replay, protocol):
    selected = {(r["target"], r["model"], r["group"]): r for r in replay["selections"]}
    classes = {(r["target"], r["model"], r["group"], r["APP"]): r for r in replay["classes"]}
    cap, raw_cap = protocol["APP21_validation_budget_pp"] / 100, protocol["maximum_validation_raw_wrong_increase"]
    rows = []
    for metric in replay["monthly"]:
        if metric["group"] not in ("validation_weighted", "validation_constrained"):
            continue
        token = tuple(metric[k] for k in ("target", "model", "group"))
        choice = selected.get(token)
        valid = choice is not None and metric["status"] == "complete"
        rule = (choice or {}).get("rule")
        identity = valid and rule is None
        focal = classes.get(token + (21,))
        cost = focal["conditional_change_vs_time_fit"] if focal else 0.
        raw = metric.get("raw_wrong_change_vs_time_fit")
        target_cap_met = (cost <= cap + 1e-12) if valid and cost is not None else None
        target_raw_met = raw <= raw_cap if valid and raw is not None else None
        val_cost = 0. if identity else rule.get("APP21_validation_conditional_change") if rule else None
        val_raw = 0 if identity else rule.get("validation_raw_wrong_change") if rule else None
        val_complete = bool(rule["validation_complete"]) if rule else bool(valid and all(n > 0 for n in choice["validation_sample_counts"]))
        val_cap_met = (val_cost <= cap + 1e-12) if val_cost is not None else (True if 21 not in cache["known"] and valid else None)
        val_raw_met = (val_raw <= raw_cap) if val_raw is not None else None
        row = {**{k: metric[k] for k in ("target", "period", "model", "group")}, "status": "complete" if valid else "unavailable_model",
               "identity": bool(identity), "validation_complete_classes": val_complete,
               "APP21_budget": cap, "raw_wrong_budget": raw_cap, "validation_APP21_change": val_cost,
               "validation_raw_wrong_change": val_raw, "validation_APP21_budget_met": val_cap_met,
               "validation_raw_budget_met": val_raw_met, "target_APP21_change": cost if valid else None,
               "target_raw_wrong_change": raw if valid else None, "target_APP21_budget_met": target_cap_met,
               "target_raw_budget_met": target_raw_met,
               "target_both_met": bool(target_cap_met and target_raw_met) if target_cap_met is not None and target_raw_met is not None else None,
               "APP21_target_minus_validation": cost - val_cost if valid and cost is not None and val_cost is not None else None,
               "weighted_target_change": metric.get("change_vs_time_fit")}
        if metric["group"] == "validation_constrained" and valid and (val_cap_met is False or val_raw_met is False):
            raise RuntimeError("replayed constrained rule violates its own past validation budget")
        rows.append(row)
    summaries = []
    for period in ("certificate", "evaluation"):
        for model in protocol["models"]:
            for group in ("validation_weighted", "validation_constrained"):
                values = [r for r in rows if (r["period"], r["model"], r["group"]) == (period, model, group)]
                observed = [r for r in values if r["target_both_met"] is not None]
                summaries.append({"period": period, "model": model, "group": group, "model_months": len(values), "checked_model_months": len(observed),
                                  "both_met": sum(r["target_both_met"] for r in observed),
                                  "APP21_violations": sum(r["target_APP21_budget_met"] is False for r in values),
                                  "raw_wrong_violations": sum(r["target_raw_budget_met"] is False for r in values),
                                  "worst_APP21_change": max((r["target_APP21_change"] for r in observed), default=None),
                                  "worst_raw_wrong_change": max((r["target_raw_wrong_change"] for r in observed), default=None)})
    return rows, summaries


def collapsed(role, positions, pairs):
    return {**role, "single": role["single"].sum(axis=3), "joint": role["joint"].sum(axis=4), "positions": positions, "pairs": pairs}


def focal_candidate_audit(cache, roles, joints, old_atoms, collection, replay, *, minimum=200, focal_app=2, app21_budget=.001, raw_budget=0):
    """All frozen candidate labels, plus explicitly non-deployed atomic diagnostics."""
    known, priors = cache["known"], cache["priors"]
    if focal_app not in known:
        return {name: [] for name in ("candidates", "candidate_summary", "leaves", "pair_atoms", "pair_summary")}
    focal = int(np.flatnonzero(known == focal_app)[0])
    positions, cuts = tuple(collection["size_positions"]), collection["size_candidates_bytes"]
    pairs = tuple(itertools.combinations(positions, 2))
    by_context = {}
    for row in replay["candidates"]:
        by_context.setdefault((row["target"], row["model"]), []).append(row)
    choices = {}
    for row in replay["selections"]:
        if row.get("rule") is not None:
            choices.setdefault((row["target"], row["model"], row["rule"]["candidate_id"]), []).append(row["group"])
    outputs = {name: [] for name in ("candidates", "candidate_summary", "leaves", "pair_atoms", "pair_summary")}
    for context in collection["window_spec"]["contexts"]:
        token = (context["target"], context["model"])
        candidates = by_context.get(token, [])
        common = {"target": token[0], "period": context["period"], "model": token[1]}
        if not candidates:
            outputs["candidate_summary"].append({**common, "kind": "all", "status": "unavailable_fit_model"})
            continue
        fit, validation = (collapsed(roles[context[name + "_id"]], positions, pairs) for name in ("fit", "validation"))
        stop = collection["low_time_atoms"]
        target = {"base": cache["counts"][token[0]][2], "joint": joints[token[0]].sum(axis=4),
                  "single": old_atoms[token[0]][:, :, :, :stop].sum(axis=3), "positions": positions, "pairs": pairs}
        ns = {"fit": fit["base"].sum(axis=1), "validation": validation["base"].sum(axis=1), "target": target["base"].sum(axis=1)}
        prediction, root_leaves = root_model(fit["base"], fit["children"], priors, collection["symbol_id"])
        parent = int(prediction[root_leaves[0]])
        values, children_by_id = [], {}
        for rule in candidates:
            children = {name: child_counts(data, rule, positions, pairs) for name, data in (("fit", fit), ("validation", validation), ("target", target))}
            labels = np.asarray(rule["prediction_indices"], dtype=np.int64)
            score = children["fit"] * (priors / ns["fit"])[:, None]
            competitor = score.copy()
            competitor[focal] = -np.inf
            margin = score[focal] - competitor.max(axis=0)
            winner = (labels == focal) & (children["fit"].sum(axis=0) > 0) & (children["fit"][focal] > 0)
            allowed = bool(rule["eligible"] and int(known[parent]) != 34)
            reasons = []
            if not rule["eligible"]:
                reasons.append("fit_leaf_support")
            if int(known[parent]) == 34:
                reasons.append("APP34_parent_protection")
            if not rule["validation_complete"]:
                reasons.append("missing_validation_classes")
            if rule["validation_weighted_change"] is None or rule["validation_weighted_change"] >= -1e-12:
                reasons.append("no_positive_validation_gain")
            if rule["validation_raw_wrong_change"] > raw_budget:
                reasons.append("validation_raw_budget")
            if 21 in known and (rule["APP21_validation_conditional_change"] is None or rule["APP21_validation_conditional_change"] > app21_budget + 1e-12):
                reasons.append("validation_APP21_budget")
            row = {**common, "candidate_id": rule["candidate_id"], "kind": rule["kind"], "positions": ";".join(map(str, rule["positions"])),
                   "thresholds_bytes": ";".join(map(str, rule["thresholds_bytes"])), "eligible": rule["eligible"], "allowed": allowed,
                   "low_parent_APP": int(known[parent]), "fit_APP2_winning_leaves": int(winner.sum()),
                   "best_fit_APP2_margin": float(margin[children["fit"][focal] > 0].max()) if np.any(children["fit"][focal] > 0) else None,
                   "fit_weighted_gain": rule["fit_gain"],
                   "validation_weighted_change": rule["validation_weighted_change"], "validation_raw_wrong_change": rule["validation_raw_wrong_change"],
                   "validation_APP21_change": rule["APP21_validation_conditional_change"],
                   "passes_original_validation_constraints": not reasons, "validation_rejection_reasons": ";".join(reasons),
                   "selected_by": ";".join(choices.get(token + (rule["candidate_id"],), []))}
            for name, a in children.items():
                gain = int(a[focal, labels == focal].sum() - (a[focal].sum() if parent == focal else 0))
                row[name + "_APP2_correct_gain"] = gain
                row[name + "_APP2_conditional_gain"] = gain / int(ns[name][focal]) if ns[name][focal] else None
            values.append(row)
            # Only selected rules and one best eligible focal candidate need full leaf tables.
            if row["selected_by"]:
                children_by_id[rule["candidate_id"]] = (rule, children)
        for kind in ("single", "joint"):
            family = [r for r in values if r["kind"] == kind]
            allowed = [r for r in family if r["allowed"]]
            best = max(allowed, key=lambda r: (r["fit_APP2_correct_gain"], -r["candidate_id"]), default=None)
            if best is not None:
                rule = next(r for r in candidates if r["candidate_id"] == best["candidate_id"])
                children_by_id[rule["candidate_id"]] = (rule, {name: child_counts(data, rule, positions, pairs) for name, data in (("fit", fit), ("validation", validation), ("target", target))})
            outputs["candidate_summary"].append({**common, "kind": kind, "status": "complete", "candidate_count": len(family), "allowed_candidates": len(allowed),
                "raw_positive_APP2_candidates": sum(r["fit_APP2_correct_gain"] > 0 for r in family),
                "allowed_positive_APP2_candidates": sum(r["fit_APP2_correct_gain"] > 0 for r in allowed),
                "validation_qualified_positive_APP2_candidates": sum(r["fit_APP2_correct_gain"] > 0 and r["passes_original_validation_constraints"] for r in allowed),
                "best_allowed_fit_APP2_correct_gain": max(0, best["fit_APP2_correct_gain"]) if best else 0,
                "best_allowed_candidate_signed_fit_gain": best["fit_APP2_correct_gain"] if best else None,
                "best_allowed_candidate_id": best["candidate_id"] if best and best["fit_APP2_correct_gain"] > 0 else None,
                "best_allowed_selected_by": best["selected_by"] if best and best["fit_APP2_correct_gain"] > 0 else "",
                "maximum_allowed_target_APP2_correct_gain_hindsight": max([0] + [r["target_APP2_correct_gain"] for r in allowed]),
                "low_parent_APP": int(known[parent]), "fit_APP2_n": int(ns["fit"][focal]), "validation_APP2_n": int(ns["validation"][focal]), "target_APP2_n": int(ns["target"][focal])})
        outputs["candidates"].extend(values)
        for rule, children in children_by_id.values():
            score = children["fit"] * (priors / ns["fit"])[:, None]
            others = score.copy()
            others[focal] = -np.inf
            for leaf, label in enumerate(rule["prediction_indices"]):
                rival = int(others[:, leaf].argmax())
                outputs["leaves"].append({**common, "candidate_id": rule["candidate_id"], "kind": rule["kind"], "positions": rule["positions"],
                    "thresholds_bytes": rule["thresholds_bytes"], "leaf": leaf, "prediction_APP": int(known[label]), "allowed": rule["eligible"] and int(known[parent]) != 34,
                    "fit_flows": int(children["fit"][:, leaf].sum()), "fit_APP2_flows": int(children["fit"][focal, leaf]),
                    "validation_APP2_flows": int(children["validation"][focal, leaf]), "target_APP2_flows": int(children["target"][focal, leaf]),
                    "APP2_fit_score": float(score[focal, leaf]), "strongest_other_APP": int(known[rival]), "strongest_other_score": float(others[rival, leaf]),
                    "APP2_margin": float(score[focal, leaf] - others[rival, leaf])})
        complete_target = bool(np.all(ns["target"] > 0))
        for index, pair in enumerate(pairs):
            a, v, b = (data["joint"][index].reshape(len(known), -1) for data in (fit, validation, target))
            pooled = a.sum(axis=0)
            score = a * (priors / ns["fit"])[:, None]
            raw = score.argmax(axis=0)
            raw[pooled == 0] = parent
            guarded = raw.copy()
            guarded[pooled < minimum] = parent
            if int(known[parent]) == 34:
                guarded[:] = parent
            raw_win = (raw == focal) & (pooled > 0) & (a[focal] > 0)
            guard_win = (guarded == focal) & (pooled > 0) & (a[focal] > 0)
            target_scores = b * (priors / ns["target"])[:, None] if complete_target else None
            target_labels = target_scores.argmax(axis=0) if complete_target else None
            empirical_win = (target_labels == focal) & (b[focal] > 0) if complete_target else None
            outputs["pair_summary"].append({**common, "left_packet": pair[0], "right_packet": pair[1], "fit_APP2_winning_atoms": int(raw_win.sum()),
                "guarded_fit_APP2_winning_atoms": int(guard_win.sum()),
                "fit_APP2_flows_lost_to_leaf_budget": int(a[focal, raw_win & (pooled < minimum) & (guarded != focal)].sum()),
                "fit_APP2_correct_gain_guarded": int(a[focal, guarded == focal].sum() - (a[focal].sum() if parent == focal else 0)),
                "target_APP2_correct_gain_guarded_diagnostic": int(b[focal, guarded == focal].sum() - (b[focal].sum() if parent == focal else 0)),
                "target_empirical_APP2_winning_atoms": int(empirical_win.sum()) if complete_target else None,
                "target_empirical_APP2_flows_in_winning_atoms": int(b[focal, empirical_win].sum()) if complete_target else None,
                "target_oracle_status": "complete" if complete_target else "unavailable_missing_target_classes",
                "parent_APP": int(known[parent]), "minimum_atom_fit_flows": minimum, "deployed": False})
            other = score.copy()
            other[focal] = -np.inf
            for atom in np.flatnonzero((a[focal] + v[focal] + b[focal]) > 0):
                left, right = np.unravel_index(int(atom), (len(cuts) + 1,) * 2)
                rival = int(other[:, atom].argmax())
                outputs["pair_atoms"].append({**common, "left_packet": pair[0], "right_packet": pair[1], "left_atom": int(left), "right_atom": int(right),
                    "left_lower_exclusive": float(cuts[left - 1]) if left else None, "left_upper_inclusive": float(cuts[left]) if left < len(cuts) else None,
                    "right_lower_exclusive": float(cuts[right - 1]) if right else None, "right_upper_inclusive": float(cuts[right]) if right < len(cuts) else None,
                    "fit_flows": int(pooled[atom]), "fit_APP2_flows": int(a[focal, atom]), "validation_APP2_flows": int(v[focal, atom]), "target_APP2_flows": int(b[focal, atom]),
                    "raw_fit_prediction_APP": int(known[raw[atom]]), "guarded_prediction_APP": int(known[guarded[atom]]),
                    "APP2_fit_margin": float(score[focal, atom] - other[rival, atom]), "strongest_other_APP": int(known[rival]),
                    "target_empirical_prediction_APP": int(known[target_labels[atom]]) if complete_target and b[:, atom].sum() > 0 else None,
                    "target_empirical_APP2_margin": float(target_scores[focal, atom] - np.delete(target_scores[:, atom], focal).max()) if complete_target and b[:, atom].sum() > 0 else None})
    return outputs


def training_split_regions(cache, roles, old_atoms, collection):
    """Compare identical fixed-root representations; data usage is the only change."""
    symbol, threshold = collection["symbol_id"], collection["fixed_IPT2_threshold_ms"]
    rows = []
    for context in collection["window_spec"]["contexts"]:
        if "fit_id" not in context:
            continue
        target_slice = next(s for s in cache["slices"] if s["key"] == context["target"])
        full_window = training_window(cache, target_slice, context["model"])
        fit = roles[context["fit_id"]]
        if full_window["status"] != "ready" or np.any(fit["base"].sum(axis=1) == 0):
            continue
        keys = full_window["training_slices"]
        full_base = sum(cache["counts"][key][2] for key in keys)
        full_children = sum(time_children(old_atoms[key], collection["IPT2_candidates_ms"], threshold) for key in keys)
        full_prediction, leaves = root_model(full_base, full_children, cache["priors"], symbol)
        fit_prediction, _ = root_model(fit["base"], fit["children"], cache["priors"], symbol)
        base = cache["counts"][context["target"]][2]
        ns = base.sum(axis=1)
        target_children = time_children(old_atoms[context["target"]], collection["IPT2_candidates_ms"], threshold)
        counts = refine_counts(base, target_children, symbol)
        regions = {"outside_479": np.setdiff1d(np.arange(base.shape[1]), [symbol]),
                   "low": leaves[:1], "high": leaves[1:2], "invalid": leaves[2:]}
        total = np.zeros(len(ns), dtype=np.int64)
        for name, indices in regions.items():
            wrong_full = (counts[:, indices] * (full_prediction[indices][None, :] != np.arange(len(ns))[:, None])).sum(axis=1)
            wrong_fit = (counts[:, indices] * (fit_prediction[indices][None, :] != np.arange(len(ns))[:, None])).sum(axis=1)
            delta = wrong_fit - wrong_full
            total += delta
            for i, app in enumerate(cache["known"]):
                rows.append({"scope": "monthly", "target": context["target"], "period": context["period"], "model": context["model"], "region": name,
                    "APP": int(app), "n": int(ns[i]), "prior": float(cache["priors"][i]), "wrong_full_past": int(wrong_full[i]), "wrong_fit_subset": int(wrong_fit[i]),
                    "wrong_change": int(delta[i]), "conditional_change": float(delta[i] / ns[i]) if ns[i] else None,
                    "weighted_change": float(cache["priors"][i] * delta[i] / ns[i]) if ns[i] else None})
        full_error = (counts * (full_prediction[None, :] != np.arange(len(ns))[:, None])).sum(axis=1)
        fit_error = (counts * (fit_prediction[None, :] != np.arange(len(ns))[:, None])).sum(axis=1)
        if not np.array_equal(total, fit_error - full_error):
            raise RuntimeError("training-split regions do not conserve class error changes")
    pooled = []
    for period in ("certificate", "evaluation"):
        keys = [s["key"] for s in cache["slices"] if s["period"] == period]
        ns = cache["period_counts"][period][2].sum(axis=1)
        for model in sorted({r["model"] for r in rows}):
            for region in ("outside_479", "low", "high", "invalid"):
                for i, app in enumerate(cache["known"]):
                    values = [r for r in rows if (r["period"], r["model"], r["region"], r["APP"]) == (period, model, region, int(app))]
                    available = len(values) == len(keys)
                    a = sum(r["wrong_full_past"] for r in values) if available else None
                    b = sum(r["wrong_fit_subset"] for r in values) if available else None
                    pooled.append({"scope": "period", "target": period, "period": period, "model": model, "region": region, "APP": int(app), "n": int(ns[i]),
                        "prior": float(cache["priors"][i]), "wrong_full_past": a, "wrong_fit_subset": b, "wrong_change": b - a if available else None,
                        "conditional_change": float((b - a) / ns[i]) if available and ns[i] else None,
                        "weighted_change": float(cache["priors"][i] * (b - a) / ns[i]) if available and ns[i] else None})
    return rows + pooled
