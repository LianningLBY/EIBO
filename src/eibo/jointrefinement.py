"""Chronological validation of bounded two-size refinements of one low-IPT cell."""

from __future__ import annotations

import itertools

import numpy as np

from .monthlydrift import month_start, optional, weighted_range
from .realdata import DAY, whole_interval_mask
from .realexperiment import histogram_predictions
from .refinement import RefinementCounts, fit_prediction, refine_counts
from .rolling import evaluate, training_window

MATCHED_GROUPS = ("time_fit", "single_fit", "joint_fit", "validation_weighted", "validation_constrained")
GROUPS = MATCHED_GROUPS + ("legacy_time_full", "legacy_hierarchy_full")
FOCAL_APPS = (2, 15, 21, 22, 34)


def validation_windows(cache, models, *, gap=DAY, validation_day=21):
    """Dates use calendar geometry only, including a whole-flow guard later."""
    if gap < 0 or not 2 <= validation_day <= 27:
        raise ValueError("nonnegative gap and validation day between 2 and 27 required")
    ranges, contexts = {}, []
    for target in (s for s in cache["slices"] if s["period"] != "pilot"):
        for model in models:
            window = training_window(cache, target, model)
            selected = [s for s in cache["slices"] if s["key"] in window["training_slices"]]
            context = {"target": target["key"], "period": target["period"], "model": model,
                       "training_slices": window["training_slices"], "target_start_epoch": target["start_epoch"], "status": window["status"]}
            if not selected:
                contexts.append(context)
                continue
            begin, end = min(s["start_epoch"] for s in selected), max(s["end_epoch"] for s in selected)
            cut = int(month_start(selected[-1]["start_epoch"]).timestamp())
            if len(selected) == 1:
                cut += (validation_day - 1) * DAY
            if not begin < cut <= cut + gap < end or end > target["start_epoch"]:
                context["status"] = "unavailable_validation_geometry"
                contexts.append(context)
                continue
            for role, bounds in (("fit", (begin, cut)), ("validation", (cut + gap, end))):
                if bounds not in ranges:
                    ranges[bounds] = "w" + str(len(ranges))
                context[role + "_id"] = ranges[bounds]
                context[role + "_start_epoch"], context[role + "_end_epoch"] = bounds
            contexts.append(context)
    return {"gap_seconds": gap, "validation_day": validation_day, "contexts": contexts,
            "ranges": [{"id": token, "start_epoch": bounds[0], "end_epoch": bounds[1]} for bounds, token in ranges.items()]}


