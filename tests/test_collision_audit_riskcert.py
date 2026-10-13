"""Exact transfer identities, raw-value preservation and full HDF5 diagnostics."""

import argparse
import contextlib
import copy
import importlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from eibo.collisionaudit import (CollisionCounts, ExactMarginal, collision_analysis,
                                compare_marginals, matched_class_wrong, paired_transfers, reallocation)
from eibo.rolling import evaluate, rolling_experiment
from eibo.realdata import DAY, PreparationAudit
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling, read_cache
from methodology_real_reallocation import read_rolling, run as run_reallocation, validate_matched
from methodology_real_collision import run as run_collision
from test_rolling_riskcert import epoch, fixture_cache, refresh, write_fixture


class TestReallocation(unittest.TestCase):
    def test_same_flow_transfer_counts_and_rescue_harm(self):
        counts = np.array([[10, 20, 30, 40], [20, 10, 40, 30]])
        pair = paired_transfers(counts, np.array([0, 0, 1, 1]), np.array([0, 1, 0, 1]))
        np.testing.assert_array_equal(pair.sum(axis=2), [[30, 70], [30, 70]])
        np.testing.assert_array_equal(pair.sum(axis=1), [[40, 60], [60, 40]])
        self.assertEqual(pair[0, 1, 0], 30)  # rescued
        self.assertEqual(pair[0, 0, 1], 20)  # harmed

    def test_all_44_classes_and_confusion_contributions_reconcile(self):
        cache = fixture_cache()
        cache["known"] = np.arange(44)
        cache["priors"] = np.full(44, 1 / 45)
        for key in cache["counts"]:
            for rung in (1, 2):
                original = cache["counts"][key][rung]
                padded = np.zeros((44, original.shape[1]), dtype=np.int64)
                padded[:3] = original
                padded[3:, 0] = 100
                cache["counts"][key][rung] = padded
        refresh(cache)
        rolling = rolling_experiment(cache, repeats=0)
        matrices = {token: value["confusion"] for token, value in rolling["evaluations"].items()}
        result = reallocation(cache, rolling["predictions"], matrices)
        for summary in result["summary"]:
            rows = [row for row in result["classes"] if all(row[key] == summary[key] for key in ("scope", "target", "log_M", "model"))]
            self.assertEqual(len(rows), 44)
            self.assertAlmostEqual(sum(row["weighted_error_change"] for row in rows), summary["error_change"]["value"])
            cells = [row for row in result["confusion_changes"] if all(row[key] == summary[key] for key in ("scope", "target", "log_M", "model"))]
            self.assertEqual(len(cells), 44 * 44)
            self.assertAlmostEqual(sum(row["weighted_error_change"] for row in cells), summary["error_change"]["value"])
            for row in rows:
                self.assertAlmostEqual(row["weighted_error_change"], (row["harmed_count"] - row["rescued_count"]) / row["target_n"] / 45)

    def test_matched_replay_reproduces_original_and_missing_targets_stay_visible(self):
        cache = fixture_cache()
        key = "evaluation/2025-05"
        for rung in (1, 2):
            cache["counts"][key][rung][0] = 0
        refresh(cache)
        original = rolling_experiment(cache, repeats=3, seed=7)
        wrong = matched_class_wrong(cache, 3, 7)
        validate_matched(cache, {"focal_APP": 2, "rolling": original}, wrong)
        matrices = {token: values["confusion"] for token, values in original["evaluations"].items()}
        result = reallocation(cache, original["predictions"], matrices, matched=wrong)
        missing = [row for row in result["classes"] if row["target"] == key and row["APP"] == 1]
        self.assertTrue(all(row["weighted_error_change"] is None and row["sample_status"] == "missing" for row in missing))
        self.assertTrue(all(row["conditional_change_mean"] is None for row in result["matched_classes"] if row["target"] == key and row["APP"] == 1))

    def test_pooled_class_month_weights_can_reverse_monthly_macro_changes(self):
        keys = ["evaluation/2025-03", "evaluation/2025-04"]
        values = [np.array([[45, 0, 9, 36], [5, 0, 2, 3]]), np.array([[3, 2, 0, 5], [36, 9, 0, 45]])]
        cache = {"known": np.array([2, 34]), "priors": np.array([.25, .25]),
                 "slices": [{"key": key, "period": "evaluation"} for key in keys],
                 "counts": {key: {1: value, 2: value} for key, value in zip(keys, values)}}
        predictions, matrices = {}, {}
        for key in keys:
            for rung in (1, 2):
                for model in ("fixed_pilot", "rolling_1m", "rolling_3m"):
                    prediction = np.array([0, 0, 1, 1] if model == "fixed_pilot" else [0, 1, 0, 1])
                    predictions[(key, rung, model)] = prediction
                    matrices[(key, rung, model)] = evaluate(cache["counts"][key][rung], cache["priors"], prediction, 0)["confusion"]
        result = reallocation(cache, predictions, matrices)
        monthly = [row for row in result["summary"] if row["scope"] == "monthly"]
        self.assertTrue(all(row["error_change"]["value"] > 0 for row in monthly))
        pooled = next(row for row in result["summary"] if row["target"] == "evaluation" and row["log_M"] == 2 and row["model"] == "rolling_1m")
        self.assertAlmostEqual(pooled["error_change"]["value"], -.035)

    def test_cached_reallocation_cli_and_tamper_rejection(self):
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as tmp:
            monthly, rolling, output = (Path(tmp) / name for name in ("monthly", "rolling", "reallocation"))
            write_fixture(monthly)
            with contextlib.redirect_stdout(io.StringIO()):
                run_rolling(argparse.Namespace(monthly_dir=monthly, out_dir=rolling, app=2, reference_months=["2024-12", "2025-01"], matched_repeats=3, seed=7, small_n=200, top=3))
                run_reallocation(argparse.Namespace(monthly_dir=monthly, rolling_dir=rolling, out_dir=output, small_n=200, top=3))
            self.assertEqual(json.loads((output / "run.json").read_text())["status"], "complete")
            self.assertTrue((output / "matched_class_changes.csv").is_file())
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            (rolling / "confusion_matrices.json").write_text("[]")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_rolling(rolling, read_cache(monthly), monthly)


