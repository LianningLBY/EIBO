"""Past-only calendar models, canonical decoding and focal attribution."""

import argparse
import contextlib
import copy
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from eibo.monthlydrift import analyze_months, month_slices
from eibo.realexperiment import PERIODS
from eibo.rolling import (MODELS, focal_attribution, month_index, project_fine, rolling_experiment,
                          subsample_counts, symbol_dictionary, training_window)
from eibo.statcore import quantize, symbol_to_id
from methodology_real_prepare import sha256
from methodology_real_rolling import read_cache, run


def epoch(value):
    return int(dt.datetime.fromisoformat(value).replace(tzinfo=dt.timezone.utc).timestamp())


def fixture_cache():
    windows = {"pilot": ("2024-06-01", "2024-11-30"), "certificate": ("2024-12-01", "2025-03-01"),
               "evaluation": ("2025-03-02", "2025-06-01")}
    plan = {"status": "prepared", "full_scan": True, "k": 1, "known_service_codes": [1, 2, 3],
            "known_prior_per_service": 0.25, "unknown_prior": 0.25,
            "source": {"path": "synthetic-fixture-only.h5", "bytes": 4096, "sha256": "f" * 64},
            "fixed_representations": [{"scheme": "log", "M": 1, "k": 1, "alphabet_size": 2},
                                      {"scheme": "log", "M": 2, "k": 1, "alphabet_size": 4}],
            "windows": {p: {"start_epoch": epoch(start), "end_epoch": epoch(stop)} for p, (start, stop) in windows.items()}}
    slices = month_slices(plan, [])
    values = {}
    for item in slices:
        before = item["month_utc"] < "2025-02"
        fine = np.array([[10, 70, 5, 15], [60, 5, 30, 5] if before else [15, 50, 5, 30], [5, 15, 10, 70]], dtype=np.int64)
        values[item["key"]] = {2: fine, 1: project_fine(fine, 1)}
    cache = {"plan": plan, "known": np.array([1, 2, 3]), "priors": np.full(3, 0.25), "slices": slices, "counts": values}
    refresh(cache)
    return cache


def refresh(cache):
    cache["period_counts"] = {p: {r: sum((cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == p),
                                       np.zeros_like(cache["counts"][cache["slices"][0]["key"]][r])) for r in (1, 2)} for p in PERIODS}


def write_fixture(directory):
    cache = fixture_cache()
    # Reuse the monthly stage's actual summary writer/analysis contract.
    experiment = SimpleNamespace(plan=cache["plan"], known=cache["known"], priors=cache["priors"],
        slices=cache["slices"], counts=cache["period_counts"], monthly=cache["counts"], encoders={1: None, 2: None},
        selected_days={item["key"]: set() for item in cache["slices"]})
    analysis = analyze_months(experiment)
    directory.mkdir()
    payloads = {"plan_snapshot.json": cache["plan"], "summary.json": analysis["summary"],
                "monthly_symbol_counts.json": {"known_service_codes": cache["known"].tolist(), "slices": cache["slices"],
                    "counts": {key: {str(r): matrix.tolist() for r, matrix in values.items()} for key, values in cache["counts"].items()}}}
    for name, payload in payloads.items():
        (directory / name).write_text(json.dumps(payload, allow_nan=False))
    run_metadata = {"status": "complete", "rows_read": sum(values[2].sum() for values in cache["counts"].values()).item(),
                    "source": cache["plan"]["source"],
                    "code": [{"path": str(ROOT / "src/eibo" / name), "sha256": sha256(ROOT / "src/eibo" / name)} for name in ("statcore.py", "realexperiment.py")],
                    "outputs": [{"path": name, "sha256": sha256(directory / name)} for name in payloads]}
    (directory / "run.json").write_text(json.dumps(run_metadata))
    return cache


