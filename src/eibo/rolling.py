"""Past-only histogram comparisons and descriptive focal-symbol attribution.

All competitors and priors remain fixed. Current-period empirical winners are
diagnostics only. Matched-count randomization is without replacement from the
observed training counts; its spread is not a population confidence interval.
"""

from __future__ import annotations

import numpy as np

from .monthlydrift import laws_and_presence, model_errors, optional, weighted_range
from .realexperiment import fine_to_coarse_ids, histogram_predictions
from .statcore import DEFAULT_MAX_SIZE, grid_cardinality, quantization_grid, quantize, symbol_to_id

MODELS = ("fixed_pilot", "rolling_1m", "rolling_3m")


def month_index(month):
    year, number = map(int, month.split("-"))
    if year < 1 or not 1 <= number <= 12:
        raise ValueError("expected a YYYY-MM calendar month")
    return year * 12 + number - 1


def month_label(index):
    year, month = divmod(index, 12)
    return f"{year:04d}-{month + 1:02d}"


def project_fine(counts, k):
    mapping = fine_to_coarse_ids(k)
    result = np.zeros((len(counts), grid_cardinality("log", log_bins=1) ** k), dtype=np.int64)
    np.add.at(result, (np.arange(len(counts))[:, None], mapping[None, :]), counts)
    return result


def training_window(cache, target, model):
    if model == "fixed_pilot":
        selected = [item for item in cache["slices"] if item["period"] == "pilot"]
        missing_months = []
    else:
        width = 1 if model == "rolling_1m" else 3 if model == "rolling_3m" else None
        if width is None:
            raise ValueError("unknown rolling model")
        end = month_index(target["month_utc"])
        required = [month_label(index) for index in range(end - width, end)]
        selected = [item for item in cache["slices"] if item["month_utc"] in required]
        missing_months = [month for month in required if not any(item["month_utc"] == month for item in selected)]
    if any(item["end_epoch"] > target["start_epoch"] for item in selected):
        raise ValueError("training window overlaps or follows the target slice")
    matrices = {rung: sum((cache["counts"][item["key"]][rung] for item in selected),
                         np.zeros_like(cache["period_counts"]["pilot"][rung])) for rung in (1, 2)}
    ns = matrices[2].sum(axis=1)
    missing_services = cache["known"][ns == 0].tolist()
    status = "unavailable_missing_calendar_months" if missing_months else "unavailable_missing_training_classes" if missing_services else "ready"
    return {"status": status, "matrices": matrices, "sample_counts": ns,
            "training_slices": [item["key"] for item in selected],
            "missing_calendar_months": missing_months, "missing_training_services": missing_services,
            "empty_training_slices": [item["key"] for item in selected if cache["counts"][item["key"]][2].sum() == 0],
            "available_table_days": sum(item["available_table_days"] for item in selected),
            "calendar_days": sum(item["calendar_days"] for item in selected)}


def confusion_counts(counts, prediction):
    result = np.zeros((len(counts), len(counts)), dtype=np.int64)
    np.add.at(result, (np.arange(len(counts))[:, None], prediction[None, :]), counts)
    if not np.array_equal(result.sum(axis=1), counts.sum(axis=1)):
        raise RuntimeError("confusion rows do not conserve target counts")
    return result


def evaluate(counts, priors, prediction, focal):
    laws, ns, present = laws_and_presence(counts)
    errors = model_errors(laws, present, prediction)
    confusion = confusion_counts(counts, prediction)
    wrong = ns - np.diag(confusion)
    probabilities = np.divide(confusion, ns[:, None], out=np.full(confusion.shape, np.nan), where=ns[:, None] > 0)
    outgoing = probabilities[focal]
    incoming = probabilities[:, focal]
    known_predicted_mass = float(np.nansum(priors * incoming)) if present.all() else None
    tp = optional(priors[focal] * incoming[focal])
    return {"sample_counts": ns, "errors": errors, "wrong_counts": wrong, "confusion": confusion,
            "focal_outgoing": outgoing, "focal_incoming": incoming,
            "summary": {"weighted_error": weighted_range(errors, priors), "focal_error": optional(errors[focal]),
                        "focal_weighted_error": optional(priors[focal] * errors[focal]),
                        "known_only_focal_precision": tp / known_predicted_mass if known_predicted_mass is not None and known_predicted_mass > 0 and tp is not None else None}}


