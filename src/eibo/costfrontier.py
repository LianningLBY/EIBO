"""Past-only gain/cost frontiers with fixed classes, priors and fitted families."""

from __future__ import annotations

import numpy as np

from .forwardvalidation import evaluate_forward
from .monthlydrift import weighted_range
from .recencyaudit import build_tables, past_table

GROUPS = ("latest_no_harm", "all_no_harm", "latest_keep_gains", "all_keep_gains")
FOCAL = (21, 22, 15)


def pareto_mask(points):
    """Exact numerical dominance; duplicate nondominated points all survive."""
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or not np.isfinite(points).all():
        raise ValueError("finite two-dimensional frontier points required")
    if not len(points):
        return np.zeros(0, dtype=bool)
    unique, inverse = np.unique(points, axis=0, return_inverse=True)
    # np.unique sorts lexicographically. A later unique point cannot dominate
    # an earlier point, so only the retained skyline needs to be inspected.
    skyline, count = np.empty_like(unique), 0
    keep = np.zeros(len(unique), dtype=bool)
    for i, point in enumerate(unique):
        if count and np.any(np.all(skyline[:count] <= point, axis=1)):
            continue
        skyline[count], count, keep[i] = point, count + 1, True
    return keep[inverse]


def cost_views(current, folds, collection, protocol, reference_id):
    """No target counts enter: H past origins x (identity + grid) x K classes."""
    known, priors = np.asarray(collection["known_service_codes"]), np.asarray(collection["known_priors"])
    if any(app not in known for app in FOCAL):
        raise ValueError("original class set must contain APP21, APP22 and APP15")
    focal = [int(np.flatnonzero(known == app)[0]) for app in FOCAL]
    n, h, k = len(current["rows"]) + 1, len(folds), len(known)
    table = past_table(current, folds, collection, protocol)
    complete = bool(table[0]["history_complete"])
    ns = np.stack([f["ns"] if f else np.zeros(k, dtype=np.int64) for f in folds])
    deltas = np.zeros((h, n, k), dtype=np.int64)
    for j, fold in enumerate(folds):
        if fold is not None:
            deltas[j, 1:] = fold["deltas"]
    support = np.array([complete] + [r["common_support"] for r in table], dtype=bool)
    ref = 0 if reference_id is None else reference_id + 1
    if not 0 <= ref < n:
        raise ValueError("reference candidate is outside the unchanged grid")
    views = {}
    for scope in ("latest", "all"):
        if not complete:
            views[scope] = {"points": np.full((n, 5), np.nan), "original": np.zeros(n, dtype=bool),
                "no_harm": np.zeros(n, dtype=bool), "keep_gains": np.zeros(n, dtype=bool)}
            continue
        if scope == "latest":
            changes, denominators = deltas[-1:], ns[-1:]
        else:
            # Preserve the original pooled budgets as well as each month.
            changes = np.concatenate((deltas, deltas.sum(axis=0, keepdims=True)))
            denominators = np.concatenate((ns, ns.sum(axis=0, keepdims=True)))
        rates = changes / denominators[:, None, :]
        gain = -(rates[-1] @ priors)  # latest month or class-count pooled gain
        costs = rates[:, :, focal].max(axis=0)
        raw = changes.sum(axis=2).max(axis=0)
        original = support & (costs[:, 0] <= protocol["APP21_validation_budget_pp"] / 100 + 1e-12) & (
            raw <= protocol["maximum_validation_raw_wrong_increase"])
        no_harm = original & np.all(changes[:, :, focal[1:]] <= 0, axis=(0, 2))
        # Integer comparisons against min(root, source-latest family) retain
        # existing gains without allowing that reference's existing harms.
        limits = np.minimum(0, changes[:, ref, focal[1:]])
        retain = np.all(changes[:, :, focal[1:]] <= limits[:, None, :], axis=(0, 2))
        views[scope] = {"points": np.column_stack((-gain, costs, raw)), "original": original,
            "no_harm": no_harm, "keep_gains": original & retain}
    return {"ns": ns, "deltas": deltas, "support": support, "views": views,
            "history_available": np.array([f is not None for f in folds]), "reference_index": ref}


