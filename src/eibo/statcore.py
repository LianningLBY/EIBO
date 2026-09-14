# Abstract fixed-grid quantization and distribution-free TV brackets for EIBO.
# Inputs are integer-coded datagram observations or already encoded symbols.
# Outputs are stable quantized tuples, cardinality tables, and TV bounds.
# Dependencies: numpy, scipy, and scikit-learn for classifier-based bounds.

from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

try:
    from scipy.stats import binom as _scipy_binom
except ImportError:  # pragma: no cover - exercised only in minimal environments
    _scipy_binom = None


DEFAULT_MAX_SIZE = 1500
DEFAULT_EXACT_SMALL_B = 200
DEFAULT_LARGE_BINS = 32
DEFAULT_LOG_BINS = 32


def _validate_scheme(scheme: str) -> str:
    valid = {"exact", "exact_small_log_large", "log", "initial_aware"}
    if scheme not in valid:
        raise ValueError(f"scheme must be one of {sorted(valid)}, got {scheme!r}")
    return scheme


def _validate_size(size: Any) -> int:
    if isinstance(size, (bool, np.bool_)):
        raise ValueError("datagram size must be a positive integer")
    size_int = int(size)
    if size_int != size or size_int <= 0:
        raise ValueError(f"datagram size must be a positive integer, got {size!r}")
    return size_int


def _log_edges(low: int, high: int, n_bins: int) -> np.ndarray:
    if low > high:
        raise ValueError("log-grid lower edge must not exceed upper edge")
    if n_bins < 1:
        raise ValueError("n_bins must be positive")
    return np.geomspace(float(low), float(high), n_bins + 1)


def _log_bin(size: int, low: int, high: int, n_bins: int) -> int:
    edges = _log_edges(low, high, n_bins)
    if size <= low:
        return 0
    if size >= high:
        return n_bins - 1
    index = int(np.searchsorted(edges, size, side="right") - 1)
    return max(0, min(n_bins - 1, index))


def _size_grid(
    scheme: str,
    *,
    exact_small_b: int = DEFAULT_EXACT_SMALL_B,
    max_size: int = DEFAULT_MAX_SIZE,
    large_bins: int = DEFAULT_LARGE_BINS,
    log_bins: int = DEFAULT_LOG_BINS,
) -> tuple[Any, ...]:
    """Return the fixed, finite size-symbol grid for a quantization scheme."""
    _validate_scheme(scheme)
    if exact_small_b < 1 or max_size < 1 or large_bins < 1 or log_bins < 1:
        raise ValueError("grid parameters must be positive")
    if exact_small_b >= max_size:
        raise ValueError("exact_small_b must be smaller than max_size")

    if scheme == "exact":
        return tuple(range(1, max_size + 1)) + ((">1500", max_size),)
    if scheme == "exact_small_log_large":
        return (
            tuple(range(1, exact_small_b + 1))
            + tuple(("log", i) for i in range(large_bins))
            + ((">1500", max_size),)
        )
    if scheme == "log":
        return tuple(("log", i) for i in range(log_bins))
    return tuple(("log", i) for i in range(log_bins)) + (1200, (">1200", max_size))


def quantization_grid(
    scheme: str = "log",
    *,
    exact_small_b: int = DEFAULT_EXACT_SMALL_B,
    max_size: int = DEFAULT_MAX_SIZE,
    large_bins: int = DEFAULT_LARGE_BINS,
    log_bins: int = DEFAULT_LOG_BINS,
) -> tuple[tuple[int, Any], ...]:
    """Return every one-datagram symbol in the fixed direction-size grid.

    The grid is fixed entirely by function parameters and never inferred from
    observed flows. This invariant is required because the finite-alphabet
    concentration bound uses a fixed alphabet size m.
    """
    size_grid = _size_grid(
        scheme,
        exact_small_b=exact_small_b,
        max_size=max_size,
        large_bins=large_bins,
        log_bins=log_bins,
    )
    return tuple((direction, size_symbol) for direction in (0, 1) for size_symbol in size_grid)


def grid_cardinality(
    scheme: str = "log",
    *,
    exact_small_b: int = DEFAULT_EXACT_SMALL_B,
    max_size: int = DEFAULT_MAX_SIZE,
    large_bins: int = DEFAULT_LARGE_BINS,
    log_bins: int = DEFAULT_LOG_BINS,
) -> int:
    """Return the fixed one-datagram alphabet cardinality."""
    return len(
        quantization_grid(
            scheme,
            exact_small_b=exact_small_b,
            max_size=max_size,
            large_bins=large_bins,
            log_bins=log_bins,
        )
    )