class JointCounts(RefinementCounts):
    """One raw scan reconciles old marginals and collects genuine pair joints."""

    def __init__(self, plan, tables, *, time_scale, previous_protocol, windows, threshold=4.):
        super().__init__(plan, tables, time_scale=time_scale, symbol=previous_protocol["symbol_id"],
                         size_cuts=previous_protocol["size_candidates_bytes"], ipt_cuts=previous_protocol["IPT2_candidates_ms"],
                         positions=previous_protocol["size_positions"])
        if threshold not in self.ipt_cuts or len(self.positions) < 2:
            raise ValueError("fixed timing threshold must be in the verified grid; at least two size positions required")
        self.threshold = float(threshold)
        self.low_time_atoms = int(np.flatnonzero(self.ipt_cuts == threshold)[0]) + 1
        self.pairs = tuple(itertools.combinations(self.positions, 2))
        self.window_spec = windows
        shape = (len(self.pairs), len(self.known), len(self.size_cuts) + 1, len(self.size_cuts) + 1, self.low_time_atoms)
        if np.prod(shape) * (len(self.slices) + len(windows["ranges"])) > 64000000:
            raise ValueError("joint count collection exceeds its aggregate memory budget")
        self.joints = {s["key"]: np.zeros(shape, dtype=np.int64) for s in self.slices}
        self.roles = {r["id"]: {"base": np.zeros_like(self.counts["pilot"][2]), "children": np.zeros((len(self.known), 3), dtype=np.int64),
                      "single": np.zeros((len(self.positions), len(self.known), len(self.size_cuts) + 1, self.low_time_atoms), dtype=np.int64),
                      "joint": np.zeros(shape, dtype=np.int64)} for r in windows["ranges"]}

    def _add_features(self, destination, ppi, app, *, single=None):
        indices = [np.searchsorted(self.size_cuts, ppi[:, 2, p - 1], side="left") for p in self.positions]
        time_atoms = np.searchsorted(self.ipt_cuts, ppi[:, 0, 1], side="left")
        if single is not None:
            for j, atoms in enumerate(indices):
                np.add.at(single[j], (app, atoms, time_atoms), 1)
        for j, (left, right) in enumerate(self.pairs):
            np.add.at(destination[j], (app, indices[self.positions.index(left)], indices[self.positions.index(right)], time_atoms), 1)

    def add(self, records, capacity):
        super().add(records, capacity)
        first, last = (np.asarray(records[field], dtype=float) / self.time_scale for field in ("TIME_FIRST", "TIME_LAST"))
        lengths, labels = np.asarray(records["PPI_LEN"], dtype=float), np.asarray(records["APP"])
        usable = (np.isfinite(first) & np.isfinite(last) & (last >= first) & (first >= self.begin) & (first < self.end) &
                  np.isfinite(lengths) & (lengths == np.floor(lengths)) & (lengths >= self.k) & (lengths <= capacity) & np.isin(labels, self.known))
        for period, bounds in self.windows.items():
            keep = usable & whole_interval_mask(first, last, bounds, self.rounding)
            if not keep.any():
                continue
            ppi, times, endings = records["PPI"][keep], first[keep], last[keep]
            app = np.searchsorted(self.known, labels[keep])
            symbols = self.encoders[2].encode(ppi)
            hit = symbols == self.symbol
            ipt = np.asarray(ppi[:, 0, 1], dtype=float)
            valid = np.isfinite(ipt) & (ipt >= 0)
            branch = np.where(valid, np.where(ipt <= self.threshold, 0, 1), 2)
            months = np.searchsorted(self.slice_starts[period], times, side="right") - 1
            for month in np.unique(months):
                mask = (months == month) & hit & (branch == 0)
                if mask.any():
                    self._add_features(self.joints[self.slice_keys[period][int(month)]], ppi[mask], app[mask])
            for window in self.window_spec["ranges"]:
                chosen = whole_interval_mask(times, endings, (window["start_epoch"], window["end_epoch"]), self.rounding)
                if not chosen.any():
                    continue
                role = self.roles[window["id"]]
                np.add.at(role["base"], (app[chosen], symbols[chosen]), 1)
                cell = chosen & hit
                np.add.at(role["children"], (app[cell], branch[cell]), 1)
                low = cell & (branch == 0)
                if low.any():
                    self._add_features(role["joint"], ppi[low], app[low], single=role["single"])

    def reconcile_joint(self, cache, old_atoms):
        self.reconcile_cache(cache)
        for key in self.atoms:
            if not np.array_equal(self.atoms[key], old_atoms[key]):
                raise ValueError("raw single-position atoms differ from stage 8")
            single = old_atoms[key][:, :, :, :self.low_time_atoms]
            check_joint(self.joints[key], single, self.pairs, self.positions)
        for role in self.roles.values():
            if not np.array_equal(role["children"].sum(axis=1), role["base"][:, self.symbol]):
                raise ValueError("fit/validation time children do not conserve original cell counts")
            check_joint(role["joint"], role["single"], self.pairs, self.positions)
            if not np.all(role["single"].sum(axis=(2, 3)) == role["children"][:, 0][None, :]):
                raise ValueError("fit/validation low marginals differ from timing children")
        for context in self.window_spec["contexts"]:
            if "fit_id" not in context:
                continue
            full = sum(cache["counts"][key][2].sum(axis=1) for key in context["training_slices"])
            observed = self.roles[context["fit_id"]]["base"].sum(axis=1) + self.roles[context["validation_id"]]["base"].sum(axis=1)
            if np.any(observed > full):
                raise ValueError("fit/validation flows exceed full past-window population")


