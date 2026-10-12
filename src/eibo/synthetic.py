"""Fixed-law synthetic experiments with known Bayes risk and sampling units.

The target is F = sum_i pi_i - sum_x max_i pi_i p_i(x), a contribution from
known classes. Laws and priors are fixed before drawing certificate samples.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import beta


CASE_SPECS = {
    "identical_6_32": (6, 32, "identical", False),
    "near_6_32": (6, 32, "near", False),
    "private_6_32": (6, 32, "private_common", False),
    "separated_6_32": (6, 32, "separated", True),
    "zipf_6_1024": (6, 1024, "zipf_tail", True),
    "identical_45_32": (45, 32, "identical", False),
    "near_45_32": (45, 32, "near", False),
    "zipf_45_1024": (45, 1024, "zipf_tail", False),
    "private_45_64": (45, 64, "private_common", False),
}


def make_case(name: str) -> dict:
    """Return a deterministic, a-priori law, including declared zero cells."""
    k, m, family, imbalanced = CASE_SPECS[name]
    zipf = np.arange(1, m + 1, dtype=float) ** -1.3
    zipf /= zipf.sum()
    laws = np.zeros((k, m))
    if family == "identical":
        laws[:] = zipf
    elif family == "near":
        for i in range(k):
            laws[i] = 0.97 * zipf
            laws[i, i % m] += 0.03
    elif family == "private_common":
        # Common probability is 0.4; the private cells are disjoint. Thus
        # F = 0.4 * (known_mass - max_i pi_i), exactly, even with skew priors.
        laws[:, 0] = 0.4
        laws[np.arange(k), np.arange(1, k + 1)] = 0.6
    elif family == "separated":
        for i in range(k):
            laws[i] = 0.1 * zipf
            laws[i, i] += 0.9
    elif family == "zipf_tail":
        head = np.arange(1, 9, dtype=float) ** -1.3
        head /= head.sum()
        tail = np.arange(1, m - 8 + 1, dtype=float) ** -1.1
        tail /= tail.sum()
        for i in range(k):
            laws[i, :8] = 0.75 * head
            laws[i, 8:] = 0.25 * np.roll(tail, i * 17)
    else:
        raise ValueError(f"unrecognized family: {family}")
    laws /= laws.sum(axis=1)[:, None]
    unknown = 1 / (k + 1)
    weights = np.arange(1, k + 1, dtype=float) ** -1.2 if imbalanced else np.ones(k)
    priors = (1 - unknown) * weights / weights.sum()
    # Integer factors preserve divisibility for the repeated-block oracle.
    factors = 2 ** (np.arange(k) % 3) if imbalanced else np.ones(k, dtype=int)
    truth = float(priors.sum() - (priors[:, None] * laws).max(axis=0).sum())
    return {"name": name, "family": family, "services": k, "alphabet_size": m,
            "laws": laws, "known_priors": priors, "unknown_prior": unknown,
            "sample_factors": factors, "true_known_risk": max(0.0, truth)}


def failure_interval(failures: int, trials: int, confidence: float = 0.95) -> list:
    """Two-sided exact Clopper-Pearson interval for independent MC replications."""
    if trials < 1 or not 0 <= failures <= trials or not 0 < confidence < 1:
        raise ValueError("invalid binomial interval parameters")
    tail = (1 - confidence) / 2
    lo = 0.0 if failures == 0 else float(beta.ppf(tail, failures, trials - failures + 1))
    hi = 1.0 if failures == trials else float(beta.ppf(1 - tail, failures + 1, trials - failures))
    return [lo, hi]


def markov_variance_factor(n: int, rho: float) -> float:
    """Exact variance inflation for a stationary rho-sticky categorical chain.

    Applies to a scalar function of one chain. It is a diagnostic only and does
    not supply a risk certificate or justify plugging n/tau into an iid bound.
    """
    if n < 1 or not 0 <= rho <= 1:
        raise ValueError("invalid sticky-chain parameters")
    lags = np.arange(1, n, dtype=float)
    return float(1 + 2 * np.sum((1 - lags / n) * rho ** lags))


def _markov_counts(rng, law, n, trials, rho):
    m = len(law)
    if rho == 0:
        return rng.multinomial(n, law, size=trials)
    if rho == 1:
        labels = rng.choice(m, size=trials, p=law)
        counts = np.zeros((trials, m), dtype=np.int64)
        counts[np.arange(trials), labels] = n
        return counts
    # Regeneration at rate 1-rho: draw iid run lengths and iid run labels. The
    # first label has law p, so the chain starts in stationarity, without burn-in.
    width = max(16, int(n * (1 - rho)) + 16)
    lengths = rng.geometric(1 - rho, size=(trials, width))
    while np.any(lengths.sum(axis=1) < n):
        lengths = np.concatenate((lengths, rng.geometric(1 - rho, size=(trials, width))), axis=1)
    starts = np.cumsum(lengths, axis=1) - lengths
    lengths = np.minimum(lengths, np.maximum(0, n - starts))
    row, column = np.nonzero(lengths)
    labels = rng.choice(m, size=len(row), p=law)
    return np.bincount(row * m + labels, weights=lengths[row, column],
                       minlength=trials * m).reshape(trials, m).astype(np.int64)


def sample_counts(rng, case, ns, trials, *, mode="iid", block_size=1, rho=0.0):
    """Return batched counts; all stress modes preserve each marginal law.

    block: independent classwise blocks, each repeating one categorical draw.
    markov: independent classwise stationary chains, P=rho I+(1-rho) 1 p^T.
    cross_service: private_common laws share Bernoulli shocks at each index;
                   within every service the observations remain iid.
    """
    ns = np.asarray(ns, dtype=int)
    k, m = case["laws"].shape
    if ns.shape != (k,) or np.any(ns < 1) or trials < 1:
        raise ValueError("positive sample counts and trials are required")
    counts = np.empty((trials, k, m), dtype=np.int64)
    if mode == "cross_service":
        if case["family"] != "private_common":
            raise ValueError("cross-service shocks require a private_common case")
        shocks = rng.random((trials, int(ns.max()))) < 0.4
        cumulative = np.cumsum(shocks, axis=1)
        counts.fill(0)
        for i, n in enumerate(ns):
            counts[:, i, 0] = cumulative[:, n - 1]
            counts[:, i, i + 1] = n - counts[:, i, 0]
        return counts
    if mode == "block" and (block_size < 1 or np.any(ns % block_size)):
        raise ValueError("block size must divide every service sample count")
    if mode == "markov" and not 0 <= rho <= 1:
        raise ValueError("rho must lie in [0, 1]")
    for i, n in enumerate(ns):
        if mode == "iid":
            counts[:, i] = rng.multinomial(int(n), case["laws"][i], size=trials)
        elif mode == "block":
            counts[:, i] = block_size * rng.multinomial(int(n // block_size), case["laws"][i], size=trials)
        elif mode == "markov":
            counts[:, i] = _markov_counts(rng, case["laws"][i], int(n), trials, rho)
        else:
            raise ValueError(f"unrecognized sampling mode: {mode}")
    return counts


def batch_known_risk(counts, priors):
    counts = np.asarray(counts)
    priors = np.asarray(priors)
    laws = counts / counts.sum(axis=2)[:, :, None]
    return np.maximum(0, priors.sum() - (priors[None, :, None] * laws).max(axis=1).sum(axis=1))
