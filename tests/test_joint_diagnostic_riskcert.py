"""Frozen-model audit identities, unsupported winners, drift and cache lineage."""

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
from eibo.jointdiagnostic import attribution, budget_audit, focal_candidate_audit, training_split_regions
from eibo.jointrefinement import run_joint, root_model, time_children
from eibo.realdata import DAY
from eibo.refinement import refine_counts
from eibo.rolling import evaluate, project_fine
from methodology_real_joint import collection_protocol, run as run_joint_cli
from methodology_real_joint_diagnostic import run
from methodology_real_prepare import run as run_prepare, sha256
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run as run_refinement
from methodology_real_hierarchy import run as run_hierarchy
from test_joint_refinement_riskcert import MODELS, protocol, refresh, xor_fixture
from test_refinement_riskcert import scan_fixture


def fixture(minimum=1):
    cache, atoms, joints, roles, windows = xor_fixture()
    collection = collection_protocol(cache, protocol(), windows, 4.)
    replay = run_joint(cache, roles, joints, atoms, windows, protocol(), {}, minimum=minimum)
    return cache, atoms, joints, roles, collection, replay


def selection_protocol():
    return {"models": MODELS, "APP21_validation_budget_pp": .1, "maximum_validation_raw_wrong_increase": 0}


def replace_low(cache, atoms, joints, key, joint):
    joints[key] = joint
    atoms[key][0, :, :, :2], atoms[key][1, :, :, :2] = joint[0].sum(axis=2), joint[0].sum(axis=1)
    base = cache["counts"][key][2]
    base[:, 479] = atoms[key][0].sum(axis=(1, 2))
    base[:, 1] = 500 - base[:, 479]
    cache["counts"][key][1] = project_fine(base, 5)
    refresh(cache)


