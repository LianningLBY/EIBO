"""Descriptive monthly/class drift on fixed, audited flow populations.

Missing classes keep their priors. Empirical Bayes functionals require every
selected class; missing-class ranges are identification ranges, not confidence
intervals. No iid significance, stationarity or real-data coverage is inferred.
"""

from __future__ import annotations

import datetime as dt

import numpy as np

from .realdata import DAY, utc
from .realexperiment import PERIODS, RealExperimentCounts, empirical_drift, histogram_predictions
from .riskcert import empirical_known_risk


def month_start(seconds):
    date = dt.datetime.fromtimestamp(float(seconds), dt.timezone.utc)
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_month(date):
    return date.replace(year=date.year + 1, month=1) if date.month == 12 else date.replace(month=date.month + 1)


def month_slices(plan, tables):
    """Calendar/period intersections, including empty months; never pool periods."""
    present_days = {table["day_seconds"] for table in tables}
    result = []
    for period in PERIODS:
        window = plan["windows"][period]
        begin, end = window["start_epoch"], window["end_epoch"]
        date = month_start(begin)
        while date.timestamp() < end:
            following = next_month(date)
            start, stop = max(begin, int(date.timestamp())), min(end, int(following.timestamp()))
            days = list(range(int(start // DAY) * DAY, stop, DAY))
            result.append({"key": period + "/" + date.strftime("%Y-%m"), "period": period,
                           "month_utc": date.strftime("%Y-%m"), "start_epoch": start, "end_epoch": stop,
                           "start_utc": utc(start), "end_utc_exclusive": utc(stop),
                           "calendar_days": len(days), "available_table_days": sum(day in present_days for day in days),
                           "missing_table_dates": [utc(day)[:10] for day in days if day not in present_days]})
            date = following
    return sorted(result, key=lambda item: item["start_epoch"])


class MonthlyDriftCounts(RealExperimentCounts):
    def __init__(self, plan, tables, *, time_scale):
        super().__init__(plan, tables, time_scale=time_scale, widths=())
        self.slices = month_slices(plan, tables)
        self.monthly = {item["key"]: {rung: np.zeros_like(self.counts["pilot"][rung]) for rung in self.encoders}
                        for item in self.slices}
        self.selected_days = {item["key"]: set() for item in self.slices}
        self.slice_starts = {p: np.array([item["start_epoch"] for item in self.slices if item["period"] == p]) for p in PERIODS}
        self.slice_keys = {p: [item["key"] for item in self.slices if item["period"] == p] for p in PERIODS}

    def add_selected(self, period, first, labels, symbols_by_rung):
        if not len(first):
            return
        indices = np.searchsorted(self.slice_starts[period], first, side="right") - 1
        if np.any(indices < 0):
            raise RuntimeError("selected flow precedes its monthly slice")
        for index in np.unique(indices):
            key = self.slice_keys[period][int(index)]
            mask = indices == index
            for rung, symbols in symbols_by_rung.items():
                np.add.at(self.monthly[key][rung], (labels[mask], symbols[mask]), 1)
            self.selected_days[key].update(map(int, np.floor(first[mask] / DAY)))

    def reconcile_months(self, baseline_counts):
        for period in PERIODS:
            keys = self.slice_keys[period]
            for rung in self.encoders:
                pooled = sum((self.monthly[key][rung] for key in keys), np.zeros_like(self.counts[period][rung]))
                if not np.array_equal(pooled, self.counts[period][rung]):
                    raise RuntimeError("monthly/period count reconciliation failed")
                if not np.array_equal(pooled, baseline_counts[period][rung]):
                    raise ValueError(f"counts differ from previous experiment: {period}, log M={rung}")
        for values in self.monthly.values():
            projected = np.zeros_like(values[1])
            for column, coarse in enumerate(self.refinement):
                projected[:, coarse] += values[2][:, column]
            if not np.array_equal(projected, values[1]):
                raise RuntimeError("monthly refinement projection failed")


def optional(value):
    return float(value) if np.isfinite(value) else None


def weighted_range(values, priors, *, signed=False, bound=1):
    """Ranges for unobserved classes only, with no sampling-uncertainty meaning."""
    available = np.isfinite(values)
    observed = float(np.dot(priors[available], values[available]))
    missing = float(priors[~available].sum())
    return {"value": observed if available.all() else None, "observed_contribution": observed,
            "unidentified_prior_mass": missing,
            "range_from_unobserved_values": [observed - bound * missing if signed else observed, observed + bound * missing]}


def laws_and_presence(counts):
    ns = counts.sum(axis=1)
    laws = np.divide(counts, ns[:, None], out=np.zeros_like(counts, dtype=float), where=ns[:, None] > 0)
    return laws, ns, ns > 0


def model_errors(laws, present, prediction):
    result = 1 - (laws * (prediction[None, :] == np.arange(len(laws))[:, None])).sum(axis=1)
    result[~present] = np.nan
    return result


def slice_metrics(counts, pilot, certificate, priors, *, evaluation=False):
    laws, ns, present = laws_and_presence(counts)
    pilot_prediction, global_unseen = histogram_predictions(pilot, priors)
    pilot_error = model_errors(laws, present, pilot_prediction)
    globally_unseen = laws[:, global_unseen].sum(axis=1)
    class_unseen = (laws * (pilot == 0)).sum(axis=1)
    globally_unseen[~present], class_unseen[~present] = np.nan, np.nan
    oracle_error = np.full(len(ns), np.nan)
    point, switch_mass = None, None
    if present.all():
        oracle_prediction, _ = histogram_predictions(counts, priors)
        oracle_error = model_errors(laws, present, oracle_prediction)
        point = empirical_known_risk(counts, priors)
        if abs(float(np.dot(priors, oracle_error)) - point) > 1e-12:
            raise RuntimeError("class empirical-risk contributions do not sum to Fhat")
        switch_mass = float(np.dot(priors, laws[:, oracle_prediction != pilot_prediction].sum(axis=1)))
    recent_error = np.full(len(ns), np.nan)
    if evaluation:
        recent_prediction, _ = histogram_predictions(certificate, priors)
        recent_error = model_errors(laws, present, recent_prediction)
    return {"counts": counts, "n": ns, "present": present, "laws": laws, "pilot_error": pilot_error,
            "recent_error": recent_error, "oracle_error": oracle_error,
            "global_unseen": globally_unseen, "class_unseen": class_unseen,
            "empirical_F": point, "decision_switch_mass": switch_mass}


def compare_metrics(source, target, priors):
    common = source["present"] & target["present"]
    tv = np.full(len(priors), np.nan)
    if common.any():
        drift = empirical_drift(source["counts"][common], target["counts"][common], priors[common])
        tv[common] = drift["per_service_empirical_tv"]
    delta_error = target["pilot_error"] - source["pilot_error"]
    delta_f = target["oracle_error"] - source["oracle_error"]
    delta_gap = delta_error - delta_f
    error = weighted_range(delta_error, priors, signed=True)
    f = weighted_range(delta_f, priors, signed=True)
    gap = weighted_range(delta_gap, priors, signed=True, bound=2)
    if error["value"] is not None and f["value"] is not None:
        if abs(error["value"] - f["value"] - gap["value"]) > 1e-12:
            raise RuntimeError("empirical error/F/gap decomposition failed")
    weighted_changes = delta_error[np.isfinite(delta_error)] * priors[np.isfinite(delta_error)]
    return {"tv": tv, "delta_error": delta_error, "delta_F": delta_f, "delta_gap": delta_gap,
            "aggregate": {"empirical_tv": weighted_range(tv, priors), "pilot_error_change": error,
                          "empirical_F_change": f, "empirical_gap_change": gap,
                          "positive_error_contributions": float(weighted_changes[weighted_changes > 0].sum()),
                          "negative_error_contributions": float(weighted_changes[weighted_changes < 0].sum())}}


def representation_metrics(coarse, fine, priors):
    contributions = priors * (coarse["oracle_error"] - fine["oracle_error"])
    gain = priors * (coarse["pilot_error"] - fine["pilot_error"])
    loss = float(contributions.sum()) if np.isfinite(contributions).all() else None
    if loss is not None and loss < -1e-12:
        raise RuntimeError("empirical coarsening loss is negative")
    return {"signed_coarsening_contribution": contributions, "pilot_model_gain": gain,
            "empirical_coarsening_loss": loss}


def rank(rows, field, top, *, decreasing=True):
    eligible = [row for row in rows if row[field] is not None]
    return sorted(eligible, key=lambda row: ((-row[field] if decreasing else row[field]), row["service_code"]))[:top]


def analyze_months(experiment, *, small_n=200, top=10):
    known, priors = experiment.known, experiment.priors
    class_rows, comparison_rows, representation_rows, monthly_summary = [], [], [], []
    rankings, comparisons = [], []
    metrics, representations = {}, {}
    scopes = [(period, {"period": period, "month_utc": None}, values) for period, values in experiment.counts.items()]
    scopes += [(item["key"], item, experiment.monthly[item["key"]]) for item in experiment.slices]
    for key, info, values in scopes:
        for rung, counts in values.items():
            metric = slice_metrics(counts, experiment.counts["pilot"][rung], experiment.counts["certificate"][rung],
                                   priors, evaluation=info["period"] == "evaluation")
            metrics[(key, rung)] = metric
            pilot_range = weighted_range(metric["pilot_error"], priors)
            summary = {"slice": key, "period": info["period"], "month_utc": info["month_utc"], "log_M": rung,
                       "sample_count": int(metric["n"].sum()), "minimum_class_n": int(metric["n"].min()),
                       "missing_service_codes": known[~metric["present"]].tolist(),
                       "small_n_service_codes": known[(metric["n"] > 0) & (metric["n"] < small_n)].tolist(),
                       "empirical_F": metric["empirical_F"], "pilot_classifier": pilot_range,
                       "known_conditional_accuracy": (1 - pilot_range["value"] / priors.sum()) if pilot_range["value"] is not None else None,
                       "global_unseen_mass": weighted_range(metric["global_unseen"], priors),
                       "class_specific_unseen_mass": weighted_range(metric["class_unseen"], priors),
                       "pilot_to_empirical_decision_switch_mass": metric["decision_switch_mass"]}
            if info["period"] == "evaluation":
                summary["recent_classifier"] = weighted_range(metric["recent_error"], priors)
            if info["month_utc"] is not None:
                summary.update({name: info[name] for name in ("start_utc", "end_utc_exclusive", "calendar_days", "available_table_days", "missing_table_dates")})
                summary["days_with_selected_flows"] = len(experiment.selected_days[key])
                summary["pilot_model_fit_scope"] = "includes this slice; resubstitution" if info["period"] == "pilot" else "earlier pilot only"
                monthly_summary.append(summary)
            for i, service in enumerate(known):
                class_rows.append({"slice": key, "period": info["period"], "month_utc": info["month_utc"], "log_M": rung,
                                   "service_code": int(service), "prior": float(priors[i]), "n": int(metric["n"][i]),
                                   "sample_status": "missing" if not metric["present"][i] else "small_n" if metric["n"][i] < small_n else "observed",
                                   "pilot_error": optional(metric["pilot_error"][i]),
                                   "recent_error": optional(metric["recent_error"][i]),
                                   "empirical_oracle_error": optional(metric["oracle_error"][i]),
                                   "weighted_pilot_error": optional(priors[i] * metric["pilot_error"][i]),
                                   "weighted_empirical_F_contribution": optional(priors[i] * metric["oracle_error"][i]),
                                   "pilot_global_unseen_mass": optional(metric["global_unseen"][i]),
                                   "pilot_class_specific_unseen_mass": optional(metric["class_unseen"][i])})
        representation = representation_metrics(metrics[(key, 1)], metrics[(key, 2)], priors)
        representations[key] = representation
    baseline_representation = representations["pilot"]
    for key, info, _ in scopes:
        values = representations[key]
        delta = values["signed_coarsening_contribution"] - baseline_representation["signed_coarsening_contribution"]
        for i, service in enumerate(known):
            representation_rows.append({"slice": key, "period": info["period"], "month_utc": info["month_utc"],
                                        "service_code": int(service), "n": int(metrics[(key, 1)]["n"][i]),
                                        "sample_status": "missing" if not metrics[(key, 1)]["present"][i] else "small_n" if metrics[(key, 1)]["n"][i] < small_n else "observed",
                                        "signed_empirical_coarsening_contribution": optional(values["signed_coarsening_contribution"][i]),
                                        "coarsening_contribution_change_from_pilot": optional(delta[i]),
                                        "weighted_pilot_model_M2_gain": optional(values["pilot_model_gain"][i])})
    pairs = [("period", "pilot", "certificate"), ("period", "certificate", "evaluation"), ("period", "pilot", "evaluation")]
    for index, item in enumerate(experiment.slices):
        pairs.append(("monthly_pilot_reference", "pilot", item["key"]))
        if item["period"] == "evaluation":
            pairs.append(("monthly_certificate_reference", "certificate", item["key"]))
        if index:
            pairs.append(("previous_time_slice", experiment.slices[index - 1]["key"], item["key"]))
    for scope, source, target in pairs:
        for rung in experiment.encoders:
            left, right = metrics[(source, rung)], metrics[(target, rung)]
            comparison = compare_metrics(left, right, priors)
            rows = []
            for i, service in enumerate(known):
                row = {"scope": scope, "source": source, "target": target, "log_M": rung, "service_code": int(service),
                       "source_n": int(left["n"][i]), "target_n": int(right["n"][i]),
                       "sample_status": "missing" if not (left["present"][i] and right["present"][i]) else "small_n" if min(left["n"][i], right["n"][i]) < small_n else "observed",
                       "empirical_TV": optional(comparison["tv"][i]),
                       "weighted_empirical_TV": optional(priors[i] * comparison["tv"][i]),
                       "weighted_error_change": optional(priors[i] * comparison["delta_error"][i]),
                       "weighted_empirical_F_change": optional(priors[i] * comparison["delta_F"][i]),
                       "weighted_empirical_gap_change": optional(priors[i] * comparison["delta_gap"][i])}
                rows.append(row)
            comparison_rows.extend(rows)
            aggregate = dict(comparison["aggregate"], scope=scope, source=source, target=target, log_M=rung)
            comparisons.append(aggregate)
            rankings.append({"scope": scope, "source": source, "target": target, "log_M": rung,
                             "largest_error_increases": rank([row for row in rows if row["weighted_error_change"] is not None and row["weighted_error_change"] > 1e-12], "weighted_error_change", top),
                             "largest_error_decreases": rank([row for row in rows if row["weighted_error_change"] is not None and row["weighted_error_change"] < -1e-12], "weighted_error_change", top, decreasing=False),
                             "largest_empirical_TV": rank(rows, "weighted_empirical_TV", top)})
    for summary in monthly_summary:
        key, rung = summary["slice"], summary["log_M"]
        summary["empirical_coarsening_loss_M1_minus_M2"] = representations[key]["empirical_coarsening_loss"]
        reference = next(item for item in comparisons if item["scope"] == "monthly_pilot_reference" and item["target"] == key and item["log_M"] == rung)
        summary["empirical_TV_from_pilot"] = reference["empirical_tv"]
        previous = next((item for item in comparisons if item["scope"] == "previous_time_slice" and item["target"] == key and item["log_M"] == rung), None)
        summary["previous_slice"] = previous["source"] if previous is not None else None
        summary["previous_slice_comparison"] = previous
    loss_rankings = {key: rank([row for row in representation_rows if row["slice"] == key and row["coarsening_contribution_change_from_pilot"] is not None and row["coarsening_contribution_change_from_pilot"] < -1e-12],
                               "coarsening_contribution_change_from_pilot", top, decreasing=False)
                     for key in ("certificate", "evaluation", *(item["key"] for item in experiment.slices if item["period"] != "pilot"))}
    summary = {"status": "descriptive; sampling uncertainty and real-data coverage are not estimated",
               "known_service_codes": known.tolist(), "known_priors": priors.tolist(), "unknown_prior": experiment.plan["unknown_prior"],
               "small_n_threshold_report_only": small_n, "monthly": monthly_summary, "comparisons": comparisons,
               "period_coarsening_loss": {p: representations[p]["empirical_coarsening_loss"] for p in PERIODS},
               "coarsening_contribution_decrease_rankings": loss_rankings,
               "scope": "same audited whole-period filtered population; calendar slices assigned by stored UTC flow start",
               "interpretation": ["Missing classes retain their priors; incomplete mixtures have no empirical F or oracle representation-loss value.",
                                  "Missing-class ranges are identification ranges, not confidence intervals; counts flag uncertainty without iid significance claims.",
                                  "Within-pilot monthly classifier errors reuse pilot training data; recent classifier is evaluated only in the later evaluation period.",
                                  "Signed per-class coarsening contributions may be negative even though their complete-class sum is nonnegative.",
                                  "Month-to-month comparisons include calendar coverage differences and sampling noise.",
                                  "No new representation, class selection or risk certificate is selected from these rankings."]}
    return {"summary": summary, "class_rows": class_rows, "comparison_rows": comparison_rows,
            "representation_rows": representation_rows, "rankings": rankings, "metrics": metrics}