def choose(current, view, group):
    scope, guard = group.split("_", 1)
    feasible = view[guard]
    best, gain = 0, 0.
    for i in np.flatnonzero(feasible):
        value = -view["points"][i, 0]
        if i == 0:
            continue
        candidate = current["rows"][i - 1]
        tie = (candidate["observed_fit_leaves"], candidate["candidate_id"])
        old_tie = (current["rows"][best - 1]["observed_fit_leaves"], best - 1) if best else (0, -1)
        if value > gain + 1e-12 or value > 1e-12 and abs(value - gain) <= 1e-12 and tie < old_tie:
            best, gain = int(i), float(value)
    status = "selected" if best else "identity_no_positive_feasible_gain" if feasible.any() else "identity_no_feasible_rule"
    if not np.isfinite(view["points"]).all():
        status = "identity_incomplete_history"
    rule = {k: v for k, v in current["rows"][best - 1].items()
            if not k.startswith("validation_") and k != "APP21_validation_conditional_change"} if best else None
    return {"rule": rule, "status": status, "selection_gain": gain,
            "past_feasible_count": int(feasible.sum()), "past_identity_feasible": bool(feasible[0]),
            "past_positive_feasible_count": int(np.sum(feasible & (view["points"][:, 0] < -1e-12))),
            "past_selected_feasible": bool(feasible[best]), "candidate_index": best,
            "objective": "latest_gain" if scope == "latest" else "pooled_gain"}


