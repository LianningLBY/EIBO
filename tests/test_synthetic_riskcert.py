"""Checks for known truth, correlated sampling, and MC uncertainty reporting."""

import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from eibo.riskcert import (empirical_known_risk, grouped_joint_risk_bound,
                           joint_radius_from_change_budget, tv_upper_bound, tree_risk_bound)
from eibo.synthetic import (batch_known_risk, failure_interval, make_case, markov_variance_factor,
                            merge_constant_runs, sample_counts, sample_counts_with_units)
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

    def test_observed_runs_only_merge_true_constant_segments(self):
        lengths = np.array([[2, 3, 1, 4, 0], [1, 2, 3, 0, 0]])
        labels = np.array([[0, 0, 1, 1, -1], [2, 2, 2, -1, -1]])
        observed = merge_constant_runs(lengths, labels)
        np.testing.assert_array_equal(observed, [[5, 5, 0, 0, 0], [6, 0, 0, 0, 0]])
        np.testing.assert_array_equal(observed.sum(axis=1), lengths.sum(axis=1))
        self.assertTrue(np.all((observed ** 2).sum(axis=1) >= (lengths ** 2).sum(axis=1)))
        with self.assertRaises(ValueError):
            merge_constant_runs([[1, 0, 2]], [[0, -1, 0]])

    def test_regeneration_retains_lengths_and_preserves_v1_markov_counts(self):
        case = make_case("zipf_6_1024")
        ns = 128 * case["sample_factors"]
        counts, info = sample_counts_with_units(np.random.default_rng(24), case, ns, 10, mode="markov", rho=0.9)
        legacy = sample_counts(np.random.default_rng(24), case, ns, 10, mode="markov", rho=0.9)
        np.testing.assert_array_equal(counts, legacy)
        changes = []
        for i, trace in enumerate(info["geometry_example"]["independent_services"]):
            lengths = np.array(trace["regeneration_lengths"])
            labels = np.array(trace["regeneration_labels"])
            self.assertEqual(lengths.sum(), ns[i])
            reconstructed = np.bincount(labels, weights=lengths, minlength=case["alphabet_size"])
            np.testing.assert_array_equal(counts[0, i], reconstructed)
            changes.extend(case["known_priors"][i] * lengths / ns[i])
        oracle = grouped_joint_risk_bound(counts[0], case["known_priors"], changes)
        batched_radius = joint_radius_from_change_budget(info["oracle_budget"])[0]
        self.assertAlmostEqual(oracle["radius"], batched_radius)
        self.assertTrue(np.all(info["observed_budget"] >= info["oracle_budget"] - 1e-12))

    def test_cross_service_units_preserve_v1_counts_and_include_cross_terms(self):
        case = make_case("private_6_32")
        ns = np.full(6, 128)
        counts, info = sample_counts_with_units(np.random.default_rng(26), case, ns, 10, mode="cross_service")
        legacy = sample_counts(np.random.default_rng(26), case, ns, 10, mode="cross_service")
        np.testing.assert_array_equal(counts, legacy)
        np.testing.assert_allclose(info["observed_budget"], 6 * info["separate_observed_budget"])
        np.testing.assert_allclose(info["oracle_budget"], case["known_priors"].sum() ** 2 / 128)

    def test_shared_regeneration_supports_unequal_priors_and_sample_lengths(self):
        case = make_case("private_6_32")
        case["known_priors"] = np.array([1, 2, 3, 4, 5, 6]) / 21 * 6 / 7
        ns = np.array([32, 64, 128, 32, 64, 128])
        counts, info = sample_counts_with_units(np.random.default_rng(28), case, ns, 12, mode="cross_markov", rho=0.9)
        np.testing.assert_array_equal(counts.sum(axis=2), np.tile(ns, (12, 1)))
        trace = info["geometry_example"]["shared_shocks"]
        lengths = np.array(trace["regeneration_lengths"])
        labels = np.array(trace["regeneration_labels"])
        sequence = np.repeat(labels, lengths)
        starts = np.cumsum(lengths) - lengths
        changes = np.zeros(len(lengths))
        for i, n in enumerate(ns):
            self.assertEqual(counts[0, i, 0], sequence[:n].sum())
            changes += case["known_priors"][i] * np.minimum(lengths, np.maximum(0, n - starts)) / n
        self.assertAlmostEqual(info["oracle_budget"][0], np.dot(changes, changes))
        self.assertTrue(np.all(info["observed_budget"] >= info["oracle_budget"] - 1e-12))

    def test_hidden_blocks_preserve_marginal_but_invalidate_run_domination(self):
        case = make_case("private_6_32")
        counts, info = sample_counts_with_units(np.random.default_rng(30), case, [128] * 6, 2000,
                                               mode="hidden_blocks", block_size=128)
        np.testing.assert_array_equal(counts.sum(axis=2), np.full((2000, 6), 128))
        self.assertLess(abs(counts[:, :, 0].mean() / 128 - 0.4), 0.03)
        self.assertTrue(np.any(info["observed_budget"] < info["oracle_budget"] - 1e-12))
        expected = np.sum(case["known_priors"] ** 2)
        np.testing.assert_allclose(info["oracle_budget"], expected)

    def test_regeneration_endpoint_has_one_independent_draw_per_service(self):
        case = make_case("private_6_32")
        counts, info = sample_counts_with_units(np.random.default_rng(32), case, [128] * 6, 20, mode="markov", rho=1)
        self.assertTrue(np.all((counts == 0) | (counts == 128)))
        np.testing.assert_allclose(info["oracle_budget"], np.sum(case["known_priors"] ** 2))
        np.testing.assert_array_equal(info["oracle_unit_counts"], np.full(20, 6))
        np.testing.assert_allclose(info["observed_budget"], info["oracle_budget"])

    def test_new_assumption_labels_reject_wrong_model_and_wrong_grouping(self):
        case = make_case("private_6_32")
        ns = np.full(6, 128)
        shared = prepare_methods(case, ns, {"mode": "cross_markov", "block_size": 1, "rho": 0.9}, 0.05, False, 8)
        self.assertTrue(shared["joint_oracle_shared_regeneration"]["assumptions_met"])
        self.assertTrue(shared["joint_observed_shared_runs"]["assumptions_met"])
        self.assertFalse(shared["joint_separate_run_heuristic"]["assumptions_met"])
        hidden = prepare_methods(case, ns, {"mode": "hidden_blocks", "block_size": 128, "rho": 0}, 0.05, False, 8)
        self.assertTrue(hidden["joint_oracle_hidden_blocks"]["assumptions_met"])
        self.assertFalse(hidden["joint_observed_runs"]["assumptions_met"])


if __name__ == "__main__":
    unittest.main()
