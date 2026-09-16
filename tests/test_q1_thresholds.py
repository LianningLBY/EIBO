# Regression tests for the Q1 gate thresholds.
#
# These pin the numbers that were once published WRONG (an alpha-split slip:
# alpha/2 was passed into a helper that halved alpha again, yielding
# alpha/4 per law and a doubly-conservative threshold). The values below are
# recomputed from the specification in scripts/evaluate_q1_absolute.py, so a
# change in the split, the quantile convention, or the radius sum will fail
# here instead of reaching a report.
#
# Run: PYTHONPATH=src python3 -m unittest tests.test_q1_thresholds -v

from __future__ import annotations

import importlib.util
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

_spec = importlib.util.spec_from_file_location(
    "evaluate_q1_absolute", ROOT / "scripts" / "evaluate_q1_absolute.py"
)
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)


class TestLowerThreshold(unittest.TestCase):
    """T(n): smallest channel TV whose two-cell lower bound exceeds 0.05."""

    # Corrected values (alpha/2 per law => joint 1-alpha).
    # The superseded table was 0.0659 / 0.0550 / 0.0522 / 0.0511.
    EXPECTED = {
        20_000: 0.0639,
        200_000: 0.0544,
        1_000_000: 0.0520,
        3_900_000: 0.0510,
    }

    def test_t_n_values(self):
        for n, want in self.EXPECTED.items():
            got = ev.t_of_n(n, n)
            self.assertAlmostEqual(
                got, want, places=4, msg=f"T({n}) = {got}, expected {want}"
            )

    def test_threshold_matches_definition(self):
        """T(n) must be the crossing point of eps_lo against 0.05."""
        for n in self.EXPECTED:
            t = ev.t_of_n(n, n)
            self.assertGreater(
                ev.eps_lo_two_cell(t, n, n), 0.05, f"eps_lo at T({n}) not > 0.05"
            )
            self.assertLessEqual(
                ev.eps_lo_two_cell(t - 1e-4, n, n),
                0.05,
                f"eps_lo just below T({n}) already > 0.05",
            )

    def test_not_doubly_conservative(self):
        """Guard the exact regression: the old alpha/4 split gave a HIGHER T.

        If the split silently reverts to alpha/4 per law, T rises ~3% at
        n=2e4 and these bounds fail.
        """
        t = ev.t_of_n(20_000, 20_000)
        self.assertLess(t, 0.0650, "T(2e4) looks like the alpha/4 (old) split")
        self.assertGreater(t, 0.0630, "T(2e4) unexpectedly low")

    def test_calibrated_constant(self):
        """T(n) ~ 0.05 + c/sqrt(n) with c ~ 1.958, not ~2.24."""
        for n in (20_000, 1_000_000, 3_900_000):
            c = (ev.t_of_n(n, n) - 0.05) * math.sqrt(n)
            self.assertGreater(c, 1.95)
            self.assertLess(c, 1.99)

    def test_unequal_n_is_handled_per_pair(self):
        """T must be computed per pair; the equal-n closed form is not used.

        The binding term is the less-precise law, so a mixed pair sits strictly
        between the two equal-n extremes: worse than (large, large) because one
        side is thin, better than (small, small) because the other side is good.
        """
        t_small = ev.t_of_n(20_000, 20_000)
        t_large = ev.t_of_n(200_000, 200_000)
        t_mixed = ev.t_of_n(20_000, 200_000)
        self.assertLess(t_mixed, t_small)
        self.assertGreater(t_mixed, t_large)


