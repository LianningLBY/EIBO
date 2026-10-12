"""Missing classes, calendar boundaries and empirical drift identities."""

import argparse
import contextlib
import datetime as dt
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
sys.path.insert(0, str(ROOT / "tests"))
from eibo.monthlydrift import (MonthlyDriftCounts, analyze_months, compare_metrics, month_slices,
                               representation_metrics, slice_metrics)
from eibo.realdata import DAY, PreparationAudit
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import read_previous, run as run_monthly
from methodology_real_prepare import run as run_prepare
from test_real_experiment_riskcert import coded_rows
from test_real_prepare_riskcert import BEGIN, table_records


def longer_tables(days=92):
    return [{"path": "/flows/D" + dt.datetime.fromtimestamp(BEGIN + day * DAY, dt.timezone.utc).strftime("%Y%m%d"),
             "rows": 2, "day_seconds": BEGIN + day * DAY, "ppi_capacity": 30} for day in range(days)]


class TestMonthlyDrift(unittest.TestCase):
    def test_calendar_leap_year_and_missing_months_preserved(self):
        begin = int(dt.datetime(2023, 12, 1, tzinfo=dt.timezone.utc).timestamp())
        end = int(dt.datetime(2024, 4, 1, tzinfo=dt.timezone.utc).timestamp())
        tables = [{"day_seconds": begin}, {"day_seconds": end - DAY}]
        audit = PreparationAudit(tables, sample_size=0)
        slices = month_slices(audit.plan(min_pilot_flows=1), tables)
        february = next(item for item in slices if item["month_utc"] == "2024-02")
        self.assertEqual(february["calendar_days"], 29)
        self.assertEqual(february["available_table_days"], 0)
        self.assertIn("2024-02-29", february["missing_table_dates"])

    def test_month_assignment_keeps_whole_period_population(self):
        tables = longer_tables()
        audit = PreparationAudit(tables, sample_size=0)
        records = [coded_rows(day) for day in (0, 47, 70)]
        crossing = coded_rows(29)
        crossing["TIME_FIRST"] = BEGIN + 29 * DAY + 23 * 3600
        crossing["TIME_LAST"] = crossing["TIME_FIRST"] + 100
        records.append(crossing)
        for values in records:
            audit.add(values, 30)
        counts = MonthlyDriftCounts(audit.plan(min_pilot_flows=1), tables, time_scale=1)
        for values in records:
            counts.add(values, 30)
        counts.reconcile(audit.period)
        counts.reconcile_months(counts.counts)
        # June-ending intervals extend into July under rounding, but remain in
        # pilot. They must not be discarded by a new monthly interval filter.
        self.assertEqual(counts.monthly["pilot/2024-06"][1].sum(), 4)
        self.assertEqual(counts.monthly["pilot/2024-07"][1].sum(), 0)
        result = analyze_months(counts)
        empty = next(row for row in result["summary"]["monthly"] if row["slice"] == "pilot/2024-07" and row["log_M"] == 2)
        self.assertEqual(empty["missing_service_codes"], [0, 1])
        self.assertIsNone(empty["empirical_F"])
        self.assertIsNone(empty["pilot_classifier"]["value"])
        adjacent = [row for row in result["summary"]["comparisons"] if row["scope"] == "previous_time_slice" and row["log_M"] == 2]
        self.assertEqual(len(adjacent), len(counts.slices) - 1)
        self.assertTrue(any(row["source"] == "pilot/2024-07" for row in adjacent))

    def test_missing_class_has_no_oracle_or_renormalized_risk(self):
        prior = np.array([1/3, 1/3])
        pilot = np.array([[10, 0], [0, 10]])
        target = np.array([[4, 0], [0, 0]])
        left = slice_metrics(pilot, pilot, pilot, prior)
        right = slice_metrics(target, pilot, pilot, prior)
        self.assertIsNone(right["empirical_F"])
        self.assertTrue(np.isnan(right["oracle_error"]).all())
        result = compare_metrics(left, right, prior)
        self.assertIsNone(result["aggregate"]["empirical_tv"]["value"])
        np.testing.assert_allclose(result["aggregate"]["empirical_tv"]["range_from_unobserved_values"], [0, 1/3])
        # An unavailable per-class gap change may lie in [-2,2], not [-1,1].
        np.testing.assert_allclose(result["aggregate"]["empirical_gap_change"]["range_from_unobserved_values"], [-4/3, 4/3])

    def test_class_specific_novelty_can_be_large_with_no_global_novelty(self):
        prior = np.array([1/3, 1/3])
        pilot = np.array([[10, 0, 0], [0, 10, 0]])
        target = np.array([[0, 10, 0], [10, 0, 0]])
        result = slice_metrics(target, pilot, pilot, prior)
        np.testing.assert_array_equal(result["global_unseen"], [0, 0])
        np.testing.assert_array_equal(result["class_unseen"], [1, 1])
        self.assertAlmostEqual(result["decision_switch_mass"], 2/3)
        self.assertAlmostEqual(result["empirical_F"], 0)

    def test_error_cancellation_and_F_gap_identity(self):
        prior = np.array([1/3, 1/3])
        pilot = np.array([[10, 0], [0, 10]])
        source = np.array([[0, 10], [0, 10]])
        target = np.array([[10, 0], [10, 0]])
        left, right = (slice_metrics(values, pilot, pilot, prior) for values in (source, target))
        result = compare_metrics(left, right, prior)
        aggregate = result["aggregate"]
        self.assertAlmostEqual(aggregate["pilot_error_change"]["value"], 0)
        self.assertAlmostEqual(aggregate["positive_error_contributions"], 1/3)
        self.assertAlmostEqual(aggregate["negative_error_contributions"], -1/3)
        self.assertAlmostEqual(aggregate["empirical_tv"]["value"], 2/3)
        np.testing.assert_allclose(result["delta_error"], result["delta_F"] + result["delta_gap"])

    def test_class_coarsening_contributions_are_signed(self):
        prior = np.array([1/3, 1/3])
        coarse = np.array([[5], [5]])
        fine = np.array([[1, 4], [4, 1]])
        left = slice_metrics(coarse, coarse, coarse, prior)
        right = slice_metrics(fine, fine, fine, prior)
        result = representation_metrics(left, right, prior)
        self.assertLess(result["signed_coarsening_contribution"][0], 0)
        self.assertAlmostEqual(result["empirical_coarsening_loss"], 0.2)

    def test_small_n_is_a_flag_not_a_selection_rule(self):
        audit = PreparationAudit(table_records(), sample_size=0)
        for day in range(16):
            audit.add(coded_rows(day), 30)
        counts = MonthlyDriftCounts(audit.plan(min_pilot_flows=1), table_records(), time_scale=1)
        for day in range(16):
            counts.add(coded_rows(day), 30)
        result = analyze_months(counts, small_n=10000)
        self.assertEqual(result["summary"]["known_service_codes"], [0, 1])
        self.assertTrue(all(row["sample_status"] == "small_n" for row in result["class_rows"]))
        self.assertTrue(all(item["empirical_F"] is not None for item in result["summary"]["monthly"]))
        # Three disjoint June slices must not be pooled into a single month.
        self.assertEqual(len(counts.slices), 3)

    def test_three_stage_hdf_pipeline_reconciles_previous_bytes(self):
        for backend in ("tables", "h5py"):
            try:
                module = importlib.import_module(backend)
                break
            except ImportError:
                continue
        else:
            self.skipTest("HDF5 integration requires tables or h5py")
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as directory:
            path, prepared, previous, out = (Path(directory) / name for name in ("fixture.h5", "prepared", "previous", "monthly"))
            if backend == "tables":
                with module.open_file(str(path), mode="w") as handle:
                    group = handle.create_group("/", "flows")
                    for day, table in enumerate(table_records()):
                        handle.create_table(group, table["path"].split("/")[-1], obj=coded_rows(day))
            else:
                with module.File(path, "w") as handle:
                    for day, table in enumerate(table_records()):
                        handle.create_dataset(table["path"], data=coded_rows(day))
            preparation = argparse.Namespace(h5=path, out_dir=prepared, backend=backend, sha256=True, expected_sha256=None,
                time_unit="seconds", k=5, gap_seconds=DAY, rounding_seconds=3600, identifier_sample=0,
                seed=0, block_seconds=[3600, 21600, DAY], max_rows=None, chunk_rows=2, min_pilot_flows=1, alpha=0.05)
            with contextlib.redirect_stdout(io.StringIO()):
                run_prepare(preparation)
                run_experiment(argparse.Namespace(h5=path, prepare_dir=prepared, out_dir=previous, backend=backend, chunk_rows=3, block_seconds=[3600, 21600, DAY]))
                run_monthly(argparse.Namespace(h5=path, prepare_dir=prepared, experiment_dir=previous, out_dir=out, backend=backend, chunk_rows=5, small_n=200, top=3))
            self.assertEqual(json.loads((out / "run.json").read_text())["status"], "complete")
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(len(summary["monthly"]), 6)
            self.assertAlmostEqual(summary["period_coarsening_loss"]["evaluation"], 1/3)
            self.assertNotIn("NaN", (out / "summary.json").read_text())
            self.assertIn("sampling confidence", (out / "report.md").read_text())
            snapshot = json.loads((previous / "plan_snapshot.json").read_text())
            (previous / "symbol_counts.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_previous(previous, snapshot)


if __name__ == "__main__":
    unittest.main()