def raw_fixture():
    dates = [f"2024-{month:02d}-01" for month in range(6, 13)] + [f"2025-{month:02d}-01" for month in range(1, 6)] + ["2025-05-31"]
    tables, batches = [], []
    dtype = np.dtype([("APP", "i2"), ("PPI", "f8", (3, 30)), ("PPI_LEN", "u2"), ("TIME_FIRST", "f8"), ("TIME_LAST", "f8")])
    for index, date in enumerate(dates):
        day = epoch(date)
        rows = np.zeros(6, dtype=dtype)
        rows["APP"] = [2, 2, 2, 34, 34, 50]
        rows["TIME_FIRST"] = day + 3600
        rows["TIME_LAST"] = day + 3700
        rows["PPI_LEN"] = 5
        rows["PPI"][:, 1, :5] = [1, -1, 1, -1, -1]
        rows["PPI"][:, 2, :5] = [1200, 70 + index, 1000, 40, 1501 + index]
        rows["PPI"][3:5, 2, :5] = [1250, 1300, 1250, 1300, 1300]
        rows["PPI"][5, 2, :5] = 20
        rows["PPI"][:, 0, :5] = [0, 0, 1, 2, 10 + index]
        rows["PPI"][3:5, 0, :5] = [0, 10, 20, 30, 40]
        tables.append({"path": "/flows/D" + date.replace("-", ""), "rows": len(rows), "day_seconds": day, "ppi_capacity": 30})
        batches.append(rows)
    return tables, batches


