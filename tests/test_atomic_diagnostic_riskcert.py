"""Fine-atom opportunities, empirical oracle decomposition and cache lineage."""

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
from eibo.atomicdiagnostic import atomic_children, attribute_hierarchy, run_atomic_diagnostic
from eibo.hierarchy import run_hierarchy
from eibo.realdata import DAY
from eibo.rolling import project_fine
from methodology_real_atomic import candidate_precision, read_hierarchy, run
from methodology_real_hierarchy import read_refinement, run as run_hierarchy_cli
from methodology_real_refinement import run as run_refinement
from methodology_real_prepare import run as run_prepare, sha256
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling, read_cache
from test_refinement_riskcert import scan_fixture
from test_hierarchy_riskcert import competing_cache, run_competing


def middle_fixture():
    cache, _ = competing_cache()
    values = np.zeros((2, 4, 3, 3), dtype=np.int64)
    values[:, 0, 1, 0] = 20  # APP2 wins only the middle size interval.
    values[:, 1, 0, 0] = 30
    values[:, 1, 2, 0] = 30  # APP21 dominates both binary half-lines.
    values[:, 2, 0, 1], values[:, 2, 2, 1] = 40, 40
    values[:, 3, 0, 1] = 60
    base = np.zeros((4, 1024), dtype=np.int64)
    base[:, 479] = values[0].sum(axis=(1, 2))
    base[:, 1] = 100 - base[:, 479]
    cache["counts"] = {item["key"]: {2: base.copy(), 1: project_fine(base, 5)} for item in cache["slices"]}
    cache["period_counts"] = {period: {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == period)
                                        for r in (1, 2)} for period in ("pilot", "certificate", "evaluation")}
    atoms = {item["key"]: values.copy() for item in cache["slices"]}
    protocol = {"symbol_id": 479, "size_positions": [1, 2], "size_candidates_bytes": [500, 1200],
                "IPT2_candidates_ms": [4], "models": ["fixed_pilot", "rolling_1m", "rolling_3m"], "minimum_leaf_flows": 1}
    return cache, atoms, protocol


