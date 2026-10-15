"""Forward monthly validation of split families with origin-specific fitted labels."""

from __future__ import annotations

import itertools

import numpy as np

from .jointrefinement import changes, child_counts, fit_candidates, root_model, rule_evaluation, time_children
from .monthlydrift import optional, weighted_range
from .realdata import DAY, whole_interval_mask
from .refinement import RefinementCounts
from .regionalvalidation import matrix_result, signed_rates, splice_background
from .rolling import month_index, month_label

GROUPS = ("previous_time", "previous_blocks", "time_baseline", "fit_only", "latest_month", "pooled_months", "all_months")
FIELDS = ("base", "children", "single", "joint")


def forward_windows(slices, original_windows, *, history=3, gap=DAY):
    """Calendar-only fit and whole-month validation roles; no sample counts used."""
    if history < 2 or gap < 0:
        raise ValueError("at least two past validation months and nonnegative gap required")
    by_month = {s["month_utc"]: s for s in slices}
    if len(by_month) != len(slices):
        raise ValueError("one audited slice per calendar month required")
    old = {(c["target"], c["model"]): c for c in original_windows["contexts"]}
    fixed = next(c for c in original_windows["contexts"] if c["model"] == "fixed_pilot" and "fit_id" in c)
    ranges, nodes = {}, []

    def role(begin, end):
        if begin >= end:
            raise ValueError("empty forward role")
        bounds = int(begin), int(end)
        if bounds not in ranges:
            ranges[bounds] = "f" + str(len(ranges))
        return ranges[bounds]

    for month, target in sorted(by_month.items()):
        for model in ("fixed_pilot", "rolling_1m", "rolling_3m"):
            row = {"id": month + "/" + model, "month": month, "month_key": target["key"], "model": model,
                   "validation_id": role(target["start_epoch"], target["end_epoch"]), "validation_start_epoch": target["start_epoch"],
                   "validation_end_epoch": target["end_epoch"], "status": "ready"}
            if model == "fixed_pilot":
                begin, end = fixed["fit_start_epoch"], fixed["fit_end_epoch"]
                selected = [s for s in slices if s["period"] == "pilot"]
                if end + gap > target["start_epoch"]:
                    row["status"] = "unavailable_fixed_fit_not_in_past"
            else:
                width = 1 if model == "rolling_1m" else 3
                required = [month_label(i) for i in range(month_index(month) - width, month_index(month))]
                selected = [by_month[m] for m in required if m in by_month]
                if len(selected) != width:
                    row["status"] = "unavailable_fit_calendar"
                begin = min((s["start_epoch"] for s in selected), default=0)
                end = min(max((s["end_epoch"] for s in selected), default=0), target["start_epoch"] - gap)
                if begin >= end:
                    row["status"] = "unavailable_fit_calendar"
            row["training_slices"] = [s["key"] for s in selected]
            if row["status"] == "ready":
                row.update(fit_id=role(begin, end), fit_start_epoch=begin, fit_end_epoch=end)
                if end + gap > target["start_epoch"]:
                    raise ValueError("forward fitting overlaps its validation month")
            nodes.append(row)
    contexts = []
    for target in (s for s in slices if s["period"] != "pilot"):
        for model in ("fixed_pilot", "rolling_1m", "rolling_3m"):
            previous = [month_label(i) for i in range(month_index(target["month_utc"]) - history, month_index(target["month_utc"]))]
            contexts.append({"target": target["key"], "period": target["period"], "model": model,
                "node_id": target["month_utc"] + "/" + model, "history_node_ids": [m + "/" + model for m in previous],
                "target_start_epoch": target["start_epoch"], "original_training_slices": old[target["key"], model]["training_slices"]})
    needed = {c["node_id"] for c in contexts} | {token for c in contexts for token in c["history_node_ids"]}
    nodes = [n for n in nodes if n["id"] in needed]
    used = {n["validation_id"] for n in nodes} | {n["fit_id"] for n in nodes if "fit_id" in n}
    return {"history_months": history, "gap_seconds": gap, "contexts": contexts, "nodes": nodes,
            "ranges": [{"id": token, "start_epoch": bounds[0], "end_epoch": bounds[1]} for bounds, token in ranges.items() if token in used]}