def select_tradeoffs(roles, collection, protocol, source_selected):
    """Select, audit and construct frontiers using only FIT and past roles."""
    tables = build_tables(roles, collection, protocol)
    old = {(r["target"], r["model"], r["group"]): r for r in source_selected["selections"]}
    selections, frontiers, summaries, past_classes, arrays, index = [], [], [], [], {}, []
    priors, known = np.asarray(collection["known_priors"]), np.asarray(collection["known_service_codes"])
    for number, context in enumerate(collection["window_spec"]["contexts"]):
        common = {key: context[key] for key in ("target", "period", "model")}
        current, folds = tables[context["target"], context["model"]]
        prefix = "context_" + str(number)
        record = {**common, "prefix": prefix, "history_node_ids": context["history_node_ids"], "available_current": current is not None}
        index.append(record)
        if current is None:
            selections.extend({**common, "group": g, "rule": None, "status": "unavailable_current_fit"} for g in GROUPS)
            continue
        reference = old[context["target"], context["model"], "latest_month"]["rule"]
        ref_id = reference["candidate_id"] if reference else None
        data = cost_views(current, folds, collection, protocol, ref_id)
        record.update(reference_source_latest_candidate=ref_id, candidate_ids=[-1] + [r["candidate_id"] for r in current["rows"]])
        for field in ("ns", "deltas", "support", "history_available"):
            arrays[prefix + "_" + field] = data[field]
        chosen = {}
        for group in GROUPS:
            scope = group.split("_", 1)[0]
            choice = choose(current, data["views"][scope], group)
            chosen[group] = choice["candidate_index"]
            hist_labels = [f["rows"][choice["candidate_index"] - 1]["prediction_APPs"]
                if f is not None and choice["candidate_index"] else None for f in folds]
            selections.append({**common, "group": group, **choice, "history_node_ids": context["history_node_ids"],
                "historical_prediction_APPs": hist_labels, "reference_source_latest_candidate": ref_id})
        for scope, view in data["views"].items():
            full, budget = np.zeros(len(data["support"]), dtype=bool), np.zeros(len(data["support"]), dtype=bool)
            for mask, domain in ((full, data["support"]), (budget, view["original"])):
                ids = np.flatnonzero(domain)
                mask[ids] = pareto_mask(view["points"][ids])
            for field, value in {**view, "frontier": full, "budget_frontier": budget}.items():
                arrays[prefix + "_" + scope + "_" + field] = value
            summaries.append({**common, "view": scope, "candidate_count_with_identity": len(full), "common_support": int(data["support"].sum()),
                "frontier_count": int(full.sum()), "original_budget_feasible": int(view["original"].sum()),
                "budget_frontier_count": int(budget.sum()), "no_harm_feasible": int(view["no_harm"].sum()),
                "keep_gains_feasible": int(view["keep_gains"].sum()),
                "no_harm_positive": int(np.sum(view["no_harm"] & (view["points"][:, 0] < -1e-12))),
                "keep_gains_positive": int(np.sum(view["keep_gains"] & (view["points"][:, 0] < -1e-12)))})
            ids = set(np.flatnonzero(full | budget).tolist())
            ids.update(i for g, i in chosen.items() if g.startswith(scope + "_"))
            for i in sorted(ids):
                point = view["points"][i]
                frontiers.append({**common, "view": scope, "candidate_id": i - 1,
                    "common_support": bool(data["support"][i]), "frontier": bool(full[i]), "budget_frontier": bool(budget[i]),
                    "original_budget_ok": bool(view["original"][i]), "no_harm_ok": bool(view["no_harm"][i]),
                    "keep_gains_ok": bool(view["keep_gains"][i]),
                    "gain": float(-point[0]) if np.isfinite(point[0]) else None,
                    **{name: float(v) if np.isfinite(v) else None for name, v in zip(("APP21_cost", "APP22_cost", "APP15_cost", "raw_cost"), point[1:])},
                    "selected_groups": ",".join(g for g, j in chosen.items() if i == j and g.startswith(scope + "_"))})
        for group, i in chosen.items():
            for origin in range(len(folds) + 1):
                pooled = origin == len(folds)
                available = bool(data["history_available"].all()) if pooled else bool(data["history_available"][origin])
                ns = data["ns"].sum(axis=0) if pooled else data["ns"][origin]
                delta = data["deltas"][:, i].sum(axis=0) if pooled else data["deltas"][origin, i]
                ref = data["deltas"][:, data["reference_index"]].sum(axis=0) if pooled else data["deltas"][origin, data["reference_index"]]
                for j, app in enumerate(known):
                    observed = available and ns[j] > 0
                    past_classes.append({**common, "group": group, "candidate_id": i - 1,
                        "validation_origin": "pooled" if pooled else context["history_node_ids"][origin],
                        "APP": int(app), "prior": float(priors[j]), "n": int(ns[j]), "available": available,
                        "wrong_change_vs_root": int(delta[j]) if available else None,
                        "conditional_change_vs_root": float(delta[j] / ns[j]) if observed else None,
                        "weighted_change_vs_root": float(priors[j] * delta[j] / ns[j]) if observed else None,
                        "reference_wrong_change_vs_root": int(ref[j]) if available else None,
                        "wrong_change_vs_reference_family": int(delta[j] - ref[j]) if available else None})
    return {"selections": selections, "frontiers": frontiers, "frontier_summary": summaries,
            "past_classes": past_classes, "arrays": arrays, "array_index": index}