class TestAtomicDiagnostic(unittest.TestCase):
    def test_middle_interval_can_help_when_no_binary_candidate_helps(self):
        cache, atoms, protocol = middle_fixture()
        previous = run_hierarchy(cache, atoms, positions=(1, 2), size_cuts=(500, 1200), ipt_cuts=(4,), root_min_leaf=1, min_leaf=1)
        precision = candidate_precision(cache, previous)
        self.assertTrue(all(row["maximum_is_exact_zero"] for row in precision))
        self.assertTrue(all(row["APP2_positive_candidates"] == 0 for row in precision))
        result = run_atomic_diagnostic(cache, atoms, protocol, minimum=1)
        self.assertTrue(all(row["selected_size_position"] == 1 for row in result["choices"]))
        for row in result["monthly"]:
            if row["group"] == "selected_atomic":
                self.assertAlmostEqual(row["training_gain_vs_IPT"], .04)
                self.assertAlmostEqual(row["APP2_change_vs_IPT"], -.2)
                self.assertAlmostEqual(row["empirical_representation_gain"], .04)
                self.assertAlmostEqual(row["past_model_regret_to_atomic_oracle"], 0)
        self.assertTrue(any(row["target_APP2_winner"] and row["size_interval"] == "(500,1200] B" for row in result["APP2_cells"]))

    def test_sparse_atom_backoff_does_not_delete_future_flows(self):
        cache, atoms, protocol = middle_fixture()
        result = run_atomic_diagnostic(cache, atoms, protocol, minimum=25)
        # One-month middle atom has 20 flows: it falls back to APP21.
        rows = [r for r in result["monthly"] if r["model"] == "rolling_1m" and r["group"] == "position_atomic"]
        self.assertTrue(all(r["APP2_change_vs_IPT"] == 0 and r["backoff_target_flows"] == 20 for r in rows))
        self.assertTrue(all(abs(r["guard_error_change"]["value"] - .04) < 1e-12 and abs(r["APP2_guard_change"] - .2) < 1e-12 for r in rows))
        self.assertTrue(all(abs(r["past_model_regret_to_atomic_oracle"] - r["unguarded_past_regret"] - r["guard_error_change"]["value"]) < 1e-12 for r in rows))
        choices = [r for r in result["choices"] if r["model"] == "rolling_1m"]
        self.assertTrue(all(r["selected_size_position"] is None for r in choices))
        for row in result["confusions"]:
            np.testing.assert_array_equal(np.asarray(row["counts_true_by_predicted"]).sum(axis=1), cache["counts"][row["target"]][2].sum(axis=1))

    def test_future_drift_has_opportunity_but_past_classifier_regret(self):
        cache, atoms, protocol = middle_fixture()
        target = "evaluation/2025-03"
        # Counts stay fixed; future APP2 moves to the left, and APP21 enters
        # the middle atom that the past classifier assigns to APP2.
        atoms[target][:, 0, 0, 0], atoms[target][:, 0, 1, 0] = 20, 0
        atoms[target][:, 1, 0, 0], atoms[target][:, 1, 1, 0] = 0, 30
        result = run_atomic_diagnostic(cache, atoms, protocol, minimum=1)
        row = next(r for r in result["monthly"] if r["target"] == target and r["model"] == "fixed_pilot" and r["group"] == "selected_atomic")
        self.assertAlmostEqual(row["root_adaptation_gain"], 0)
        self.assertAlmostEqual(row["empirical_representation_gain"], .04)
        self.assertAlmostEqual(row["past_model_regret_to_atomic_oracle"], .10)
        self.assertAlmostEqual(row["error_change_vs_IPT"]["value"], .06)
        self.assertAlmostEqual(row["APP2_change_vs_IPT"], 0)
        self.assertAlmostEqual(row["APP2_atomic_oracle_change_vs_IPT"], -.2)

    def test_future_values_cannot_choose_position_or_training_score(self):
        cache, atoms, protocol = middle_fixture()
        left = run_atomic_diagnostic(cache, atoms, protocol, minimum=1)
        changed = copy.deepcopy(atoms)
        changed["evaluation/2025-05"] = changed["evaluation/2025-05"][:, :, ::-1, :].copy()
        right = run_atomic_diagnostic(cache, changed, protocol, minimum=1)
        self.assertEqual(left["choices"], right["choices"])
        self.assertEqual([r for r in left["monthly"] if r["target"] != "evaluation/2025-05"], [r for r in right["monthly"] if r["target"] != "evaluation/2025-05"])
        changed_cache = copy.deepcopy(cache)
        first = next(r for r in cache["slices"] if r["period"] == "certificate")
        changed_cache["slices"][5]["end_epoch"] = first["start_epoch"] + 1
        with self.assertRaisesRegex(ValueError, "overlaps"):
            run_atomic_diagnostic(changed_cache, atoms, protocol, minimum=1)

    def test_all44_classes_keep_priors_confusions_and_period_rows(self):
        cache, atoms, protocol = middle_fixture()
        old = cache["known"]
        extra = [app for app in range(1, 100) if app not in old][:40]
        known = np.array(sorted(old.tolist() + extra))
        index, other = np.searchsorted(known, old), np.searchsorted(known, extra)
        cache["known"], cache["priors"] = known, np.full(44, 1 / 45)
        for key in atoms:
            base = np.zeros((44, 1024), dtype=np.int64)
            base[index], base[other, 0] = cache["counts"][key][2], 100
            cache["counts"][key] = {2: base, 1: project_fine(base, 5)}
            full = np.zeros((2, 44, 3, 3), dtype=np.int64)
            full[:, index] = atoms[key]
            atoms[key] = full
        cache["period_counts"] = {period: {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == period)
                                            for r in (1, 2)} for period in ("pilot", "certificate", "evaluation")}
        result = run_atomic_diagnostic(cache, atoms, protocol, minimum=1)
        for r in result["periods"]:
            rows = [c for c in result["period_classes"] if (c["period"], c["model"], c["group"]) == (r["period"], r["model"], r["group"])]
            self.assertEqual([c["APP"] for c in rows], known.tolist())
            self.assertAlmostEqual(sum(c["weighted_change_vs_IPT"] for c in rows), r["error_change_vs_IPT"]["value"])
        for r in result["confusions"]:
            np.testing.assert_array_equal(np.asarray(r["counts_true_by_predicted"]).sum(axis=1), cache["counts"][r["target"]][2].sum(axis=1))
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_missing_target_prior_and_training_window_are_preserved(self):
        cache, atoms, protocol = middle_fixture()
        key = "evaluation/2025-04"
        cache["counts"][key][2][0] = 0
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        atoms[key][:, 0] = 0
        cache["period_counts"]["evaluation"] = {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == "evaluation") for r in (1, 2)}
        result = run_atomic_diagnostic(cache, atoms, protocol, minimum=1)
        row = next(r for r in result["monthly"] if r["target"] == key and r["model"] == "fixed_pilot" and r["group"] == "selected_atomic")
        self.assertIsNone(row["empirical_representation_gain"])
        self.assertEqual(row["weighted_error"]["unidentified_prior_mass"], .2)
        unavailable = next(r for r in result["choices"] if r["target"] == "evaluation/2025-05" and r["model"] == "rolling_1m")
        self.assertEqual(unavailable["status"], "unavailable_missing_training_classes")
        rows = [r for r in result["period_classes"] if r["period"] == "evaluation" and r["model"] == "rolling_1m" and r["group"] == "selected_atomic"]
        self.assertEqual([r["APP"] for r in rows], cache["known"].tolist())
        self.assertTrue(all(r["status"] == "unavailable_model" for r in rows))

    def test_macro_gain_and_raw_count_are_distinct_and_transfers_exact(self):
        cache, atoms = competing_cache()
        key = "evaluation/2025-03"
        cache["counts"][key][2][0, 1] = 0  # APP2 target n=30, while past n=100.
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        atoms[key][:, 1, 0, 0], atoms[key][:, 1, 1, 0] = 30, 30
        cache["period_counts"]["evaluation"] = {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == "evaluation") for r in (1, 2)}
        previous = run_competing(cache, atoms)
        audit = attribute_hierarchy(cache, previous)
        row = next(r for r in audit["summary"] if r["scope"] == "monthly" and r["target"] == key and r["model"] == "fixed_pilot")
        self.assertEqual(row["raw_rescued"], 30)
        self.assertEqual(row["raw_harmed"], 30)
        self.assertEqual(row["raw_error_change_count"], 0)
        self.assertAlmostEqual(row["weighted_change"]["value"], -.14)
        for r in audit["classes"]:
            self.assertEqual(r["harmed"] - r["rescued"], r["raw_wrong_change"])

    def test_precision_keeps_a_positive_value_hidden_by_previous_display(self):
        cache, _, _ = middle_fixture()
        target = "evaluation/2025-03"
        key = "certificate/2025-02"
        cache["counts"][key][2][0, 1] += 100000000 - 100
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        gain = .2 / 100000000
        previous = {"selections": [{"target": target, "model": "rolling_1m", "status": "ready", "best_eligible_APP2_training_gain": gain}],
                    "candidates": [{"target": target, "model": "rolling_1m", "eligible": True, "APP2_training_weighted_gain": gain}]}
        row = candidate_precision(cache, previous)[0]
        self.assertEqual(format(gain * 100, ".5f"), "0.00000")
        self.assertFalse(row["maximum_is_exact_zero"])
        self.assertEqual(row["APP2_positive_candidates"], 1)
        self.assertEqual(row["max_APP2_training_correct_change_count"], 1)

    def test_atomic_partition_preserves_invalid_and_high_branches(self):
        _, atoms, _ = middle_fixture()
        values = next(iter(atoms.values())).copy()
        values[:, 2, 0, 1] -= 10
        values[:, 2, 0, 2] += 10
        children, mapping = atomic_children(values, 0, {"atom_index": 0})
        np.testing.assert_array_equal(children.sum(axis=1), values[0].sum(axis=(1, 2)))
        np.testing.assert_array_equal(children[:, -2], values[0, :, :, 1].sum(axis=1))
        np.testing.assert_array_equal(children[:, -1], values[0, :, :, 2].sum(axis=1))
        np.testing.assert_array_equal(mapping, [0, 0, 0, 1, 2])

    def test_complete_cache_pipeline_and_hierarchy_tamper_rejection(self):
        for backend in ("tables", "h5py"):
            try:
                module = importlib.import_module(backend)
                break
            except ImportError:
                continue
        else:
            self.skipTest("HDF5 fixture creation requires tables or h5py")
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as tmp:
            path, prepared, experiment, monthly, rolling, refinement, hierarchy, output = (Path(tmp) / name for name in ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy", "atomic"))
            tables, batches, _, _ = scan_fixture()
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
                run_rolling(argparse.Namespace(monthly_dir=monthly, out_dir=rolling, app=2, reference_months=["2024-12", "2025-01"], matched_repeats=0, seed=7, small_n=200, top=3))
                run_refinement(argparse.Namespace(h5=path, prepare_dir=prepared, monthly_dir=monthly, rolling_dir=rolling, out_dir=refinement, backend=backend,
                    symbol_id=479, size_positions=None, size_cuts=[1000, 1200], ipt_cuts=[0, 4, 10], models=["fixed_pilot", "rolling_1m", "rolling_3m"], min_leaf_flows=1, chunk_rows=2, small_n=200))
                path.unlink()
                run_hierarchy_cli(argparse.Namespace(monthly_dir=monthly, refinement_dir=refinement, out_dir=hierarchy, min_leaf_flows=1, small_n=200))
                run(argparse.Namespace(monthly_dir=monthly, refinement_dir=refinement, hierarchy_dir=hierarchy, out_dir=output, min_atom_flows=1, small_n=200))
            summary = json.loads((output / "summary.json").read_text())
            self.assertTrue(summary["stage8_stage9_reproduced"])
            self.assertFalse(summary["raw_H5_rescan"])
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertEqual(json.loads((output / "run.json").read_text())["status"], "complete")
            self.assertEqual(len(summary["choices"]), 18)
            self.assertIn("No pooled oracle", (output / "report.md").read_text())
            for name in ("binary_candidate_precision.csv", "APP2_atomic_cells.csv", "hierarchy_attribution.csv", "atomic_period_classes.csv"):
                self.assertTrue((output / name).is_file())
            cache = read_cache(monthly)
            atoms, protocol, _ = read_refinement(refinement, cache, monthly)
            original = (hierarchy / "summary.json").read_text()
            (hierarchy / "summary.json").write_text(original + " ")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_hierarchy(hierarchy, cache, atoms, protocol, monthly, refinement)
            (hierarchy / "summary.json").write_text(original)
            saved = json.loads(original)
            saved["monthly"][0]["APP2_error"] += .01
            (hierarchy / "summary.json").write_text(json.dumps(saved))
            metadata = json.loads((hierarchy / "run.json").read_text())
            next(item for item in metadata["outputs"] if item["path"] == "summary.json")["sha256"] = sha256(hierarchy / "summary.json")
            (hierarchy / "run.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError, "replay metric"):
                read_hierarchy(hierarchy, cache, atoms, protocol, monthly, refinement)


if __name__ == "__main__":
    unittest.main()