class ForwardCounts(RefinementCounts):
    """Collect collapsed low-IPT pair atoms for exact whole-flow calendar roles."""

    def __init__(self, plan, tables, *, time_scale, previous_protocol, windows, threshold):
        super().__init__(plan, tables, time_scale=time_scale, symbol=previous_protocol["symbol_id"],
                         size_cuts=previous_protocol["size_candidates_bytes"], ipt_cuts=previous_protocol["IPT2_candidates_ms"], positions=previous_protocol["size_positions"])
        self.threshold, self.window_spec = threshold, windows
        self.pairs = tuple(itertools.combinations(self.positions, 2))
        k, bins = len(self.known), len(self.size_cuts) + 1
        cells = len(windows["ranges"]) * len(self.pairs) * k * bins * bins
        if cells > 64000000:
            raise ValueError("forward pair-role cache exceeds its memory budget")
        self.roles = {r["id"]: {"base": np.zeros_like(self.counts["pilot"][2]), "children": np.zeros((k, 3), dtype=np.int64),
            "single": np.zeros((len(self.positions), k, bins), dtype=np.int64), "joint": np.zeros((len(self.pairs), k, bins, bins), dtype=np.int64)} for r in windows["ranges"]}

    def add(self, records, capacity):
        super().add(records, capacity)
        first, last = (np.asarray(records[field], dtype=float) / self.time_scale for field in ("TIME_FIRST", "TIME_LAST"))
        lengths, labels = np.asarray(records["PPI_LEN"], dtype=float), np.asarray(records["APP"])
        usable = (np.isfinite(first) & np.isfinite(last) & (last >= first) & np.isfinite(lengths) &
                  (lengths == np.floor(lengths)) & (lengths >= self.k) & (lengths <= capacity) & np.isin(labels, self.known))
        for period, bounds in self.windows.items():
            keep = usable & whole_interval_mask(first, last, bounds, self.rounding)
            if not keep.any():
                continue
            ppi, starts, ends = records["PPI"][keep], first[keep], last[keep]
            app, symbols = np.searchsorted(self.known, labels[keep]), self.encoders[2].encode(ppi)
            ipt = np.asarray(ppi[:, 0, 1], dtype=float)
            branch = np.where(np.isfinite(ipt) & (ipt >= 0), np.where(ipt <= self.threshold, 0, 1), 2)
            indices = [np.searchsorted(self.size_cuts, ppi[:, 2, p - 1], side="left") for p in self.positions]
            for window in self.window_spec["ranges"]:
                chosen = whole_interval_mask(starts, ends, (window["start_epoch"], window["end_epoch"]), self.rounding)
                if not chosen.any():
                    continue
                role = self.roles[window["id"]]
                np.add.at(role["base"], (app[chosen], symbols[chosen]), 1)
                cell = chosen & (symbols == self.symbol)
                np.add.at(role["children"], (app[cell], branch[cell]), 1)
                low = cell & (branch == 0)
                for j, size in enumerate(indices):
                    np.add.at(role["single"][j], (app[low], size[low]), 1)
                for j, (left, right) in enumerate(self.pairs):
                    np.add.at(role["joint"][j], (app[low], indices[self.positions.index(left)][low], indices[self.positions.index(right)][low]), 1)


def check_roles(roles, collection):
    pairs, positions, symbol = tuple(map(tuple, collection["size_pairs"])), tuple(collection["size_positions"]), collection["symbol_id"]
    for role in roles.values():
        if not np.array_equal(role["children"].sum(axis=1), role["base"][:, symbol]) or not np.all(role["single"].sum(axis=2) == role["children"][:, 0][None, :]):
            raise ValueError("forward role does not conserve local flows")
        for j, (left, right) in enumerate(pairs):
            if not np.array_equal(role["joint"][j].sum(axis=2), role["single"][positions.index(left)]) or not np.array_equal(role["joint"][j].sum(axis=1), role["single"][positions.index(right)]):
                raise ValueError("forward pair atoms do not project to singles")


def role_data(role, collection):
    return {**role, "positions": tuple(collection["size_positions"]), "pairs": tuple(map(tuple, collection["size_pairs"]))}


def scored_family(fit, validation, collection, minimum):
    known, priors = np.asarray(collection["known_service_codes"]), np.asarray(collection["known_priors"])
    prediction, leaves = root_model(fit["base"], fit["children"], priors, collection["symbol_id"])
    old = int(prediction[leaves[0]])
    rows = fit_candidates(fit, validation, priors, known, old, fit["positions"], fit["pairs"], collection["size_candidates_bytes"], minimum=minimum)
    ns = validation["base"].sum(axis=1)
    deltas = np.stack([changes(child_counts(validation, row, fit["positions"], fit["pairs"]), np.asarray(row["prediction_indices"]), old, ns, priors)[0] for row in rows])
    return {"rows": rows, "deltas": deltas, "ns": ns, "protected_parent": int(known[old]) == 34,
            "fit_ns": fit["base"].sum(axis=1), "root_APP": int(known[old])}


