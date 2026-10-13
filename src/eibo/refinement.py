"""Past-only, bounded binary refinements of one canonical prefix cell.

Cut candidates are fixed before scanning. Counts for all fixed known classes
share the audited population. Selection minimizes training empirical risk;
future-month labels are used only to evaluate the frozen selection.
"""

from __future__ import annotations

import numpy as np

from .monthlydrift import MonthlyDriftCounts, optional, weighted_range
from .realdata import whole_interval_mask
from .realexperiment import histogram_predictions
from .riskcert import empirical_known_risk
from .rolling import MODELS, evaluate, training_window

GROUPS = ("original", "size_split", "ipt_split", "size_ipt_split")
SIZE_CUTS = (39, 63, 127, 255, 511, 767, 1023, 1199, 1200, 1279, 1399, 1499, 1500, 2047, 4095, 8191, 16383, 32767, 65535)
IPT_CUTS = (0, 1, 2, 3, 4, 5, 7, 10, 15, 20, 30, 50, 100, 200, 500, 1000)


def validate_grid(values, *, integer=False):
    grid = np.asarray(values, dtype=float)
    if grid.ndim != 1 or len(grid) == 0 or not np.isfinite(grid).all() or np.any(grid < 0) or np.any(np.diff(grid) <= 0):
        raise ValueError("cut candidates must be finite, nonnegative, strictly increasing")
    if integer and np.any(grid != np.floor(grid)):
        raise ValueError("size cut candidates must be integer bytes")
    return grid


class RefinementCounts(MonthlyDriftCounts):
    """One full scan; retain bounded size-position x IPT2 joint histograms."""

    def __init__(self, plan, tables, *, time_scale, symbol=479, size_cuts=SIZE_CUTS, ipt_cuts=IPT_CUTS, positions=None):
        super().__init__(plan, tables, time_scale=time_scale)
        self.size_cuts = validate_grid(size_cuts, integer=True)
        self.ipt_cuts = validate_grid(ipt_cuts)
        self.positions = tuple(range(1, self.k + 1)) if positions is None else tuple(positions)
        if self.k < 2 or not self.positions or self.positions != tuple(sorted(set(self.positions))) or min(self.positions) < 1 or max(self.positions) > self.k:
            raise ValueError("IPT2 requires k>=2; size positions must be distinct, sorted and inside the prefix")
        if not 0 <= symbol < self.encoders[2].alphabet:
            raise ValueError("canonical cell ID outside the original alphabet")
        self.symbol = int(symbol)
        shape = (len(self.positions), len(self.known), len(self.size_cuts) + 1, len(self.ipt_cuts) + 2)
        if np.prod(shape) > 1000000:
            raise ValueError("candidate grids exceed the per-month atomic-count memory budget")
        # Last IPT atom is an explicit invalid-value marker. No flow is dropped.
        self.atoms = {item["key"]: np.zeros(shape, dtype=np.int64) for item in self.slices}

    def add(self, records, capacity):
        super().add(records, capacity)
        first, last = (np.asarray(records[field], dtype=float) / self.time_scale for field in ("TIME_FIRST", "TIME_LAST"))
        lengths, labels = np.asarray(records["PPI_LEN"], dtype=float), np.asarray(records["APP"])
        usable = (np.isfinite(first) & np.isfinite(last) & (last >= first) & (first >= self.begin) & (first < self.end) &
                  np.isfinite(lengths) & (lengths == np.floor(lengths)) & (lengths >= self.k) & (lengths <= capacity) & np.isin(labels, self.known))
        for period, window in self.windows.items():
            selected = usable & whole_interval_mask(first, last, window, self.rounding)
            ppi = records["PPI"][selected]
            hit = self.encoders[2].encode(ppi) == self.symbol
            if not hit.any():
                continue
            ppi, times, app = ppi[hit], first[selected][hit], np.searchsorted(self.known, labels[selected][hit])
            ipt = np.asarray(ppi[:, 0, 1], dtype=float)
            valid = np.isfinite(ipt) & (ipt >= 0)
            time_atom = np.full(len(ipt), len(self.ipt_cuts) + 1, dtype=np.int64)
            time_atom[valid] = np.searchsorted(self.ipt_cuts, ipt[valid], side="left")
            indices = np.searchsorted(self.slice_starts[period], times, side="right") - 1
            for index in np.unique(indices):
                key, mask = self.slice_keys[period][int(index)], indices == index
                for p, position in enumerate(self.positions):
                    size_atom = np.searchsorted(self.size_cuts, ppi[mask, 2, position - 1], side="left")
                    np.add.at(self.atoms[key][p], (app[mask], size_atom, time_atom[mask]), 1)

    def reconcile_cache(self, cache):
        self.reconcile_months(cache["period_counts"])
        for item in self.slices:
            key = item["key"]
            for rung in (1, 2):
                if not np.array_equal(self.monthly[key][rung], cache["counts"][key][rung]):
                    raise ValueError(f"raw monthly symbols differ from verified cache: {key}, M={rung}")
            expected = cache["counts"][key][2][:, self.symbol]
            if not np.all(self.atoms[key].sum(axis=(2, 3)) == expected[None, :]):
                raise RuntimeError("joint feature atoms do not conserve canonical cell counts")
            if not np.all(self.atoms[key].sum(axis=2) == self.atoms[key][0].sum(axis=1)[None, :, :]):
                raise RuntimeError("IPT2 histograms differ among size-position views")


