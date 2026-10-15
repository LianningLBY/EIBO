"""Separate common support, historical budgets and temporal scoring objectives."""

from __future__ import annotations

import numpy as np

from .forwardvalidation import evaluate_forward, role_data, scored_family
from .monthlydrift import weighted_range
from .regionalvalidation import signed_rates

OBJECTIVES = ("latest", "pooled", "uniform", "recent")
MATCHED = tuple(prefix + "_" + objective for prefix in ("shared", "strict") for objective in OBJECTIVES)
SOURCE_GROUPS = {"time_baseline": "time_baseline", "fit_only": "source_fit", "latest_month": "source_latest", "pooled_months": "source_pooled", "all_months": "source_all"}


def recency_weights(months, ratio):
    if months < 1 or not np.isfinite(ratio) or ratio < 1:
        raise ValueError("positive month count and finite recency ratio >= 1 required")
    # Subtract the largest exponent to avoid overflow for long histories.
    values = np.exp((np.arange(months) - (months - 1)) * np.log(ratio))
    return values / values.sum()


def past_table(current, folds, collection, protocol, *, ratio=2.):
    known, priors = np.asarray(collection["known_service_codes"]), np.asarray(collection["known_priors"])
    weights = recency_weights(len(folds), ratio)
    cap, raw_cap = protocol["APP21_validation_budget_pp"] / 100, protocol["maximum_validation_raw_wrong_increase"]
    available = all(f is not None for f in folds)
    complete = available and all(np.all(f["ns"] > 0) for f in folds)
    rows = []
    for index, candidate in enumerate(current["rows"]):
        monthly = [f["rows"][index] if f else None for f in folds]
        support = bool(candidate["eligible"] and not current["protected_parent"] and complete and
                       all(r["eligible"] and not f["protected_parent"] for r, f in zip(monthly, folds)))
        if complete:
            ns, delta = sum(f["ns"] for f in folds), sum(f["deltas"][index] for f in folds)
            rates = signed_rates(delta, ns)
            pooled_change, raw = float(np.dot(priors, rates)), int(delta.sum())
            app21 = float(rates[np.flatnonzero(known == 21)[0]]) if 21 in known else 0.
            month_gain = np.array([-r["validation_weighted_change"] for r in monthly])
            gains = {"latest": float(month_gain[-1]), "pooled": -pooled_change, "uniform": float(month_gain.mean()), "recent": float(np.dot(weights, month_gain))}
            month_app21_ok = [bool(21 not in known or r["APP21_validation_conditional_change"] <= cap + 1e-12) for r in monthly]
            month_raw_ok = [bool(r["validation_raw_wrong_change"] <= raw_cap) for r in monthly]
            pool_app21_ok, pool_raw_ok = bool(app21 <= cap + 1e-12), bool(raw <= raw_cap)
            latest_ok = month_app21_ok[-1] and month_raw_ok[-1]
            strict_ok = all(month_app21_ok) and all(month_raw_ok) and pool_app21_ok and pool_raw_ok
        else:
            gains = {key: None for key in OBJECTIVES}
            raw, app21, pool_app21_ok, pool_raw_ok, latest_ok, strict_ok = None, None, False, False, False, False
            month_app21_ok, month_raw_ok = [None] * len(folds), [None] * len(folds)
        rows.append({"candidate_id": index, "common_support": support, "current_fit_support": bool(candidate["eligible"]),
            "current_parent_protected": bool(current["protected_parent"]), "history_available": available, "history_complete": bool(complete),
            "historical_fit_support": [bool(r["eligible"]) if r else None for r in monthly],
            "historical_parent_protected": [bool(f["protected_parent"]) if f else None for f in folds],
            "month_APP21_ok": month_app21_ok, "month_raw_ok": month_raw_ok,
            "pooled_APP21_ok": pool_app21_ok, "pooled_raw_ok": pool_raw_ok, "pooled_APP21_change": app21, "pooled_raw_change": raw,
            "latest_budget_ok": bool(latest_ok), "strict_budget_ok": bool(strict_ok), **{key + "_gain": value for key, value in gains.items()}})
    return rows