def _quantize_size(
    size: int,
    scheme: str,
    *,
    exact_small_b: int,
    max_size: int,
    large_bins: int,
    log_bins: int,
) -> Any:
    if scheme == "exact":
        return size if size <= max_size else (">1500", max_size)
    if scheme == "exact_small_log_large":
        if size <= exact_small_b:
            return size
        if size > max_size:
            return (">1500", max_size)
        return ("log", _log_bin(size, exact_small_b + 1, max_size, large_bins))
    if scheme == "log":
        return ("log", _log_bin(size, 1, max_size, log_bins))
    raise AssertionError("initial_aware is handled with first-datagram context")


def quantize(
    flow: Sequence[tuple[int, int]],
    k: int,
    scheme: str = "log",
    *,
    client_direction: int = 0,
    exact_small_b: int = DEFAULT_EXACT_SMALL_B,
    max_size: int = DEFAULT_MAX_SIZE,
    large_bins: int = DEFAULT_LARGE_BINS,
    log_bins: int = DEFAULT_LOG_BINS,
) -> tuple[tuple[int, Any], ...]:
    """Quantize the first k observations of one flow onto a fixed grid.

    The output alphabet depends only on ``scheme`` and its explicit parameters,
    never on the observed flow. A data-dependent alphabet would invalidate the
    finite-alphabet concentration bound because that bound requires a fixed m.
    ``initial_aware`` marks the first client-origin datagram as 1200 or >1200;
    all other sizes use the fixed log grid.
    """
    _validate_scheme(scheme)
    if k < 1:
        raise ValueError("k must be positive")
    if client_direction not in (0, 1):
        raise ValueError("client_direction must be 0 or 1")
    if len(flow) < k:
        raise ValueError(f"flow has {len(flow)} observations but k={k} was requested")

    result: list[tuple[int, Any]] = []
    first_client_seen = False
    for direction_raw, size_raw in flow[:k]:
        direction = int(direction_raw)
        if direction not in (0, 1) or direction != direction_raw:
            raise ValueError(f"direction must be integer-coded 0 or 1, got {direction_raw!r}")
        size = _validate_size(size_raw)
        if scheme == "initial_aware":
            if direction == client_direction and not first_client_seen:
                first_client_seen = True
                size_symbol = 1200 if size == 1200 else (">1200", max_size) if size > 1200 else _quantize_size(
                    size,
                    "log",
                    exact_small_b=exact_small_b,
                    max_size=max_size,
                    large_bins=large_bins,
                    log_bins=log_bins,
                )
            else:
                size_symbol = _quantize_size(
                    size,
                    "log",
                    exact_small_b=exact_small_b,
                    max_size=max_size,
                    large_bins=large_bins,
                    log_bins=log_bins,
                )
        else:
            size_symbol = _quantize_size(
                size,
                scheme,
                exact_small_b=exact_small_b,
                max_size=max_size,
                large_bins=large_bins,
                log_bins=log_bins,
            )
        result.append((direction, size_symbol))
    return tuple(result)


def _size_label_index(size_symbol: Any, labels: tuple[Any, ...]) -> int:
    try:
        return labels.index(size_symbol)
    except ValueError as exc:
        raise ValueError(f"symbol contains size token {size_symbol!r} outside the fixed grid") from exc


def symbol_to_id(
    symbol: Any,
    scheme: str = "log",
    *,
    exact_small_b: int = DEFAULT_EXACT_SMALL_B,
    max_size: int = DEFAULT_MAX_SIZE,
    large_bins: int = DEFAULT_LARGE_BINS,
    log_bins: int = DEFAULT_LOG_BINS,
) -> int:
    """Map a one-datagram or k-datagram quantized tuple to a stable integer.

    IDs use base encoding over the fixed one-datagram grid, so no observed-data
    dictionary is needed and the same symbol always receives the same ID.
    """
    labels = _size_grid(
        scheme,
        exact_small_b=exact_small_b,
        max_size=max_size,
        large_bins=large_bins,
        log_bins=log_bins,
    )
    one_datagram = (
        isinstance(symbol, tuple)
        and len(symbol) == 2
        and isinstance(symbol[0], (int, np.integer))
        and int(symbol[0]) in (0, 1)
    )
    symbols = (symbol,) if one_datagram else tuple(symbol)
    if not symbols:
        raise ValueError("symbol sequence must not be empty")
    base = 2 * len(labels)
    encoded = 0
    for item in symbols:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError(f"invalid quantized symbol {item!r}")
        direction, size_symbol = item
        if direction not in (0, 1):
            raise ValueError(f"symbol direction must be 0 or 1, got {direction!r}")
        local_id = int(direction) * len(labels) + _size_label_index(size_symbol, labels)
        encoded = encoded * base + local_id
    return encoded


