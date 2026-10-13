"""Past-only size refinement confined to the low-IPT branch of one cell."""

from __future__ import annotations

import numpy as np

from .monthlydrift import optional, weighted_range
from .realexperiment import histogram_predictions
from .refinement import collapse_atoms, fit_prediction, refine_counts, select_splits
from .riskcert import empirical_known_risk
from .rolling import MODELS, evaluate, training_window

GROUPS = ("original", "ipt_split", "crossed_size_ipt", "low_size_split")
FOCAL_APPS = (2, 21, 34)


def focal_value(values, known, app):
    return optional(values[np.flatnonzero(known == app)[0]]) if app in known else None


def select_low_size(atoms, ns, priors, known, positions, size_cuts, root, root_prediction, *, min_leaf=200):
    """Search only past low-IPT counts using unchanged full-class denominators."""
    if root is None:
        return None, []
    if min_leaf < 1 or np.any(ns <= 0):
        raise ValueError("positive leaf budget and every fixed training class required")
    scale = priors / ns
    selected, rows = None, []
    for p, position in enumerate(positions):
        marginal = atoms[p, :, :, :root["atom_index"] + 1].sum(axis=2)
        totals, cumulative = marginal.sum(axis=1), np.cumsum(marginal, axis=1)
        original_correct = np.zeros(len(ns))
        original_correct[root_prediction] = totals[root_prediction]
        for index, threshold in enumerate(size_cuts):
            left = cumulative[:, index]
            children = np.stack((left, totals - left), axis=1)
            eligible = bool(np.all(children.sum(axis=0) >= min_leaf))
            scores = children * scale[:, None]
            winners = scores.argmax(axis=0)
            correct = (children * (winners[None, :] == np.arange(len(ns))[:, None])).sum(axis=1)
            gain_by_class = (correct - original_correct) * scale
            gain = float(gain_by_class.sum())
            row = {"size_position": int(position), "size_threshold_bytes": float(threshold), "atom_index": index,
                   "eligible": eligible, "training_empirical_gain": gain,
                   "APP2_training_weighted_gain": focal_value(gain_by_class, known, 2),
                   "APP21_training_weighted_gain": focal_value(gain_by_class, known, 21),
                   "low_child_flows": children.sum(axis=0).tolist(),
                   "child_predictions_APP": known[winners].tolist(), "selected": False}
            rows.append(row)
            if eligible and gain > 1e-12 and (selected is None or gain > selected["training_empirical_gain"] + 1e-12):
                selected = row
    if selected is not None:
        selected["selected"] = True
    return selected, rows


def low_children(atoms, positions, root_selection, cut):
    """Return children and their exact map to the unchanged IPT-only children."""
    root, root_labels = collapse_atoms(atoms, positions, root_selection, "ipt_split")
    if root_selection["ipt"] is None or cut is None:
        return root, root_labels, np.arange(root.shape[1])
    p = positions.index(cut["size_position"])
    time_index, size_index = root_selection["ipt"]["atom_index"], cut["atom_index"]
    values = atoms[p]
    left = values[:, :size_index + 1, :time_index + 1].sum(axis=(1, 2))
    right = values[:, size_index + 1:, :time_index + 1].sum(axis=(1, 2))
    children = np.stack((left, right, root[:, 1], root[:, 2]), axis=1)
    labels = [root_labels[0] + f"; size_p{cut['size_position']} <= {cut['size_threshold_bytes']:g} B",
              root_labels[0] + f"; size_p{cut['size_position']} > {cut['size_threshold_bytes']:g} B", root_labels[1], root_labels[2]]
    if not np.array_equal(children[:, :2].sum(axis=1), root[:, 0]):
        raise RuntimeError("low-branch children do not project to the IPT-only parent")
    return children, labels, np.array([0, 0, 1, 2])


def fit_low_prediction(train, priors, root_prediction, root_leaves, parent_map, symbol, alphabet):
    prediction, unseen = histogram_predictions(train, priors)
    leaves = np.concatenate(([symbol], np.arange(alphabet, train.shape[1])))
    outside = np.arange(alphabet) != symbol
    outside_indices = np.flatnonzero(outside)
    prediction[outside_indices] = root_prediction[outside_indices]
    for b, parent in enumerate(parent_map):
        if parent != 0 or unseen[leaves[b]]:
            prediction[leaves[b]] = root_prediction[root_leaves[parent]]
    if not np.array_equal(prediction[:alphabet][outside], root_prediction[:alphabet][outside]):
        raise RuntimeError("hierarchical prediction changed outside the original cell")
    for b, parent in enumerate(parent_map):
        if parent != 0 and prediction[leaves[b]] != root_prediction[root_leaves[parent]]:
            raise RuntimeError("high/invalid branch prediction changed")
    return prediction, leaves, unseen[leaves]


