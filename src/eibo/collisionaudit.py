"""Descriptive error transfers and exact PPI marginals inside a fixed cell.

All fixed known classes compete. No significance test, independence claim,
new classifier or risk certificate is produced by this diagnostic stage.
"""

from __future__ import annotations

import collections

import numpy as np

from .monthlydrift import MonthlyDriftCounts, optional, weighted_range
from .realdata import whole_interval_mask
from .realexperiment import histogram_predictions
from .rolling import (MODELS, evaluate, month_index, project_fine,
                      randomization_summary, subsample_counts, training_window)


def paired_transfers(counts, old, new):
    """Exact true-class x old-prediction x new-prediction counts, same flows."""
    classes = len(counts)
    result = np.zeros((classes, classes, classes), dtype=np.int64)
    np.add.at(result, (np.arange(classes)[:, None], old[None, :], new[None, :]), counts)
    return result


def matched_class_wrong(cache, repeats, seed, progress=None):
    """Replay stage 6 randomization, retaining every class, without new fitting rules."""
    result = {}
    if repeats < 1:
        return result
    for target in (item for item in cache["slices"] if item["period"] != "pilot"):
        windows = {model: training_window(cache, target, model) for model in MODELS}
        if all(window["status"] == "ready" for window in windows.values()):
            budgets = np.min(np.stack([windows[model]["sample_counts"] for model in MODELS]), axis=0)
            for model_index, model in enumerate(MODELS):
                wrong = {rung: [] for rung in (1, 2)}
                for repetition in range(repeats):
                    rng = np.random.default_rng(np.random.SeedSequence(
                        [seed, month_index(target["month_utc"]), model_index, repetition]))
                    fine = subsample_counts(windows[model]["matrices"][2], budgets, rng)
                    for rung, sampled in ((1, project_fine(fine, cache["plan"]["k"])), (2, fine)):
                        prediction, _ = histogram_predictions(sampled, cache["priors"])
                        wrong[rung].append(evaluate(cache["counts"][target["key"]][rung], cache["priors"], prediction, 0)["wrong_counts"])
                for rung in (1, 2):
                    result[(target["key"], rung, model)] = np.stack(wrong[rung])
        if progress:
            progress(target["key"])
    return result