def subsample_counts(counts, budgets, rng):
    """Exact finite-population draws, including a fallback for older NumPy."""
    sampled = np.zeros_like(counts)
    for row, (values, budget) in enumerate(zip(counts, budgets)):
        total, wanted = int(values.sum()), int(budget)
        if wanted < 1 or wanted > total:
            raise ValueError("matched per-class budgets must be positive and no larger than training counts")
        if wanted == total:
            sampled[row] = values
        elif hasattr(rng, "multivariate_hypergeometric"):
            sampled[row] = rng.multivariate_hypergeometric(values, wanted)
        else:
            indices = np.flatnonzero(values)
            remaining = wanted
            for index in indices[:-1]:
                good = int(values[index])
                draw = int(rng.hypergeometric(good, total - good, remaining)) if remaining else 0
                sampled[row, index] = draw
                remaining -= draw
                total -= good
            sampled[row, indices[-1]] = remaining
    if not np.array_equal(sampled.sum(axis=1), budgets) or np.any(sampled > counts):
        raise RuntimeError("matched draw exceeded the observed counts")
    return sampled


def randomization_summary(values):
    values = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(values)):
        return None
    return {"mean": float(values.mean()), "sd_across_training_subsets": float(values.std()),
            "randomization_q05": float(np.quantile(values, 0.05)), "randomization_q95": float(np.quantile(values, 0.95))}