def matched_choices(current, rows):
    choices = {}
    for group in MATCHED:
        budget, objective = group.split("_", 1)
        best, gain = None, 0.
        if current["protected_parent"]:
            status = "identity_APP34_parent_protection"
        elif not rows[0]["history_available"]:
            status = "identity_unavailable_history"
        elif not rows[0]["history_complete"]:
            status = "identity_missing_history_classes"
        else:
            status = "identity_no_positive_qualified_gain"
            for row, candidate in zip(rows, current["rows"]):
                if not row["common_support"] or not row["latest_budget_ok" if budget == "shared" else "strict_budget_ok"]:
                    continue
                value = row[objective + "_gain"]
                if value > gain + 1e-12 or best is not None and value > 1e-12 and abs(value - gain) <= 1e-12 and (
                        candidate["observed_fit_leaves"], candidate["candidate_id"]) < (best["observed_fit_leaves"], best["candidate_id"]):
                    best, gain = candidate, value
            if best is not None:
                status = "selected"
        rule = {k: v for k, v in best.items() if not k.startswith("validation_") and k != "APP21_validation_conditional_change"} if best else None
        choices[group] = {"rule": rule, "status": status, "selection_gain": gain if best else 0.}
    return choices


def build_tables(roles, collection, protocol):
    """This interface never receives original monthly target histograms."""
    nodes = {n["id"]: n for n in collection["window_spec"]["nodes"]}
    fits, validation = {}, {}

    def fitted(node):
        if node is None or node["status"] != "ready" or np.any(roles[node["fit_id"]]["base"].sum(axis=1) == 0):
            return None
        token = node["fit_id"]
        if token not in fits:
            data = role_data(roles[token], collection)
            fits[token] = scored_family(data, data, collection, protocol["minimum_fit_leaf_flows"])
        return fits[token]

    tables = {}
    for c in collection["window_spec"]["contexts"]:
        current = fitted(nodes[c["node_id"]])
        folds = []
        if current is not None:
            for token in c["history_node_ids"]:
                node = nodes.get(token)
                if fitted(node) is None:
                    folds.append(None)
                    continue
                if node["fit_end_epoch"] + collection["window_spec"]["gap_seconds"] > node["validation_start_epoch"] or node["validation_end_epoch"] > c["target_start_epoch"]:
                    raise ValueError("historical fold is not strictly before its target")
                if token not in validation:
                    validation[token] = scored_family(role_data(roles[node["fit_id"]], collection), role_data(roles[node["validation_id"]], collection), collection, protocol["minimum_fit_leaf_flows"])
                folds.append(validation[token])
        tables[c["target"], c["model"]] = current, folds
    return tables


def select_and_audit(roles, collection, protocol, source_selected, *, ratio=2.):
    old = {(r["target"], r["model"], r["group"]): r for r in source_selected["selections"]}
    tables = build_tables(roles, collection, protocol)
    selections, candidates, exclusions, months, focal = [], [], [], [], []
    for c in collection["window_spec"]["contexts"]:
        common = {k: c[k] for k in ("target", "period", "model")}
        current, folds = tables[c["target"], c["model"]]
        if current is None:
            selections.extend({**common, "group": group, "rule": None, "status": "unavailable_current_fit"} for group in MATCHED)
            continue
        rows = past_table(current, folds, collection, protocol, ratio=ratio)
        choices = matched_choices(current, rows)
        # Strict pooled uses exactly the old all-month support, objective and budgets.
        if choices["strict_pooled"]["rule"] != old[c["target"], c["model"], "all_months"]["rule"]:
            raise RuntimeError("strict pooled does not reproduce the original all-month choice")
        selections.extend({**common, "group": group, **choice, "history_node_ids": c["history_node_ids"], "current_node_id": c["node_id"]} for group, choice in choices.items())
        candidates.extend({**common, **row} for row in rows)
        latest = old[c["target"], c["model"], "latest_month"]["rule"]
        index = latest["candidate_id"] if latest else None
        summary = {**common, "source_latest_candidate": index, "source_latest_identity": index is None,
                   "history_node_ids": c["history_node_ids"],
                   "source_all_candidate": (old[c["target"], c["model"], "all_months"]["rule"] or {}).get("candidate_id")}
        if index is not None:
            summary.update(rows[index])
            for group, choice in choices.items():
                objective = group.split("_", 1)[1]
                budget = "latest_budget_ok" if group.startswith("shared_") else "strict_budget_ok"
                row = rows[index]
                exclusions.append({**common, "group": group, "candidate_id": index,
                    "common_support": row["common_support"], "budget_ok": row[budget], "focal_gain": row[objective + "_gain"],
                    "winner_candidate": (choice["rule"] or {}).get("candidate_id"), "winner_gain": choice["selection_gain"],
                    "objective_gap": choice["selection_gain"] - row[objective + "_gain"] if row[objective + "_gain"] is not None else None,
                    "selected": (choice["rule"] or {}).get("candidate_id") == index})
        focal.append(summary)
        selected_ids = {r["rule"]["candidate_id"] for r in choices.values() if r["rule"] is not None}
        selected_ids.update(old[c["target"], c["model"], g]["rule"]["candidate_id"] for g in ("latest_month", "pooled_months", "all_months") if old[c["target"], c["model"], g]["rule"])
        for i in sorted(selected_ids):
            for token, fold in zip(c["history_node_ids"], folds):
                r = fold["rows"][i] if fold else None
                months.append({**common, "candidate_id": i, "validation_origin": token, "available": fold is not None,
                    "complete_classes": bool(np.all(fold["ns"] > 0)) if fold else False,
                    "fit_eligible": r["eligible"] if r else None, "parent_protected": fold["protected_parent"] if fold else None,
                    "weighted_change": r["validation_weighted_change"] if r else None, "raw_change": r["validation_raw_wrong_change"] if r else None,
                    "APP21_change": r["APP21_validation_conditional_change"] if r else None,
                    "historical_prediction_APPs": r["prediction_APPs"] if r else None, "current_prediction_APPs": current["rows"][i]["prediction_APPs"],
                    "fit_leaf_flows": r["fit_leaf_flows"] if r else None, "minimum_class_n": int(fold["ns"].min()) if fold else None})
    return {"selections": selections, "candidates": candidates, "focal": focal, "exclusions": exclusions, "months": months}