def low_marginals(atoms, ipt_cuts, threshold):
    stop = int(np.flatnonzero(np.asarray(ipt_cuts) == threshold)[0]) + 1
    return atoms[:, :, :, :stop].sum(axis=3)


def time_children(atoms, ipt_cuts, threshold):
    stop = int(np.flatnonzero(np.asarray(ipt_cuts) == threshold)[0]) + 1
    values = atoms[0].sum(axis=1)
    return np.stack((values[:, :stop].sum(axis=1), values[:, stop:-1].sum(axis=1), values[:, -1]), axis=1)


def check_joint(joint, single, pairs, positions):
    for j, (left, right) in enumerate(pairs):
        if (not np.array_equal(joint[j].sum(axis=2), single[positions.index(left)])
                or not np.array_equal(joint[j].sum(axis=1), single[positions.index(right)])):
            raise ValueError("joint counts do not project to saved single-position marginals")


def root_model(base, children, priors, symbol):
    coarse, _ = histogram_predictions(base, priors)
    refined = refine_counts(base, children, symbol)
    prediction, leaves, _ = fit_prediction(refined, priors, coarse, symbol, base.shape[1])
    return prediction, leaves


def child_counts(data, rule, positions, pairs):
    if rule is None:
        return data["children"][:, :1]
    if rule["kind"] == "single":
        marginal = data["single"][positions.index(rule["positions"][0])]
        left = marginal[:, :rule["indices"][0] + 1].sum(axis=1)
        return np.stack((left, marginal.sum(axis=1) - left), axis=1)
    values = data["joint"][pairs.index(tuple(rule["positions"]))]
    i, j = rule["indices"]
    return np.stack((values[:, :i + 1, :j + 1].sum(axis=(1, 2)), values[:, :i + 1, j + 1:].sum(axis=(1, 2)),
                     values[:, i + 1:, :j + 1].sum(axis=(1, 2)), values[:, i + 1:, j + 1:].sum(axis=(1, 2))), axis=1)


def changes(children, labels, old_label, ns, priors):
    correct = (children * (labels[None, :] == np.arange(len(ns))[:, None])).sum(axis=1)
    old_correct = np.zeros(len(ns), dtype=np.int64)
    old_correct[old_label] = children[old_label].sum()
    delta = old_correct - correct
    rates = np.divide(delta, ns, out=np.full(len(ns), np.nan), where=ns > 0)
    return delta, rates, weighted_range(rates, priors, signed=True)


def fit_candidates(fit, validation, priors, known, old_label, positions, pairs, cuts, *, minimum=200):
    """Exhaustive four-quadrant search detects interactions with zero main effects."""
    fit_ns, val_ns = fit["base"].sum(axis=1), validation["base"].sum(axis=1)
    if minimum < 1 or np.any(fit_ns == 0):
        raise ValueError("positive leaf budget and complete fit-class population required")
    rows = []
    complete_validation = bool(np.all(val_ns > 0))

    def consider(kind, pos, indices):
        rule = {"kind": kind, "positions": list(pos), "indices": list(indices)}
        a, b = child_counts(fit, rule, positions, pairs), child_counts(validation, rule, positions, pairs)
        counts = a.sum(axis=0)
        observed = counts > 0
        eligible = bool(observed.sum() >= 2 and np.all(counts[observed] >= minimum))
        labels = (a * (priors / fit_ns)[:, None]).argmax(axis=0)
        labels[~observed] = old_label
        _, _, training = changes(a, labels, old_label, fit_ns, priors)
        delta, rates, score = changes(b, labels, old_label, val_ns, priors)
        app21 = optional(rates[np.flatnonzero(known == 21)[0]]) if 21 in known else None
        rows.append({"candidate_id": len(rows), **rule, "thresholds_bytes": [float(cuts[i]) for i in indices],
                     "prediction_indices": labels.tolist(), "prediction_APPs": known[labels].tolist(), "fit_leaf_flows": counts.tolist(),
                     "observed_fit_leaves": int(observed.sum()), "eligible": eligible, "fit_gain": -training["value"],
                     "validation_complete": complete_validation, "validation_weighted_change": score["value"],
                     "validation_raw_wrong_change": int(delta.sum()), "APP21_validation_conditional_change": app21})

    for position in positions:
        for i in range(len(cuts)):
            consider("single", (position,), (i,))
    for pair in pairs:
        for i in range(len(cuts)):
            for j in range(len(cuts)):
                consider("joint", pair, (i, j))
    return rows


