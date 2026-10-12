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


def _regeneration_lengths(rng, n, trials, rho):
    if rho == 0:
        return np.ones((trials, n), dtype=np.int64)
    if rho == 1:
        return np.full((trials, 1), n, dtype=np.int64)
    # Regeneration at rate 1-rho: draw iid run lengths and iid run labels. The
    # first label has law p, so the chain starts in stationarity, without burn-in.
    width = max(16, int(n * (1 - rho)) + 16)
    lengths = rng.geometric(1 - rho, size=(trials, width))
    while np.any(lengths.sum(axis=1) < n):
        lengths = np.concatenate((lengths, rng.geometric(1 - rho, size=(trials, width))), axis=1)
    starts = np.cumsum(lengths, axis=1) - lengths
    lengths = np.minimum(lengths, np.maximum(0, n - starts))
    return lengths


def merge_constant_runs(lengths, labels):
    """Merge adjacent equally labelled segments, preserving their lengths.

    Returned constant runs coarsen the input segmentation. The squared total
    lengths therefore dominate the input squared lengths. The validity of a
    certificate still requires a justified independent-unit model underneath.
    """
    lengths, labels = np.asarray(lengths), np.asarray(labels)
    if lengths.ndim != 2 or labels.shape != lengths.shape or not lengths.shape[1]:
        raise ValueError("matching nonempty segment matrices are required")
    if np.any(lengths < 0) or np.any(lengths != np.floor(lengths)) or np.any(lengths[:, 0] <= 0):
        raise ValueError("segment lengths must be nonnegative integers with a positive first segment")
    active = lengths > 0
    if np.any(active[:, 1:] & ~active[:, :-1]):
        raise ValueError("zero padding is allowed only after all active segments")
    changes = active.copy()
    changes[:, 1:] &= labels[:, 1:] != labels[:, :-1]
    groups = np.cumsum(changes, axis=1) - 1
    rows, columns = np.nonzero(active)
    width = lengths.shape[1]
    return np.bincount(rows * width + groups[rows, columns], weights=lengths[rows, columns],
                       minlength=lengths.shape[0] * width).reshape(lengths.shape).astype(np.int64)


def _markov_counts(rng, law, n, trials, rho, *, return_units=False):
    m = len(law)
    if rho == 0 and not return_units:
        return rng.multinomial(n, law, size=trials)
    lengths = _regeneration_lengths(rng, n, trials, rho)
    row, column = np.nonzero(lengths)
    labels = np.full(lengths.shape, -1, dtype=np.int64)
    labels[row, column] = rng.choice(m, size=len(row), p=law)
    counts = np.bincount(row * m + labels[row, column], weights=lengths[row, column],
                         minlength=trials * m).reshape(trials, m).astype(np.int64)
    if not return_units:
        return counts
    observed = merge_constant_runs(lengths, labels)
    return counts, {"lengths": lengths, "labels": labels, "observed_lengths": observed}


def _trace_example(trace):
    active = trace["lengths"][0] > 0
    return {"regeneration_lengths": trace["lengths"][0, active].tolist(),
            "regeneration_labels": trace["labels"][0, active].tolist(),
            "observed_run_lengths": trace["observed_lengths"][0, trace["observed_lengths"][0] > 0].tolist()}


def _shared_segment_budget(lengths, ns, priors):
    """Square changes after summing contributions from every affected class."""
    starts = np.cumsum(lengths, axis=1) - lengths
    changes = np.zeros(lengths.shape, dtype=float)
    separate = np.zeros(len(lengths))
    for n, prior in zip(ns, priors):
        clipped = np.minimum(lengths, np.maximum(0, n - starts))
        weighted = prior * clipped / n
        changes += weighted
        separate += (weighted ** 2).sum(axis=1)
    return (changes ** 2).sum(axis=1), separate