def select_splits(atoms, ns, priors, positions, size_cuts, ipt_cuts, *, min_leaf=200):
    """Multiclass training objective uses full-class n_i, never cell-only n_i."""
    if min_leaf < 1 or np.any(ns <= 0):
        raise ValueError("positive leaf budget and every fixed training class required")
    expected = atoms[0].sum(axis=(1, 2))
    if not np.all(atoms.sum(axis=(2, 3)) == expected[None, :]):
        raise ValueError("position views disagree on training cell population")
    scale = priors / ns
    parent_correct = float(np.max(expected * scale))
    chosen, candidates = {"size": None, "ipt": None}, []

    def consider(kind, children, *, position, index, threshold):
        valid = bool(children[:, 0].sum() >= min_leaf and children[:, 1].sum() >= min_leaf)
        gain = float((children * scale[:, None]).max(axis=0).sum() - parent_correct) if valid else None
        row = {"feature": kind, "position": position, "threshold": float(threshold), "atom_index": index,
               "eligible": valid, "training_empirical_gain": gain, "child_counts": children.sum(axis=0).tolist(), "selected": False}
        candidates.append(row)
        if valid and (chosen[kind] is None or gain > chosen[kind]["training_empirical_gain"] + 1e-12):
            chosen[kind] = row

    for p, position in enumerate(positions):
        marginal = atoms[p].sum(axis=2)
        cumulative, total = np.cumsum(marginal, axis=1), marginal.sum(axis=1)
        for index, threshold in enumerate(size_cuts):
            left = cumulative[:, index]
            consider("size", np.stack((left, total - left), axis=1), position=int(position), index=index, threshold=threshold)
    marginal = atoms[0].sum(axis=1)
    cumulative = np.cumsum(marginal[:, :-1], axis=1)
    valid_total, invalid = marginal[:, :-1].sum(axis=1), marginal[:, -1]
    for index, threshold in enumerate(ipt_cuts):
        left = cumulative[:, index]
        consider("ipt", np.stack((left, valid_total - left, invalid), axis=1), position=2, index=index, threshold=threshold)
    for row in chosen.values():
        if row is not None:
            row["selected"] = True
    return chosen, candidates