def select_context(current, folds, collection, protocol):
    """Only current FIT data and strictly past folds enter family selection."""
    priors, known = np.asarray(collection["known_priors"]), np.asarray(collection["known_service_codes"])
    cap, raw_cap = protocol["APP21_validation_budget_pp"] / 100, protocol["maximum_validation_raw_wrong_increase"]
    selected, summaries = {}, []
    for group in GROUPS[3:]:
        use = folds[-1:] if group == "latest_month" else folds
        best, score = None, 0.
        reason = "identity_no_positive_qualified_gain"
        if current["protected_parent"]:
            reason = "identity_APP34_parent_protection"
        elif group != "fit_only" and any(f is None for f in use):
            reason = "identity_unavailable_past_month"
        elif group != "fit_only" and any(np.any(f["ns"] == 0) for f in use):
            reason = "identity_missing_validation_classes"
        else:
            for index, candidate in enumerate(current["rows"]):
                eligible = candidate["eligible"]
                value, raw, app21, monthly_caps = candidate["fit_gain"], None, None, None
                if group != "fit_only":
                    eligible = eligible and all(f["rows"][index]["eligible"] and not f["protected_parent"] for f in use)
                    ns, delta = sum(f["ns"] for f in use), sum(f["deltas"][index] for f in use)
                    rates = signed_rates(delta, ns)
                    value, raw = -float(np.dot(priors, rates)), int(delta.sum())
                    app21 = float(rates[np.flatnonzero(known == 21)[0]]) if 21 in known else 0.
                    monthly_caps = all(f["rows"][index]["validation_raw_wrong_change"] <= raw_cap and
                        (21 not in known or f["rows"][index]["APP21_validation_conditional_change"] <= cap + 1e-12) for f in use)
                    eligible = eligible and raw <= raw_cap and app21 <= cap + 1e-12 and (group != "all_months" or monthly_caps)
                summaries.append({"group": group, "candidate_id": index, "eligible": bool(eligible), "gain": value,
                    "pooled_raw_change": raw, "pooled_APP21_change": app21, "all_month_budgets_met": monthly_caps,
                    "current_fit_gain": candidate["fit_gain"], "current_fit_eligible": candidate["eligible"],
                    "month_weighted_changes": [f["rows"][index]["validation_weighted_change"] for f in use] if group != "fit_only" else [],
                    "month_raw_changes": [f["rows"][index]["validation_raw_wrong_change"] for f in use] if group != "fit_only" else [],
                    "month_APP21_changes": [f["rows"][index]["APP21_validation_conditional_change"] for f in use] if group != "fit_only" else [],
                    "month_fit_eligible": [bool(f["rows"][index]["eligible"] and not f["protected_parent"]) for f in use] if group != "fit_only" else []})
                if eligible and (value > score + 1e-12 or best is not None and value > 1e-12 and abs(value - score) <= 1e-12 and
                        (candidate["observed_fit_leaves"], index) < (best["observed_fit_leaves"], best["candidate_id"])):
                    best, score = candidate, value
            if best is not None:
                reason = "selected"
        # Current self-fit validation fields are training quantities, not historical holdout estimates.
        rule = {k: v for k, v in best.items() if not k.startswith("validation_") and k != "APP21_validation_conditional_change"} if best else None
        selected[group] = {"status": reason, "rule": rule, "selection_gain": score if best else 0.}
    return selected, summaries


