# Rejection-generic/divisibility lower bounds for total variation.
# Inputs are two independent feature samples, one per distribution.
# Outputs are a lower bound and diagnostics for a q-quantized classifier ladder.
# Dependencies: numpy, scipy, and scikit-learn.

from __future__ import annotations

import copy
import math
from typing import Any, Sequence

import numpy as np
from scipy.stats import beta


DEFAULT_Q_VALUES = (2, 4, 8, 16, 32)


def _clone_classifier(clf: Any) -> Any:
    try:
        from sklearn.base import clone

        return clone(clf)
    except Exception:
        return copy.deepcopy(clf)


def _default_classifier() -> Any:
    from sklearn.tree import DecisionTreeClassifier

    # An unrestricted tree is deliberately used: a realizable test class must
    # be able to represent the observed rejection rule when the feature map is
    # informative, while held-out evaluation controls its sampling optimism.
    return DecisionTreeClassifier(random_state=0)


def _validate_inputs(X1: Sequence[Sequence[float]], X2: Sequence[Sequence[float]]) -> tuple[np.ndarray, np.ndarray]:
    array1 = np.asarray(X1, dtype=float)
    array2 = np.asarray(X2, dtype=float)
    if array1.ndim != 2 or array2.ndim != 2 or array1.shape[1] != array2.shape[1]:
        raise ValueError("X1 and X2 must be two-dimensional matrices with equal feature width")
    if len(array1) < 8 or len(array2) < 8:
        raise ValueError("each class needs at least eight samples for train/test and confidence bounds")
    if not np.all(np.isfinite(array1)) or not np.all(np.isfinite(array2)):
        raise ValueError("X1 and X2 must contain only finite values")
    return array1, array2


def _split_data(X1: np.ndarray, X2: np.ndarray, random_state: int) -> tuple[np.ndarray, ...]:
    from sklearn.model_selection import train_test_split

    combined = np.vstack([X1, X2])
    labels = np.concatenate([np.zeros(len(X1), dtype=int), np.ones(len(X2), dtype=int)])
    return train_test_split(
        combined,
        labels,
        test_size=0.30,
        random_state=random_state,
        stratify=labels,
    )


def _quantize_train_test(
    X_train: np.ndarray,
    X_test: np.ndarray,
    q: int,
) -> tuple[np.ndarray, np.ndarray, list[list[float]]]:
    if q < 2:
        raise ValueError("q must be at least 2")
    # Bins are learned from training data only. This keeps the held-out error
    # calculation conditionally valid instead of letting test values set bins.
    edges: list[list[float]] = []
    train_q = np.empty_like(X_train, dtype=float)
    test_q = np.empty_like(X_test, dtype=float)
    for column in range(X_train.shape[1]):
        values = X_train[:, column]
        finite_unique = np.unique(values)
        if len(finite_unique) <= q:
            # Midpoints preserve discrete categories: using category values as
            # right-sided search cutpoints would collapse 0 and 1 together.
            cuts = ((finite_unique[:-1] + finite_unique[1:]) / 2.0).tolist()
        else:
            cuts = np.quantile(values, np.linspace(0.0, 1.0, q + 1)[1:-1]).tolist()
            cuts = np.unique(np.asarray(cuts, dtype=float)).tolist()
        edges.append(cuts)
        train_q[:, column] = np.searchsorted(np.asarray(cuts), values, side="right")
        test_q[:, column] = np.searchsorted(np.asarray(cuts), X_test[:, column], side="right")
    return train_q, test_q, edges


def _clopper_pearson_upper(errors: int, n: int, alpha: float) -> float:
    if errors < 0 or errors > n or n < 1:
        raise ValueError("invalid binomial count")
    if errors == n:
        return 1.0
    return float(beta.ppf(1.0 - alpha, errors + 1, n - errors))


def _fit_and_score(
    X_train: np.ndarray,
    X_test: np.ndarray,
    y_train: np.ndarray,
    y_test: np.ndarray,
    q: int,
    clf: Any,
) -> dict[str, Any]:
    train_q, test_q, edges = _quantize_train_test(X_train, X_test, q)
    model = _clone_classifier(clf)
    model.fit(train_q, y_train)
    prediction = np.asarray(model.predict(test_q), dtype=int).reshape(-1)
    errors = prediction != y_test
    n0 = int(np.sum(y_test == 0))
    n1 = int(np.sum(y_test == 1))
    e0 = int(np.sum(errors & (y_test == 0)))
    e1 = int(np.sum(errors & (y_test == 1)))
    return {
        "q": int(q),
        "classifier": model,
        "classifier_name": type(model).__name__,
        "n_test_class_0": n0,
        "n_test_class_1": n1,
        "errors_class_0": e0,
        "errors_class_1": e1,
        "empirical_error_class_0": float(e0 / n0),
        "empirical_error_class_1": float(e1 / n1),
        "quantization_edges": edges,
    }


