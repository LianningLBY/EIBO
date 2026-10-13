"""Past-fit low-IPT atom diagnostics and exact all-class error attribution.

Target oracles are descriptive competitors under the frozen high/invalid and
outside-cell rules. They are never used to select a position or fit a model.
"""

from __future__ import annotations

import numpy as np

from .hierarchy import fit_low_prediction
from .monthlydrift import optional, weighted_range
from .realexperiment import histogram_predictions
from .refinement import collapse_atoms, fit_prediction, refine_counts, select_splits
from .rolling import evaluate, training_window

FOCAL_APPS = (2, 15, 21, 22, 34)


def atomic_children(atoms, position_index, root):
    """Single-position size x IPT atoms within low IPT; other parents intact."""
    if root is None:
        raise ValueError("an eligible IPT root is required for low-atom diagnostics")
    values = atoms[position_index]
    stop = root["atom_index"] + 1
    low = values[:, :, :stop].reshape(len(values), -1)
    high = values[:, :, stop:-1].sum(axis=(1, 2))
    invalid = values[:, :, -1].sum(axis=1)
    children = np.concatenate((low, high[:, None], invalid[:, None]), axis=1)
    return children, np.array([0] * low.shape[1] + [1, 2])


def guarded_prediction(train, priors, parent_prediction, parent_leaves, parent_map, symbol, alphabet, minimum):
    if minimum < 1:
        raise ValueError("positive atomic training-flow budget required")
    prediction, leaves, _ = fit_low_prediction(train, priors, parent_prediction, parent_leaves, parent_map, symbol, alphabet)
    pooled = train[:, leaves].sum(axis=0)
    backed_off = (parent_map == 0) & (pooled < minimum)
    prediction[leaves[backed_off]] = parent_prediction[parent_leaves[0]]
    return prediction, leaves, backed_off


def low_oracle(test, priors, prediction, leaves, parent_map):
    result = prediction.copy()
    fitted, _ = histogram_predictions(test, priors)
    low = leaves[parent_map == 0]
    result[low] = fitted[low]
    return result


def interval_label(index, cuts, unit):
    if index == 0:
        return f"[0,{cuts[0]:g}] {unit}"
    if index == len(cuts):
        return f"({cuts[-1]:g},inf) {unit}"
    return f"({cuts[index - 1]:g},{cuts[index]:g}] {unit}"


def metrics(train, test, priors, prediction, leaves, parent_map, root_train_values, root_test_values,
            root_oracle_values, known):
    fitted_train, fitted_test = evaluate(train, priors, prediction, 0), evaluate(test, priors, prediction, 0)
    change = fitted_test["errors"] - root_test_values["errors"]
    oracle = evaluate(test, priors, low_oracle(test, priors, prediction, leaves, parent_map), 0) if np.all(test.sum(axis=1) > 0) else None
    root_error = root_test_values["summary"]["weighted_error"]["value"]
    new_error = fitted_test["summary"]["weighted_error"]["value"]
    oracle_error = oracle["summary"]["weighted_error"]["value"] if oracle else None
    coarse_oracle_error = root_oracle_values["summary"]["weighted_error"]["value"] if root_oracle_values else None
    gain = coarse_oracle_error - oracle_error if oracle else None
    if gain is not None and gain < -1e-12:
        raise RuntimeError("atomic refinement raised the constrained target empirical risk")
    result = {"training_gain_vs_IPT": float((root_train_values["errors"] - fitted_train["errors"]) @ priors),
              "weighted_error": fitted_test["summary"]["weighted_error"], "error_change_vs_IPT": weighted_range(change, priors, signed=True),
              "raw_wrong": int(fitted_test["wrong_counts"].sum()),
              "raw_error_change_count_vs_IPT": int((fitted_test["wrong_counts"] - root_test_values["wrong_counts"]).sum()),
              "root_adaptation_gain": root_error - coarse_oracle_error if oracle else None,
              "empirical_representation_gain": gain, "total_oracle_gain_vs_IPT": root_error - oracle_error if oracle else None,
              "past_model_regret_to_atomic_oracle": new_error - oracle_error if oracle else None,
              "cell_children": len(leaves)}
    for app in FOCAL_APPS:
        if app not in known:
            result[f"APP{app}_error"] = result[f"APP{app}_change_vs_IPT"] = None
            continue
        i = int(np.flatnonzero(known == app)[0])
        result[f"APP{app}_error"] = optional(fitted_test["errors"][i])
        result[f"APP{app}_change_vs_IPT"] = optional(change[i])
    if 2 in known:
        i = int(np.flatnonzero(known == 2)[0])
        result["APP2_wrong"] = int(fitted_test["wrong_counts"][i])
        result["APP2_atomic_oracle_error"] = optional(oracle["errors"][i]) if oracle else None
        result["APP2_atomic_oracle_change_vs_IPT"] = optional(oracle["errors"][i] - root_test_values["errors"][i]) if oracle else None
    if oracle and abs(result["error_change_vs_IPT"]["value"] + result["total_oracle_gain_vs_IPT"] - result["past_model_regret_to_atomic_oracle"]) > 1e-12:
        raise RuntimeError("atomic oracle gain/regret identity failed")
    return result, fitted_test