def reallocation(cache, predictions, matrices, *, matched=None, small_n=200, top=10):
    known, priors = cache["known"], cache["priors"]
    targets = [item for item in cache["slices"] if item["period"] != "pilot"]
    scopes = [("monthly", item["key"], [item]) for item in targets]
    scopes += [("period", period, [item for item in targets if item["period"] == period])
               for period in ("certificate", "evaluation")]
    summaries, classes, cells, transfers, matched_rows = [], [], [], [], []
    matched = matched or {}
    for scope, key, items in scopes:
        for rung in (1, 2):
            ns = sum((cache["counts"][item["key"]][rung].sum(axis=1) for item in items), np.zeros(len(known), dtype=np.int64))
            for model in MODELS[1:]:
                tokens = [(item["key"], rung, name) for item in items for name in (MODELS[0], model)]
                context = {"scope": scope, "target": key, "log_M": rung, "model": model}
                if not items or not all(token in matrices for token in tokens):
                    summaries.append({**context, "status": "unavailable_model_windows"})
                    for i, app in enumerate(known):
                        classes.append({**context, "APP": int(app), "target_n": int(ns[i]), "sample_status": "unavailable_model",
                                        "fixed_error": None, "updated_error": None, "conditional_error_change": None,
                                        "weighted_error_change": None, "rescued_count": None, "harmed_count": None,
                                        "wrong_to_wrong_changed_count": None, "prediction_changed_count": None})
                    continue
                old = sum((matrices[(item["key"], rung, MODELS[0])] for item in items), np.zeros((len(known), len(known)), dtype=np.int64))
                new = sum((matrices[(item["key"], rung, model)] for item in items), np.zeros_like(old))
                pair = sum((paired_transfers(cache["counts"][item["key"]][rung],
                            predictions[(item["key"], rung, MODELS[0])], predictions[(item["key"], rung, model)])
                            for item in items), np.zeros((len(known),) * 3, dtype=np.int64))
                if not np.array_equal(pair.sum(axis=2), old) or not np.array_equal(pair.sum(axis=1), new):
                    raise RuntimeError("paired predictions and confusion matrices disagree")
                fixed_error = np.divide(ns - old.diagonal(), ns, out=np.full(len(known), np.nan), where=ns > 0)
                updated_error = np.divide(ns - new.diagonal(), ns, out=np.full(len(known), np.nan), where=ns > 0)
                delta = updated_error - fixed_error
                weighted = priors * delta
                local = []
                for i, app in enumerate(known):
                    rescued = int(pair[i, :, i].sum() - pair[i, i, i])
                    harmed = int(pair[i, i, :].sum() - pair[i, i, i])
                    changed = int(pair[i].sum() - pair[i].trace())
                    if harmed - rescued != old[i, i] - new[i, i]:
                        raise RuntimeError("rescued/harmed identity failed")
                    row = {**context, "APP": int(app), "target_n": int(ns[i]),
                           "sample_status": "missing" if ns[i] == 0 else "small_n" if ns[i] < small_n else "observed",
                           "fixed_error": optional(fixed_error[i]), "updated_error": optional(updated_error[i]),
                           "conditional_error_change": optional(delta[i]), "weighted_error_change": optional(weighted[i]),
                           "rescued_count": rescued, "harmed_count": harmed,
                           "wrong_to_wrong_changed_count": changed - rescued - harmed, "prediction_changed_count": changed}
                    classes.append(row)
                    local.append(row)
                    for j, predicted in enumerate(known):
                        cell_delta = int(new[i, j] - old[i, j])
                        cells.append({**context, "true_APP": int(app), "predicted_APP": int(predicted),
                                      "target_n": int(ns[i]), "fixed_count": int(old[i, j]), "updated_count": int(new[i, j]),
                                      "count_change": cell_delta,
                                      "conditional_probability_change": cell_delta / int(ns[i]) if ns[i] else None,
                                      "weighted_error_change": float(priors[i] * cell_delta / ns[i]) if ns[i] and i != j else 0.0 if ns[i] else None})
                    left, right = np.nonzero(pair[i])
                    for a, b in zip(left, right):
                        if a == b:
                            continue
                        count = int(pair[i, a, b])
                        kind = "rescued" if b == i else "harmed" if a == i else "wrong_to_wrong"
                        transfers.append({**context, "true_APP": int(app), "old_prediction": int(known[a]),
                                          "new_prediction": int(known[b]), "count": count, "target_n": int(ns[i]),
                                          "kind": kind, "weighted_error_change": float(priors[i] * count / ns[i] * ((b != i) - int(a != i)))})
                point = weighted_range(delta, priors, signed=True)
                finite = weighted[np.isfinite(weighted)]
                if abs(float(finite.sum()) - point["observed_contribution"]) > 1e-12:
                    raise RuntimeError("class contributions do not sum to error change")
                ranked = [row for row in local if row["weighted_error_change"] is not None]
                summaries.append({**context, "status": "complete", "sample_counts": ns.tolist(),
                                  "fixed_weighted_error": weighted_range(fixed_error, priors),
                                  "updated_weighted_error": weighted_range(updated_error, priors), "error_change": point,
                                  "positive_class_contributions": float(finite[finite > 0].sum()),
                                  "negative_class_contributions": float(finite[finite < 0].sum()),
                                  "classes_harmed": int(np.sum(finite > 0)), "classes_improved": int(np.sum(finite < 0)),
                                  "largest_increases": sorted((row for row in ranked if row["weighted_error_change"] > 0), key=lambda row: -row["weighted_error_change"])[:top],
                                  "largest_decreases": sorted((row for row in ranked if row["weighted_error_change"] < 0), key=lambda row: row["weighted_error_change"])[:top]})
                if all(token in matched for token in tokens):
                    a = sum((matched[(item["key"], rung, MODELS[0])] for item in items))
                    b = sum((matched[(item["key"], rung, model)] for item in items))
                    differences = np.divide(b - a, ns[None, :], out=np.full(a.shape, np.nan), where=ns[None, :] > 0)
                    summaries[-1]["matched_weighted_change"] = randomization_summary(differences @ priors)
                    for i, app in enumerate(known):
                        stats = randomization_summary(differences[:, i]) or dict.fromkeys(
                            ("mean", "sd_across_training_subsets", "randomization_q05", "randomization_q95"))
                        matched_rows.append({**context, "APP": int(app), "target_n": int(ns[i]), "repetitions": len(a),
                                             "conditional_change_mean": stats["mean"],
                                             "weighted_change_mean": None if stats["mean"] is None else float(priors[i] * stats["mean"]),
                                             "conditional_randomization_sd": stats["sd_across_training_subsets"],
                                             "conditional_randomization_q05": stats["randomization_q05"],
                                             "conditional_randomization_q95": stats["randomization_q95"]})
    return {"summary": summaries, "classes": classes, "confusion_changes": cells,
            "prediction_transfers": transfers, "matched_classes": matched_rows}