def select_forward(roles, collection, protocol):
    nodes = {n["id"]: n for n in collection["window_spec"]["nodes"]}
    minimum = protocol["minimum_fit_leaf_flows"]
    trained, validated = {}, {}

    def training(node):
        if node["status"] != "ready" or np.any(roles[node["fit_id"]]["base"].sum(axis=1) == 0):
            return None
        if node["fit_id"] not in trained:
            fit = role_data(roles[node["fit_id"]], collection)
            trained[node["fit_id"]] = scored_family(fit, fit, collection, minimum)
        return trained[node["fit_id"]]

    selections, candidates, fold_rows, coverage = [], [], [], []
    for context in collection["window_spec"]["contexts"]:
        common = {k: context[k] for k in ("target", "period", "model")}
        current = training(nodes[context["node_id"]])
        if current is None:
            selections.extend({**common, "group": g, "status": "unavailable_current_fit", "rule": None} for g in GROUPS[2:])
            continue
        folds = []
        for token in context["history_node_ids"]:
            node = nodes.get(token)
            if node is None or training(node) is None:
                folds.append(None)
                continue
            if node["validation_end_epoch"] > context["target_start_epoch"]:
                raise ValueError("a historical validation month reaches the target")
            if token not in validated:
                fit = role_data(roles[node["fit_id"]], collection)
                val = role_data(roles[node["validation_id"]], collection)
                validated[token] = scored_family(fit, val, collection, minimum)
            f = validated[token]
            folds.append(f)
            coverage.extend({**common, "validation_origin": token, "APP": int(app), "n": int(f["ns"][i]), "fit_n": int(f["fit_ns"][i]),
                             "prior": float(collection["known_priors"][i])} for i, app in enumerate(collection["known_service_codes"]))
        choices, scores = select_context(current, folds, collection, protocol)
        selections.append({**common, "group": "time_baseline", "status": "identity_baseline", "rule": None})
        for group, choice in choices.items():
            selections.append({**common, "group": group, **choice, "current_fit_role": nodes[context["node_id"]]["fit_id"],
                               "history_node_ids": context["history_node_ids"], "historical_labels_refitted_per_origin": True})
            index = choice["rule"]["candidate_id"] if choice["rule"] else None
            for token, f in zip(context["history_node_ids"], folds):
                r = f["rows"][index] if f is not None and index is not None else None
                fold_rows.append({**common, "group": group, "validation_origin": token, "candidate_id": index,
                    "available": f is not None, "identity_current_choice": index is None,
                    "historical_prediction_APPs": r["prediction_APPs"] if r else None, "historical_eligible": r["eligible"] if r else None,
                    "historical_parent_APP": f["root_APP"] if f else None,
                    "weighted_change": r["validation_weighted_change"] if r else 0. if f is not None and index is None else None,
                    "raw_change": r["validation_raw_wrong_change"] if r else 0 if f is not None and index is None else None,
                    "APP21_change": r["APP21_validation_conditional_change"] if r else 0. if f is not None and index is None else None})
        candidates.extend({**common, **r} for r in scores)
    return {"selections": selections, "candidates": candidates, "folds": fold_rows, "coverage": coverage}