def run_atomic_diagnostic(cache, atoms, protocol, *, minimum=200, small_n=200, progress=None):
    known, priors = cache["known"], cache["priors"]
    positions = tuple(protocol["size_positions"])
    size_cuts, ipt_cuts, symbol = protocol["size_candidates_bytes"], protocol["IPT2_candidates_ms"], protocol["symbol_id"]
    monthly, choices, cells, confusions, results, monthly_classes = [], [], [], [], {}, []
    for target in (item for item in cache["slices"] if item["period"] != "pilot"):
        key, base = target["key"], cache["counts"][target["key"]][2]
        target_ns, alphabet = base.sum(axis=1), base.shape[1]
        for model in protocol["models"]:
            context = {"target": key, "period": target["period"], "model": model}
            window = training_window(cache, target, model)
            if window["status"] != "ready":
                choices.append({**context, "status": window["status"], "selected_size_position": None, "training_slices": window["training_slices"]})
                monthly.append({**context, "group": "selected_atomic", "status": window["status"], "size_position": None, "weighted_error": None})
                for i, app in enumerate(known):
                    monthly_classes.append({**context, "group": "selected_atomic", "APP": int(app), "n": int(target_ns[i]), "status": "unavailable_model",
                                            "wrong": None, "error": None, "conditional_change_vs_IPT": None, "weighted_change_vs_IPT": None})
                continue
            train_base, train_ns = window["matrices"][2], window["sample_counts"]
            past = sum((atoms[name] for name in window["training_slices"]), np.zeros_like(atoms[key]))
            selection, _ = select_splits(past, train_ns, priors, positions, size_cuts, ipt_cuts, min_leaf=protocol["minimum_leaf_flows"])
            root_train, _ = collapse_atoms(past, positions, selection, "ipt_split")
            root_test, _ = collapse_atoms(atoms[key], positions, selection, "ipt_split")
            tr, te = refine_counts(train_base, root_train, symbol), refine_counts(base, root_test, symbol)
            original, _ = histogram_predictions(train_base, priors)
            root_prediction, root_leaves, _ = fit_prediction(tr, priors, original, symbol, alphabet)
            root_train_values, root_test_values = evaluate(tr, priors, root_prediction, 0), evaluate(te, priors, root_prediction, 0)
            root_map = np.arange(len(root_leaves))
            root_oracle = evaluate(te, priors, low_oracle(te, priors, root_prediction, root_leaves, root_map), 0) if np.all(target_ns > 0) else None
            identity, _ = metrics(tr, te, priors, root_prediction, root_leaves, root_map, root_train_values, root_test_values, root_oracle, known)
            selected = {**context, "status": "complete", "group": "selected_atomic", "size_position": None, **identity,
                        "backoff_target_flows": 0, "APP34_protected": True,
                        "guard_error_change": weighted_range(np.where(target_ns > 0, 0., np.nan), priors, signed=True),
                        "unguarded_past_regret": identity["past_model_regret_to_atomic_oracle"],
                        "APP2_guard_change": 0. if 2 in known and target_ns[np.flatnonzero(known == 2)[0]] else None}
            selected_values, best_gain = root_test_values, 0.0
            low_label = int(root_prediction[root_leaves[0]])
            if selection["ipt"] is not None:
                for p, position in enumerate(positions):
                    a, parent_map = atomic_children(past, p, selection["ipt"])
                    b, _ = atomic_children(atoms[key], p, selection["ipt"])
                    train, test = refine_counts(train_base, a, symbol), refine_counts(base, b, symbol)
                    prediction, leaves, backed = guarded_prediction(train, priors, root_prediction, root_leaves, parent_map, symbol, alphabet, minimum)
                    measured, values = metrics(train, test, priors, prediction, leaves, parent_map, root_train_values, root_test_values, root_oracle, known)
                    unguarded, _, _ = fit_low_prediction(train, priors, root_prediction, root_leaves, parent_map, symbol, alphabet)
                    unguarded_values = evaluate(test, priors, unguarded, 0)
                    guard_delta = values["errors"] - unguarded_values["errors"]
                    guard_change = weighted_range(guard_delta, priors, signed=True)
                    regret = measured["past_model_regret_to_atomic_oracle"]
                    unguarded_regret = regret - guard_change["value"] if regret is not None else None
                    if unguarded_regret is not None and unguarded_regret < -1e-12:
                        raise RuntimeError("unguarded model beat the constrained target oracle")
                    if measured["training_gain_vs_IPT"] < -1e-12:
                        raise RuntimeError("past atomic model increased training risk")
                    protected = np.arange(len(known)) != low_label
                    if np.any(values["wrong_counts"][protected] > root_test_values["wrong_counts"][protected]):
                        raise RuntimeError("atomic model harmed a structurally protected class")
                    row = {**context, "status": "complete", "group": "position_atomic", "size_position": int(position), **measured,
                           "backoff_target_flows": int(b[:, backed].sum()), "APP34_protected": 34 not in known or int(known[low_label]) != 34,
                           "guard_error_change": guard_change, "unguarded_past_regret": unguarded_regret,
                           "APP2_guard_change": optional(guard_delta[np.flatnonzero(known == 2)[0]]) if 2 in known else None}
                    monthly.append(row)
                    # The target metrics above are diagnostic; only the past
                    # training gain controls selection. Identity wins zero ties.
                    if measured["training_gain_vs_IPT"] > best_gain + 1e-12:
                        selected = {**row, "group": "selected_atomic"}
                        selected_values, best_gain = values, measured["training_gain_vs_IPT"]
                    if 2 in known:
                        focal, stop = int(np.flatnonzero(known == 2)[0]), selection["ipt"]["atom_index"] + 1
                        scores = a * (priors / train_ns)[:, None]
                        target_scores = b * np.divide(priors, target_ns, out=np.zeros(len(known)), where=target_ns > 0)[:, None]
                        raw_prediction, _ = histogram_predictions(train, priors)
                        complete = bool(np.all(target_ns > 0))
                        for j in np.flatnonzero(parent_map == 0):
                            s, t = divmod(int(j), stop)
                            present = bool(b[:, j].sum())
                            winner = int(target_scores[:, j].argmax()) if complete and present else None
                            rivals = np.arange(len(known)) != focal
                            cells.append({**context, "size_position": int(position), "size_atom": s, "IPT_atom": t,
                                          "size_interval": interval_label(s, size_cuts, "B"), "IPT_interval": interval_label(t, ipt_cuts, "ms"),
                                          "training_flows": int(a[:, j].sum()), "target_flows": int(b[:, j].sum()),
                                          "target_population_complete": complete,
                                          "APP2_training_flows": int(a[focal, j]), "APP2_target_flows": int(b[focal, j]),
                                          "APP2_training_score": float(scores[focal, j]), "APP2_target_score": float(target_scores[focal, j]) if target_ns[focal] else None,
                                          "APP2_training_margin": float(scores[focal, j] - scores[rivals, j].max()) if rivals.any() else None,
                                          "APP2_target_margin": float(target_scores[focal, j] - target_scores[rivals, j].max()) if complete and present and rivals.any() else None,
                                          "strongest_training_rival_APP": int(known[np.flatnonzero(rivals)[scores[rivals, j].argmax()]]) if a[:, j].sum() and rivals.any() else None,
                                          "strongest_target_rival_APP": int(known[np.flatnonzero(rivals)[target_scores[rivals, j].argmax()]]) if complete and present and rivals.any() else None,
                                          "unrestricted_training_winner_APP": int(known[raw_prediction[leaves[j]]]) if a[:, j].sum() else None,
                                          "trained_prediction_APP": int(known[prediction[leaves[j]]]),
                                          "target_empirical_winner_APP": int(known[winner]) if winner is not None else None,
                                          "training_backoff": bool(backed[j]),
                                          "training_APP2_winner": bool(a[:, j].sum() and raw_prediction[leaves[j]] == focal),
                                          "target_APP2_winner": bool(winner == focal) if winner is not None else None})
            monthly.append(selected)
            choices.append({**context, "status": "ready", "training_slices": window["training_slices"],
                            "last_training_end_epoch": max(item["end_epoch"] for item in cache["slices"] if item["key"] in window["training_slices"]),
                            "target_start_epoch": target["start_epoch"], "IPT2_threshold_ms": selection["ipt"]["threshold"] if selection["ipt"] else None,
                            "low_parent_APP": int(known[low_label]), "selected_size_position": selected["size_position"], "training_gain_vs_IPT": best_gain})
            for group, values in (("ipt_split", root_test_values), ("selected_atomic", selected_values)):
                results[(key, model, group)] = values["wrong_counts"]
                confusions.append({"target": key, "model": model, "group": group, "counts_true_by_predicted": values["confusion"].tolist()})
                delta = values["errors"] - root_test_values["errors"]
                for i, app in enumerate(known):
                    monthly_classes.append({**context, "group": group, "APP": int(app), "n": int(target_ns[i]),
                                            "status": "missing" if target_ns[i] == 0 else "small_n" if target_ns[i] < small_n else "observed",
                                            "wrong": int(values["wrong_counts"][i]), "error": optional(values["errors"][i]),
                                            "conditional_change_vs_IPT": optional(delta[i]), "weighted_change_vs_IPT": optional(priors[i] * delta[i])})
        if progress:
            progress(key)
    periods, classes = [], []
    for period in ("certificate", "evaluation"):
        ns = cache["period_counts"][period][2].sum(axis=1)
        targets = [item["key"] for item in cache["slices"] if item["period"] == period]
        for model in protocol["models"]:
            for group in ("ipt_split", "selected_atomic"):
                tokens = [(key, model, group) for key in targets]
                if not all(token in results for token in tokens):
                    periods.append({"period": period, "model": model, "group": group, "status": "unavailable_model_windows", "weighted_error": None})
                    for i, app in enumerate(known):
                        classes.append({"period": period, "model": model, "group": group, "APP": int(app), "n": int(ns[i]), "status": "unavailable_model", "wrong": None,
                                        "error": None, "conditional_change_vs_IPT": None, "weighted_change_vs_IPT": None})
                    continue
                wrong = sum((results[token] for token in tokens), np.zeros(len(ns), dtype=np.int64))
                root_wrong = sum((results[(key, model, "ipt_split")] for key in targets), np.zeros_like(wrong))
                error, change = (np.divide(v, ns, out=np.full(len(ns), np.nan), where=ns > 0) for v in (wrong, wrong - root_wrong))
                row = {"period": period, "model": model, "group": group, "status": "complete", "weighted_error": weighted_range(error, priors),
                       "error_change_vs_IPT": weighted_range(change, priors, signed=True), "raw_wrong": int(wrong.sum()), "raw_error_change_count_vs_IPT": int((wrong - root_wrong).sum())}
                for app in FOCAL_APPS:
                    row[f"APP{app}_error"] = optional(error[np.flatnonzero(known == app)[0]]) if app in known else None
                periods.append(row)
                for i, app in enumerate(known):
                    classes.append({"period": period, "model": model, "group": group, "APP": int(app), "n": int(ns[i]), "wrong": int(wrong[i]),
                                    "status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                                    "error": optional(error[i]), "conditional_change_vs_IPT": optional(change[i]), "weighted_change_vs_IPT": optional(priors[i] * change[i])})
    return {"monthly": monthly, "monthly_classes": monthly_classes, "periods": periods, "period_classes": classes,
            "choices": choices, "APP2_cells": cells, "confusions": confusions}


def attribute_hierarchy(cache, previous, *, small_n=200):
    """Reconstruct monthly and pooled losses from integer confusion counts."""
    known, priors = cache["known"], cache["priors"]
    matrices = {(r["target"], r["model"], r["group"]): np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in previous["confusions"]}
    transfers = {(r["target"], r["model"], r["APP"]): r for r in previous["classes"] if r["group"] == "low_size_split"}
    models = list(dict.fromkeys(r["model"] for r in previous["selections"]))
    scopes = [("monthly", item["key"], [item["key"]]) for item in cache["slices"] if item["period"] != "pilot"]
    scopes += [("period", period, [item["key"] for item in cache["slices"] if item["period"] == period]) for period in ("certificate", "evaluation")]
    classes, summaries = [], []
    for scope, target, keys in scopes:
        ns = sum((cache["counts"][key][2].sum(axis=1) for key in keys), np.zeros(len(known), dtype=np.int64))
        for model in models:
            context = {"scope": scope, "target": target, "model": model}
            available = all((key, model, group) in matrices for key in keys for group in ("ipt_split", "low_size_split"))
            if not available:
                summaries.append({**context, "status": "unavailable_model_windows", "raw_error_change_count": None, "weighted_change": None})
                for i, app in enumerate(known):
                    classes.append({**context, "APP": int(app), "n": int(ns[i]), "status": "unavailable_model", "rescued": None, "harmed": None,
                                    "raw_wrong_change": None, "conditional_change": None, "weighted_change": None})
                continue
            old, new = (sum((matrices[(key, model, group)] for key in keys), np.zeros((len(known), len(known)), dtype=np.int64)) for group in ("ipt_split", "low_size_split"))
            if not np.array_equal(old.sum(axis=1), ns) or not np.array_equal(new.sum(axis=1), ns):
                raise RuntimeError("attribution confusion population differs")
            delta = np.diag(old) - np.diag(new)
            rates = np.divide(delta, ns, out=np.full(len(ns), np.nan), where=ns > 0)
            rescues, harms = [], []
            for i, app in enumerate(known):
                rescued = sum(transfers[(key, model, int(app))]["rescued_from_IPT"] for key in keys)
                harmed = sum(transfers[(key, model, int(app))]["harmed_from_IPT"] for key in keys)
                if harmed - rescued != delta[i]:
                    raise RuntimeError("attribution transfer identity failed")
                rescues.append(rescued)
                harms.append(harmed)
                classes.append({**context, "APP": int(app), "n": int(ns[i]), "status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                                "rescued": int(rescued), "harmed": int(harmed), "raw_wrong_change": int(delta[i]),
                                "conditional_change": optional(rates[i]), "weighted_change": optional(priors[i] * rates[i])})
            summaries.append({**context, "status": "complete", "raw_error_change_count": int(delta.sum()),
                              "raw_rescued": int(sum(rescues)), "raw_harmed": int(sum(harms)), "weighted_change": weighted_range(rates, priors, signed=True),
                              "positive_weighted_changes": float(np.nansum((priors * rates)[rates > 0])),
                              "negative_weighted_changes": float(np.nansum((priors * rates)[rates < 0]))})
    return {"classes": classes, "summary": summaries}