class ExactMarginal:
    """Aggregate observed values, without exporting individual records."""

    def __init__(self, *, integer=False):
        self.integer = integer
        self.values = collections.Counter()
        self.total = self.invalid = 0

    def add(self, values):
        values = np.asarray(values, dtype=float)
        valid = np.isfinite(values) & (values >= (1 if self.integer else 0))
        if self.integer:
            valid &= values == np.floor(values)
        self.total += len(values)
        self.invalid += int((~valid).sum())
        keys, counts = np.unique(values[valid], return_counts=True)
        self.values.update({float(value): int(count) for value, count in zip(keys, counts)})

    def merge(self, other):
        self.values.update(other.values)
        self.total += other.total
        self.invalid += other.invalid

    def summary(self):
        count = sum(self.values.values())
        result = {"flows": self.total, "valid_values": count, "invalid_values": self.invalid,
                  "distinct_values": len(self.values), "mean": None, "q05": None, "q25": None,
                  "median": None, "q75": None, "q95": None, "min": None, "max": None,
                  "zero_fraction": None, "fraction_eq_1200": None, "fraction_gt_1500": None}
        if count:
            keys = sorted(self.values)
            cumulative = np.cumsum([self.values[value] for value in keys])
            result.update({"mean": sum(value * self.values[value] for value in keys) / count,
                           "min": keys[0], "max": keys[-1], "zero_fraction": self.values[0.0] / count,
                           "fraction_eq_1200": self.values[1200.0] / count,
                           "fraction_gt_1500": sum(n for value, n in self.values.items() if value > 1500) / count})
            # Empirical inverse-CDF quantiles: no interpolation over unobserved values.
            for name, q in (("q05", .05), ("q25", .25), ("median", .5), ("q75", .75), ("q95", .95)):
                result[name] = keys[int(np.searchsorted(cumulative, max(1, int(np.ceil(q * count))), side="left"))]
        return result


def compare_marginals(left, right):
    nl, nr = sum(left.values.values()), sum(right.values.values())
    if not nl or not nr:
        return {"empirical_TV": None, "empirical_CDF_sup_distance": None, "empirical_overlap": None}
    keys = sorted(set(left.values) | set(right.values))
    changes = np.array([left.values[value] / nl - right.values[value] / nr for value in keys])
    tv = float(.5 * np.abs(changes).sum())
    return {"empirical_TV": tv, "empirical_CDF_sup_distance": float(np.abs(np.cumsum(changes)).max()),
            "empirical_overlap": 1 - tv}


class CollisionCounts(MonthlyDriftCounts):
    """Rescan the audited population; detail only the selected classes/cell."""

    def __init__(self, plan, tables, *, time_scale, symbol=479, apps=(2, 34)):
        super().__init__(plan, tables, time_scale=time_scale)
        if not 0 <= symbol < self.encoders[2].alphabet or not set(apps).issubset(self.known) or len(set(apps)) != 2:
            raise ValueError("two distinct fixed known APPs and a canonical symbol are required")
        self.symbol, self.apps = int(symbol), tuple(map(int, apps))
        self.details = {item["key"]: {app: {(feature, position): ExactMarginal(integer=feature == "size_bytes")
                        for feature in ("size_bytes", "IPT_ms") for position in range(1, self.k + 1)}
                        for app in self.apps} for item in self.slices}
        self.detail_counts = {item["key"]: collections.Counter() for item in self.slices}

    def add(self, records, capacity):
        super().add(records, capacity)
        first, last = (np.asarray(records[field], dtype=float) / self.time_scale for field in ("TIME_FIRST", "TIME_LAST"))
        lengths, labels = np.asarray(records["PPI_LEN"], dtype=float), np.asarray(records["APP"])
        usable = (np.isfinite(first) & np.isfinite(last) & (last >= first) & (first >= self.begin) & (first < self.end) &
                  np.isfinite(lengths) & (lengths == np.floor(lengths)) & (lengths >= self.k) & (lengths <= capacity) & np.isin(labels, self.apps))
        for period, window in self.windows.items():
            selected = usable & whole_interval_mask(first, last, window, self.rounding)
            ppi = records["PPI"][selected]
            hit = self.encoders[2].encode(ppi) == self.symbol
            if not hit.any():
                continue
            ppi, times, selected_labels = ppi[hit], first[selected][hit], labels[selected][hit]
            indices = np.searchsorted(self.slice_starts[period], times, side="right") - 1
            for index in np.unique(indices):
                key = self.slice_keys[period][int(index)]
                for app in self.apps:
                    values = ppi[(indices == index) & (selected_labels == app)]
                    self.detail_counts[key][app] += len(values)
                    for position in range(1, self.k + 1):
                        for feature, row in (("size_bytes", 2), ("IPT_ms", 0)):
                            self.details[key][app][(feature, position)].add(values[:, row, position - 1])

    def reconcile_cache(self, cache):
        self.reconcile_months(cache["period_counts"])
        for item in self.slices:
            key = item["key"]
            for rung in (1, 2):
                if not np.array_equal(self.monthly[key][rung], cache["counts"][key][rung]):
                    raise ValueError(f"raw monthly symbols differ from cache: {key}, M={rung}")
            for app in self.apps:
                expected = int(self.monthly[key][2][np.flatnonzero(self.known == app)[0], self.symbol])
                if self.detail_counts[key][app] != expected or any(m.total != expected for m in self.details[key][app].values()):
                    raise RuntimeError(f"collision detail count differs from canonical cell: {key}, APP={app}")