class TestJointDiagnostic(unittest.TestCase):
    def test_integer_class_attribution_and_paired_scope(self):
        cache, _, _, _, _, replay = fixture()
        rows, summaries = attribution(cache, replay, MODELS)
        for summary in summaries:
            if summary["status"] != "complete":
                continue
            values = [r for r in rows if all(r[k] == summary[k] for k in ("scope", "target", "model", "group", "reference"))]
            self.assertEqual([r["APP"] for r in values], cache["known"].tolist())
            self.assertEqual(sum(r["wrong_change"] for r in values), summary["raw_wrong_change"])
            self.assertAlmostEqual(sum(r["weighted_change"] for r in values), summary["weighted_change"]["value"])
            for r in values:
                if r["reference"] == "time_fit":
                    self.assertEqual(r["harmed"] - r["rescued"], r["wrong_change"])
                else:
                    self.assertIsNone(r["rescued"])
                    self.assertIsNone(r["harmed"])

    def test_past_constraints_can_fail_under_future_drift(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        key = "evaluation/2025-05"
        joint = joints[key].copy()
        joint[0, 0] = 0
        joint[0, 0, 0, 0, 1] = 1
        joint[0, 1, 0, 1, 1] -= 10
        joint[0, 1, 0, 0, 1] += 10
        replace_low(cache, atoms, joints, key, joint)
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        rows, summary = budget_audit(cache, replay, selection_protocol())
        values = [r for r in rows if r["target"] == key and r["group"] == "validation_constrained"]
        self.assertEqual(len(values), 3)
        for r in values:
            self.assertTrue(r["validation_APP21_budget_met"])
            self.assertTrue(r["validation_raw_budget_met"])
            self.assertFalse(r["target_APP21_budget_met"])
            self.assertFalse(r["target_raw_budget_met"])
            self.assertEqual(r["target_raw_wrong_change"], 9)
        for r in summary:
            if r["period"] == "evaluation" and r["group"] == "validation_constrained":
                self.assertEqual(r["both_met"], 2)
                self.assertEqual(r["APP21_violations"], 1)

    def test_candidates_and_fine_atoms_detect_XOR(self):
        cache, atoms, joints, roles, collection, replay = fixture()
        result = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1)
        for r in result["candidate_summary"]:
            if r["kind"] == "single":
                self.assertEqual(r["raw_positive_APP2_candidates"], 0)
            else:
                self.assertEqual(r["allowed_positive_APP2_candidates"], 1)
                self.assertEqual(r["best_allowed_fit_APP2_correct_gain"], 120)
                self.assertEqual(r["maximum_allowed_target_APP2_correct_gain_hindsight"], 200)
        for r in result["pair_summary"]:
            self.assertEqual(r["fit_APP2_winning_atoms"], 2)
            self.assertEqual(r["target_empirical_APP2_flows_in_winning_atoms"], 200)
            self.assertFalse(r["deployed"])
        self.assertTrue(any(r["prediction_APP"] == 2 for r in result["leaves"]))

    def test_support_gate_can_remove_all_APP2_winners(self):
        cache, atoms, joints, roles, collection, replay = fixture(minimum=1000)
        result = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1000)
        joint = [r for r in result["candidate_summary"] if r["kind"] == "joint"]
        self.assertTrue(all(r["raw_positive_APP2_candidates"] == 1 and r["allowed_positive_APP2_candidates"] == 0 for r in joint))
        self.assertTrue(all(r["fit_APP2_winning_atoms"] == 2 and r["guarded_fit_APP2_winning_atoms"] == 0 for r in result["pair_summary"]))
        self.assertTrue(all(r["fit_APP2_flows_lost_to_leaf_budget"] == 120 for r in result["pair_summary"]))

    def test_backoff_to_APP2_parent_does_not_remove_focal_correct_flows(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        for token in {c["fit_id"] for c in collection["window_spec"]["contexts"]}:
            r = roles[token]
            r["children"][1, 1] += r["children"][1, 0]
            r["children"][1, 0] = 0
            r["single"][:, 1], r["joint"][:, 1] = 0, 0
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1000)
        result = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1000)
        self.assertTrue(all(r["parent_APP"] == 2 and r["fit_APP2_flows_lost_to_leaf_budget"] == 0 for r in result["pair_summary"]))
        self.assertTrue(all(r["best_allowed_fit_APP2_correct_gain"] == 0 for r in result["candidate_summary"]))

    def test_overall_selection_can_skip_a_focal_positive_candidate(self):
        cache, _, _, roles0, collection0, _ = fixture()
        prior = {**protocol(), "size_candidates_bytes": [1000, 1200]}

        def data(scale):
            joint = np.zeros((1, 4, 3, 3, 2), dtype=np.int64)
            joint[0, 0, 0, 0, 1], joint[0, 1, 2, 2, 1], joint[0, 3, 1, 1, 1] = 10 * scale, 80 * scale, 30 * scale
            child = np.zeros((4, 3), dtype=np.int64)
            child[:, 0], child[:, 1] = [10 * scale, 80 * scale, 0, 30 * scale], [0, 0, 80 * scale, 0]
            base = np.zeros((4, 1024), dtype=np.int64)
            base[:, 479], base[:, 1] = child.sum(axis=1), 100 * scale - child.sum(axis=1)
            return {"base": base, "children": child, "single": np.stack((joint[0].sum(axis=2), joint[0].sum(axis=1))), "joint": joint}

        fitting = {c["fit_id"] for c in collection0["window_spec"]["contexts"]}
        roles = {token: data(3 if token in fitting else 2) for token in roles0}
        month = data(5)
        atoms, joints = {}, {}
        for key in cache["counts"]:
            cache["counts"][key] = {2: month["base"].copy(), 1: project_fine(month["base"], 5)}
            a = np.zeros((2, 4, 3, 4), dtype=np.int64)
            a[:, :, :, :2], a[:, 2, 0, 2] = month["single"], 400
            atoms[key], joints[key] = a, month["joint"].copy()
        refresh(cache)
        collection = collection_protocol(cache, prior, collection0["window_spec"], 4.)
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], prior, {}, minimum=1)
        audit = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1)
        single = [r for r in audit["candidate_summary"] if r["kind"] == "single"]
        self.assertTrue(all(r["allowed_positive_APP2_candidates"] > 0 and r["best_allowed_selected_by"] == "" for r in single))
        chosen = [r for r in audit["candidates"] if r["selected_by"] == "single_fit"]
        self.assertTrue(chosen)
        self.assertTrue(all(r["fit_APP2_correct_gain"] == 0 for r in chosen))

    def test_missing_fit_class_stays_unavailable(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        for token in {c["fit_id"] for c in collection["window_spec"]["contexts"]}:
            roles[token]["base"][0], roles[token]["children"][0] = 0, 0
            roles[token]["single"][:, 0], roles[token]["joint"][:, 0] = 0, 0
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        focal = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1)
        self.assertTrue(all(r["status"] == "unavailable_fit_model" for r in focal["candidate_summary"]))
        budgets, _ = budget_audit(cache, replay, selection_protocol())
        self.assertTrue(all(r["target_both_met"] is None for r in budgets))

    def test_diagnostics_never_change_frozen_selections(self):
        cache, atoms, joints, roles, collection, replay = fixture()
        frozen = copy.deepcopy(replay["selections"])
        a = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1)
        key = "evaluation/2025-05"
        joint = joints[key].copy()
        joint[0, 0] = np.roll(joint[0, 0], 1, axis=0)
        replace_low(cache, atoms, joints, key, joint)
        b = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1)
        self.assertEqual(replay["selections"], frozen)
        self.assertEqual([r["fit_APP2_correct_gain"] for r in a["candidates"]], [r["fit_APP2_correct_gain"] for r in b["candidates"]])
        self.assertEqual([r["selected_by"] for r in a["candidates"]], [r["selected_by"] for r in b["candidates"]])
        self.assertNotEqual([r["target_APP2_correct_gain"] for r in a["candidates"]], [r["target_APP2_correct_gain"] for r in b["candidates"]])

    def test_missing_target_class_preserves_prior_and_disables_oracle(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        key = "evaluation/2025-05"
        cache["counts"][key][2][0], atoms[key][:, 0], joints[key][:, 0] = 0, 0, 0
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        refresh(cache)
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        focal = focal_candidate_audit(cache, roles, joints, atoms, collection, replay, minimum=1)
        self.assertTrue(all(r["target_empirical_APP2_winning_atoms"] is None for r in focal["pair_summary"] if r["target"] == key))
        rows, summaries = attribution(cache, replay, MODELS)
        metric = next(r for r in summaries if r["target"] == key and r["group"] == "joint_fit" and r["reference"] == "time_fit")
        self.assertIsNone(metric["weighted_change"]["value"])
        self.assertEqual(metric["weighted_change"]["unidentified_prior_mass"], .2)
        self.assertTrue(all(r["prior"] == .2 and r["conditional_change"] is None for r in rows if r["target"] == key and r["APP"] == 2))

    def test_training_split_localizes_change_outside_refined_cell(self):
        cache, atoms, joints, roles, collection, _ = fixture()
        fitting = {c["fit_id"] for c in collection["window_spec"]["contexts"]}
        for token in fitting:
            base = roles[token]["base"]
            base[0, 2], base[0, 1] = base[0, 1], 0
        split = training_split_regions(cache, roles, atoms, collection)
        focal = [r for r in split if r["scope"] == "monthly" and r["APP"] == 2]
        self.assertTrue(all(r["wrong_change"] == (300 if r["region"] == "outside_479" else 0) for r in focal))
        legacy = {}
        for c in collection["window_spec"]["contexts"]:
            full = sum(cache["counts"][key][2] for key in c["training_slices"])
            child = sum(time_children(atoms[key], [0, 4, 10], 4.) for key in c["training_slices"])
            pred, _ = root_model(full, child, cache["priors"], 479)
            target = refine_counts(cache["counts"][c["target"]][2], time_children(atoms[c["target"]], [0, 4, 10], 4.), 479)
            legacy[c["target"], c["model"], "legacy_time_full"] = evaluate(target, cache["priors"], pred, 0)["confusion"]
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), legacy, minimum=1)
        attr, _ = attribution(cache, replay, MODELS)
        for r in attr:
            if r["group"] == "time_fit" and r["APP"] == 2:
                parts = [v for v in split if all(v[k] == r[k] for k in ("scope", "target", "model", "APP"))]
                self.assertEqual(sum(v["wrong_change"] for v in parts), r["wrong_change"])

    def test_all_44_classes_are_kept_in_every_attribution(self):
        cache, _, _, _, _, replay = fixture()
        known, old = np.array(list(range(43)) + [50]), cache["known"].copy()
        indices = np.searchsorted(known, old)
        other = np.setdiff1d(np.arange(44), indices)
        cache["known"], cache["priors"] = known, np.full(44, 1 / 45)
        for key in cache["counts"]:
            base = np.zeros((44, 1024), dtype=np.int64)
            base[indices], base[other, 1] = cache["counts"][key][2], 500
            cache["counts"][key] = {2: base, 1: project_fine(base, 5)}
        refresh(cache)
        for r in replay["confusions"]:
            matrix = np.zeros((44, 44), dtype=np.int64)
            matrix[np.ix_(indices, indices)] = r["counts_true_by_predicted"]
            matrix[other, other] = 500
            r["counts_true_by_predicted"] = matrix.tolist()
        for target in [s for s in cache["slices"] if s["period"] != "pilot"]:
            for model in MODELS:
                for group in ("time_fit", "single_fit", "joint_fit", "validation_weighted", "validation_constrained"):
                    replay["classes"].extend({"target": target["key"], "model": model, "group": group, "APP": int(app), "rescued": 0, "harmed": 0} for app in known[other])
        rows, summaries = attribution(cache, replay, MODELS)
        for summary in summaries:
            values = [r for r in rows if all(r[k] == summary[k] for k in ("scope", "target", "model", "group", "reference"))]
            self.assertEqual([r["APP"] for r in values], known.tolist())
            if summary["status"] == "complete":
                self.assertAlmostEqual(sum(r["weighted_change"] for r in values), summary["weighted_change"]["value"])

    def test_no_focal_class_has_empty_focal_outputs(self):
        cache, atoms, joints, roles, collection, replay = fixture()
        cache["known"] = np.array([1, 21, 34, 50])
        focal = focal_candidate_audit(cache, roles, joints, atoms, collection, replay)
        self.assertTrue(all(not rows for rows in focal.values()))

    def test_complete_pipeline_without_H5_and_forged_summary_rejected(self):
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
                ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy", "joint", "diagnostic"))
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
            args = argparse.Namespace(prepare_dir=prepared, monthly_dir=monthly, refinement_dir=refinement, hierarchy_dir=hierarchy,
                                      joint_dir=joint, out_dir=output, small_n=200, top=3)
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
            self.assertTrue(summary["stage11_reproduced"])
            self.assertFalse(summary["raw_H5_rescan"])
            self.assertEqual(json.loads((output / "run.json").read_text())["rows_read"], 0)
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertTrue((output / "APP2_candidates.csv").is_file())
            self.assertIn("## APP2 training-split regions", (output / "report.md").read_text())
            stored = json.loads((joint / "summary.json").read_text())
            stored["monthly"][0]["APP2_error"] += .01
            (joint / "summary.json").write_text(json.dumps(stored))
            args.out_dir = Path(tmp) / "bad_hash"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "hash mismatch"):
                run(args)
            metadata = json.loads((joint / "run.json").read_text())
            next(r for r in metadata["outputs"] if r["path"] == "summary.json")["sha256"] = sha256(joint / "summary.json")
            (joint / "run.json").write_text(json.dumps(metadata))
            args.out_dir = Path(tmp) / "bad_replay"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "replay metric"):
                run(args)


if __name__ == "__main__":
    unittest.main()
