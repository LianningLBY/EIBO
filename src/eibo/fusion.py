"""Frozen score maps and paired confidence bounds for the two-view probe."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.sparse import csr_matrix, hstack
from scipy.special import expit

from .riskcert import joint_radius_from_change_budget

BUDGETS = (4, 8, 16)
METHODS = ("prefix", "phist", "early", "late")
# Four two-sided TV intervals, three two-sided frozen gains and two oracle gain lower bounds.
TAILS_PER_COMPARISON = 16


def logit_fit(features, y, *, penalty=0.01):
    """Ridge logistic regression with equal total weight per service."""
    ns = np.bincount(y, minlength=2)
    if np.any(ns == 0):
        raise ValueError("both services are required to fit a pair score")
    weights = 0.5 / ns[y]

    def objective(parameters):
        coef, intercept = parameters[:-1], parameters[-1]
        score = features @ coef + intercept
        residual = weights * (expit(score) - y)
        loss = weights @ (np.logaddexp(0, score) - y * score) + 0.5 * penalty * (coef @ coef)
        gradient = np.r_[features.T @ residual + penalty * coef, residual.sum()]
        return loss, gradient

    result = minimize(objective, np.zeros(features.shape[1] + 1), method="L-BFGS-B", jac=True,
                      options={"maxiter": 500, "gtol": 1e-7, "ftol": 1e-12})
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f"logistic fit failed: {result.message}")
    return result.x


def score(features, parameters):
    return features @ parameters[:-1] + parameters[-1]


def views(rows, alphabet):
    prefix = csr_matrix((np.ones(len(rows)), (np.arange(len(rows)), rows["prefix"])),
                        shape=(len(rows), alphabet))
    phist = np.sqrt(rows["phist"].astype(float))
    early = hstack((prefix, csr_matrix(phist)), format="csr")
    return prefix, phist, early


@dataclass
class PairScores:
    alphabet: int
    base_parameters: tuple
    late_base_parameters: tuple
    stack_parameters: np.ndarray

    @classmethod
    def fit(cls, alphabet, fit_rows, fit_y, stack_rows, stack_y):
        late_base = tuple(logit_fit(x, fit_y) for x in views(fit_rows, alphabet)[:2])
        prefix, phist, _ = views(stack_rows, alphabet)
        stack = logit_fit(np.column_stack((score(prefix, late_base[0]), score(phist, late_base[1]))), stack_y)
        # The single-view and early models may use both windows so that all
        # candidates receive the same fitting labels overall.
        all_rows, all_y = np.concatenate((fit_rows, stack_rows)), np.concatenate((fit_y, stack_y))
        base = tuple(logit_fit(x, all_y) for x in views(all_rows, alphabet))
        return cls(alphabet, base, late_base, stack)

    def predict(self, rows):
        features = views(rows, self.alphabet)
        scores = [score(x, p) for x, p in zip(features, self.base_parameters)]
        late_scores = [score(x, p) for x, p in zip(features, self.late_base_parameters)]
        scores.append(score(np.column_stack(late_scores), self.stack_parameters))
        return dict(zip(METHODS, scores))


def symbol_counts(symbols, y, budget):
    return np.bincount(y * budget + symbols, minlength=2 * budget).reshape(2, budget)


@dataclass
class ScoreQuantizer:
    cuts: np.ndarray
    decision: np.ndarray
    calibration_accuracy: float

    @classmethod
    def fit(cls, scores, y, budget):
        cuts = np.quantile(scores, np.arange(1, budget) / budget)
        counts = symbol_counts(np.searchsorted(cuts, scores, side="left"), y, budget)
        law = counts / counts.sum(axis=1)[:, None]
        return cls(cuts, law.argmax(axis=0), float(0.5 * law.max(axis=0).sum()))

    def encode(self, scores):
        return np.searchsorted(self.cuts, scores, side="left")


def measure(scores, y, maps, budget, strongest):
    ns = np.bincount(y, minlength=2)
    weights = 0.5 / ns[y]
    metrics = {}
    for method, quantizer in maps.items():
        symbols = quantizer.encode(scores[method])
        counts = symbol_counts(symbols, y, budget)
        laws = counts / ns[:, None]
        tv = 0.5 * np.abs(laws[0] - laws[1]).sum()
        accuracy = weights[quantizer.decision[symbols] == y].sum()
        metrics[method] = {"balanced_accuracy": float(accuracy), "tv_hat": float(tv),
                           "sample_bayes_accuracy": float((1 + tv) / 2),
                           "occupied_symbols": int(np.count_nonzero(counts.sum(axis=0))),
                           "counts": counts.tolist()}
    baseline = metrics[strongest]["balanced_accuracy"]
    best_sample = max(metrics[m]["sample_bayes_accuracy"] for m in METHODS[:2])
    gains = {m: metrics[m]["balanced_accuracy"] - baseline for m in METHODS[2:]}
    gains["late_minus_early"] = metrics["late"]["balanced_accuracy"] - metrics["early"]["balanced_accuracy"]
    witnesses = {m: metrics[m]["balanced_accuracy"] - best_sample for m in METHODS[2:]}
    return {"strongest_single_calibration": strongest, "methods": metrics,
            "frozen_accuracy_gains": gains, "fusion_minus_best_single_sample_oracle": witnesses}


def bounds(measured, squared_mass, tail_alpha):
    """Conditional Hoeffding bounds for any dependence within independent blocks.

    A block of mass w contributes a signed score with range 2w to each TV
    contrast or paired accuracy contrast. For the TV upper endpoint use the
    fixed population-optimal event, whose empirical contrast is <= TV_hat.
    For the lower endpoint use the frozen decision event. For the Bayes gain
    compare the frozen fusion rule with the population-optimal rule among the
    two single-view outputs. Its empirical accuracy is <= the larger of their
    two sample Bayes accuracies, making the measured witness conservative.
    """
    radius = float(joint_radius_from_change_budget([4 * squared_mass], alpha=tail_alpha)[0])
    tv, risk = {}, {}
    for method, row in measured["methods"].items():
        low = max(0.0, 2 * row["balanced_accuracy"] - 1 - radius)
        high = min(1.0, row["tv_hat"] + radius)
        tv[method] = [low, high]
        risk[method] = [(1 - high) / 2, (1 - low) / 2]
    gains = {name: [max(-1.0, gain - radius), min(1.0, gain + radius)]
             for name, gain in measured["frozen_accuracy_gains"].items()}
    bayes = {name: max(-0.5, gap - radius) for name, gap in measured["fusion_minus_best_single_sample_oracle"].items()}
    return {"radius": radius, "tv_intervals": tv, "bayes_error_intervals": risk,
            "frozen_gain_intervals": gains, "bayes_gain_lower_vs_best_single": bayes}