def sample_counts_with_units(rng, case, ns, trials, *, mode="iid", block_size=1, rho=0.0):
    """Sample counts and retain valid oracle and observable-run change budgets.

    Observed runs dominate true independent units for the sticky-refresh model
    because no symbol changes within a regeneration segment. Hidden blocks
    deliberately violate that property. Shared shocks must be grouped across
    services BEFORE squaring change bounds. Boundary geometry is exogenous to
    the regenerated labels; it is not estimated from the sample for the oracle.
    """
    ns = np.asarray(ns, dtype=int)
    laws, priors = case["laws"], case["known_priors"]
    k, m = laws.shape
    if ns.shape != (k,) or np.any(ns < 1) or trials < 1 or not 0 <= rho <= 1:
        raise ValueError("invalid sample counts, trials or rho")
    info = {"oracle_budget": np.zeros(trials), "oracle_unit_counts": np.zeros(trials, dtype=np.int64),
            "observed_budget": None, "observed_unit_counts": None, "geometry_example": None}
    if mode in ("iid", "block"):
        counts = sample_counts(rng, case, ns, trials, mode=mode, block_size=block_size)
        factor = block_size if mode == "block" else 1
        info["oracle_budget"][:] = np.sum(priors ** 2 * factor / ns)
        info["oracle_unit_counts"][:] = (ns // factor).sum()
        return counts, info
    counts = np.zeros((trials, k, m), dtype=np.int64)
    if mode == "markov":
        info["observed_budget"] = np.zeros(trials)
        info["observed_unit_counts"] = np.zeros(trials, dtype=np.int64)
        examples = []
        for i, n in enumerate(ns):
            counts[:, i], trace = _markov_counts(rng, laws[i], int(n), trials, rho, return_units=True)
            weight = (priors[i] / n) ** 2
            info["oracle_budget"] += weight * (trace["lengths"].astype(float) ** 2).sum(axis=1)
            info["observed_budget"] += weight * (trace["observed_lengths"].astype(float) ** 2).sum(axis=1)
            info["oracle_unit_counts"] += (trace["lengths"] > 0).sum(axis=1)
            info["observed_unit_counts"] += (trace["observed_lengths"] > 0).sum(axis=1)
            examples.append(_trace_example(trace))
        info["geometry_example"] = {"independent_services": examples}
        return counts, info
    if case["family"] != "private_common":
        raise ValueError("shared and hidden-block sampling require private_common laws")
    if mode in ("cross_service", "cross_markov"):
        longest = int(ns.max())
        lengths = (_regeneration_lengths(rng, longest, trials, rho) if mode == "cross_markov"
                   else np.ones((trials, longest), dtype=np.int64))
        labels = np.zeros(lengths.shape, dtype=np.int64)
        active = lengths > 0
        # For cross_service all positions are active, preserving its v1 RNG.
        labels[active] = rng.random(int(active.sum())) < 0.4
        starts = np.cumsum(lengths, axis=1) - lengths
        for i, n in enumerate(ns):
            clipped = np.minimum(lengths, np.maximum(0, n - starts))
            counts[:, i, 0] = (clipped * labels).sum(axis=1)
            counts[:, i, i + 1] = n - counts[:, i, 0]
        observed = merge_constant_runs(lengths, labels)
        info["oracle_budget"], _ = _shared_segment_budget(lengths, ns, priors)
        info["observed_budget"], info["separate_observed_budget"] = _shared_segment_budget(observed, ns, priors)
        info["oracle_unit_counts"] = active.sum(axis=1)
        info["observed_unit_counts"] = (observed > 0).sum(axis=1)
        info["geometry_example"] = {"shared_shocks": _trace_example({"lengths": lengths, "labels": labels, "observed_lengths": observed})}
        return counts, info
    if mode == "hidden_blocks":
        if block_size < 1 or np.any(ns % block_size):
            raise ValueError("hidden block size must divide every service sample count")
        info["observed_budget"] = np.zeros(trials)
        info["observed_unit_counts"] = np.zeros(trials, dtype=np.int64)
        examples = []
        for i, n in enumerate(ns):
            blocks = int(n // block_size)
            # Independent latent blocks have q=0.1 or 0.7 with equal chances;
            # conditional Bernoulli observations may change inside each block.
            probabilities = 0.1 + 0.6 * (rng.random((trials, blocks)) < 0.5)
            labels = (rng.random((trials, blocks, block_size)) < probabilities[:, :, None]).reshape(trials, int(n))
            counts[:, i, 0] = labels.sum(axis=1)
            counts[:, i, i + 1] = n - counts[:, i, 0]
            observed = merge_constant_runs(np.ones(labels.shape, dtype=np.int64), labels)
            info["oracle_budget"] += priors[i] ** 2 * block_size / n
            info["observed_budget"] += (priors[i] / n) ** 2 * (observed.astype(float) ** 2).sum(axis=1)
            info["oracle_unit_counts"] += blocks
            info["observed_unit_counts"] += (observed > 0).sum(axis=1)
            examples.append({"latent_block_lengths": [block_size] * blocks,
                             "latent_common_probabilities": probabilities[0].tolist(),
                             "observed_run_lengths": observed[0, observed[0] > 0].tolist()})
        info["geometry_example"] = {"independent_hidden_blocks": examples}
        return counts, info
    raise ValueError(f"unrecognized sampling mode: {mode}")


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
