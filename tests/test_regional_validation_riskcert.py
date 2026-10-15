"""Exact regional cancellation, outside data tradeoffs and no-raw-data replay."""

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
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from eibo.regionalvalidation import BACKGROUNDS, run_regional, splice_background
from eibo.jointrefinement import MATCHED_GROUPS, root_model, run_joint, time_children
from eibo.refinement import refine_counts
from eibo.rolling import evaluate, project_fine
from eibo.realdata import DAY
from methodology_real_regional import run
from methodology_real_joint import run as run_joint_cli, collection_protocol
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run as run_refinement
from methodology_real_hierarchy import run as run_hierarchy
from test_joint_diagnostic_riskcert import fixture, selection_protocol
from test_joint_refinement_riskcert import MODELS, protocol, refresh
from test_refinement_riskcert import scan_fixture


def shifted_fixture():
    cache, atoms, joints, roles, collection, _ = fixture()
    for token in {c["fit_id"] for c in collection["window_spec"]["contexts"]}:
        roles[token]["base"][0, 2], roles[token]["base"][0, 1] = roles[token]["base"][0, 1], 0
    replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
    return cache, atoms, joints, roles, collection, replay


def regional(values):
    cache, atoms, joints, roles, collection, replay = values
    return run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay)


class TestRegionalValidation(unittest.TestCase):
    def test_splice_changes_only_original_outside_symbols(self):
        local, full = np.array([0, 1, 2, 3, 0, 1]), np.array([3, 2, 1, 0, 3, 2])
        combined = splice_background(local, full, 4, 1)
        np.testing.assert_array_equal(combined, [3, 1, 1, 0, 0, 1])
        np.testing.assert_array_equal(local, [0, 1, 2, 3, 0, 1])
        with self.assertRaises(ValueError):
            splice_background(local, full[:-1], 4, 1)

    def test_full_confusion_deltas_and_all_populations_are_preserved(self):
        values = shifted_fixture()
        cache, _, _, _, _, replay = values
        result = regional(values)
        self.assertEqual(len(result["invariants"]), 18 * 5)
        original = {(r["target"], r["model"], r["group"]): np.asarray(r["counts_true_by_predicted"]) for r in replay["confusions"]}
        matrices = {(r["target"], r["model"], r["background"], r["group"]): np.asarray(r["counts_true_by_predicted"]) for r in result["confusions"]}
        for r in result["confusions"]:
            np.testing.assert_array_equal(np.asarray(r["counts_true_by_predicted"]).sum(axis=1), cache["counts"][r["target"]][2].sum(axis=1))
            if r["background"] == "fit_subset":
                np.testing.assert_array_equal(r["counts_true_by_predicted"], original[r["target"], r["model"], r["group"]])
        for target in [s["key"] for s in cache["slices"] if s["period"] != "pilot"]:
            for model in MODELS:
                for group in MATCHED_GROUPS:
                    a = matrices[target, model, "fit_subset", group] - matrices[target, model, "fit_subset", "time_fit"]
                    b = matrices[target, model, "full_past", group] - matrices[target, model, "full_past", "time_fit"]
                    np.testing.assert_array_equal(a, b)
        self.assertTrue(all(r["local_harmed"] == 0 for r in result["classes"] if r["APP"] == 34))

    def test_outside_APP2_restoration_and_symbol_counts_reconcile(self):
        result = regional(shifted_fixture())
        for r in result["metrics"]:
            if r["scope"] == "period" and r["background"] == "full_past" and r["group"] == "time_fit":
                focal = next(c for c in result["classes"] if all(c[k] == r[k] for k in ("scope", "target", "model", "background", "group")) and c["APP"] == 2)
                self.assertEqual(focal["wrong_change_vs_subset_same_group"], -900)
                self.assertEqual(focal["wrong_change_vs_full_past_time"], 0)
        for r in result["outside_effects"]:
            if r["APP"] == 2:
                self.assertEqual(r["wrong_change"], -300)
                symbols = [v for v in result["APP2_outside_symbols"] if (v["target"], v["model"]) == (r["target"], r["model"])]
                self.assertEqual(sum(v["APP2_wrong_change"] for v in symbols), r["wrong_change"])

    def test_full_past_outside_can_harm_a_class(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        for key in cache["counts"]:
            atoms[key][:, 3, 1, 2] = 100
            cache["counts"][key][2][3, 479], cache["counts"][key][2][3, 1] = 100, 400
            cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        refresh(cache)
        fitting = {c["fit_id"] for c in collection["window_spec"]["contexts"]}
        for token, role in roles.items():
            role["base"][3] = 0
            high, outside = (60, 40) if token in fitting else (40, 360)
            role["base"][3, 479], role["base"][3, 1] = high, outside
            role["children"][3, 1] = high
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        result = run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay)
        self.assertTrue(all(r["wrong_change"] == 300 for r in result["outside_effects"] if r["APP"] == 2))
        self.assertTrue(all(r["APP34_local_no_harm"] for r in result["invariants"]))

    def test_only_local_validation_increments_are_exported(self):
        cache, _, _, _, _, replay = shifted_fixture()
        result = regional(shifted_fixture())
        choices = {(r["target"], r["model"], r["group"]): r for r in replay["selections"]}
        for r in result["validation_increments"]:
            self.assertTrue(r["both_backgrounds_identical"])
            self.assertNotIn("error", r)
            self.assertNotIn("wrong", r)
            if r["group"] == "validation_constrained":
                rule = choices[r["target"], r["model"], r["group"]]["rule"]
                if r["APP"] == 21:
                    self.assertAlmostEqual(r["conditional_increment"], rule["APP21_validation_conditional_change"])
        # The background can change absolute APP21 errors while its local increment stays zero.
        focal = [r for r in result["classes"] if r["scope"] == "monthly" and r["background"] == "full_past" and r["group"] == "validation_constrained" and r["APP"] == 21]
        self.assertTrue(all(r["wrong_change_vs_subset_same_group"] == 250 and r["wrong_change_vs_same_background_time"] == 0 for r in focal))
        self.assertEqual(cache["known"].tolist(), [2, 21, 34, 50])

    def test_future_changes_do_not_change_local_validation(self):
        values = shifted_fixture()
        cache, atoms, joints, roles, collection, replay = values
        frozen = copy.deepcopy(replay["selections"])
        before = regional(values)
        key = "evaluation/2025-05"
        cache["counts"][key][2][0, 3], cache["counts"][key][2][0, 1] = cache["counts"][key][2][0, 1], 0
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        refresh(cache)
        replay2 = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        after = run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay2)
        self.assertEqual(frozen, replay2["selections"])
        self.assertEqual(before["validation_increments"], after["validation_increments"])
        self.assertEqual([r for r in before["metrics"] if r["scope"] == "monthly" and r["target"] != key],
                         [r for r in after["metrics"] if r["scope"] == "monthly" and r["target"] != key])

    def test_missing_target_class_keeps_prior_and_identification_range(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        key = "evaluation/2025-05"
        cache["counts"][key][2][0], atoms[key][:, 0], joints[key][:, 0] = 0, 0, 0
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        refresh(cache)
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        result = run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay)
        for r in result["metrics"]:
            if r["scope"] == "monthly" and r["target"] == key:
                self.assertIsNone(r["weighted_error"]["value"])
                self.assertEqual(r["weighted_error"]["unidentified_prior_mass"], .2)
        self.assertTrue(all(r["error"] is None and r["prior"] == .2 for r in result["classes"] if r["target"] == key and r["APP"] == 2))

    def test_unavailable_fit_keeps_all_class_rows(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        for token in {c["fit_id"] for c in collection["window_spec"]["contexts"]}:
            roles[token]["base"][0], roles[token]["children"][0] = 0, 0
            roles[token]["single"][:, 0], roles[token]["joint"][:, 0] = 0, 0
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        result = run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay)
        self.assertTrue(all(r["status"] == "unavailable_fit_model" for r in result["metrics"]))
        self.assertEqual(len(result["classes"]), len(result["metrics"]) * 4)
        self.assertFalse(result["invariants"])

    def test_period_errors_pool_counts_within_class(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        key = "evaluation/2025-03"
        cache["counts"][key][2][0, 1] += 500
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        refresh(cache)
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        result = run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay)
        row = next(r for r in result["classes"] if (r["scope"], r["target"], r["model"], r["background"], r["group"], r["APP"]) ==
                   ("period", "evaluation", "fixed_pilot", "full_past", "joint_fit", 2))
        self.assertEqual(row["n"], 2000)
        self.assertEqual(row["wrong_change_vs_same_background_time"], -600)
        self.assertAlmostEqual(row["conditional_change_vs_same_background_time"], -.3)

    def test_actual_legacy_and_fixed_root_references_are_separate(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        legacy = {}
        for c in collection["window_spec"]["contexts"]:
            base = sum(cache["counts"][key][2] for key in c["training_slices"])
            child = sum(time_children(atoms[key], [0, 4, 10], 0.) for key in c["training_slices"])
            prediction, _ = root_model(base, child, cache["priors"], 479)
            target = refine_counts(cache["counts"][c["target"]][2], time_children(atoms[c["target"]], [0, 4, 10], 0.), 479)
            legacy[c["target"], c["model"], "legacy_time_full"] = evaluate(target, cache["priors"], prediction, 0)["confusion"]
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), legacy, minimum=1)
        result = run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay)
        rows = [r for r in result["metrics"] if r["status"] == "complete"]
        self.assertTrue(any(r["raw_change_vs_full_past_time"] != r["raw_change_vs_legacy_time_full"] for r in rows))

    def test_all_44_class_contributions_and_frozen_transfers(self):
        cache, atoms, joints, roles, collection0, _ = fixture()
        known = np.array(list(range(43)) + [50])
        index, other = np.searchsorted(known, cache["known"]), np.setdiff1d(np.arange(44), np.searchsorted(known, cache["known"]))
        cache["known"], cache["priors"], cache["plan"]["unknown_prior"] = known, np.full(44, 1 / 45), 1 / 45
        for key in cache["counts"]:
            base = np.zeros((44, 1024), dtype=np.int64)
            base[index], base[other, 1] = cache["counts"][key][2], 500
            cache["counts"][key] = {2: base, 1: project_fine(base, 5)}
            a, j = np.zeros((2, 44, 2, 4), dtype=np.int64), np.zeros((1, 44, 2, 2, 2), dtype=np.int64)
            a[:, index], j[:, index] = atoms[key], joints[key]
            atoms[key], joints[key] = a, j
        for r in roles.values():
            base, child = np.zeros((44, 1024), dtype=np.int64), np.zeros((44, 3), dtype=np.int64)
            base[index], base[other, 1], child[index] = r["base"], 200, r["children"]
            a, j = np.zeros((2, 44, 2, 2), dtype=np.int64), np.zeros((1, 44, 2, 2, 2), dtype=np.int64)
            a[:, index], j[:, index] = r["single"], r["joint"]
            r.update(base=base, children=child, single=a, joint=j)
        refresh(cache)
        collection = collection_protocol(cache, protocol(), collection0["window_spec"], 4.)
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        result = run_regional(cache, roles, joints, atoms, collection, selection_protocol(), replay)
        for metric in result["metrics"]:
            rows = [r for r in result["classes"] if all(r[k] == metric[k] for k in ("scope", "target", "model", "background", "group"))]
            self.assertEqual([r["APP"] for r in rows], known.tolist())
            self.assertAlmostEqual(sum(r["weighted_change_vs_same_background_time"] for r in rows), metric["change_vs_same_background_time"]["value"])
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_complete_pipeline_without_raw_H5_and_cache_tamper_rejected(self):
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
            path, prepared, experiment, monthly, rolling, refinement, hierarchy, joint, output = (Path(tmp) / name for name in
                ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy", "joint", "regional"))
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
            args = argparse.Namespace(prepare_dir=prepared, monthly_dir=monthly, refinement_dir=refinement, hierarchy_dir=hierarchy, joint_dir=joint, out_dir=output, small_n=200)
            with contextlib.redirect_stdout(io.StringIO()):
                run_prepare(argparse.Namespace(h5=path, out_dir=prepared, backend=backend, sha256=True, expected_sha256=None, time_unit="seconds", k=5,
                    gap_seconds=DAY, rounding_seconds=3600, identifier_sample=0, seed=0, block_seconds=[3600, 21600, DAY], max_rows=None, chunk_rows=2, min_pilot_flows=1, alpha=.05))
                run_experiment(argparse.Namespace(h5=path, prepare_dir=prepared, out_dir=experiment, backend=backend, chunk_rows=2, block_seconds=[3600, 21600, DAY]))
                run_monthly(argparse.Namespace(h5=path, prepare_dir=prepared, experiment_dir=experiment, out_dir=monthly, backend=backend, chunk_rows=2, small_n=200, top=3))
                run_rolling(argparse.Namespace(monthly_dir=monthly, out_dir=rolling, app=2, reference_months=["2024-12", "2025-01"], matched_repeats=0, seed=7, small_n=200, top=3))
                run_refinement(argparse.Namespace(h5=path, prepare_dir=prepared, monthly_dir=monthly, rolling_dir=rolling, out_dir=refinement, backend=backend,
                    symbol_id=479, size_positions=None, size_cuts=[1000, 1200], ipt_cuts=[0, 4, 10], models=MODELS, min_leaf_flows=1, chunk_rows=2, small_n=200))
                run_hierarchy(argparse.Namespace(monthly_dir=monthly, refinement_dir=refinement, out_dir=hierarchy, min_leaf_flows=1, small_n=200))
                run_joint_cli(argparse.Namespace(h5=path, reuse_counts_dir=None, prepare_dir=prepared, monthly_dir=monthly, refinement_dir=refinement,
                    hierarchy_dir=hierarchy, out_dir=joint, backend=backend, chunk_rows=2, ipt_threshold_ms=4., validation_day=21,
                    validation_gap_seconds=DAY, min_leaf_flows=1, app21_budget_pp=.1, max_validation_raw_increase=0, small_n=200))
                path.unlink()
                run(args)
            summary = json.loads((output / "summary.json").read_text())
            self.assertTrue(summary["stage11_reproduced"] and summary["local_selection_unchanged"])
            self.assertFalse(summary["raw_H5_rescan"])
            self.assertEqual(json.loads((output / "run.json").read_text())["rows_read"], 0)
            self.assertEqual(json.loads((output / "frozen_selections.json").read_text()), json.loads((joint / "summary.json").read_text())["selections"])
            self.assertEqual(len(json.loads((output / "invariants.json").read_text())), 90)
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertTrue((output / "validation_local_increments.csv").is_file())
            self.assertTrue((output / "APP2_outside_symbols.csv").is_file())
            self.assertIn("Absolute validation accuracy", (output / "report.md").read_text())
            with (joint / "joint_counts.npz").open("ab") as handle:
                handle.write(b"changed")
            args.out_dir = Path(tmp) / "bad_cache"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "hash mismatch"):
                run(args)


if __name__ == "__main__":
    unittest.main()
