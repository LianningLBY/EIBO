"""Exploratory multiclass risk baselines on a fixed observable.

These are classical baselines, not new theorems. Every result assumes independent
draws within each service. The optional joint bound additionally requires mutual
independence across services. Unknown-class error is discarded, not estimated.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

from .statcore import tv_upper_bound


def validate_counts(counts: Sequence[Sequence[int]]) -> np.ndarray:
    values = np.asarray(counts, dtype=float)
    if values.ndim != 2 or values.shape[0] < 2 or values.shape[1] < 1:
        raise ValueError("counts must be a matrix with at least two services")
    if not np.all(np.isfinite(values)) or np.any(values < 0):
        raise ValueError("counts must be finite and nonnegative")
    if np.any(values != np.floor(values)) or np.any(values.sum(axis=1) <= 0):
        raise ValueError("counts must be integers; each service needs observations")
    return values


def validate_priors(priors: Sequence[float], services: int) -> np.ndarray:
    values = np.asarray(priors, dtype=float)
    if values.shape != (services,) or not np.all(np.isfinite(values)):
        raise ValueError("one finite prior is required for each service")
    if np.any(values < 0) or not 0 < values.sum() <= 1 + 1e-12:
        raise ValueError("known-class priors must be nonnegative and sum to (0, 1]")
    return values


def empirical_known_risk(counts, priors) -> float:
    """Known-class contribution to Bayes risk, with unknown error discarded."""
    values = validate_counts(counts)
    weights = validate_priors(priors, len(values))
    laws = values / values.sum(axis=1)[:, None]
    return max(0.0, float(weights.sum() - (weights[:, None] * laws).max(axis=0).sum()))


def grouped_joint_risk_bound(counts, priors, unit_change_bounds, *, alpha: float = 0.05) -> dict:
    """Bound risk when independent sampling units have known change bounds.

    Each empirical law must be unbiased for its fixed target law. The supplied
    c_b must bound the change in empirical risk when independent unit b is
    replaced. This is an oracle interface, not an estimator of effective sample
    size or a guarantee for arbitrary correlation. Independent iid observations
    have c_b = pi_i/n_i; a shared cross-service draw can affect several laws.
    """
    point = empirical_known_risk(counts, priors)
    changes = np.asarray(unit_change_bounds, dtype=float)
    if changes.ndim != 1 or not len(changes) or not np.all(np.isfinite(changes)) or np.any(changes < 0):
        raise ValueError("unit_change_bounds must be a nonempty finite nonnegative vector")
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    radius = math.sqrt(0.5 * math.log(1 / alpha) * float(np.dot(changes, changes)))
    return {"lower_floor": max(0.0, point - radius), "radius": radius,
            "assumption": "independent sampling units; unbiased empirical laws; externally justified change bounds"}


def direct_risk_bounds(counts, priors, *, alphabet_size: int, alpha: float = 0.05) -> dict:
    """Two baselines, with explicitly different independence assumptions.

    Classwise: Bayes risk is Lipschitz in each law with weight pi_i. Bound each
    law's TV deviation using statcore and a union bound over services.

    Joint: empirical Bayes risk is concave in the empirical laws, hence downward
    biased. Replacing one class-i observation changes it by at most pi_i/n_i;
    McDiarmid gives the one-sided radius below without an alphabet penalty.
    """
    values = validate_counts(counts)
    weights = validate_priors(priors, len(values))
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    if alphabet_size < values.shape[1] or alphabet_size < 1:
        raise ValueError("declared alphabet cannot be smaller than the count columns")
    ns = values.sum(axis=1).astype(np.int64)
    point = empirical_known_risk(values, weights)
    radii = []
    for n in ns:
        # Call the formula authority. The dummy symbols are only an efficient
        # way to request radius_1; their point estimate is never used.
        reference = tv_upper_bound(
            np.zeros(int(n), dtype=np.uint8), [0],
            alphabet_size=alphabet_size, alpha=alpha / len(values),
        )
        radii.append(float(reference.radius_1))
    classwise_radius = float(np.dot(weights, radii))
    joint_radius = math.sqrt(0.5 * math.log(1 / alpha) * float(np.sum(weights**2 / ns)))
    return {
        "empirical_known_risk": point,
        "sample_counts": ns.tolist(),
        "known_priors": weights.tolist(),
        "unknown_prior": float(max(0.0, 1 - weights.sum())),
        "alpha": alpha,
        "declared_alphabet_size": int(alphabet_size),
        "classwise": {
            "lower_floor": max(0.0, point - classwise_radius),
            "radius": classwise_radius,
            "per_service_alpha": alpha / len(values),
            "per_service_radii": radii,
            "assumption": "iid draws within each service; cross-service independence is not required",
        },
        "joint": {
            "lower_floor": max(0.0, point - joint_radius),
            "radius": joint_radius,
            "assumption": "all observations mutually independent, including across services",
        },
        "scope": "fixed observable and fixed priors; unknown-class error discarded; not a bound for finer features",
    }


def tree_risk_bound(pair_upper, priors) -> dict:
    """Hunter union bound on weighted density subgraphs, using Kruskal.

    Pair overlap is at least min(pi_i, pi_j) * (1 - TV_upper_ij).
    A maximum spanning tree of these overlap lower bounds gives a risk floor.
    Every pair bound must hold on one simultaneous event before selection.
    """
    upper = np.asarray(pair_upper, dtype=float)
    k = len(upper)
    weights = validate_priors(priors, k)
    if upper.shape != (k, k) or not np.all(np.isfinite(upper)):
        raise ValueError("pair_upper must be a square finite matrix")
    if np.any(upper < 0) or np.any(upper > 1) or not np.allclose(upper, upper.T):
        raise ValueError("pair upper bounds must be symmetric and lie in [0, 1]")
    if not np.allclose(np.diag(upper), 0):
        raise ValueError("pair_upper diagonal must be zero")
    edges = sorted(
        ((float(min(weights[i], weights[j]) * (1 - upper[i, j])), i, j)
         for i in range(k) for j in range(i + 1, k)), reverse=True,
    )
    parents = list(range(k))

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    chosen = []
    for overlap, i, j in edges:
        a, b = root(i), root(j)
        if a == b:
            continue
        parents[a] = b
        chosen.append({"i": i, "j": j, "overlap_lower": overlap})
        if len(chosen) == k - 1:
            break
    return {"lower_floor": float(sum(e["overlap_lower"] for e in chosen)), "edges": chosen,
            "assumption": "all pair upper bounds hold simultaneously on this observable"}