def alphabet_cardinality(
    flows: Iterable[Sequence[tuple[int, int]]],
    scheme: str = "log",
    *,
    max_k: int = 15,
    exact_small_b: int = DEFAULT_EXACT_SMALL_B,
    max_size: int = DEFAULT_MAX_SIZE,
    large_bins: int = DEFAULT_LARGE_BINS,
    log_bins: int = DEFAULT_LOG_BINS,
    client_direction: int = 0,
) -> list[dict[str, Any]]:
    """Report fixed-grid theoretical size and realized support for k=1..max_k."""
    flow_list = list(flows)
    if max_k < 1:
        raise ValueError("max_k must be positive")
    base = grid_cardinality(
        scheme,
        exact_small_b=exact_small_b,
        max_size=max_size,
        large_bins=large_bins,
        log_bins=log_bins,
    )
    n = len(flow_list)
    rows: list[dict[str, Any]] = []
    for k in range(1, max_k + 1):
        log_theoretical = k * math.log(base)
        theoretical = math.exp(log_theoretical) if log_theoretical < math.log(np.finfo(float).max) else float("inf")
        support = {
            symbol_to_id(
                quantize(
                    flow,
                    k,
                    scheme,
                    client_direction=client_direction,
                    exact_small_b=exact_small_b,
                    max_size=max_size,
                    large_bins=large_bins,
                    log_bins=log_bins,
                ),
                scheme,
                exact_small_b=exact_small_b,
                max_size=max_size,
                large_bins=large_bins,
                log_bins=log_bins,
            )
            for flow in flow_list
        }
        rows.append(
            {
                "scheme": scheme,
                "k": k,
                "theoretical_max": float(theoretical),
                "log_theoretical_max": float(log_theoretical),
                "realized_support": len(support),
                "n_samples": n,
                "support_per_sqrt_n": float(len(support) / math.sqrt(n)) if n else 0.0,
                "grid_size_one_datagram": base,
            }
        )
    return rows


def _empirical_counts(sample: Iterable[Any]) -> Mapping[Any, int]:
    counts: dict[Any, int] = {}
    for item in sample:
        counts[item] = counts.get(item, 0) + 1
    return counts


@dataclass(frozen=True)
class TVUpperBoundResult:
    """Point TV estimate and the finite-alphabet distribution-free upper bound."""

    tv_hat: float
    eps_hi: float
    alpha: float
    alphabet_size: float
    n1: int
    n2: int
    radius_1: float
    radius_2: float

    @property
    def error_floor_lower_bound(self) -> float:
        """The valid error-floor implication supported by eps_hi."""
        return max(0.0, (1.0 - self.eps_hi) / 2.0)


