# Focused tests for the rejection-generic TV lower bound.
# Inputs are synthetic two-sample feature matrices.
# Outputs are assertions about validity metadata, vacuity, and monotonicity.
# Dependencies: numpy, pytest, scikit-learn, and the local eibo package.

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.tree import DecisionTreeClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eibo.divisibility import tv_lower_bound_divisibility  # noqa: E402


def test_divisibility_reports_q_ladder_and_nonnegative_output() -> None:
    rng = np.random.default_rng(701)
    x1 = rng.normal(0.0, 1.0, size=(300, 4))
    x2 = rng.normal(1.5, 1.0, size=(300, 4))
    lo, diagnostics = tv_lower_bound_divisibility(x1, x2, random_state=7)
    assert 0.0 <= lo <= 1.0
    assert diagnostics["q_values_tried"] == [2, 4, 8, 16, 32]
    assert diagnostics["raw_bound"] == max(row["raw_bound"] for row in diagnostics["candidates"])
    assert "realizability" in diagnostics["realizability_assumption"]


def test_weak_classifier_cannot_increase_bound() -> None:
    rng = np.random.default_rng(702)
    x1 = rng.normal(0.0, 1.0, size=(400, 3))
    x2 = rng.normal(1.0, 1.0, size=(400, 3))
    strong, _ = tv_lower_bound_divisibility(
        x1,
        x2,
        clf=DecisionTreeClassifier(max_depth=4, random_state=1),
        random_state=9,
    )
    weak, weak_diag = tv_lower_bound_divisibility(
        x1,
        x2,
        clf=DummyClassifier(strategy="prior"),
        random_state=9,
    )
    assert strong >= weak
    assert weak == 0.0
    assert weak_diag["vacuous"] is True


def test_identical_samples_can_be_explicitly_vacuous() -> None:
    rng = np.random.default_rng(703)
    x = rng.normal(size=(500, 5))
    lo, diagnostics = tv_lower_bound_divisibility(x, x.copy(), random_state=4)
    assert lo == 0.0
    assert diagnostics["vacuous"] is True
    assert diagnostics["vacuous_value"] == 0.0
    assert diagnostics["raw_bound"] <= 0.0