def choose_rule(candidates, mode, *, protected_parent=False, app21_present=True, app21_budget=.001, raw_budget=0):
    if mode not in MATCHED_GROUPS[1:] or app21_budget < 0 or raw_budget < 0:
        raise ValueError("known selection mode and nonnegative validation budgets required")
    if protected_parent:
        return None, "identity_APP34_parent_protection"
    best, gain = None, 0.
    for rule in candidates:
        if not rule["eligible"]:
            continue
        if mode in ("single_fit", "joint_fit"):
            if rule["kind"] != ("single" if mode == "single_fit" else "joint"):
                continue
            value = rule["fit_gain"]
        else:
            if not rule["validation_complete"]:
                continue
            value = -rule["validation_weighted_change"]
            if mode == "validation_constrained" and (rule["validation_raw_wrong_change"] > raw_budget
                    or (app21_present and (rule["APP21_validation_conditional_change"] is None
                                          or rule["APP21_validation_conditional_change"] > app21_budget + 1e-12))):
                continue
        if value > gain + 1e-12 or (best is not None and value > 1e-12 and abs(value - gain) <= 1e-12
                                  and (rule["observed_fit_leaves"], rule["candidate_id"]) < (best["observed_fit_leaves"], best["candidate_id"])):
            best, gain = rule, value
    status = "selected" if best is not None else "identity_no_positive_eligible_gain"
    if mode.startswith("validation") and candidates and not candidates[0]["validation_complete"]:
        status = "identity_missing_validation_classes"
    return best, status


def rule_evaluation(data, rule, prediction, root_leaves, priors, symbol):
    positions, pairs = data["positions"], data["pairs"]
    low = child_counts(data, rule, positions, pairs)
    children = np.concatenate((low, data["children"][:, 1:]), axis=1)
    counts = refine_counts(data["base"], children, symbol)
    fitted = np.concatenate((prediction[:data["base"].shape[1]].copy(), np.zeros(children.shape[1] - 1, dtype=np.int64)))
    leaves = np.concatenate(([symbol], np.arange(data["base"].shape[1], counts.shape[1])))
    low_labels = np.asarray(rule["prediction_indices"]) if rule is not None else prediction[root_leaves[:1]]
    fitted[leaves] = np.concatenate((low_labels, prediction[root_leaves[1:]]))
    if not np.array_equal(fitted[leaves[-2:]], prediction[root_leaves[1:]]):
        raise RuntimeError("joint rule changed high/invalid predictions")
    values = evaluate(counts, priors, fitted, 0)
    old = prediction[root_leaves[0]]
    transfers = []
    for i in range(len(priors)):
        rescued = int(low[i, (old != i) & (low_labels == i)].sum())
        harmed = int(low[i, (old == i) & (low_labels != i)].sum())
        transfers.append((rescued, harmed))
    return values, transfers