def evaluate_forward(cache, roles, joints, atoms, collection, protocol, selected, previous, *, small_n=200):
    known, priors, symbol = cache["known"], cache["priors"], collection["symbol_id"]
    nodes = {n["id"]: n for n in collection["window_spec"]["nodes"]}
    choices = {(r["target"], r["model"], r["group"]): r for r in selected["selections"]}
    values, transfers, matrices, budgets = {}, {}, [], []
    for c in collection["window_spec"]["contexts"]:
        key, model = c["target"], c["model"]
        target = {"base": cache["counts"][key][2], "children": time_children(atoms[key], collection["IPT2_candidates_ms"], collection["fixed_IPT2_threshold_ms"]),
                  "single": atoms[key][:, :, :, :collection["low_time_atoms"]].sum(axis=3), "joint": joints[key].sum(axis=4),
                  "positions": tuple(collection["size_positions"]), "pairs": tuple(map(tuple, collection["size_pairs"]))}
        ns = target["base"].sum(axis=1)
        for group in GROUPS[:2]:
            matrix = previous.get((key, model, group))
            if matrix is not None:
                values[key, model, group] = matrix_result(matrix, ns, priors)
        if choices[key, model, "time_baseline"]["status"] == "unavailable_current_fit":
            continue
        fit = roles[nodes[c["node_id"]]["fit_id"]]
        prediction, leaves = root_model(fit["base"], fit["children"], priors, symbol)
        full_base = sum(cache["counts"][name][2] for name in c["original_training_slices"])
        full_child = sum(time_children(atoms[name], collection["IPT2_candidates_ms"], collection["fixed_IPT2_threshold_ms"]) for name in c["original_training_slices"])
        full_prediction, _ = root_model(full_base, full_child, priors, symbol)
        prediction = splice_background(prediction, full_prediction, full_base.shape[1], symbol)
        for group in GROUPS[2:]:
            choice = choices[key, model, group]
            value, transfer = rule_evaluation(target, choice["rule"], prediction, leaves, priors, symbol)
            values[key, model, group], transfers[key, model, group] = value, transfer
            root = values[key, model, "time_baseline"]
            delta = value["wrong_counts"] - root["wrong_counts"]
            if any(h - r != delta[i] or int(known[i]) == 34 and h for i, (r, h) in enumerate(transfer)):
                raise RuntimeError("forward local transfers or APP34 protection failed")
            rates = signed_rates(delta, ns)
            app21 = optional(rates[np.flatnonzero(known == 21)[0]]) if 21 in known else 0.
            app21_met = app21 <= protocol["APP21_validation_budget_pp"] / 100 + 1e-12 if app21 is not None else None
            raw_met = int(delta.sum()) <= protocol["maximum_validation_raw_wrong_increase"]
            budgets.append({"target": key, "period": c["period"], "model": model, "group": group, "APP21_change": app21, "raw_change": int(delta.sum()),
                "APP21_met": app21_met, "raw_met": raw_met, "both_met": bool(app21_met and raw_met) if app21_met is not None else None,
                "identity": choice["rule"] is None, "status": choice["status"]})
    metrics, classes = [], []
    for (key, model, group), value in values.items():
        matrices.append({"target": key, "model": model, "group": group, "counts_true_by_predicted": value["confusion"].tolist()})
    for scope in ("monthly", "period"):
        targets = [(s["key"], s["period"], [s["key"]]) for s in cache["slices"] if s["period"] != "pilot"] if scope == "monthly" else [
            (p, p, [s["key"] for s in cache["slices"] if s["period"] == p]) for p in ("certificate", "evaluation")]
        for target, period, keys in targets:
            ns = sum(cache["counts"][key][2].sum(axis=1) for key in keys)
            for model, group in itertools.product(protocol["models"], GROUPS):
                common = {"scope": scope, "target": target, "period": period, "model": model, "group": group}
                available = all((key, model, group) in values for key in keys)
                value, deltas, rates = None, {}, {}
                if available:
                    value = matrix_result(sum(values[key, model, group]["confusion"] for key in keys), ns, priors)
                    for ref in ("time_baseline", "previous_time", "previous_blocks"):
                        if all((key, model, ref) in values for key in keys):
                            deltas[ref] = value["wrong_counts"] - sum(values[key, model, ref]["wrong_counts"] for key in keys)
                            rates[ref] = signed_rates(deltas[ref], ns)
                row = {**common, "status": "complete" if available else "unavailable_fit_model", "weighted_error": value["summary"]["weighted_error"] if value else None,
                       "raw_wrong": int(value["wrong_counts"].sum()) if value else None}
                for ref in ("time_baseline", "previous_time", "previous_blocks"):
                    row["change_vs_" + ref] = weighted_range(rates[ref], priors, signed=True) if ref in rates else None
                    row["raw_change_vs_" + ref] = int(deltas[ref].sum()) if ref in deltas else None
                for app in (2, 21, 34):
                    row[f"APP{app}_error"] = optional(value["errors"][np.flatnonzero(known == app)[0]]) if value and app in known else None
                metrics.append(row)
                for i, app in enumerate(known):
                    t = [transfers.get((key, model, group)) for key in keys]
                    r = {**common, "APP": int(app), "prior": float(priors[i]), "n": int(ns[i]), "wrong": int(value["wrong_counts"][i]) if value else None,
                         "error": optional(value["errors"][i]) if value else None, "status": "unavailable" if not value else "missing" if not ns[i] else "small_n" if ns[i] < small_n else "observed",
                         "rescued": sum(x[i][0] for x in t) if all(x is not None for x in t) else None,
                         "harmed": sum(x[i][1] for x in t) if all(x is not None for x in t) else None}
                    for ref in ("time_baseline", "previous_time", "previous_blocks"):
                        r["wrong_change_vs_" + ref] = int(deltas[ref][i]) if ref in deltas else None
                        r["weighted_change_vs_" + ref] = optional(priors[i] * rates[ref][i]) if ref in rates else None
                    classes.append(r)
    summaries = []
    for period, model, group in itertools.product(("certificate", "evaluation"), protocol["models"], GROUPS[2:]):
        rows = [r for r in budgets if (r["period"], r["model"], r["group"]) == (period, model, group)]
        checked = [r for r in rows if r["both_met"] is not None]
        summaries.append({"period": period, "model": model, "group": group, "expected": sum(s["period"] == period for s in cache["slices"]),
            "available": len(rows), "checked": len(checked), "both_met": sum(r["both_met"] for r in checked),
            "APP21_violations": sum(r["APP21_met"] is False for r in checked), "raw_violations": sum(not r["raw_met"] for r in rows),
            "identity": sum(r["identity"] for r in rows)})
    return {"metrics": metrics, "classes": classes, "confusions": matrices, "budget_monthly": budgets, "budget_summary": summaries}