def evaluate_matched(cache, roles, joints, atoms, collection, protocol, selected, source_selected, source_result, previous, *, small_n=200):
    """Use the unchanged original evaluator in two four-choice batches."""
    result = {name: [{**r, "group": SOURCE_GROUPS[r["group"]]} for r in source_result[name] if r["group"] in SOURCE_GROUPS]
              for name in ("metrics", "classes", "confusions", "budget_monthly", "budget_summary")}
    choices = {(r["target"], r["model"], r["group"]): r for r in selected["selections"]}
    roots = [r for r in source_selected["selections"] if r["group"] == "time_baseline"]
    source_matrices = {(r["target"], r["model"]): r["counts_true_by_predicted"] for r in source_result["confusions"] if r["group"] == "time_baseline"}
    slots = ("fit_only", "latest_month", "pooled_months", "all_months")
    for prefix in ("shared", "strict"):
        names = [prefix + "_" + objective for objective in OBJECTIVES]
        rename = dict(zip(slots, names))
        adapted = list(roots)
        for c in collection["window_spec"]["contexts"]:
            adapted.extend({**choices[c["target"], c["model"], name], "group": slot} for slot, name in zip(slots, names))
        batch = evaluate_forward(cache, roles, joints, atoms, collection, protocol, {"selections": adapted}, previous, small_n=small_n)
        for r in batch["confusions"]:
            if r["group"] == "time_baseline" and r["counts_true_by_predicted"] != source_matrices[r["target"], r["model"]]:
                raise RuntimeError("matched selector changed the common baseline")
        for name in result:
            result[name].extend({**r, "group": rename[r["group"]]} for r in batch[name] if r["group"] in rename)
    # Cross-selector comparisons are integer net changes; paired rescue/harm is only vs the shared root.
    index = {(r["scope"], r["target"], r["model"], r["group"], r["APP"]): r for r in result["classes"]}
    buckets = {}
    for r in result["classes"]:
        ref = index[r["scope"], r["target"], r["model"], "source_latest", r["APP"]]
        delta = r["wrong"] - ref["wrong"] if r["wrong"] is not None and ref["wrong"] is not None else None
        rate = delta / r["n"] if delta is not None and r["n"] > 0 else None
        r.update(wrong_change_vs_source_latest=delta, conditional_change_vs_source_latest=rate,
                 weighted_change_vs_source_latest=r["prior"] * rate if rate is not None else None)
        buckets.setdefault((r["scope"], r["target"], r["model"], r["group"]), []).append(r)
    for r in result["metrics"]:
        rows = buckets[r["scope"], r["target"], r["model"], r["group"]]
        complete_model = all(c["wrong_change_vs_source_latest"] is not None for c in rows)
        rates = np.array([c["conditional_change_vs_source_latest"] if c["conditional_change_vs_source_latest"] is not None else np.nan for c in rows])
        r["change_vs_source_latest"] = weighted_range(rates, cache["priors"], signed=True) if complete_model else None
        r["raw_change_vs_source_latest"] = sum(c["wrong_change_vs_source_latest"] for c in rows) if complete_model else None
    return result