def run_joint(cache, roles, monthly_joint, old_atoms, window_spec, previous_protocol, legacy, *, threshold=4., minimum=200,
              app21_budget=.001, raw_budget=0, small_n=200, progress=None):
    known, priors, symbol = cache["known"], cache["priors"], previous_protocol["symbol_id"]
    positions = tuple(previous_protocol["size_positions"])
    pairs, cuts = tuple(itertools.combinations(positions, 2)), previous_protocol["size_candidates_bytes"]
    roles = {key: {**role, "single": role["single"].sum(axis=3), "joint": role["joint"].sum(axis=4)} for key, role in roles.items()}
    monthly, classes, candidates, selections, confusions, results = [], [], [], [], [], {}
    fitted_cache = {}
    for context in window_spec["contexts"]:
        key, model = context["target"], context["model"]
        common = {"target": key, "period": context["period"], "model": model}
        base = cache["counts"][key][2]
        ns = base.sum(axis=1)
        target = {"base": base, "joint": monthly_joint[key].sum(axis=4), "single": low_marginals(old_atoms[key], previous_protocol["IPT2_candidates_ms"], threshold),
                  "children": time_children(old_atoms[key], previous_protocol["IPT2_candidates_ms"], threshold), "positions": positions, "pairs": pairs}
        evaluations = {}
        for group in GROUPS[-2:]:
            matrix = legacy.get((key, model, group))
            if matrix is not None:
                wrong = ns - np.diag(matrix)
                error = np.divide(wrong, ns, out=np.full(len(ns), np.nan), where=ns > 0)
                evaluations[group] = {"wrong_counts": wrong, "errors": error, "confusion": matrix,
                                      "summary": {"weighted_error": weighted_range(error, priors)}}
        status = context["status"]
        rules, root_values, transfer_map = {}, None, {}
        if status == "ready":
            fit, validation = roles[context["fit_id"]], roles[context["validation_id"]]
            fit_ns, validation_ns = fit["base"].sum(axis=1), validation["base"].sum(axis=1)
            for data in (fit, validation):
                data["positions"], data["pairs"] = positions, pairs
            full_ns = sum(cache["counts"][name][2].sum(axis=1) for name in context["training_slices"])
            if np.any(fit_ns + validation_ns > full_ns):
                raise ValueError("fitting and validation exceed the full past window")
            status = "unavailable_missing_fit_classes" if np.any(fit_ns == 0) else "ready"
            if status == "ready":
                prediction, root_leaves = root_model(fit["base"], fit["children"], priors, symbol)
                root_values, transfer_map["time_fit"] = rule_evaluation(target, None, prediction, root_leaves, priors, symbol)
                evaluations["time_fit"] = root_values
                low_parent = int(known[prediction[root_leaves[0]]])
                token = (context["fit_id"], context["validation_id"])
                if token not in fitted_cache:
                    fitted_cache[token] = fit_candidates(fit, validation, priors, known, int(prediction[root_leaves[0]]), positions, pairs, cuts, minimum=minimum)
                fitted = fitted_cache[token]
                candidates.extend({**common, **row} for row in fitted)
                for group in MATCHED_GROUPS[1:]:
                    rule, selection_status = choose_rule(fitted, group, protected_parent=low_parent == 34,
                                                        app21_present=21 in known, app21_budget=app21_budget, raw_budget=raw_budget)
                    rules[group] = rule
                    selections.append({**common, "group": group, "status": selection_status, "fit_sample_counts": fit_ns.tolist(),
                                       "validation_sample_counts": validation_ns.tolist(), "unused_past_sample_counts": (full_ns - fit_ns - validation_ns).tolist(),
                                       "fit_start_epoch": context["fit_start_epoch"], "fit_end_epoch": context["fit_end_epoch"],
                                       "validation_start_epoch": context["validation_start_epoch"], "validation_end_epoch": context["validation_end_epoch"],
                                       "target_start_epoch": context["target_start_epoch"], "low_parent_APP": low_parent, "rule": rule})
                    evaluations[group], transfer_map[group] = rule_evaluation(target, rule, prediction, root_leaves, priors, symbol)
        if status != "ready":
            selections.append({**common, "group": "all_matched", "status": status, "rule": None})
        for group in GROUPS:
            values = evaluations.get(group)
            if values is None:
                monthly.append({**common, "group": group, "status": status if group in MATCHED_GROUPS else "unavailable_legacy_window", "weighted_error": None,
                                "change_vs_time_fit": None, "raw_wrong_change_vs_time_fit": None})
                for i, app in enumerate(known):
                    classes.append({**common, "group": group, "APP": int(app), "n": int(ns[i]), "status": "unavailable_model", "error": None,
                                    "conditional_change_vs_time_fit": None, "weighted_change_vs_time_fit": None, "rescued": None, "harmed": None})
                continue
            delta = values["errors"] - root_values["errors"] if root_values else np.full(len(ns), np.nan)
            raw = int((values["wrong_counts"] - root_values["wrong_counts"]).sum()) if root_values else None
            if group in MATCHED_GROUPS:
                for i, (rescued, harmed) in enumerate(transfer_map[group]):
                    if harmed - rescued != int(values["wrong_counts"][i] - root_values["wrong_counts"][i]):
                        raise RuntimeError("joint classification change escaped the low branch")
                    if int(known[i]) == 34 and harmed:
                        raise RuntimeError("joint model violated APP34 protection")
            row = {**common, "group": group, "status": "complete", "weighted_error": values["summary"]["weighted_error"],
                   "change_vs_time_fit": weighted_range(delta, priors, signed=True) if root_values else None,
                   "raw_wrong": int(values["wrong_counts"].sum()), "raw_wrong_change_vs_time_fit": raw,
                   "selected_kind": rules[group]["kind"] if group in rules and rules[group] else "identity" if group in MATCHED_GROUPS else "legacy_full_past"}
            for app in FOCAL_APPS:
                row[f"APP{app}_error"] = optional(values["errors"][np.flatnonzero(known == app)[0]]) if app in known else None
            monthly.append(row)
            results[(key, model, group)] = values["wrong_counts"]
            confusions.append({"target": key, "model": model, "group": group, "counts_true_by_predicted": values["confusion"].tolist()})
            for i, app in enumerate(known):
                transfers = transfer_map.get(group)
                classes.append({**common, "group": group, "APP": int(app), "n": int(ns[i]),
                                "status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed", "error": optional(values["errors"][i]),
                                "conditional_change_vs_time_fit": optional(delta[i]), "weighted_change_vs_time_fit": optional(priors[i] * delta[i]),
                                "rescued": transfers[i][0] if transfers else None, "harmed": transfers[i][1] if transfers else None})
        if progress:
            progress(key, model)
    periods, period_classes = [], []
    for period in ("certificate", "evaluation"):
        keys = [s["key"] for s in cache["slices"] if s["period"] == period]
        ns = cache["period_counts"][period][2].sum(axis=1)
        for model in previous_protocol["models"]:
            for group in GROUPS:
                common = {"period": period, "model": model, "group": group}
                tokens = [(key, model, group) for key in keys]
                if not all(t in results for t in tokens):
                    periods.append({**common, "status": "unavailable_model_windows", "weighted_error": None, "change_vs_time_fit": None})
                    for i, app in enumerate(known):
                        period_classes.append({**common, "APP": int(app), "n": int(ns[i]), "error": None, "conditional_change_vs_time_fit": None,
                                               "weighted_change_vs_time_fit": None, "status": "unavailable_model"})
                    continue
                wrong = sum((results[t] for t in tokens), np.zeros(len(ns), dtype=np.int64))
                root_tokens = [(key, model, "time_fit") for key in keys]
                root = sum((results[t] for t in root_tokens), np.zeros_like(wrong)) if all(t in results for t in root_tokens) else None
                errors = np.divide(wrong, ns, out=np.full(len(ns), np.nan), where=ns > 0)
                delta = np.divide(wrong - root, ns, out=np.full(len(ns), np.nan), where=ns > 0) if root is not None else np.full(len(ns), np.nan)
                row = {**common, "status": "complete", "weighted_error": weighted_range(errors, priors),
                       "change_vs_time_fit": weighted_range(delta, priors, signed=True) if root is not None else None,
                       "raw_wrong": int(wrong.sum()), "raw_wrong_change_vs_time_fit": int((wrong - root).sum()) if root is not None else None}
                for app in FOCAL_APPS:
                    row[f"APP{app}_error"] = optional(errors[np.flatnonzero(known == app)[0]]) if app in known else None
                periods.append(row)
                for i, app in enumerate(known):
                    period_classes.append({**common, "APP": int(app), "n": int(ns[i]), "error": optional(errors[i]),
                                           "conditional_change_vs_time_fit": optional(delta[i]), "weighted_change_vs_time_fit": optional(priors[i] * delta[i]),
                                           "status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed"})
    return {"monthly": monthly, "classes": classes, "periods": periods, "period_classes": period_classes, "candidates": candidates,
            "selections": selections, "confusions": confusions}