def collapse_atoms(atoms, positions, selection, group):
    size = selection["size"] if group in ("size_split", "size_ipt_split") else None
    ipt = selection["ipt"] if group in ("ipt_split", "size_ipt_split") else None
    position = positions.index(size["position"]) if size is not None else 0
    values = atoms[position]
    blocks = (values[:, :size["atom_index"] + 1, :].sum(axis=1), values[:, size["atom_index"] + 1:, :].sum(axis=1)) if size else (values.sum(axis=1),)
    children, labels = [], []
    for number, block in enumerate(blocks):
        prefix = (f"size_p{size['position']} {'<=' if number == 0 else '>'} {size['threshold']:g} B; ") if size else ""
        if ipt:
            index = ipt["atom_index"]
            children.extend((block[:, :index + 1].sum(axis=1), block[:, index + 1:-1].sum(axis=1), block[:, -1]))
            labels.extend((prefix + f"IPT2 <= {ipt['threshold']:g} ms", prefix + f"IPT2 > {ipt['threshold']:g} ms", prefix + "IPT2 invalid"))
        else:
            children.append(block.sum(axis=1))
            labels.append(prefix.rstrip("; ") or "original cell")
    return np.stack(children, axis=1), labels


def refine_counts(base, children, symbol):
    if not np.array_equal(children.sum(axis=1), base[:, symbol]):
        raise ValueError("refined children differ from the original cell population")
    result = np.concatenate((base.copy(), children[:, 1:]), axis=1)
    result[:, symbol] = children[:, 0]
    mapping = np.concatenate((np.arange(base.shape[1]), np.full(children.shape[1] - 1, symbol)))
    projected = np.zeros_like(base)
    np.add.at(projected, (np.arange(len(base))[:, None], mapping[None, :]), result)
    if not np.array_equal(projected, base):
        raise RuntimeError("refined representation does not project to original counts")
    return result


def fit_prediction(train, priors, baseline, symbol, original_alphabet):
    prediction, unseen = histogram_predictions(train, priors)
    outside = np.arange(original_alphabet) != symbol
    if not np.array_equal(prediction[:original_alphabet][outside], baseline[outside]):
        raise RuntimeError("prediction changed outside the refined cell")
    leaves = np.concatenate(([symbol], np.arange(original_alphabet, train.shape[1])))
    # A child absent from every training class backs off to its parent rule.
    prediction[leaves[unseen[leaves]]] = baseline[symbol]
    return prediction, leaves, unseen[leaves]