class TestUpperRadius(unittest.TestCase):
    """radius_sum(M, n): two-sided concentration radius at k=5.

    Uses per-law alpha/2 (joint 1-alpha), matching the lower side. The earlier
    values used per-law alpha (joint 0.90) and so claimed a different level on
    one side of the same gate; the shift is ~1e-4 and flips no verdict.
    """

    EXPECTED = {1: 0.0044, 2: 0.0177, 4: 0.0932, 8: 0.5200, 16: 2.9347}

    def test_radius_values(self):
        for M, want in self.EXPECTED.items():
            got = ev.radius_sum(M, 3_900_000, 3_900_000)
            self.assertAlmostEqual(
                got, want, places=4, msg=f"radius(M={M}) = {got}, expected {want}"
            )

    def test_radius_uses_two_sided_sum(self):
        """Must be r_1 + r_2, not a single-side radius (halving it)."""
        single = ev.radius_sum(1, 3_900_000, 3_900_000)
        m = (2 * 1) ** 5
        one_side = 0.5 * math.sqrt(m / 3_900_000) + 0.5 * math.sqrt(
            2 * math.log(2 / ev.ALPHA_PER_LAW) / 3_900_000
        )
        self.assertAlmostEqual(single, 2 * one_side, places=10)

    def test_both_sides_use_the_same_level(self):
        """Guard the asymmetry: upper and lower must share one convention.

        If the upper side silently reverts to per-law alpha while the lower
        keeps alpha/2, one gate claims joint 0.90 and 0.95 simultaneously.
        The unsplit alpha=0.05 call yields the SMALLER radius r=0.004239862, i.e.
        the narrower (less conservative) interval, which is the weaker guarantee;
        alpha/2 yields the larger radius r=0.004363524 and the stronger one.
        Default must be the alpha/2 convention, matching the lower side.
        """
        per_law_alpha = ev.radius_sum(1, 3_900_000, 3_900_000, alpha_per_law=ev.ALPHA)
        per_law_half = ev.radius_sum(1, 3_900_000, 3_900_000, alpha_per_law=ev.ALPHA_PER_LAW)
        self.assertLess(
            per_law_alpha, per_law_half,
            "the unsplit alpha=0.05 call gives the SMALLER radius, i.e. the "
            "narrower interval and the WEAKER guarantee (joint 0.90); alpha/2 "
            "gives the larger radius and the stronger guarantee (joint 0.95). "
            "Default must be alpha/2.",
        )
        # default must be the alpha/2 convention, matching the lower side
        self.assertAlmostEqual(
            ev.radius_sum(1, 3_900_000, 3_900_000), per_law_half, places=12
        )
        self.assertAlmostEqual(ev.ALPHA_PER_LAW, ev.ALPHA / 2, places=12)

    def test_guard_rejects_the_unsplit_constant(self):
        """The guard must REJECT the unsplit constant, not merely accept the split one."""
        import math
        C_split = math.sqrt(2 * math.log(2 / ev.ALPHA_PER_LAW))
        C_unsplit = math.sqrt(2 * math.log(1 / ev.ALPHA_PER_LAW))
        self.assertNotAlmostEqual(C_unsplit, C_split, places=6)
        self.assertLess(C_unsplit, C_split)  # the unsplit constant is weaker
        # the radius computed with the unsplit constant must NOT equal the pinned radius
        n = 3_900_000
        pinned = ev.radius_sum(1, n, n, alpha_per_law=ev.ALPHA_PER_LAW)
        # unsplit: per-law alpha = ALPHA (0.05), which is the wrong convention here
        wrong = ev.radius_sum(1, n, n, alpha_per_law=ev.ALPHA)
        self.assertNotAlmostEqual(pinned, wrong, places=6,
                                  msg="the unsplit convention must produce a different radius")

    def test_under_split_guard(self):
        """Reject the unsplit alpha=0.05 upper-side convention."""
        n = 3_900_000
        expected = ev.radius_sum(
            1, n, n, alpha_per_law=ev.ALPHA / 2
        )
        unsplit = ev.radius_sum(1, n, n, alpha_per_law=ev.ALPHA)
        self.assertAlmostEqual(
            ev.radius_sum(1, n, n), expected, places=12,
            msg="upper radius must use per-law alpha/2",
        )
        self.assertGreater(
            expected, unsplit,
            "the unsplit alpha=0.05 form must be rejected, not silently accepted",
        )
        self.assertNotAlmostEqual(expected, unsplit, places=12)

    def test_constant_is_pinned_to_its_joint_level(self):
        """A split slip must fail here, not be noticed by a person."""
        ALPHA, ALPHA_LAW = ev.ALPHA, ev.ALPHA_PER_LAW
        C = math.sqrt(2 * math.log(2 / ALPHA_LAW))
        per_law_tail = math.exp(-C * C / 2)
        self.assertAlmostEqual(per_law_tail, ALPHA_LAW / 2, places=12)
        self.assertAlmostEqual(per_law_tail, 0.0125, places=12)
        joint = 1 - 2 * per_law_tail
        self.assertAlmostEqual(joint, 1 - ALPHA_LAW, places=12)
        self.assertGreater(joint, 1 - 2 * ALPHA_LAW)
        unsplit = math.sqrt(2 * math.log(1 / ALPHA_LAW))
        self.assertLess(unsplit, C, "the unsplit constant is weaker and must be rejected")
        self.assertNotAlmostEqual(unsplit, C, places=6)