class TestRolling(unittest.TestCase):
    def test_calendar_window_excludes_target_and_uses_exact_months(self):
        cache = fixture_cache()
        target = next(item for item in cache["slices"] if item["month_utc"] == "2025-03")
        one, three = (training_window(cache, target, model) for model in ("rolling_1m", "rolling_3m"))
        self.assertEqual(one["training_slices"], ["certificate/2025-02"])
        self.assertEqual(three["training_slices"], ["certificate/2024-12", "certificate/2025-01", "certificate/2025-02"])
        self.assertNotIn(target["key"], three["training_slices"])
        self.assertEqual(month_index("2025-01") - month_index("2024-12"), 1)

    def test_empty_latest_month_is_not_replaced_with_older_month(self):
        cache = fixture_cache()
        for r in (1, 2):
            cache["counts"]["pilot/2024-11"][r][:] = 0
        refresh(cache)
        target = next(item for item in cache["slices"] if item["month_utc"] == "2024-12")
        result = training_window(cache, target, "rolling_1m")
        self.assertEqual(result["training_slices"], ["pilot/2024-11"])
        self.assertEqual(result["status"], "unavailable_missing_training_classes")
        self.assertEqual(result["missing_training_services"], [1, 2, 3])

    def test_missing_training_class_keeps_model_unavailable(self):
        cache = fixture_cache()
        for r in (1, 2):
            cache["counts"]["certificate/2025-01"][r][2] = 0
        refresh(cache)
        result = rolling_experiment(cache, repeats=2)
        row = next(row for row in result["full"] if row["target"] == "certificate/2025-02" and row["model"] == "rolling_1m" and row["log_M"] == 2)
        self.assertIsNone(row["weighted_error"])
        self.assertEqual(row["missing_training_services"], [3])
        matched = next(row for row in result["matched"] if row["target"] == "certificate/2025-02")
        self.assertEqual(matched["repetitions"], 0)

    def test_future_changes_do_not_change_earlier_models_or_randomization(self):
        first = fixture_cache()
        second = copy.deepcopy(first)
        for r in (1, 2):
            second["counts"]["evaluation/2025-05"][r] *= 2
        refresh(second)
        left, right = (rolling_experiment(cache, repeats=3, seed=1) for cache in (first, second))
        for model in MODELS:
            token = ("certificate/2025-02", 2, model)
            np.testing.assert_array_equal(left["predictions"][token], right["predictions"][token])
            a = next(row for row in left["matched"] if row["target"] == token[0] and row["log_M"] == 2 and row["model"] == model)
            b = next(row for row in right["matched"] if row["target"] == token[0] and row["log_M"] == 2 and row["model"] == model)
            self.assertEqual(a, b)

    def test_without_replacement_counts_and_shared_refinement(self):
        counts = np.array([[10, 0, 20, 0], [0, 12, 4, 9]])
        budgets = np.array([10, 8])
        sampled = subsample_counts(counts, budgets, np.random.default_rng(9))
        self.assertTrue(np.all(sampled <= counts))
        np.testing.assert_array_equal(sampled.sum(axis=1), budgets)
        np.testing.assert_array_equal(project_fine(sampled, 1).sum(axis=1), budgets)
        class OldRng:
            def __init__(self):
                self.rng = np.random.default_rng(9)
            def hypergeometric(self, *args):
                return self.rng.hypergeometric(*args)
        fallback = subsample_counts(counts, budgets, OldRng())
        self.assertTrue(np.all(fallback <= counts))
        np.testing.assert_array_equal(fallback.sum(axis=1), budgets)

    def test_symbol_decode_uses_canonical_codec(self):
        digits, readable = symbol_dictionary(5, 2)
        flow = [(0, 20), (1, 1200), (0, 1501), (1, 38), (0, 39)]
        value = symbol_to_id(quantize(flow, 5, "log", log_bins=2), "log", log_bins=2)
        self.assertEqual(readable[value], "C:1-38 S:39+ C:39+ S:1-38 C:39+")
        np.testing.assert_array_equal(digits[value], [0, 3, 1, 2, 1])

    def test_focal_terms_sum_and_all_competitors_remain_included(self):
        cache = fixture_cache()
        rolling = rolling_experiment(cache, repeats=0)
        result = focal_attribution(cache, rolling, app=2)
        row = next(row for row in result["summary"] if row["target"] == "certificate/2025-02")
        self.assertAlmostEqual(row["weighted_pilot_error_change"], 0.175)
        self.assertAlmostEqual(row["weighted_oracle_distribution_term"], 0.175)
        self.assertAlmostEqual(row["weighted_oracle_reassignment_term"], 0.0125)
        self.assertAlmostEqual(row["signed_coarsening_contribution_change"], -0.1875)
        symbols = [row for row in result["symbols"] if row["target"] == "certificate/2025-02"]
        self.assertAlmostEqual(sum(row["TV_contribution"] for row in symbols), row["empirical_TV"])
        self.assertAlmostEqual(sum(row["weighted_pilot_error_change"] for row in symbols), 0.175)
        self.assertEqual({row["other_service_code"] for row in result["confusions"]}, {1, 2, 3})

    def test_chronology_guard_rejects_overlap(self):
        cache = fixture_cache()
        target = next(item for item in cache["slices"] if item["month_utc"] == "2024-12")
        cache["slices"][5]["end_epoch"] = target["start_epoch"] + 1
        with self.assertRaisesRegex(ValueError, "overlaps"):
            training_window(cache, target, "fixed_pilot")

    def test_cache_only_cli_pipeline_and_hash_validation(self):
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as directory:
            monthly, out = Path(directory) / "monthly", Path(directory) / "output"
            write_fixture(monthly)
            cache = read_cache(monthly)
            self.assertEqual(cache["known"].tolist(), [1, 2, 3])
            args = argparse.Namespace(monthly_dir=monthly, out_dir=out, app=2,
                reference_months=["2024-12", "2025-01"], matched_repeats=3, seed=1, small_n=200, top=3)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                run(args)
            self.assertIn("No H5 scan", output.getvalue())
            self.assertEqual(json.loads((out / "run.json").read_text())["status"], "complete")
            result = json.loads((out / "summary.json").read_text())
            self.assertEqual(len(result["rolling"]["full"]), 36)
            self.assertEqual(len(result["attribution"]["summary"]), 4)
            self.assertNotIn("NaN", (out / "summary.json").read_text())
            self.assertIn("not a population confidence", (out / "report.md").read_text())
            (monthly / "monthly_symbol_counts.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_cache(monthly)


if __name__ == "__main__":
    unittest.main()