def rolling_experiment(cache, *, app=2, repeats=100, seed=20261012, small_n=200, progress=None):
    known, priors, k = cache["known"], cache["priors"], cache["plan"]["k"]
    if app not in known:
        raise ValueError("focal APP is absent from the fixed known-class plan")
    focal = int(np.flatnonzero(known == app)[0])
    targets = [item for item in cache["slices"] if item["period"] != "pilot"]
    full_rows, class_rows, focal_rows, matched_rows = [], [], [], []
    predictions, evaluations, matched_wrong, model_windows = {}, {}, {}, {}
    for target in targets:
        key = target["key"]
        windows = {model: training_window(cache, target, model) for model in MODELS}
        model_windows[key] = windows
        for model in MODELS:
            window = windows[model]
            for rung in (1, 2):
                row = {"target": key, "period": target["period"], "log_M": rung, "model": model,
                       "status": window["status"], "training_slices": window["training_slices"],
                       "training_sample_counts": window["sample_counts"].tolist(),
                       "missing_calendar_months": window["missing_calendar_months"],
                       "missing_training_services": window["missing_training_services"],
                       "empty_training_slices": window["empty_training_slices"],
                       "training_calendar_days": window["calendar_days"], "training_available_table_days": window["available_table_days"]}
                if window["status"] != "ready":
                    row.update({"weighted_error": None, "focal_error": None})
                    full_rows.append(row)
                    continue
                prediction, _ = histogram_predictions(window["matrices"][rung], priors)
                predictions[(key, rung, model)] = prediction
                values = evaluate(cache["counts"][key][rung], priors, prediction, focal)
                evaluations[(key, rung, model)] = values
                row.update(values["summary"])
                row["target_sample_counts"] = values["sample_counts"].tolist()
                full_rows.append(row)
                for i, service in enumerate(known):
                    n = int(values["sample_counts"][i])
                    class_rows.append({"target": key, "log_M": rung, "model": model, "service_code": int(service),
                        "training_n": int(window["sample_counts"][i]), "target_n": n,
                        "target_sample_status": "missing" if n == 0 else "small_n" if n < small_n else "observed",
                        "error": optional(values["errors"][i]), "weighted_error": optional(priors[i] * values["errors"][i])})
                    focal_rows.append({"target": key, "log_M": rung, "model": model, "other_service_code": int(service),
                        "APP_focal_target_n": int(values["sample_counts"][focal]),
                        "focal_to_other_count": int(values["confusion"][focal, i]),
                        "focal_to_other_probability": optional(values["focal_outgoing"][i]),
                        "other_target_n": n, "other_to_focal_count": int(values["confusion"][i, focal]),
                        "other_to_focal_probability": optional(values["focal_incoming"][i])})
        if repeats and all(window["status"] == "ready" for window in windows.values()):
            budgets = np.min(np.stack([windows[model]["sample_counts"] for model in MODELS]), axis=0)
            for model_index, model in enumerate(MODELS):
                errors, focal_errors = {r: [] for r in (1, 2)}, {r: [] for r in (1, 2)}
                wrong_by_rung = {r: [] for r in (1, 2)}
                for repetition in range(repeats):
                    rng = np.random.default_rng(np.random.SeedSequence([seed, month_index(target["month_utc"]), model_index, repetition]))
                    fine = subsample_counts(windows[model]["matrices"][2], budgets, rng)
                    # Identical selected training flows for both representations.
                    sampled = {2: fine, 1: project_fine(fine, k)}
                    for rung in (1, 2):
                        prediction, _ = histogram_predictions(sampled[rung], priors)
                        values = evaluate(cache["counts"][key][rung], priors, prediction, focal)
                        point = values["summary"]["weighted_error"]["value"]
                        errors[rung].append(np.nan if point is None else point)
                        focal_errors[rung].append(values["errors"][focal])
                        wrong_by_rung[rung].append(values["wrong_counts"])
                for rung in (1, 2):
                    matched_wrong[(key, rung, model)] = np.stack(wrong_by_rung[rung])
                    matched_rows.append({"target": key, "period": target["period"], "log_M": rung, "model": model,
                                         "status": "conditional_training_subsample_comparison", "repetitions": repeats,
                                         "per_class_training_budgets": budgets.tolist(),
                                         "weighted_error": randomization_summary(errors[rung]), "focal_error": randomization_summary(focal_errors[rung])})
        elif repeats:
            matched_rows.append({"target": key, "period": target["period"], "log_M": None, "model": None,
                                 "status": "unavailable; all three complete training models are required", "repetitions": 0,
                                 "per_class_training_budgets": None, "weighted_error": None, "focal_error": None})
        if progress:
            progress(key)
    periods = []
    for period in ("certificate", "evaluation"):
        selected = [item for item in targets if item["period"] == period]
        if not selected:
            continue
        ns = cache["period_counts"][period][2].sum(axis=1)
        for rung in (1, 2):
            for model in MODELS:
                tokens = [(item["key"], rung, model) for item in selected]
                row = {"period": period, "log_M": rung, "model": model, "target_sample_counts": ns.tolist(),
                       "status": "complete" if all(token in evaluations for token in tokens) else "unavailable_model_windows",
                       "weighted_error": None, "focal_error": None, "matched_weighted_error": None, "matched_focal_error": None}
                if row["status"] == "complete":
                    wrong = sum((evaluations[token]["wrong_counts"] for token in tokens), np.zeros(len(known), dtype=np.int64))
                    errors = np.divide(wrong, ns, out=np.full(len(ns), np.nan), where=ns > 0)
                    row["weighted_error"] = weighted_range(errors, priors)
                    row["focal_error"] = optional(errors[focal])
                    if model == "fixed_pilot":
                        pilot_prediction, _ = histogram_predictions(cache["period_counts"]["pilot"][rung], priors)
                        expected = evaluate(cache["period_counts"][period][rung], priors, pilot_prediction, focal)
                        if not np.array_equal(wrong, expected["wrong_counts"]):
                            raise RuntimeError("fixed-pilot period aggregation differs from pooled evaluation")
                if repeats and all(token in matched_wrong for token in tokens):
                    wrong = sum((matched_wrong[token] for token in tokens), np.zeros((repeats, len(known)), dtype=np.int64))
                    errors = np.divide(wrong, ns[None, :], out=np.full(wrong.shape, np.nan), where=ns[None, :] > 0)
                    weighted = errors @ priors
                    row["matched_weighted_error"] = randomization_summary(weighted)
                    row["matched_focal_error"] = randomization_summary(errors[:, focal])
                periods.append(row)
    return {"full": full_rows, "classes": class_rows, "focal_confusions": focal_rows,
            "matched": matched_rows, "periods": periods, "predictions": predictions, "evaluations": evaluations,
            "model_windows": model_windows}