def run_refinements(cache, atoms, *, symbol=479, positions=(1, 2, 3, 4, 5), size_cuts=SIZE_CUTS,
                    ipt_cuts=IPT_CUTS, min_leaf=200, small_n=200, models=MODELS, progress=None):
    known, priors = cache["known"], cache["priors"]
    monthly, classes, children_rows, selections, candidate_rows, results = [], [], [], [], [], {}
    targets = [item for item in cache["slices"] if item["period"] != "pilot"]
    for target in targets:
        key = target["key"]
        base = cache["counts"][key][2]
        ns = base.sum(axis=1)
        full_target = bool(np.all(ns > 0))
        base_F = empirical_known_risk(base, priors) if full_target else None
        for model in models:
            window = training_window(cache, target, model)
            context = {"target": key, "period": target["period"], "model": model}
            if window["status"] != "ready":
                selections.append({**context, "status": window["status"], "training_slices": window["training_slices"],
                                   "missing_calendar_months": window["missing_calendar_months"], "missing_training_services": window["missing_training_services"],
                                   "size": None, "ipt": None})
                for group in GROUPS:
                    monthly.append({**context, "group": group, "status": window["status"], "target_sample_counts": ns.tolist(),
                                    "weighted_error": None, "error_change": None, "empirical_F": None, "empirical_representation_gain": None})
                    for i, app in enumerate(known):
                        classes.append({**context, "group": group, "APP": int(app), "target_n": int(ns[i]), "status": "unavailable_model",
                                        "error": None, "conditional_error_change": None, "weighted_error_change": None,
                                        "rescued_count": None, "harmed_count": None, "signed_empirical_representation_gain": None})
                continue
            train_atoms = sum((atoms[name] for name in window["training_slices"]), np.zeros_like(atoms[key]))
            train_base = window["matrices"][2]
            if not np.all(train_atoms.sum(axis=(2, 3)) == train_base[:, symbol][None, :]):
                raise RuntimeError("past-only training atoms differ from the base cell counts")
            selection, candidates = select_splits(train_atoms, window["sample_counts"], priors, positions, size_cuts, ipt_cuts, min_leaf=min_leaf)
            selections.append({**context, "status": "ready", "training_slices": window["training_slices"],
                               "last_training_end_epoch": max(item["end_epoch"] for item in cache["slices"] if item["key"] in window["training_slices"]),
                               "target_start_epoch": target["start_epoch"], "training_sample_counts": window["sample_counts"].tolist(), **selection})
            candidate_rows.extend({**context, **row, "child_counts": ";".join(map(str, row["child_counts"]))} for row in candidates)
            baseline_prediction, _ = histogram_predictions(train_base, priors)
            baseline = evaluate(base, priors, baseline_prediction, 0)
            train_base_F = empirical_known_risk(train_base, priors)
            base_oracle = evaluate(base, priors, histogram_predictions(base, priors)[0], 0)["errors"] if full_target else None
            gain_by_group = {}
            for group in GROUPS:
                train_children, labels = collapse_atoms(train_atoms, positions, selection, group)
                target_children, _ = collapse_atoms(atoms[key], positions, selection, group)
                train = refine_counts(train_base, train_children, symbol)
                test = refine_counts(base, target_children, symbol)
                prediction, leaves, unseen = fit_prediction(train, priors, baseline_prediction, symbol, base.shape[1])
                values = evaluate(test, priors, prediction, 0)
                delta = values["errors"] - baseline["errors"]
                target_F = empirical_known_risk(test, priors) if full_target else None
                train_gain = train_base_F - empirical_known_risk(train, priors)
                target_gain = base_F - target_F if full_target else None
                if train_gain < -1e-12 or (target_gain is not None and target_gain < -1e-12):
                    raise RuntimeError("empirical risk increased under deterministic refinement")
                gain_by_group[group] = (train_gain, target_gain)
                oracle = evaluate(test, priors, histogram_predictions(test, priors)[0], 0)["errors"] if full_target else None
                change = weighted_range(delta, priors, signed=True)
                size_active = group in ("size_split", "size_ipt_split") and selection["size"] is not None
                time_active = group in ("ipt_split", "size_ipt_split") and selection["ipt"] is not None
                row = {**context, "group": group, "status": "complete", "effective_size_split": size_active, "effective_IPT_split": time_active,
                       "training_sample_counts": window["sample_counts"].tolist(), "target_sample_counts": ns.tolist(),
                       "alphabet_size": test.shape[1], "cell_children": len(labels), "weighted_error": values["summary"]["weighted_error"],
                       "error_change": change, "empirical_F": target_F,
                       "empirical_representation_gain": target_gain, "training_empirical_gain": train_gain,
                       "empirical_gap_change": change["value"] + target_gain if change["value"] is not None and target_gain is not None else None,
                       "APP2_error": optional(values["errors"][np.flatnonzero(known == 2)[0]]) if 2 in known else None,
                       "APP34_error": optional(values["errors"][np.flatnonzero(known == 34)[0]]) if 34 in known else None,
                       "unseen_child_target_flows": int(target_children[:, unseen].sum()),
                       "unseen_child_weighted_target_mass": optional(np.dot(priors, np.divide(target_children[:, unseen].sum(axis=1), ns,
                                                    out=np.full(len(ns), np.nan), where=ns > 0))),
                       "positive_class_changes": float(np.nansum((priors * delta)[delta > 0])),
                       "negative_class_changes": float(np.nansum((priors * delta)[delta < 0]))}
                monthly.append(row)
                results[(key, model, group)] = {"wrong": values["wrong_counts"], "confusion": values["confusion"]}
                cell_prediction = prediction[leaves]
                scale = priors / window["sample_counts"]
                scores = train_children * scale[:, None]
                denominator = scores.sum(axis=0)
                for i, app in enumerate(known):
                    rescued = int(target_children[i, (baseline_prediction[symbol] != i) & (cell_prediction == i)].sum())
                    harmed = int(target_children[i, (baseline_prediction[symbol] == i) & (cell_prediction != i)].sum())
                    if harmed - rescued != int(values["wrong_counts"][i] - baseline["wrong_counts"][i]):
                        raise RuntimeError("refinement error change escaped the selected cell")
                    classes.append({**context, "group": group, "APP": int(app), "target_n": int(ns[i]),
                                    "status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                                    "error": optional(values["errors"][i]), "conditional_error_change": optional(delta[i]),
                                    "weighted_error_change": optional(priors[i] * delta[i]), "rescued_count": rescued, "harmed_count": harmed,
                                    "signed_empirical_representation_gain": optional(priors[i] * (base_oracle[i] - oracle[i])) if full_target else None})
                    for b, label in enumerate(labels):
                        children_rows.append({**context, "group": group, "child": b, "condition": label, "APP": int(app),
                                              "class_training_n": int(window["sample_counts"][i]), "training_child_n": int(train_children[i, b]),
                                              "target_child_n": int(target_children[i, b]), "trained_prediction_APP": int(known[cell_prediction[b]]),
                                              "unseen_training_child": bool(unseen[b]),
                                              "known_only_training_posterior": float(scores[i, b] / denominator[b]) if denominator[b] else None})
            for part in ("size_split", "ipt_split"):
                for a, b in zip(gain_by_group["size_ipt_split"], gain_by_group[part]):
                    if a is not None and b is not None and a < b - 1e-12:
                        raise RuntimeError("combined representation does not refine both main effects")
        if progress:
            progress(key)
    periods, period_classes = [], []
    for period in ("certificate", "evaluation"):
        items = [item for item in targets if item["period"] == period]
        ns = cache["period_counts"][period][2].sum(axis=1)
        for model in models:
            for group in GROUPS:
                tokens = [(item["key"], model, group) for item in items]
                baseline_tokens = [(item["key"], model, "original") for item in items]
                context = {"period": period, "model": model, "group": group}
                if not all(token in results for token in tokens + baseline_tokens):
                    periods.append({**context, "status": "unavailable_model_windows", "weighted_error": None, "error_change": None})
                    for i, app in enumerate(known):
                        period_classes.append({**context, "APP": int(app), "target_n": int(ns[i]), "error": None,
                                               "conditional_error_change": None, "weighted_error_change": None, "status": "unavailable_model"})
                    continue
                wrong = sum((results[token]["wrong"] for token in tokens), np.zeros(len(ns), dtype=np.int64))
                baseline_wrong = sum((results[token]["wrong"] for token in baseline_tokens), np.zeros_like(wrong))
                errors, delta = wrong / ns, (wrong - baseline_wrong) / ns
                periods.append({**context, "status": "complete", "weighted_error": weighted_range(errors, priors),
                                "error_change": weighted_range(delta, priors, signed=True),
                                "APP2_error": optional(errors[np.flatnonzero(known == 2)[0]]) if 2 in known else None,
                                "APP34_error": optional(errors[np.flatnonzero(known == 34)[0]]) if 34 in known else None,
                                "positive_class_changes": float((priors * delta)[delta > 0].sum()),
                                "negative_class_changes": float((priors * delta)[delta < 0].sum())})
                for i, app in enumerate(known):
                    period_classes.append({**context, "APP": int(app), "target_n": int(ns[i]), "error": float(errors[i]),
                                           "conditional_error_change": float(delta[i]), "weighted_error_change": float(priors[i] * delta[i]),
                                           "status": "small_n" if ns[i] < small_n else "observed"})
    return {"monthly": monthly, "periods": periods, "classes": classes, "period_classes": period_classes,
            "children": children_rows, "selections": selections, "candidates": candidate_rows,
            "confusions": [{"target": key[0], "model": key[1], "group": key[2], "counts_true_by_predicted": value["confusion"].tolist()}
                           for key, value in results.items()]}
