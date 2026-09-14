# Synthetic validation for EIBO's abstract statistical core.
# Inputs are small discrete distributions and QUIC-like synthetic flows.
# Outputs are unittest assertions and printed validation summaries.
# Dependencies: numpy and the local eibo.statcore module; sklearn is optional.

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eibo.statcore import (  # noqa: E402
    alphabet_cardinality,
    grid_cardinality,
    quantize,
    symbol_to_id,
    tv_lower_bound,
    tv_upper_bound,
)


def _draw(rng: np.random.Generator, probabilities: np.ndarray, n: int) -> list[int]:
    return rng.choice(len(probabilities), size=n, p=probabilities).tolist()


def _one_hot(values: list[int], width: int) -> np.ndarray:
    result = np.zeros((len(values), width), dtype=float)
    result[np.arange(len(values)), values] = 1.0
    return result


class StrongClassifier:
    def fit(self, X, y):
        self.classes_ = np.array([0, 1])
        self.means_ = np.vstack([X[y == label].mean(axis=0) for label in self.classes_])
        return self

    def predict_proba(self, X):
        distances = ((X[:, None, :] - self.means_[None, :, :]) ** 2).sum(axis=2)
        logits = -distances
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        return probabilities / probabilities.sum(axis=1, keepdims=True)


class ChanceClassifier:
    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        return np.tile(np.array([[0.5, 0.5]]), (len(X), 1))


class TestStatcore(unittest.TestCase):
    def test_quantization_is_fixed_and_stable(self) -> None:
        flow = [(0, 1200), (1, 60), (0, 1800), (1, 3)]
        for scheme in ("exact", "exact_small_log_large", "log", "initial_aware"):
            first = quantize(flow, 3, scheme)
            second = quantize(flow, 3, scheme)
            self.assertEqual(first, second)
            self.assertEqual(symbol_to_id(first, scheme), symbol_to_id(second, scheme))
        self.assertEqual(quantize(flow, 1, "initial_aware")[0], (0, 1200))
        self.assertEqual(quantize([(0, 1300), (1, 100)], 1, "initial_aware")[0][1], (">1200", 1500))
        self.assertEqual(grid_cardinality("log"), 64)

    def test_tv_point_and_upper_bound_coverage(self) -> None:
        rng = np.random.default_rng(1001)
        p = np.array([0.35, 0.25, 0.20, 0.20])
        q = np.array([0.20, 0.30, 0.25, 0.25])
        true_tv = 0.5 * np.abs(p - q).sum()
        covered = 0
        estimates = []
        for _ in range(200):
            result = tv_upper_bound(_draw(rng, p, 5000), _draw(rng, q, 5000), alphabet_size=4)
            covered += result.eps_hi >= true_tv
            estimates.append(result.tv_hat)
        coverage = covered / 200
        self.assertGreaterEqual(coverage, 0.95)
        self.assertLess(abs(float(np.mean(estimates)) - true_tv), 0.02)
        print(f"TV coverage at alpha=0.05: {coverage:.3f}; mean tv_hat={np.mean(estimates):.4f}; true_tv={true_tv:.4f}")

    def test_interval_sanity_and_informative_fraction(self) -> None:
        rng = np.random.default_rng(1002)
        p = np.array([0.50, 0.20, 0.20, 0.10])
        q = np.array([0.25, 0.25, 0.25, 0.25])
        X1 = _one_hot(_draw(rng, p, 4000), 4)
        X2 = _one_hot(_draw(rng, q, 4000), 4)
        lo, diagnostics = tv_lower_bound(X1, X2, alpha=0.05, random_state=4)
        upper = tv_upper_bound(np.argmax(X1, axis=1), np.argmax(X2, axis=1), alphabet_size=4)
        self.assertTrue(0.0 <= lo <= upper.eps_hi)
        self.assertEqual(diagnostics["method"], "michel_adaptive_sup_cutoff")
        informative = float(upper.eps_hi < 0.5)
        print(f"Interval sanity: lo={lo:.4f}, eps_hi={upper.eps_hi:.4f}, informative_fraction={informative:.3f}")

    def test_lower_bound_monotonicity_and_degenerate_classifier(self) -> None:
        rng = np.random.default_rng(1003)
        values1 = _draw(rng, np.array([0.92, 0.04, 0.03, 0.01]), 1600)
        values2 = _draw(rng, np.array([0.02, 0.03, 0.05, 0.90]), 1600)
        X1, X2 = _one_hot(values1, 4), _one_hot(values2, 4)
        strong, strong_diag = tv_lower_bound(X1, X2, alpha=0.05, clf=StrongClassifier(), random_state=5)
        weak, weak_diag = tv_lower_bound(X1, X2, alpha=0.05, clf=ChanceClassifier(), random_state=5)
        self.assertGreaterEqual(strong, weak)
        self.assertLessEqual(weak, 0.0)
        self.assertLessEqual(weak_diag["raw_statistic"], 0.05)
        self.assertGreater(strong_diag["per_class_accuracies"]["class_0"], 0.8)
        print(f"Lower-bound monotonicity: strong={strong:.4f}, random/chance={weak:.4f}")

    def test_identical_distributions_shrink_with_n(self) -> None:
        rng = np.random.default_rng(1004)
        p = np.array([0.40, 0.30, 0.20, 0.10])
        small = tv_upper_bound(_draw(rng, p, 10_000), _draw(rng, p, 10_000), alphabet_size=4)
        large = tv_upper_bound(_draw(rng, p, 1_000_000), _draw(rng, p, 1_000_000), alphabet_size=4)
        self.assertLess(small.tv_hat, 0.03)
        self.assertLess(large.tv_hat, small.tv_hat)
        self.assertLess(large.eps_hi, small.eps_hi)
        self.assertLess(large.eps_hi, 0.02)
        print(
            f"Identical distributions: n=1e4 tv_hat={small.tv_hat:.5f}, eps_hi={small.eps_hi:.5f}; "
            f"n=1e6 tv_hat={large.tv_hat:.5f}, eps_hi={large.eps_hi:.5f}"
        )

    def test_cardinality_growth_across_schemes(self) -> None:
        rng = np.random.default_rng(1005)
        flows = _synthetic_quic_like_flows(2500, rng)
        for scheme in ("exact", "exact_small_log_large", "log", "initial_aware"):
            rows = alphabet_cardinality(flows, scheme, max_k=15)
            self.assertEqual(len(rows), 15)
            self.assertEqual(rows[0]["n_samples"], 2500)
            self.assertGreaterEqual(rows[-1]["realized_support"], rows[0]["realized_support"])
            self.assertTrue(all(row["theoretical_max"] >= row["realized_support"] for row in rows))
            self.assertTrue(all(math.isfinite(row["log_theoretical_max"]) for row in rows))
            print(
                f"Cardinality {scheme}: "
                + ", ".join(f"k={r['k']}:{r['realized_support']}/{r['theoretical_max']:.3g}" for r in rows)
            )


def _synthetic_quic_like_flows(n: int, rng: np.random.Generator) -> list[list[tuple[int, int]]]:
    flows: list[list[tuple[int, int]]] = []
    for _ in range(n):
        direction = 0
        flow = [(0, 1200)]
        for _ in range(14):
            if rng.random() > 0.85:
                direction = 1 - direction
            size = int(np.clip(np.exp(rng.normal(5.0, 1.1)), 1, 2200))
            flow.append((direction, size))
        flows.append(flow)
    return flows


if __name__ == "__main__":
    unittest.main(verbosity=2)