def tv_upper_bound(
    sample1: Iterable[Any],
    sample2: Iterable[Any],
    *,
    alphabet_size: float | None = None,
    scheme: str | None = None,
    k: int | None = None,
    alpha: float = 0.05,
    exact_small_b: int = DEFAULT_EXACT_SMALL_B,
    max_size: int = DEFAULT_MAX_SIZE,
    large_bins: int = DEFAULT_LARGE_BINS,
    log_bins: int = DEFAULT_LOG_BINS,
) -> TVUpperBoundResult:
    """Compute empirical TV and the specified finite-alphabet upward bound.

    The returned upper bound is exactly
    ``TV_hat + 0.5*sqrt(m/n1) + 0.5*sqrt(2*log(2/alpha)/n1)``
    plus the analogous terms for sample 2, clipped to [0, 1]. The alphabet
    size must be the fixed grid size, not the observed support size.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    values1, values2 = list(sample1), list(sample2)
    n1, n2 = len(values1), len(values2)
    if n1 < 1 or n2 < 1:
        raise ValueError("both samples must be non-empty")
    if alphabet_size is None:
        if scheme is None or k is None:
            raise ValueError("provide alphabet_size or both scheme and k")
        alphabet_size = float(
            grid_cardinality(
                scheme,
                exact_small_b=exact_small_b,
                max_size=max_size,
                large_bins=large_bins,
                log_bins=log_bins,
            )
            ** k
        )
    m = float(alphabet_size)
    if not math.isfinite(m) or m < 1:
        raise ValueError("alphabet_size must be a finite positive number")
    counts1, counts2 = _empirical_counts(values1), _empirical_counts(values2)
    if len(set(counts1) | set(counts2)) > m:
        raise ValueError("alphabet_size is smaller than the observed support")
    union = set(counts1) | set(counts2)
    tv_hat = 0.5 * sum(abs(counts1.get(value, 0) / n1 - counts2.get(value, 0) / n2) for value in union)
    fluctuation = math.sqrt(2.0 * math.log(2.0 / alpha))
    radius_1 = 0.5 * math.sqrt(m / n1) + 0.5 * fluctuation / math.sqrt(n1)
    radius_2 = 0.5 * math.sqrt(m / n2) + 0.5 * fluctuation / math.sqrt(n2)
    eps_hi = min(1.0, max(0.0, tv_hat + radius_1 + radius_2))
    return TVUpperBoundResult(tv_hat, eps_hi, alpha, m, n1, n2, radius_1, radius_2)


def _clone_classifier(clf: Any) -> Any:
    try:
        from sklearn.base import clone

        return clone(clf)
    except Exception:
        return copy.deepcopy(clf)


def _default_classifier() -> Any:
    try:
        from sklearn.linear_model import LogisticRegression

        return LogisticRegression(max_iter=1000, random_state=0)
    except ImportError:
        return _NumpyCentroidClassifier()


class _NumpyCentroidClassifier:
    """Small optional-dependency fallback with sklearn-like fit/predict_proba."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> "_NumpyCentroidClassifier":
        self.classes_ = np.unique(y)
        self.centroids_ = np.vstack([X[y == label].mean(axis=0) for label in self.classes_])
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        distances = ((X[:, None, :] - self.centroids_[None, :, :]) ** 2).sum(axis=2)
        logits = -distances
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        return probabilities


def _classifier_scores(clf: Any, X: np.ndarray) -> np.ndarray:
    if hasattr(clf, "predict_proba"):
        probabilities = np.asarray(clf.predict_proba(X), dtype=float)
        if probabilities.ndim == 2 and probabilities.shape[1] >= 2:
            scores = probabilities[:, 1]
        else:
            scores = probabilities.reshape(-1)
    elif hasattr(clf, "decision_function"):
        raw = np.asarray(clf.decision_function(X), dtype=float).reshape(-1)
        scores = 1.0 / (1.0 + np.exp(-np.clip(raw, -700.0, 700.0)))
    else:
        scores = np.asarray(clf.predict(X), dtype=float).reshape(-1)
    return np.clip(scores, 0.0, 1.0)


