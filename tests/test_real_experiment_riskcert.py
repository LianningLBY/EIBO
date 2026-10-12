"""Canonical encoding, interval coarsening and honest temporal evaluation."""

import argparse
import contextlib
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
from eibo.realdata import DAY, PreparationAudit
from eibo.realexperiment import (FixedPrefixEncoder, RealExperimentCounts, TimeUnitGeometry,
                                 analyze_counts, classifier_metrics, fine_to_coarse_ids, histogram_predictions)
from eibo.statcore import quantize, symbol_to_id
from methodology_real_experiment import read_preparation, run as run_experiment
from methodology_real_prepare import run as run_prepare
from test_real_prepare_riskcert import BEGIN, rows, table_records


def coded_rows(day, services=(0, 1)):
    values = rows(day, services)
    values["PPI"][:, 1, :] = 1
    values["PPI"][:, 1, 1::2] = -1
    for i, service in enumerate(services):
        # Two laws distinguished by sizes only; change which size each class
        # uses in the late period. k=5 directions remain identical.
        size = 20 if (service == 0) == (day < 13) else 1200
        values["PPI"][i, 2, :] = size
    return values


class TestRealExperiment(unittest.TestCase):
    def test_lookup_matches_canonical_codec_and_ignores_padding(self):
        rng = np.random.default_rng(8)
        values = np.zeros((25, 3, 30), dtype=np.int64)
        values[:, 1, :5] = rng.choice([-1, 1], (25, 5))
        values[:, 2, :5] = rng.integers(1, 5000, (25, 5))
        for bins in (1, 2):
            codec = FixedPrefixEncoder(5, bins)
            expected = [symbol_to_id(quantize([(int(d < 0), int(s)) for d, s in zip(row[1, :5], row[2, :5])], 5, "log", log_bins=bins), "log", log_bins=bins) for row in values]
            np.testing.assert_array_equal(codec.encode(values), expected)
            values[:, :, 5:] = 12345  # invalid padding must never be observed
            np.testing.assert_array_equal(codec.encode(values), expected)

    def test_invalid_prefix_refused_without_silent_filtering(self):
        codec = FixedPrefixEncoder(5, 2)
        values = coded_rows(0)
        values["PPI"][0, 1, 0] = 0
        with self.assertRaisesRegex(ValueError, "direction"):
            codec.encode(values["PPI"])
        values = coded_rows(0)
        values["PPI"][0, 2, 0] = 0
        with self.assertRaisesRegex(ValueError, "size"):
            codec.encode(values["PPI"])

    def test_refinement_matches_two_encodings(self):
        values = coded_rows(0)
        fine = FixedPrefixEncoder(5, 2).encode(values["PPI"])
        coarse = FixedPrefixEncoder(5, 1).encode(values["PPI"])
        np.testing.assert_array_equal(fine_to_coarse_ids(5)[fine], coarse)

    def test_global_cross_service_budget_and_unselected_flow_bridge(self):
        geometry = TimeUnitGeometry((0, 10800), 2, [3600], 3600)
        # Two selected flows occupy distinct hours. An unselected flow touches
        # both hours and forces them into the same unit.
        geometry.add(np.array([0., 3600., 0.]), np.array([0., 3600., 1.]),
                     np.array([0., 3600.]), np.array([0, 1]))
        result = geometry.diagnostics(np.array([1/3, 1/3]), 0.05)[0]
        self.assertEqual(result["start_assigned_nonempty_blocks"], 2)
        self.assertEqual(result["span_merged_nonempty_units"], 1)
        self.assertAlmostEqual(result["start_assigned_squared_change_budget"], 2/9)
        self.assertAlmostEqual(result["span_merged_squared_change_budget"], 4/9)
        self.assertGreater(result["span_merged_radius_if_assumptions_hold"], result["start_assigned_radius_if_assumptions_hold"])

    def test_rounding_exact_end_does_not_merge_next_block(self):
        geometry = TimeUnitGeometry((0, 10800), 2, [3600], 3600)
        geometry.add(np.array([0., 3600.]), np.array([0., 3600.]),
                     np.array([0., 3600.]), np.array([0, 1]))
        result = geometry.diagnostics(np.array([1/3, 1/3]), 0.05)[0]
        self.assertEqual(result["merged_boundary_edges"], 0)
        self.assertEqual(result["span_merged_nonempty_units"], 2)

    def test_ties_and_unseen_symbols_are_fixed_by_pilot(self):
        pilot = np.array([[10, 0, 0], [0, 10, 0]])
        evaluation = np.array([[0, 0, 10], [10, 0, 0]])
        prior = np.array([1/3, 1/3])
        prediction, unseen = histogram_predictions(pilot, prior)
        np.testing.assert_array_equal(prediction, [0, 1, 0])
        result = classifier_metrics(evaluation, prior, prediction, unseen)
        self.assertAlmostEqual(result["known_weighted_error"], 1/3)
        self.assertAlmostEqual(result["known_weighted_unseen_symbol_mass"], 1/3)

    def test_temporal_drift_and_refinement_do_not_become_coverage(self):
        audit = PreparationAudit(table_records(), sample_size=0)
        for day in range(16):
            audit.add(coded_rows(day), 30)
        plan = audit.plan(min_pilot_flows=1)
        counts = RealExperimentCounts(plan, table_records(), time_scale=1, widths=[3600, DAY])
        for day in range(16):
            counts.add(coded_rows(day), 30)
        counts.reconcile(audit.period)
        summary = analyze_counts(counts)
        coarse, fine = summary["representations"]
        self.assertFalse(summary["assumptions_established"])
        self.assertNotIn("coverage", summary)
        self.assertAlmostEqual(coarse["periods"]["evaluation"]["empirical_known_bayes_risk"], 1/3)
        self.assertAlmostEqual(fine["periods"]["evaluation"]["empirical_known_bayes_risk"], 0)
        self.assertAlmostEqual(fine["periods"]["evaluation"]["pilot_classifier"]["known_weighted_error"], 2/3)
        self.assertAlmostEqual(fine["drift"]["certificate_to_evaluation"]["prior_weighted_empirical_tv"], 2/3)
        wrong = {p: dict(v) for p, v in audit.period.items()}
        wrong["pilot"][0] += 1
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            counts.reconcile(wrong)

    def test_complete_hdf_pipeline_hashes_and_manifest_tamper(self):
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
            path, prepared, out = Path(directory) / "fixture.h5", Path(directory) / "prepared", Path(directory) / "experiment"
            if backend == "tables":
                with module.open_file(str(path), mode="w") as handle:
                    group = handle.create_group("/", "flows")
                    for day, table in enumerate(table_records()):
                        handle.create_table(group, table["path"].split("/")[-1], obj=coded_rows(day))
            else:
                with module.File(path, "w") as handle:
                    for day, table in enumerate(table_records()):
                        handle.create_dataset(table["path"], data=coded_rows(day))
            args = argparse.Namespace(h5=path, out_dir=prepared, backend=backend, sha256=True, expected_sha256=None,
                                      time_unit="seconds", k=5, gap_seconds=DAY, rounding_seconds=3600,
                                      identifier_sample=10, seed=0, block_seconds=[3600, 21600, DAY],
                                      max_rows=None, chunk_rows=1, min_pilot_flows=1, alpha=0.05)
            with contextlib.redirect_stdout(io.StringIO()):
                run_prepare(args)
                run_experiment(argparse.Namespace(h5=path, prepare_dir=prepared, out_dir=out, backend=backend,
                                                  chunk_rows=3, block_seconds=[3600, 21600, DAY]))
            metadata = json.loads((out / "run.json").read_text())
            self.assertEqual(metadata["status"], "complete")
            self.assertEqual(metadata["rows_read"], 32)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(summary["known_service_codes"], [0, 1])
            self.assertAlmostEqual(summary["empirical_coarsening_loss_M1_minus_M2"]["evaluation"], 1/3)
            self.assertIn("1200-byte", (out / "report.md").read_text())
            (prepared / "audit.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_preparation(prepared)


if __name__ == "__main__":
    unittest.main()