class TestRadiusIsKPerRow(unittest.TestCase):
    """The radius must use the row's OWN k, not a fixed k=5.

    The alphabet is (2M)^k, so scoring a k=10 row with the k=5 alphabet
    understates the radius by a factor sqrt((2M)^5) -- at M=2 that is 32x,
    which turns a lost certificate into an apparent pass. The count table
    carries k=5 AND k=10 rows, so this is not hypothetical.
    """

    def test_radius_grows_with_k(self):
        n = 3_900_000
        c = math.sqrt(2 * math.log(2 / ev.ALPHA_PER_LAW))
        for M in (1, 2, 4, 8, 16):
            r5 = ev.radius_sum(M, n, n, k=5)
            r10 = ev.radius_sum(M, n, n, k=10)
            self.assertGreater(r10, r5, f"M={M}: k=10 radius must exceed k=5")
            # radius = (sqrt((2M)^k) + c)/sqrt(n); the k=10/k=5 ratio therefore
            # approaches (2M)^2.5 but sits BELOW it, since the additive constant
            # is not negligible at small M (M=1: 4.06, not 5.66).
            want = ((2 * M) ** 5 + c) / (math.sqrt((2 * M) ** 5) + c)
            self.assertAlmostEqual(r10 / r5, want, places=6)
            self.assertGreater(r10 / r5, 3.0)

    def test_default_k_is_five(self):
        self.assertAlmostEqual(
            ev.radius_sum(2, 200_000, 200_000),
            ev.radius_sum(2, 200_000, 200_000, k=5),
            places=12,
        )
        self.assertEqual(ev.K_DEFAULT, 5)

    def test_evaluate_scores_each_k_with_its_own_alphabet(self):
        """A k=10 row must not borrow the k=5 radius.

        tv is chosen so the k=5 upper side passes and the k=10 upper side does
        not; if evaluate() ignores the row's k, both rungs report a pass.
        """
        tv = 0.30
        n = 3_900_000
        r5 = ev.radius_sum(4, n, n, k=5)
        r10 = ev.radius_sum(4, n, n, k=10)
        self.assertLess(tv, 0.5 - r5, "fixture: k=5 upper side should pass")
        self.assertGreater(tv, 0.5 - r10, "fixture: k=10 upper side should fail")

        table = {
            "label": "k-dispatch fixture",
            "pairs": [
                {"service_a": "a", "service_b": "b", "k": 5, "M": 4,
                 "n_a": n, "n_b": n, "tv_masked": tv},
                {"service_a": "c", "service_b": "d", "k": 10, "M": 4,
                 "n_a": n, "n_b": n, "tv_masked": tv},
            ],
        }
        rep = ev.evaluate(table)
        by_k = {
            r["k"]: r for r in rep["per_rung"]
            if r.get("M") == 4 and r.get("pairs")
        }
        self.assertEqual(set(by_k), {5, 10}, "both k blocks must be reported")
        self.assertEqual(by_k[5]["upper_side_pairs"], 1)
        self.assertEqual(by_k[10]["upper_side_pairs"], 0)
        self.assertGreater(by_k[10]["radius_median"], by_k[5]["radius_median"])

    def test_rows_without_k_fall_back_to_k_default(self):
        table = {
            "label": "legacy fixture",
            "pairs": [
                {"service_a": "a", "service_b": "b", "M": 2,
                 "n_a": 200_000, "n_b": 200_000, "tv_k5_masked": 0.20},
            ],
        }
        rep = ev.evaluate(table)
        row = next(r for r in rep["per_rung"] if r.get("pairs"))
        self.assertEqual(row["k"], ev.K_DEFAULT)
        self.assertAlmostEqual(
            row["radius_median"],
            ev.radius_sum(2, 200_000, 200_000, k=ev.K_DEFAULT),
            places=12,
        )


class TestGateSemantics(unittest.TestCase):
    """The gate is an ABSOLUTE comparison; no ratio may enter it."""

    def test_m8_and_m16_have_no_upper_certificate_at_corpus_mean(self):
        for M in (8, 16):
            self.assertGreaterEqual(
                ev.radius_sum(M, 3_900_000, 3_900_000),
                0.5,
                f"M={M} unexpectedly has an upper certificate at n=3.9e6",
            )

    def test_m1_window_is_empty_under_the_assumed_factor(self):
        """With comp(1)=0.02 < T(n), the lower side can never fire."""
        t = ev.t_of_n(3_900_000, 3_900_000)
        self.assertLess(0.02, t, "assumed comp(1) would clear T(n) -- check T")

    def test_evaluate_reports_both_sides_and_both(self):
        table = {
            "label": "regression fixture",
            "chosen_k": 10,
            "alt_k": 15,
            "pairs": [
                {"service_a": "a", "service_b": "b", "M": 4,
                 "n_a": 200_000, "n_b": 200_000, "tv_k5_masked": 0.20},
            ],
        }
        rep = ev.evaluate(table)
        row = next(r for r in rep["per_rung"] if r["M"] == 4)
        self.assertEqual(row["pairs"], 1)
        self.assertIn("lower_side_fraction", row)
        self.assertIn("upper_side_fraction", row)
        self.assertIn("gate_fraction_both", row)
        # tv=0.20 vs T~0.054: lower fires. radius(M=4, 2e5)=0.4108 => ceiling 0.089,
        # so 0.20 exceeds it and the upper side fails.
        self.assertEqual(row["gate_pairs_both"], 0)
        self.assertEqual(row["lower_side_pairs"], 1)
        self.assertEqual(row["upper_side_pairs"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