def branch_context(counts, ns, priors, known):
    if np.any(ns == 0) or counts.sum() == 0:
        return {"scores": None, "posterior": None, "winner": None, "APP2_rank": None, "APP2_margin": None}
    scores = counts * priors / ns
    winner = int(known[scores.argmax()])
    posterior = scores / scores.sum()
    rank, margin = None, None
    if 2 in known:
        focal = int(np.flatnonzero(known == 2)[0])
        rank = int(1 + np.sum(scores > scores[focal]))
        others = scores[np.arange(len(known)) != focal]
        margin = float(scores[focal] - others.max()) if len(others) else None
    return {"scores": scores, "posterior": posterior, "winner": winner, "APP2_rank": rank, "APP2_margin": margin}


def run_hierarchy(cache, atoms, *, positions, size_cuts, ipt_cuts, symbol=479, root_min_leaf=200,
                  min_leaf=200, small_n=200, models=MODELS, progress=None):
    known, priors = cache["known"], cache["priors"]
    targets = [item for item in cache["slices"] if item["period"] != "pilot"]
    monthly, classes, selections, candidates, competition, confusions = [], [], [], [], [], []
    results = {}
    for target in targets:
        key, base = target["key"], cache["counts"][target["key"]][2]
        ns, alphabet = base.sum(axis=1), base.shape[1]
        complete = bool(np.all(ns > 0))
        for model in models:
            context = {"target": key, "period": target["period"], "model": model}
            window = training_window(cache, target, model)
            if window["status"] != "ready":
                selections.append({**context, "status": window["status"], "training_slices": window["training_slices"],
                                   "IPT2_threshold_ms": None, "low_size_cut": None})
                for group in GROUPS:
                    monthly.append({**context, "group": group, "status": window["status"], "weighted_error": None,
                                    "error_change_from_original": None, "error_change_from_IPT": None,
                                    "empirical_gain_from_original": None, "empirical_gain_from_IPT": None})
                    for i, app in enumerate(known):
                        classes.append({**context, "group": group, "APP": int(app), "target_n": int(ns[i]), "status": "unavailable_model",
                                        "error": None, "conditional_change_from_IPT": None, "weighted_change_from_IPT": None,
                                        "rescued_from_IPT": None, "harmed_from_IPT": None, "signed_empirical_gain_from_IPT": None})
                continue
            train_base = window["matrices"][2]
            train_ns = window["sample_counts"]
            train_atoms = sum((atoms[name] for name in window["training_slices"]), np.zeros_like(atoms[key]))
            if not np.all(train_atoms.sum(axis=(2, 3)) == train_base[:, symbol][None, :]):
                raise RuntimeError("past-only training atoms differ from the base cell counts")
            root_selection, _ = select_splits(train_atoms, train_ns, priors, positions, size_cuts, ipt_cuts, min_leaf=root_min_leaf)
            parent_prediction, _ = histogram_predictions(train_base, priors)
            root_train, root_labels = collapse_atoms(train_atoms, positions, root_selection, "ipt_split")
            root_test, _ = collapse_atoms(atoms[key], positions, root_selection, "ipt_split")
            train_root = refine_counts(train_base, root_train, symbol)
            test_root = refine_counts(base, root_test, symbol)
            root_prediction, root_leaves, _ = fit_prediction(train_root, priors, parent_prediction, symbol, alphabet)
            root_values = evaluate(test_root, priors, root_prediction, 0)
            old_values = evaluate(base, priors, parent_prediction, 0)
            low_prediction = int(root_prediction[root_leaves[0]])
            cut, choice_rows = select_low_size(train_atoms, train_ns, priors, known, positions, size_cuts,
                                               root_selection["ipt"], low_prediction, min_leaf=min_leaf)
            train_low, train_labels, parent_map = low_children(train_atoms, positions, root_selection, cut)
            test_low, _, _ = low_children(atoms[key], positions, root_selection, cut)
            train_hierarchy = refine_counts(train_base, train_low, symbol)
            test_hierarchy = refine_counts(base, test_low, symbol)
            low_model, low_leaves, _ = fit_low_prediction(train_hierarchy, priors, root_prediction, root_leaves, parent_map, symbol, alphabet)
            root_before = branch_context(root_train[:, 0], train_ns, priors, known)
            root_target = branch_context(root_test[:, 0], ns, priors, known)
            protected = known.tolist() if cut is None else known[np.arange(len(known)) != low_prediction].tolist()
            selections.append({**context, "status": "ready", "training_slices": window["training_slices"],
                               "last_training_end_epoch": max(item["end_epoch"] for item in cache["slices"] if item["key"] in window["training_slices"]),
                               "target_start_epoch": target["start_epoch"],
                               "IPT2_threshold_ms": root_selection["ipt"]["threshold"] if root_selection["ipt"] else None,
                               "low_size_cut": cut, "low_branch_prediction_APP": int(known[low_prediction]),
                               "APP2_training_rank_in_low": root_before["APP2_rank"], "APP2_target_rank_in_low": root_target["APP2_rank"],
                               "APP2_training_margin_in_low": root_before["APP2_margin"], "APP2_target_margin_in_low": root_target["APP2_margin"],
                               "pointwise_no_harm_APPs_relative_to_IPT": protected,
                               "APP34_pointwise_no_harm_relative_to_IPT": 34 in protected,
                               "best_eligible_APP2_training_gain": max((row["APP2_training_weighted_gain"] for row in choice_rows if row["eligible"] and row["APP2_training_weighted_gain"] is not None), default=None)})
            candidates.extend({**context, **row, "low_child_flows": ";".join(map(str, row["low_child_flows"])),
                               "child_predictions_APP": ";".join(map(str, row["child_predictions_APP"]))} for row in choice_rows)
            before_F = empirical_known_risk(base, priors) if complete else None
            root_F = empirical_known_risk(test_root, priors) if complete else None
            root_oracle = evaluate(test_root, priors, histogram_predictions(test_root, priors)[0], 0)["errors"] if complete else None
            for b, label in enumerate(root_labels):
                left = branch_context(root_train[:, b], train_ns, priors, known)
                right = branch_context(root_test[:, b], ns, priors, known)
                for i, app in enumerate(known):
                    competition.append({**context, "view": "IPT_parent", "child": b, "condition": label, "APP": int(app),
                                        "training_class_n": int(train_ns[i]), "target_class_n": int(ns[i]),
                                        "training_child_n": int(root_train[i, b]), "target_child_n": int(root_test[i, b]),
                                        "trained_prediction_APP": int(known[root_prediction[root_leaves[b]]]),
                                        "target_empirical_winner_APP": right["winner"],
                                        "training_known_posterior": float(left["posterior"][i]) if left["posterior"] is not None else None,
                                        "target_known_posterior": float(right["posterior"][i]) if right["posterior"] is not None else None})
            configurations = {}
            for group, old_group in (("original", "original"), ("ipt_split", "ipt_split"), ("crossed_size_ipt", "size_ipt_split")):
                tr, labels = collapse_atoms(train_atoms, positions, root_selection, old_group)
                te, _ = collapse_atoms(atoms[key], positions, root_selection, old_group)
                train, test = refine_counts(train_base, tr, symbol), refine_counts(base, te, symbol)
                prediction, leaves, unseen = fit_prediction(train, priors, parent_prediction, symbol, alphabet)
                configurations[group] = (train, test, prediction, leaves, unseen, tr, te, labels, None)
            configurations["low_size_split"] = (train_hierarchy, test_hierarchy, low_model, low_leaves,
                        np.all(train_low == 0, axis=0), train_low, test_low, train_labels, parent_map)
            for group in GROUPS:
                train, test, prediction, leaves, unseen, tr, te, labels, to_root = configurations[group]
                values = evaluate(test, priors, prediction, 0)
                delta_old, delta_root = values["errors"] - old_values["errors"], values["errors"] - root_values["errors"]
                point = empirical_known_risk(test, priors) if complete else None
                gain_root = root_F - point if complete else None
                oracle = evaluate(test, priors, histogram_predictions(test, priors)[0], 0)["errors"] if complete else None
                if group == "low_size_split" and gain_root is not None and gain_root < -1e-12:
                    raise RuntimeError("low refinement increased the target empirical risk")
                change_root = weighted_range(delta_root, priors, signed=True)
                monthly.append({**context, "group": group, "status": "complete", "weighted_error": values["summary"]["weighted_error"],
                                "error_change_from_original": weighted_range(delta_old, priors, signed=True),
                                "error_change_from_IPT": change_root, "empirical_F": point,
                                "empirical_gain_from_original": before_F - point if complete else None,
                                "empirical_gain_from_IPT": gain_root,
                                "empirical_gap_change_from_IPT": change_root["value"] + gain_root if change_root["value"] is not None and gain_root is not None else None,
                                **{f"APP{app}_error": focal_value(values["errors"], known, app) for app in FOCAL_APPS},
                                "cell_children": te.shape[1], "unseen_child_target_flows": int(te[:, unseen].sum()),
                                "low_size_split_active": group == "low_size_split" and cut is not None})
                results[(key, model, group)] = values["wrong_counts"]
                confusions.append({"target": key, "model": model, "group": group, "counts_true_by_predicted": values["confusion"].tolist()})
                for i, app in enumerate(known):
                    rescued = harmed = None
                    if group == "low_size_split":
                        old = root_prediction[root_leaves[parent_map]]
                        new = prediction[leaves]
                        rescued = int(te[i, (old != i) & (new == i)].sum())
                        harmed = int(te[i, (old == i) & (new != i)].sum())
                        if harmed - rescued != int(values["wrong_counts"][i] - root_values["wrong_counts"][i]):
                            raise RuntimeError("hierarchical transfer identity failed")
                        if int(app) in protected and harmed:
                            raise RuntimeError("pointwise protected class acquired a new error")
                    classes.append({**context, "group": group, "APP": int(app), "target_n": int(ns[i]),
                                    "status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                                    "error": optional(values["errors"][i]), "conditional_change_from_IPT": optional(delta_root[i]),
                                    "weighted_change_from_IPT": optional(priors[i] * delta_root[i]),
                                    "rescued_from_IPT": rescued, "harmed_from_IPT": harmed,
                                    "signed_empirical_gain_from_IPT": optional(priors[i] * (root_oracle[i] - oracle[i])) if complete else None})
                if group == "low_size_split":
                    for b, label in enumerate(labels):
                        left = branch_context(tr[:, b], train_ns, priors, known)
                        right = branch_context(te[:, b], ns, priors, known)
                        for i, app in enumerate(known):
                            competition.append({**context, "view": "hierarchical_child", "child": b, "condition": label, "APP": int(app),
                                                "training_class_n": int(train_ns[i]), "target_class_n": int(ns[i]),
                                                "training_child_n": int(tr[i, b]), "target_child_n": int(te[i, b]),
                                                "trained_prediction_APP": int(known[prediction[leaves[b]]]),
                                                "target_empirical_winner_APP": right["winner"],
                                                "training_known_posterior": float(left["posterior"][i]) if left["posterior"] is not None else None,
                                                "target_known_posterior": float(right["posterior"][i]) if right["posterior"] is not None else None})
        if progress:
            progress(key)
    periods, period_classes = [], []
    for period in ("certificate", "evaluation"):
        items = [item for item in targets if item["period"] == period]
        ns = cache["period_counts"][period][2].sum(axis=1)
        for model in models:
            for group in GROUPS:
                context = {"period": period, "model": model, "group": group}
                tokens = [(item["key"], model, group) for item in items]
                root_tokens = [(item["key"], model, "ipt_split") for item in items]
                old_tokens = [(item["key"], model, "original") for item in items]
                if not all(token in results for token in tokens + root_tokens + old_tokens):
                    periods.append({**context, "status": "unavailable_model_windows", "weighted_error": None,
                                    "error_change_from_original": None, "error_change_from_IPT": None})
                    for i, app in enumerate(known):
                        period_classes.append({**context, "APP": int(app), "target_n": int(ns[i]), "error": None,
                                               "conditional_change_from_IPT": None, "weighted_change_from_IPT": None, "status": "unavailable_model"})
                    continue
                wrong = sum((results[token] for token in tokens), np.zeros(len(ns), dtype=np.int64))
                root_wrong = sum((results[token] for token in root_tokens), np.zeros_like(wrong))
                old_wrong = sum((results[token] for token in old_tokens), np.zeros_like(wrong))
                error, delta_root, delta_old = (np.divide(values, ns, out=np.full(len(ns), np.nan), where=ns > 0)
                                               for values in (wrong, wrong - root_wrong, wrong - old_wrong))
                periods.append({**context, "status": "complete", "weighted_error": weighted_range(error, priors),
                                "error_change_from_original": weighted_range(delta_old, priors, signed=True),
                                "error_change_from_IPT": weighted_range(delta_root, priors, signed=True),
                                **{f"APP{app}_error": focal_value(error, known, app) for app in FOCAL_APPS},
                                "positive_class_changes_from_IPT": float((priors * delta_root)[delta_root > 0].sum()),
                                "negative_class_changes_from_IPT": float((priors * delta_root)[delta_root < 0].sum())})
                for i, app in enumerate(known):
                    period_classes.append({**context, "APP": int(app), "target_n": int(ns[i]), "error": optional(error[i]),
                                           "conditional_change_from_IPT": optional(delta_root[i]), "weighted_change_from_IPT": optional(priors[i] * delta_root[i]),
                                           "status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed"})
    return {"monthly": monthly, "periods": periods, "classes": classes, "period_classes": period_classes,
            "selections": selections, "candidates": candidates, "competition": competition, "confusions": confusions}
