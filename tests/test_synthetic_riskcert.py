"""Checks for known truth, correlated sampling, and MC uncertainty reporting."""

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from eibo.riskcert import empirical_known_risk, tv_upper_bound, tree_risk_bound
from eibo.synthetic import batch_known_risk, failure_interval, make_case, markov_variance_factor, sample_counts
from methodology_synthetic import finalize_intervals, prepare_methods, stable_seed, tree_floors


class TestSyntheticRiskcert(unittest.TestCase):
    def test_private_common_exact_risk_and_declared_zero_cells(self):
        case = make_case("private_45_64")
        p = case["known_priors"]
        self.assertAlmostEqual(case["true_known_risk"], 0.4 * (p.sum() - p.max()))
        self.assertEqual(case["laws"].shape, (45, 64))
        self.assertEqual(np.count_nonzero(case["laws"][:, 46:]), 0)

    def test_repeated_blocks_match_iid_representatives_exactly(self):
        case = make_case("zipf_6_1024")
        ns = 64 * case["sample_factors"]
        blocks = sample_counts(np.random.default_rng(10), case, ns, 10, mode="block", block_size=8)
        representatives = sample_counts(np.random.default_rng(10), case, ns // 8, 10)
        np.testing.assert_array_equal(blocks, representatives * 8)
        np.testing.assert_allclose(batch_known_risk(blocks, case["known_priors"]),
                                   batch_known_risk(representatives, case["known_priors"]))
        with self.assertRaises(ValueError):
            sample_counts(np.random.default_rng(10), case, ns + 1, 2, mode="block", block_size=8)

    def test_shared_shocks_keep_per_service_marginals_and_equal_common_counts(self):
        case = make_case("private_6_32")
        counts = sample_counts(np.random.default_rng(12), case, [64] * 6, 8, mode="cross_service")
        np.testing.assert_array_equal(counts[:, :, 0], np.repeat(counts[:, :1, 0], 6, axis=1))
        for i in range(6):
            np.testing.assert_array_equal(counts[:, i, 0] + counts[:, i, i + 1], [64] * 8)
        self.assertEqual(np.count_nonzero(counts[:, :, 7:]), 0)

    def test_stationary_markov_endpoints_and_sample_conservation(self):
        case = make_case("private_6_32")
        for rho in (0, 0.9, 0.99, 1):
            counts = sample_counts(np.random.default_rng(14), case, [128] * 6, 9, mode="markov", rho=rho)
            np.testing.assert_array_equal(counts.sum(axis=2), np.full((9, 6), 128))
            if rho == 1:
                np.testing.assert_array_equal(np.count_nonzero(counts, axis=2), np.ones((9, 6)))
                self.assertTrue(np.all((counts == 0) | (counts == 128)))
        self.assertAlmostEqual(markov_variance_factor(64, 0), 1)
        self.assertAlmostEqual(markov_variance_factor(64, 1), 64)

    def test_stationary_markov_mean_and_variance_match_known_law(self):
        case = make_case("private_6_32")
        n, trials, rho = 128, 8000, 0.9
        counts = sample_counts(np.random.default_rng(20261012), case, [n] * 6, trials, mode="markov", rho=rho)
        proportions = counts[:, :, 0] / n
        expected_variance = 0.4 * 0.6 * markov_variance_factor(n, rho) / n
        # Fixed seed; six standard errors protects against MC noise while
        # detecting a wrong initial state or a nonstationary generator.
        self.assertTrue(np.all(np.abs(proportions.mean(axis=0) - 0.4) < 6 * np.sqrt(expected_variance / trials)))
        self.assertLess(abs(proportions.var(axis=0, ddof=1).mean() / expected_variance - 1), 0.08)

    def test_batched_risk_matches_reference(self):
        case = make_case("separated_6_32")
        counts = sample_counts(np.random.default_rng(16), case, 128 * case["sample_factors"], 8)
        values = batch_known_risk(counts, case["known_priors"])
        for row, value in zip(counts, values):
            self.assertAlmostEqual(value, empirical_known_risk(row, case["known_priors"]))

    def test_exact_binomial_interval_endpoints_and_mc_verdict(self):
        self.assertAlmostEqual(failure_interval(0, 100)[1], 1 - 0.025 ** 0.01)
        self.assertAlmostEqual(failure_interval(100, 100)[0], 0.025 ** 0.01)
        rows = [{"failures": count, "trials": 2000, "nominal_failure_budget": 0.05} for count in (0, 1000, 100)]
        finalize_intervals(rows, 0.05)
        self.assertEqual([row["mc_verdict"] for row in rows],
                         ["failure_rate_below_budget_on_this_fixed_case", "failure_rate_above_budget", "inconclusive"])

    def test_assumption_labels_and_seed_are_fixed_before_sampling(self):
        case = make_case("private_6_32")
        ns = np.full(6, 128)
        methods = prepare_methods(case, ns, {"mode": "cross_service", "block_size": 1, "rho": 0}, 0.05, True, 8)
        self.assertTrue(methods["classwise_naive"]["assumptions_met"])
        self.assertTrue(methods["tree_naive"]["assumptions_met"])
        self.assertTrue(methods["joint_oracle_shared_units"]["assumptions_met"])
        self.assertFalse(methods["joint_naive"]["assumptions_met"])
        a = np.random.default_rng(stable_seed(20, "cell-a")).integers(0, 10000, size=10)
        b = np.random.default_rng(stable_seed(20, "cell-a")).integers(0, 10000, size=10)
        np.testing.assert_array_equal(a, b)

    def test_batch_tree_agrees_with_canonical_pair_bounds(self):
        case = make_case("private_6_32")
        counts = sample_counts(np.random.default_rng(22), case, [128] * 6, 1)[0]
        methods = prepare_methods(case, np.full(6, 128), {"mode": "iid", "block_size": 1, "rho": 0}, 0.05, True, 8)
        upper = np.zeros((6, 6))
        for i in range(6):
            for j in range(i + 1, 6):
                a = np.repeat(np.arange(32), counts[i])
                b = np.repeat(np.arange(32), counts[j])
                upper[i, j] = upper[j, i] = tv_upper_bound(a, b, alphabet_size=32, alpha=0.05 / 15).eps_hi
        scalar = tree_risk_bound(upper, case["known_priors"])["lower_floor"]
        batched = tree_floors(counts[None], case["known_priors"], methods["tree_naive"]["pair_radii"])[0]
        self.assertAlmostEqual(scalar, batched)


if __name__ == "__main__":
    unittest.main()