def _cutoff_statistics(scores: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    order = np.argsort(scores, kind="mergesort")
    sorted_scores, sorted_labels = scores[order], labels[order]
    class0 = (sorted_labels == 0).astype(int)
    cumulative_class0 = np.cumsum(class0)
    end_of_tie = np.r_[sorted_scores[1:] != sorted_scores[:-1], True]
    positions = np.flatnonzero(end_of_tie) + 1
    positions = positions[positions < len(scores)]
    if not len(positions):
        return np.empty(0), np.empty(0, dtype=int), np.empty(0, dtype=int)
    cutoffs = sorted_scores[positions - 1]
    v = cumulative_class0[positions - 1]
    return cutoffs, positions.astype(int), v.astype(int)


def _gumbel_quantile(tail_probability: float) -> float:
    return -math.log(-math.log1p(-tail_probability))


def _binom_ppf(probability: float, n: int, p: float) -> int:
    """Use scipy when present, otherwise evaluate the binomial CDF by recurrence."""
    if _scipy_binom is not None:
        return int(_scipy_binom.ppf(probability, n, p))
    if p <= 0.0:
        return 0
    if p >= 1.0:
        return n
    if n > 2_000_000:
        # This path is only a dependency-free fallback; normal approximation
        # keeps it bounded for unusually large caller-provided classifier sets.
        z = 2.128045234184983 if probability >= 0.983 else 0.0
        return int(np.clip(round(n * p + z * math.sqrt(n * p * (1.0 - p))), 0, n))
    if p > 0.5:
        return n - _binom_ppf(1.0 - probability, n, 1.0 - p)
    pmf = (1.0 - p) ** n
    cumulative = pmf
    if cumulative >= probability:
        return 0
    ratio = p / (1.0 - p)
    for k in range(0, n):
        pmf *= (n - k) / (k + 1) * ratio
        cumulative += pmf
        if cumulative >= probability:
            return k + 1
    return n


def _michel_beta(alpha: float, m: float) -> float:
    """Appendix B.1's iterated-log confidence constant.

    For very small effective m the paper's asymptotic iterated-log expression
    is undefined; returning a large conservative constant makes the candidate
    constraint easier to satisfy instead of extrapolating the asymptotics.
    """
    if m <= math.exp(math.e):
        return math.sqrt(2.0 * math.log(6.0 / alpha))
    ll = math.log(math.log(m))
    if ll <= 0:
        return math.sqrt(2.0 * math.log(6.0 / alpha))
    return math.sqrt(2.0 * ll) + (
        math.log(math.log(math.log(m))) - math.log(math.pi) + 2.0 * _gumbel_quantile(alpha)
    ) / (2.0 * math.sqrt(2.0 * ll))


def _michel_upper_count(
    z: np.ndarray,
    m: int,
    n: int,
    lambda_tilde: float,
    alpha: float,
) -> np.ndarray:
    """Evaluate Michel et al. Eq. (17) and Appendix B.1 for all cutoffs."""
    q_m = _binom_ppf(1.0 - alpha / 3.0, m, lambda_tilde)
    q_n = _binom_ppf(1.0 - alpha / 3.0, n, lambda_tilde)
    m_tilde, n_tilde = m - q_m, n - q_n
    if m_tilde <= 0 or n_tilde <= 0:
        return np.full_like(z, float(m), dtype=float)
    total = m_tilde + n_tilde
    result = np.empty_like(z, dtype=float)
    low = z <= q_m
    high = z >= m + n_tilde
    middle = ~(low | high)
    result[low] = z[low]
    result[high] = float(m)
    if np.any(middle):
        z_tilde = z[middle].astype(float) - q_m
        beta = _michel_beta(alpha / 3.0, float(m_tilde))
        correction = np.sqrt(
            (m_tilde / total)
            * (n_tilde / total)
            * np.maximum(total - z_tilde, 0.0)
            / max(total - 1, 1)
            * np.maximum(z_tilde, 0.0)
        )
        result[middle] = q_m + z_tilde * m_tilde / total + beta * correction
    return result


def _michel_bound(
    z: np.ndarray,
    v: np.ndarray,
    m: int,
    n: int,
    alpha: float,
    *,
    grid_points: int,
) -> tuple[float, float]:
    """Find the infimum feasible lambda in the adaptive cutoff construction."""
    if len(z) == 0:
        return 0.0, 0.0

    def feasible(value: float) -> bool:
        upper = _michel_upper_count(z, m, n, value, alpha)
        return bool(np.all(v <= upper + 1e-12))

    grid = np.linspace(0.0, 1.0, grid_points)
    feasible_grid = np.array([feasible(float(value)) for value in grid], dtype=bool)
    indices = np.flatnonzero(feasible_grid)
    if not len(indices):
        return 1.0, 0.0
    index = int(indices[0])
    if index == 0:
        return 0.0, 0.0
    lo, hi = float(grid[index - 1]), float(grid[index])
    if feasible(lo):
        return lo, 0.0
    for _ in range(35):
        mid = (lo + hi) / 2.0
        if feasible(mid):
            hi = mid
        else:
            lo = mid
    return hi, 0.0


def tv_lower_bound(
    X1: Sequence[Sequence[float]],
    X2: Sequence[Sequence[float]],
    alpha: float = 0.05,
    clf: Any | None = None,
    *,
    test_size: float = 0.3,
    random_state: int = 0,
    method: str = "michel",
    michel_grid_points: int = 1001,
) -> tuple[float, dict[str, Any]]:
    """Estimate an assumption-free high-probability TV lower bound.

    With ``method='michel'`` this implements the adaptive sup-over-cutoff
    in-class-accuracy construction from Michel et al., arXiv:2005.06006:
    ``lambda_adapt = inf{lambda: V_m(z) <= Q_{alpha/3}(z, lambda) for all z}``,
    with Eq. (17)'s binomial trimming and Appendix B.1's iterated-log
    hypergeometric-process confidence constant. The classifier is trained and
    evaluated on disjoint data. For very small effective sample counts the
    Appendix asymptotic constant is replaced by a conservative finite value.

    ``method='classical'`` instead returns the held-out statistic
    ``max_cutoff(accuracy_class_0 + accuracy_class_1 - 1)``; its raw value may
    be negative and it is not Michel's adaptive bound.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    if method not in {"michel", "classical"}:
        raise ValueError("method must be 'michel' or 'classical'")
    array1 = np.asarray(X1, dtype=float)
    array2 = np.asarray(X2, dtype=float)
    if array1.ndim != 2 or array2.ndim != 2 or array1.shape[1] != array2.shape[1]:
        raise ValueError("X1 and X2 must be two-dimensional matrices with equal feature width")
    if len(array1) < 4 or len(array2) < 4:
        raise ValueError("each class needs at least four samples for a held-out bound")

    swapped = len(array1) > len(array2)
    small, large = (array1, array2) if not swapped else (array2, array1)
    combined = np.vstack([small, large])
    labels = np.concatenate([np.zeros(len(small), dtype=int), np.ones(len(large), dtype=int)])
    rng = np.random.default_rng(random_state)
    train_indices: list[int] = []
    test_indices: list[int] = []
    for label in (0, 1):
        label_indices = np.flatnonzero(labels == label)
        rng.shuffle(label_indices)
        if isinstance(test_size, (int, np.integer)):
            n_test = int(test_size)
        else:
            n_test = int(math.ceil(float(test_size) * len(label_indices)))
        n_test = max(1, min(len(label_indices) - 1, n_test))
        test_indices.extend(label_indices[:n_test].tolist())
        train_indices.extend(label_indices[n_test:].tolist())
    train_indices = np.asarray(train_indices, dtype=int)
    test_indices = np.asarray(test_indices, dtype=int)
    X_train, X_test = combined[train_indices], combined[test_indices]
    y_train, y_test = labels[train_indices], labels[test_indices]
    model = _clone_classifier(clf) if clf is not None else _default_classifier()
    model.fit(X_train, y_train)
    scores = _classifier_scores(model, X_test)
    cutoffs, z, v = _cutoff_statistics(scores, y_test)
    m = int(np.sum(y_test == 0))
    n = int(np.sum(y_test == 1))

    raw_values = np.zeros(1 if len(z) == 0 else len(z), dtype=float)
    if len(z):
        raw_values = v / m - (z - v) / n
    best_index = int(np.argmax(raw_values)) if len(raw_values) else 0
    raw_statistic = float(raw_values[best_index]) if len(raw_values) else 0.0
    chosen_cutoff = float(cutoffs[best_index]) if len(cutoffs) else None
    if chosen_cutoff is None:
        accuracy0 = 0.5
        accuracy1 = 0.5
    else:
        predicted_class0 = scores <= chosen_cutoff
        accuracy0 = float(np.mean(predicted_class0[y_test == 0]))
        accuracy1 = float(np.mean(~predicted_class0[y_test == 1]))

    if method == "classical":
        raw_bound = raw_statistic
        bound_method = "classical_balanced_accuracy"
    else:
        raw_bound, _ = _michel_bound(
            z,
            v,
            m,
            n,
            alpha,
            grid_points=michel_grid_points,
        )
        bound_method = "michel_adaptive_sup_cutoff"
    diagnostics = {
        "classifier": model,
        "method": bound_method,
        "held_out_per_class": {"class_0": m, "class_1": n},
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
        "per_class_accuracies": {"class_0": accuracy0, "class_1": accuracy1},
        "cutoff": chosen_cutoff,
        "raw_statistic": raw_statistic,
        "bound_before_clipping": float(raw_bound),
        "alpha": alpha,
        "swapped_to_balance_classes": swapped,
        "confidence_statement": f"reported as a nominal 1-alpha={1-alpha:.3f} lower bound",
        "note": (
            "Michel et al. adaptive construction; the small-effective-m sample "
            "constant uses a conservative finite stabilization because the "
            "iterated-log asymptotic expression is undefined there."
            if method == "michel"
            else "Classical held-out balanced-accuracy fallback, not Michel's adaptive bound."
        ),
    }
    return float(np.clip(raw_bound, 0.0, 1.0)), diagnostics