def collision_analysis(counts, *, reference_months=("2024-12", "2025-01"), small_n=200):
    reference = [item for item in counts.slices if item["month_utc"] in reference_months]
    if len(set(reference_months)) != len(reference_months) or any(not any(item["month_utc"] == month for item in reference) for month in reference_months):
        raise ValueError("reference months must be distinct and present")
    scopes = [("monthly", item["key"], [item]) for item in counts.slices]
    scopes += [("period", period, [item for item in counts.slices if item["period"] == period]) for period in counts.windows]
    scopes.append(("reference", "+".join(reference_months), reference))
    pooled, feature_rows, distribution_rows, occupancy, comparisons = {}, [], [], [], []
    for scope, key, items in scopes:
        matrix = sum((counts.monthly[item["key"]][2] for item in items), np.zeros_like(counts.counts["pilot"][2]))
        ns, cell = matrix.sum(axis=1), matrix[:, counts.symbol]
        scores = np.divide(cell * counts.priors, ns, out=np.full(len(ns), np.nan), where=ns > 0)
        denominator = scores.sum() if np.isfinite(scores).all() else np.nan
        for i, app in enumerate(counts.known):
            occupancy.append({"scope": scope, "target": key, "APP": int(app), "class_n": int(ns[i]),
                              "symbol_n": int(cell[i]), "class_probability_of_symbol": cell[i] / ns[i] if ns[i] else None,
                              "fixed_prior_symbol_mass": optional(scores[i]),
                              "known_only_posterior_in_symbol": float(scores[i] / denominator) if denominator > 0 else None})
        pooled[key] = {}
        for app in counts.apps:
            pooled[key][app] = {}
            for feature, position in counts.details[items[0]["key"]][app]:
                marginal = ExactMarginal(integer=feature == "size_bytes")
                for item in items:
                    marginal.merge(counts.details[item["key"]][app][(feature, position)])
                pooled[key][app][(feature, position)] = marginal
                stats = marginal.summary()
                feature_rows.append({"scope": scope, "target": key, "APP": app, "feature": feature, "position": position,
                                     "structural_first_IPT": feature == "IPT_ms" and position == 1,
                                     "sample_status": "missing" if stats["flows"] == 0 else "small_n" if stats["flows"] < small_n else "observed", **stats})
                valid = stats["valid_values"]
                for value, n in sorted(marginal.values.items()):
                    distribution_rows.append({"scope": scope, "target": key, "APP": app, "feature": feature, "position": position,
                                              "value": value, "count": n, "valid_values": valid, "probability": n / valid})
        for feature, position in pooled[key][counts.apps[0]]:
            left, right = (pooled[key][app][(feature, position)] for app in counts.apps)
            comparisons.append({"comparison": "within_symbol_between_classes", "scope": scope, "source": key, "target": key,
                                "source_APP": counts.apps[0], "target_APP": counts.apps[1], "feature": feature, "position": position,
                                "source_valid_n": sum(left.values.values()), "target_valid_n": sum(right.values.values()),
                                "structural_first_IPT": feature == "IPT_ms" and position == 1, **compare_marginals(left, right)})
    reference_key = "+".join(reference_months)
    stop = max(item["end_epoch"] for item in reference)
    for item in counts.slices:
        if item["start_epoch"] < stop:
            continue
        for app in counts.apps:
            for (feature, position), right in pooled[item["key"]][app].items():
                left = pooled[reference_key][app][(feature, position)]
                comparisons.append({"comparison": "within_class_reference_to_month", "scope": "monthly", "source": reference_key, "target": item["key"],
                                    "source_APP": app, "target_APP": app, "feature": feature, "position": position,
                                    "source_valid_n": sum(left.values.values()), "target_valid_n": sum(right.values.values()),
                                    "structural_first_IPT": feature == "IPT_ms" and position == 1, **compare_marginals(left, right)})
    return {"features": feature_rows, "distributions": distribution_rows, "occupancy": occupancy, "comparisons": comparisons}