def evaluate_tradeoffs(cache, roles, joints, atoms, collection, protocol, selected, source_selected, source_result, previous, *, small_n=200):
    """Score only frozen policies, preserving every original class and control."""
    slots = ("fit_only", "latest_month", "pooled_months", "all_months")
    rename = dict(zip(slots, GROUPS))
    adapted = [r for r in source_selected["selections"] if r["group"] == "time_baseline"]
    adapted += [{**r, "group": slots[GROUPS.index(r["group"])]} for r in selected["selections"]]
    batch = evaluate_forward(cache, roles, joints, atoms, collection, protocol, {"selections": adapted}, previous, small_n=small_n)
    roots = {(r["target"], r["model"]): r["counts_true_by_predicted"] for r in source_result["confusions"] if r["group"] == "time_baseline"}
    for r in batch["confusions"]:
        if r["group"] == "time_baseline" and r["counts_true_by_predicted"] != roots[r["target"], r["model"]]:
            raise RuntimeError("cost selector changed the common baseline")
    result = {name: [dict(r) for r in source_result[name]] + [{**r, "group": rename[r["group"]]} for r in batch[name] if r["group"] in rename]
        for name in ("metrics", "classes", "confusions", "budget_monthly", "budget_summary")}
    ref = {(r["scope"], r["target"], r["model"], r["APP"]): r for r in result["classes"] if r["group"] == "source_latest"}
    buckets = {}
    for r in result["classes"]:
        reference = ref[r["scope"], r["target"], r["model"], r["APP"]]
        delta = r["wrong"] - reference["wrong"] if r["wrong"] is not None and reference["wrong"] is not None else None
        rate = delta / r["n"] if delta is not None and r["n"] else None
        local = r["wrong_change_vs_time_baseline"]
        r.update(wrong_change_vs_source_latest=delta, conditional_change_vs_source_latest=rate,
            weighted_change_vs_source_latest=r["prior"] * rate if rate is not None else None,
            conditional_change_vs_time_baseline=local / r["n"] if local is not None and r["n"] else None)
        buckets.setdefault((r["scope"], r["target"], r["model"], r["group"]), []).append(r)
    for r in result["metrics"]:
        rows = buckets[r["scope"], r["target"], r["model"], r["group"]]
        valid = all(c["wrong_change_vs_source_latest"] is not None for c in rows)
        rates = np.array([c["conditional_change_vs_source_latest"] if c["conditional_change_vs_source_latest"] is not None else np.nan for c in rows])
        r["change_vs_source_latest"] = weighted_range(rates, cache["priors"], signed=True) if valid else None
        r["raw_change_vs_source_latest"] = sum(c["wrong_change_vs_source_latest"] for c in rows) if valid else None
    result["compatibility"] = []
    selections = {(r["target"], r["model"], r["group"]): r for r in selected["selections"]}
    for metric in result["metrics"]:
        if metric["scope"] != "monthly":
            continue
        token = metric["scope"], metric["target"], metric["model"], metric["group"]
        rows = {r["APP"]: r for r in buckets[token]}
        values = {app: rows[app]["conditional_change_vs_time_baseline"] for app in FOCAL}
        refs = {app: ref[token[0], token[1], token[2], app]["conditional_change_vs_time_baseline"] for app in FOCAL}
        raw = metric["raw_change_vs_time_baseline"]
        complete = raw is not None and all(v is not None for v in values.values())
        legacy = bool(values[21] <= protocol["APP21_validation_budget_pp"] / 100 + 1e-12 and
            raw <= protocol["maximum_validation_raw_wrong_increase"]) if raw is not None and values[21] is not None else None
        no_harm = bool(legacy and all(rows[a]["wrong_change_vs_time_baseline"] <= 0 for a in (22, 15))) if complete else None
        keep = bool(legacy and all(rows[a]["wrong_change_vs_time_baseline"] <= min(0,
            ref[token[0], token[1], token[2], a]["wrong_change_vs_time_baseline"]) for a in (22, 15))) if complete and all(refs[a] is not None for a in (22, 15)) else None
        choice = selections.get((token[1], token[2], token[3]))
        result["compatibility"].append({**{k: metric[k] for k in ("target", "period", "model", "group", "status")},
            **{"APP" + str(a) + "_change": values[a] for a in FOCAL}, "raw_change": raw,
            "legacy_met": legacy, "root_joint_met": no_harm, "keep_joint_met": keep,
            "APP22_vs_latest": rows[22]["conditional_change_vs_source_latest"],
            "APP15_vs_latest": rows[15]["conditional_change_vs_source_latest"],
            "identity": choice["rule"] is None if choice and metric["status"] == "complete" else None,
            "selection_status": choice["status"] if choice else None})
    return result