def tv_lower_bound_divisibility(
    X1: Sequence[Sequence[float]],
    X2: Sequence[Sequence[float]],
    alpha: float = 0.05,
    clf: Any | None = None,
    mode: str = "realizable",
    *,
    q_values: Sequence[int] = DEFAULT_Q_VALUES,
    random_state: int = 0,
) -> tuple[float, dict[str, Any]]:
    """Estimate a rejection-generic lower bound on ``TV(P1, P2)``.

    For a binary test with class-conditional errors e0 and e1,
    ``TV(P1,P2) >= 1 - e0 - e1``. The implementation
    replaces each held-out error by a one-sided Clopper-Pearson upper limit and
    maximizes the resulting lower bound over a Bonferroni-protected q ladder.
    The ``realizable`` mode records the explicit assumption that the chosen
    classifier family contains (or sufficiently approximates) a useful test;
    the held-out confidence statement itself is conditional on the trained
    classifier and does not make that assumption distribution-free.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must lie in (0, 1)")
    if mode != "realizable":
        raise ValueError("mode must be 'realizable'")
    q_values = tuple(int(q) for q in q_values)
    if not q_values or any(q < 2 for q in q_values):
        raise ValueError("q_values must contain integers >= 2")
    if len(set(q_values)) != len(q_values):
        raise ValueError("q_values must be unique")

    array1, array2 = _validate_inputs(X1, X2)
    X_train, X_test, y_train, y_test = _split_data(array1, array2, random_state)
    model_template = clf if clf is not None else _default_classifier()
    alpha_per_q_class = alpha / (2.0 * len(q_values))
    candidates: list[dict[str, Any]] = []
    for q in q_values:
        row = _fit_and_score(X_train, X_test, y_train, y_test, q, model_template)
        row["error_upper_class_0"] = _clopper_pearson_upper(
            row["errors_class_0"], row["n_test_class_0"], alpha_per_q_class
        )
        row["error_upper_class_1"] = _clopper_pearson_upper(
            row["errors_class_1"], row["n_test_class_1"], alpha_per_q_class
        )
        # The exact test witness is 1-U0-U1. Its half-sum is the optimistic
        # balanced error, so the same expression is 1-2*optimistic_error.
        row["optimistic_error"] = float(
            0.5 * (row["error_upper_class_0"] + row["error_upper_class_1"])
        )
        row["raw_bound"] = float(1.0 - 2.0 * row["optimistic_error"])
        row["nonempty"] = bool(row["raw_bound"] > 0.0)
        candidates.append(row)

    best = max(candidates, key=lambda row: row["raw_bound"])
    raw_bound = float(best["raw_bound"])
    diagnostics = {
        "method": "rejection_generic_divisibility",
        "classifier": best["classifier"],
        "classifier_name": best["classifier_name"],
        "mode": mode,
        "alpha": float(alpha),
        "confidence_level": float(1.0 - alpha),
        "q_values_tried": list(q_values),
        "candidates": candidates,
        "selected_q": int(best["q"]),
        "empirical_per_class_error": {
            "class_0": best["empirical_error_class_0"],
            "class_1": best["empirical_error_class_1"],
        },
        "optimistic_error": best["optimistic_error"],
        "raw_bound": raw_bound,
        "raw_bound_went_negative": bool(raw_bound <= 0.0),
        "vacuous": bool(raw_bound <= 0.0),
        "vacuous_value": 0.0 if raw_bound <= 0.0 else None,
        "realizability_assumption": (
            "The realizability assumption is that the selected classifier family contains, or sufficiently approximate, "
            "a useful binary rejection test for the pair; this is not distribution-free. "
            "The held-out binomial calibration is conditional on the trained classifier and "
            "requires independent iid samples from P1 and P2."
        ),
        "bound_exact_form": (
            "For each q, let U_j be a one-sided Clopper-Pearson upper confidence limit "
            "for the held-out class-j error e_j, with alpha/(2|Q|) per class and q. "
            "The q-specific lower bound is 1 - U_0 - U_1 = 1 - 2*optimistic_error, "
            "where optimistic_error=(U_0+U_1)/2; return the maximum over q before clipping at zero."
        ),
        "bound_source": (
            "Population identity TV(P1,P2) = 1 - inf_h[P1(h=1)+P2(h=0)] and the "
            "test witness TV >= 1-e0-e1; finite-sample Clopper-Pearson construction is "
            "the present implementation's own conservative construction."
        ),
    }
    return float(max(0.0, raw_bound)), diagnostics