class TestCollision(unittest.TestCase):
    def test_exact_distribution_quantiles_overflow_and_invalid_values(self):
        size = ExactMarginal(integer=True)
        size.add([39, 39, 1200, 1501, 2000])
        self.assertEqual(size.summary()["median"], 1200)
        self.assertEqual(size.summary()["q95"], 2000)
        self.assertAlmostEqual(size.summary()["fraction_gt_1500"], .4)
        timing = ExactMarginal()
        timing.add([0, 1, 1, -1, np.nan])
        self.assertEqual(timing.summary()["flows"], 5)
        self.assertEqual(timing.summary()["invalid_values"], 2)
        self.assertAlmostEqual(timing.summary()["zero_fraction"], 1 / 3)
        right = ExactMarginal()
        right.add([0, 2, 2])
        self.assertAlmostEqual(compare_marginals(timing, right)["empirical_TV"], 2 / 3)
        self.assertAlmostEqual(compare_marginals(timing, right)["empirical_CDF_sup_distance"], 2 / 3)

    def test_raw_cell_selection_keeps_population_and_invalid_IPT(self):
        tables, batches = raw_fixture()
        audit = PreparationAudit(tables, sample_size=0)
        batches[0]["PPI"][0, 0, 1] = -1
        for rows in batches:
            audit.add(rows, 30)
        counts = CollisionCounts(audit.plan(min_pilot_flows=1), tables, time_scale=1)
        for rows in batches:
            counts.add(rows, 30)
        for key in counts.monthly:
            for app in counts.apps:
                i = np.flatnonzero(counts.known == app)[0]
                self.assertEqual(counts.detail_counts[key][app], counts.monthly[key][2][i, 479])
        analysis = collision_analysis(counts)
        row = next(row for row in analysis["features"] if row["target"] == "pilot/2024-06" and row["APP"] == 2 and row["feature"] == "IPT_ms" and row["position"] == 2)
        self.assertEqual(row["flows"], 3)
        self.assertEqual(row["invalid_values"], 1)
        self.assertTrue(any(row["value"] > 1500 for row in analysis["distributions"] if row["feature"] == "size_bytes"))
        self.assertEqual({row["APP"] for row in analysis["occupancy"]}, {2, 34, 50})
        first = [row for row in analysis["comparisons"] if row["structural_first_IPT"]]
        self.assertTrue(all(row["empirical_TV"] in (0, None) for row in first))

    def test_full_HDF5_pipeline_and_raw_collision_reconciliation(self):
        for backend in ("tables", "h5py"):
            try:
                module = importlib.import_module(backend)
                break
            except ImportError:
                continue
        else:
            self.skipTest("HDF5 integration requires tables or h5py")
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as tmp:
            path, prepared, experiment, monthly, output = (Path(tmp) / name for name in ("fixture.h5", "prepared", "experiment", "monthly", "collision"))
            tables, batches = raw_fixture()
            if backend == "tables":
                with module.open_file(str(path), mode="w") as handle:
                    group = handle.create_group("/", "flows")
                    for table, rows in zip(tables, batches):
                        handle.create_table(group, table["path"].split("/")[-1], obj=rows)
            else:
                with module.File(path, "w") as handle:
                    for table, rows in zip(tables, batches):
                        handle.create_dataset(table["path"], data=rows)
            with contextlib.redirect_stdout(io.StringIO()):
                run_prepare(argparse.Namespace(h5=path, out_dir=prepared, backend=backend, sha256=True, expected_sha256=None, time_unit="seconds", k=5,
                    gap_seconds=DAY, rounding_seconds=3600, identifier_sample=0, seed=0, block_seconds=[3600, 21600, DAY], max_rows=None, chunk_rows=2, min_pilot_flows=1, alpha=.05))
                run_experiment(argparse.Namespace(h5=path, prepare_dir=prepared, out_dir=experiment, backend=backend, chunk_rows=2, block_seconds=[3600, 21600, DAY]))
                run_monthly(argparse.Namespace(h5=path, prepare_dir=prepared, experiment_dir=experiment, out_dir=monthly, backend=backend, chunk_rows=2, small_n=200, top=3))
                run_collision(argparse.Namespace(h5=path, prepare_dir=prepared, monthly_dir=monthly, out_dir=output, backend=backend,
                    symbol_id=479, apps=[2, 34], reference_months=["2024-12", "2025-01"], chunk_rows=2, small_n=200))
            result = json.loads((output / "summary.json").read_text())
            self.assertTrue(result["counts_reconciled"])
            self.assertEqual(result["decoded"], "C:39+ S:39+ C:39+ S:39+ S:39+")
            self.assertEqual(json.loads((output / "run.json").read_text())["rows_read"], 78)
            self.assertTrue((output / "distributions.csv").is_file())
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            cache = read_cache(monthly)
            changed = copy.deepcopy(cache)
            changed["counts"]["certificate/2025-02"][2][0, 479] += 1
            source_counts = CollisionCounts(cache["plan"], tables, time_scale=1)
            for rows in batches:
                source_counts.add(rows, 30)
            with self.assertRaisesRegex(ValueError, "raw monthly symbols"):
                source_counts.reconcile_cache(changed)


if __name__ == "__main__":
    unittest.main()