def symbol_dictionary(k, bins):
    grid = quantization_grid("log", log_bins=bins)
    base = len(grid)
    labels = {}
    for size in range(1, DEFAULT_MAX_SIZE + 1):
        token = quantize([(0, size)], 1, "log", log_bins=bins)[0][1]
        labels.setdefault(token, []).append(size)
    overflow = quantize([(0, DEFAULT_MAX_SIZE + 1)], 1, "log", log_bins=bins)[0][1]
    descriptions = {token: f"{min(sizes)}+" if token == overflow else f"{min(sizes)}-{max(sizes)}" for token, sizes in labels.items()}
    digits = np.zeros((base ** k, k), dtype=np.int64)
    decoded = []
    for value in range(base ** k):
        items, readable = [], []
        for position in range(k):
            digit = (value // base ** (k - position - 1)) % base
            digits[value, position] = digit
            direction, token = grid[digit]
            items.append((direction, token))
            readable.append(("C" if direction == 0 else "S") + ":" + ("*" if bins == 1 else descriptions[token]))
        if symbol_to_id(tuple(items), "log", log_bins=bins) != value:
            raise RuntimeError("canonical symbol decoding failed")
        decoded.append(" ".join(readable))
    return digits, decoded


def score_context(counts, priors, focal, known):
    laws, ns, present = laws_and_presence(counts)
    if not present.all():
        return None
    scores = priors[:, None] * laws
    winner = scores.argmax(axis=0)
    others = np.arange(len(known)) != focal
    candidates = np.flatnonzero(others)
    rival = candidates[scores[others].argmax(axis=0)]
    denominator = scores.sum(axis=0)
    posterior = np.divide(scores[focal], denominator, out=np.full(len(denominator), np.nan), where=denominator > 0)
    return {"winner": winner, "rival": rival, "margin": scores[focal] - scores[rival, np.arange(len(winner))],
            "focal_score": scores[focal], "posterior": posterior,
            "supported": denominator > 0, "ties": (scores == scores.max(axis=0)).sum(axis=0) > 1}


def focal_attribution(cache, rolling, *, app=2, reference_months=("2024-12", "2025-01"), top=10):
    known, priors, k = cache["known"], cache["priors"], cache["plan"]["k"]
    focal = int(np.flatnonzero(known == app)[0])
    if not reference_months or len(set(reference_months)) != len(reference_months):
        raise ValueError("reference months must be nonempty and distinct")
    reference = [item for item in cache["slices"] if item["month_utc"] in reference_months]
    if any(not any(item["month_utc"] == month for item in reference) for month in reference_months):
        raise ValueError("reference calendar month absent from the count cache")
    stop_month = max(month_index(month) for month in reference_months)
    targets = [item for item in cache["slices"] if item["period"] != "pilot" and month_index(item["month_utc"]) > stop_month]
    if not targets:
        raise ValueError("no later target months available for focal attribution")
    ref_counts = {r: sum((cache["counts"][item["key"]][r] for item in reference), np.zeros_like(cache["period_counts"]["pilot"][r])) for r in (1, 2)}
    ref_laws, ref_ns, ref_present = laws_and_presence(ref_counts[2])
    if not ref_present[focal]:
        raise ValueError("focal APP has no reference observations")
    ref_context = {r: score_context(ref_counts[r], priors, focal, known) for r in (1, 2)}
    mapping = fine_to_coarse_ids(k)
    digits, readable = symbol_dictionary(k, 2)
    symbols, marginals, position_rows, summaries, confusions = [], [], [], [], []
    pilot_prediction, _ = histogram_predictions(cache["period_counts"]["pilot"][2], priors)
    old_error = pilot_prediction != focal
    def add_confusions(key, matrices, context):
        rules = {"fixed_pilot": pilot_prediction}
        if context is not None:
            rules["diagnostic_empirical_winner"] = context["winner"]
        for rule, prediction in rules.items():
            values = evaluate(matrices[2], priors, prediction, focal)
            for i, service in enumerate(known):
                confusions.append({"slice": key, "rule": rule, "other_service_code": int(service),
                    "focal_n": int(values["sample_counts"][focal]),
                    "focal_to_other_count": int(values["confusion"][focal, i]),
                    "focal_to_other_probability": optional(values["focal_outgoing"][i]),
                    "other_to_focal_count": int(values["confusion"][i, focal]),
                    "other_to_focal_probability": optional(values["focal_incoming"][i])})
    add_confusions("reference/" + "+".join(reference_months), ref_counts, ref_context[2])
    for target in targets:
        key = target["key"]
        if any(item["end_epoch"] > target["start_epoch"] for item in reference):
            raise ValueError("focal reference overlaps or follows the target")
        target_laws, ns, present = laws_and_presence(cache["counts"][key][2])
        if not present[focal]:
            summaries.append({"target": key, "status": "focal APP absent", "sample_count": 0})
            continue
        p, q = ref_laws[focal], target_laws[focal]
        delta = q - p
        pilot_error_change = priors[focal] * delta * old_error
        contexts = {r: score_context(cache["counts"][key][r], priors, focal, known) for r in (1, 2)}
        add_confusions(key, cache["counts"][key], contexts[2])
        terms = {name: np.full(len(p), np.nan) for name in ("oracle_distribution", "oracle_reassignment", "coarsening_change")}
        if all(context is not None for context in (*ref_context.values(), *contexts.values())):
            ref_error, target_error = ref_context[2]["winner"] != focal, contexts[2]["winner"] != focal
            terms["oracle_distribution"] = priors[focal] * delta * ref_error
            terms["oracle_reassignment"] = priors[focal] * q * (target_error.astype(int) - ref_error.astype(int))
            ref_loss = priors[focal] * p * ((ref_context[1]["winner"][mapping] != focal).astype(int) - ref_error.astype(int))
            target_loss = priors[focal] * q * ((contexts[1]["winner"][mapping] != focal).astype(int) - target_error.astype(int))
            terms["coarsening_change"] = target_loss - ref_loss
            expected = priors[focal] * (float(np.dot(q, target_error)) - float(np.dot(p, ref_error)))
            if abs(terms["oracle_distribution"].sum() + terms["oracle_reassignment"].sum() - expected) > 1e-12:
                raise RuntimeError("focal oracle mass/reassignment decomposition failed")
            coarse_delta = priors[focal] * (np.dot(q, contexts[1]["winner"][mapping] != focal) - np.dot(p, ref_context[1]["winner"][mapping] != focal))
            if abs(terms["coarsening_change"].sum() - (coarse_delta - expected)) > 1e-12:
                raise RuntimeError("focal signed coarsening contributions failed to reconcile")
        if abs(pilot_error_change.sum() - priors[focal] * (np.dot(q, old_error) - np.dot(p, old_error))) > 1e-12:
            raise RuntimeError("focal fixed-model symbol contributions do not sum to error change")
        rows = []
        for value in range(len(p)):
            row = {"target": key, "symbol_id": value, "decoded": readable[value], "coarse_parent_id": int(mapping[value]),
                   "reference_count": int(ref_counts[2][focal, value]), "target_count": int(cache["counts"][key][2][focal, value]),
                   "reference_probability": float(p[value]), "target_probability": float(q[value]), "probability_change": float(delta[value]),
                   "TV_contribution": float(0.5 * abs(delta[value])),
                   "weighted_pilot_error_change": float(pilot_error_change[value]),
                   "weighted_oracle_distribution_term": optional(terms["oracle_distribution"][value]),
                   "weighted_oracle_reassignment_term": optional(terms["oracle_reassignment"][value]),
                   "signed_coarsening_contribution_change": optional(terms["coarsening_change"][value]),
                   "pilot_prediction": int(known[pilot_prediction[value]])}
            for model in ("rolling_1m", "rolling_3m"):
                prediction = rolling["predictions"].get((key, 2, model))
                row[model + "_prediction"] = int(known[prediction[value]]) if prediction is not None else None
            for name, context in (("reference", ref_context[2]), ("target", contexts[2])):
                supported = context is not None and context["supported"][value]
                row[name + "_empirical_winner"] = int(known[context["winner"][value]]) if supported else None
                row[name + "_strongest_competitor"] = int(known[context["rival"][value]]) if supported else None
                row[name + "_focal_margin"] = optional(context["margin"][value]) if supported else None
                row[name + "_known_only_focal_posterior"] = optional(context["posterior"][value]) if supported else None
                row[name + "_winner_tied"] = bool(context["ties"][value]) if supported else None
                coarse = ref_context[1] if name == "reference" else contexts[1]
                parent = mapping[value]
                row[name + "_coarse_winner"] = int(known[coarse["winner"][parent]]) if coarse is not None and coarse["supported"][parent] else None
            rows.append(row)
        symbols.extend(rows)
        for position in range(k):
            left = np.bincount(digits[:, position], weights=p, minlength=4)
            right = np.bincount(digits[:, position], weights=q, minlength=4)
            for digit in range(4):
                marginals.append({"target": key, "packet_position": position + 1, "canonical_digit": digit,
                                  "direction": "C" if digit < 2 else "S", "size_bin": digit % 2,
                                  "reference_probability": float(left[digit]), "target_probability": float(right[digit]),
                                  "probability_change": float(right[digit] - left[digit])})
            position_rows.append({"target": key, "packet_position": position + 1,
                "direction_size_marginal_TV": float(0.5 * np.abs(left - right).sum()),
                "direction_marginal_TV": float(0.5 * np.abs(left.reshape(2, 2).sum(axis=1) - right.reshape(2, 2).sum(axis=1)).sum()),
                "size_marginal_TV": float(0.5 * np.abs(left.reshape(2, 2).sum(axis=0) - right.reshape(2, 2).sum(axis=0)).sum())})
        def highest(field, decreases=False):
            eligible = [row for row in rows if row[field] is not None and (row[field] < -1e-12 if decreases else row[field] > 1e-12)]
            return sorted(eligible, key=lambda row: (row[field] if decreases else -row[field], row["symbol_id"]))[:top]
        summaries.append({"target": key, "status": "descriptive", "sample_count": int(ns[focal]),
            "empirical_TV": float(0.5 * np.abs(delta).sum()), "weighted_pilot_error_change": float(pilot_error_change.sum()),
            "weighted_oracle_distribution_term": optional(terms["oracle_distribution"].sum()),
            "weighted_oracle_reassignment_term": optional(terms["oracle_reassignment"].sum()),
            "signed_coarsening_contribution_change": optional(terms["coarsening_change"].sum()),
            "largest_error_increase_symbols": highest("weighted_pilot_error_change"),
            "largest_TV_symbols": highest("TV_contribution"),
            "largest_coarsening_contribution_decreases": highest("signed_coarsening_contribution_change", True)})
    return {"reference_months": list(reference_months), "reference_slices": [item["key"] for item in reference],
            "reference_sample_count": int(ref_ns[focal]), "summary": summaries, "symbols": symbols,
            "packet_marginals": marginals, "packet_TV": position_rows, "confusions": confusions}
