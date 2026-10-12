"""Known-truth and normalization checks for exploratory risk certificates."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from eibo.riskcert import direct_risk_bounds, empirical_known_risk, grouped_joint_risk_bound, tree_risk_bound


class TestRiskcert(unittest.TestCase):
    def test_identical_laws_recover_multiclass_error(self):
        counts = [[100, 100]] * 4
        priors = [0.2] * 4  # one equally likely unknown class
        self.assertAlmostEqual(empirical_known_risk(counts, priors), 0.6)
        self.assertAlmostEqual(tree_risk_bound(np.zeros((4, 4)), priors)["lower_floor"], 0.6)

    def test_disjoint_laws_and_zero_overlap_edges(self):
        counts = np.eye(4, dtype=int) * 200
        upper = np.ones((4, 4)) - np.eye(4)
        result = direct_risk_bounds(counts, [0.25] * 4, alphabet_size=4)
        self.assertEqual(result["classwise"]["lower_floor"], 0)
        self.assertEqual(result["joint"]["lower_floor"], 0)
        tree = tree_risk_bound(upper, [0.25] * 4)
        self.assertEqual(tree["lower_floor"], 0)
        self.assertEqual(len(tree["edges"]), 3)

    def test_weighted_tree_below_exact_bayes_risk(self):
        rng = np.random.default_rng(20261012)
        for k in range(2, 9):
            for _ in range(25):
                laws = rng.dirichlet(np.ones(12), size=k)
                priors = rng.dirichlet(np.ones(k))
                tv = 0.5 * np.abs(laws[:, None, :] - laws[None, :, :]).sum(axis=-1)
                exact = 1 - (priors[:, None] * laws).max(axis=0).sum()
                self.assertLessEqual(tree_risk_bound(tv, priors)["lower_floor"], exact + 1e-12)

    def test_reject_invalid_probabilities_and_counts(self):
        for counts, priors in [([[1.5, 2], [3, 4]], [.5, .5]),
                               ([[0, 0], [3, 4]], [.5, .5]),
                               ([[1, 2], [3, 4]], [.7, .7])]:
            with self.assertRaises(ValueError):
                empirical_known_risk(counts, priors)

    def test_more_samples_tighten_bounds_on_fixed_identical_laws(self):
        small = direct_risk_bounds([[100, 100]] * 3, [1 / 3] * 3, alphabet_size=2)
        large = direct_risk_bounds([[10000, 10000]] * 3, [1 / 3] * 3, alphabet_size=2)
        for method in ["classwise", "joint"]:
            self.assertGreater(large[method]["lower_floor"], small[method]["lower_floor"])
            self.assertLessEqual(large[method]["lower_floor"], 2 / 3)

    def test_grouped_bound_reduces_to_individual_iid_bound(self):
        counts = np.array([[120, 80], [60, 340], [250, 50]])
        priors = np.array([0.2, 0.3, 0.4])
        ns = counts.sum(axis=1)
        individual_changes = np.repeat(priors / ns, ns)
        direct = direct_risk_bounds(counts, priors, alphabet_size=2)["joint"]
        grouped = grouped_joint_risk_bound(counts, priors, individual_changes)
        self.assertAlmostEqual(direct["radius"], grouped["radius"])
        self.assertAlmostEqual(direct["lower_floor"], grouped["lower_floor"])

    def test_shared_units_widen_joint_bound(self):
        counts = [[40, 60]] * 6
        priors = [1 / 7] * 6
        individual = direct_risk_bounds(counts, priors, alphabet_size=2)["joint"]
        grouped = grouped_joint_risk_bound(counts, priors, [sum(priors) / 100] * 100)
        self.assertAlmostEqual(grouped["radius"] / individual["radius"], np.sqrt(6))
        self.assertLess(grouped["lower_floor"], individual["lower_floor"])


if __name__ == "__main__":
    unittest.main()
