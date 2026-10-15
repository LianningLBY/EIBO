"""Chronological block validation, dilution counterexamples and raw/cache parity."""

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
from eibo.blockvalidation import GROUPS, block_windows, evaluate_rules, reconcile_blocks, select_rules, sum_roles
from eibo.jointrefinement import JointCounts, run_joint
from eibo.realdata import DAY, whole_interval_mask
from eibo.rolling import project_fine
from methodology_real_blocks import run
from methodology_real_joint import collection_protocol, run as run_joint_cli
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run as run_refinement
from methodology_real_hierarchy import run as run_hierarchy
from test_joint_diagnostic_riskcert import fixture, selection_protocol
from test_joint_refinement_riskcert import MODELS, protocol, refresh, xor_data
from test_refinement_riskcert import scan_fixture


def block_fixture(*, bad=None, budget=.1):
    cache, atoms, joints, old_roles, collection0, _ = fixture()
    windows = block_windows(collection0["window_spec"])
    # The count-only fixture has no real within-month density. Keep synthetic block
    # populations distinct even when a calendar block equals an older role range.
    aliases = {token: "test_" + token for c in windows["contexts"] for token in c["block_ids"]}
    windows["ranges"].extend({**r, "id": aliases[r["id"]]} for r in list(windows["ranges"]) if r["id"] in aliases)
    for context in windows["contexts"]:
        context["block_ids"] = [aliases[token] for token in context["block_ids"]]
    fitting = {c["fit_id"] for c in windows["contexts"]}
    roles = {token: xor_data(2 if token in fitting else 3) for token in old_roles}
    for context in windows["contexts"]:
        for token in context["block_ids"]:
            roles[token] = xor_data(1)
        if bad:
            role = roles[context["block_ids"][0]]
            if bad != "flat":
                role["joint"][0, 1, 0, 1, 1] -= 1
                role["joint"][0, 1, 0, 0, 1] += 1
            if bad in ("raw", "flat"):
                role["joint"][0, 0, 0, 0, 1] = role["joint"][0, 0, 1, 1, 1] = 0
                role["joint"][0, 0, 0, 1, 1] = 40
            role["single"] = np.stack((role["joint"][0].sum(axis=2), role["joint"][0].sum(axis=1)))
        roles[context["validation_id"]] = sum_roles([roles[token] for token in context["block_ids"]])
    collection = {**collection0, "window_spec": windows}
    local_protocol = {**selection_protocol(), "minimum_fit_leaf_flows": 1, "APP21_validation_budget_pp": budget}
    replay = run_joint(cache, roles, joints, atoms, collection0["window_spec"], protocol(), {}, minimum=1, app21_budget=budget / 100)
    return cache, atoms, joints, roles, collection, local_protocol, replay


def select(values):
    _, _, _, roles, collection, local_protocol, replay = values
    return select_rules(roles, collection, local_protocol, replay["selections"])


def evaluate(values, selected=None):
    cache, atoms, joints, roles, collection, local_protocol, replay = values
    return evaluate_rules(cache, roles, joints, atoms, collection, local_protocol, selected or select(values), replay)


class TestBlockValidation(unittest.TestCase):
    def test_geometry_is_calendar_only_and_original_roles_unchanged(self):
        _, _, _, _, collection, _ = fixture()
        before = copy.deepcopy(collection["window_spec"])
        windows = block_windows(before)
        self.assertEqual(before, collection["window_spec"])
        ranges = {r["id"]: r for r in windows["ranges"]}
        for old, context in zip(before["contexts"], windows["contexts"]):
            for name in old:
                self.assertEqual(old[name], context[name])
            blocks = [ranges[token] for token in context["block_ids"]]
            self.assertEqual(blocks[0]["start_epoch"], old["validation_start_epoch"])
            self.assertEqual(blocks[-1]["end_epoch"], old["validation_end_epoch"])
            self.assertTrue(all(a["end_epoch"] == b["start_epoch"] for a, b in zip(blocks[:-1], blocks[1:])))
        fixed = [c for c in windows["contexts"] if c["model"] == "fixed_pilot"]
        self.assertTrue(all(c["block_ids"] == fixed[0]["block_ids"] for c in fixed))
        with self.assertRaises(ValueError):
            block_windows(before, blocks=1)
        with self.assertRaises(ValueError):
            block_windows(before, rounding=100 * DAY)

    def test_whole_flow_guard_drops_boundary_crossers_without_duplicate_flows(self):
        first = np.array([1., 5., 8., 11., 18., 21., 28.])
        last = np.array([2., 10., 9., 12., 21., 22., 29.])
        masks = [whole_interval_mask(first, last, bounds, 1) for bounds in ((0, 10), (10, 20), (20, 30))]
        self.assertTrue(np.all(sum(masks) <= 1))
        self.assertFalse(any(mask[1] or mask[4] for mask in masks))

    def test_pooled_APP21_budget_can_hide_a_bad_block(self):
        values = block_fixture(bad="APP21", budget=.5)
        selected = select(values)
        for r in selected["selections"]:
            if r["group"] in ("original_pooled", "block_pooled"):
                self.assertIsNotNone(r["rule"])
                self.assertLess(r["rule"]["APP21_validation_conditional_change"], .005)
            if r["group"] in GROUPS[3:]:
                self.assertIsNone(r["rule"])
        candidates = [r for r in selected["candidates"] if r["kind"] == "joint"]
        self.assertTrue(all(max(r["block_APP21_changes"]) > .005 for r in candidates))

    def test_pooled_raw_gain_can_hide_a_positive_error_block(self):
        selected = select(block_fixture(bad="raw", budget=100))
        for r in selected["selections"]:
            if r["group"] == "block_pooled":
                self.assertIsNotNone(r["rule"])
                self.assertLess(r["rule"]["validation_raw_wrong_change"], 0)
            if r["group"] in GROUPS[3:]:
                self.assertIsNone(r["rule"])
        self.assertTrue(all(max(r["block_raw_changes"]) == 1 for r in selected["candidates"] if r["kind"] == "joint"))

    def test_positive_stable_rule_and_all_old_target_counts_preserved(self):
        values = block_fixture()
        result = evaluate(values)
        cache = values[0]
        self.assertTrue(all(r["rule"] is not None for r in select(values)["selections"] if r["group"] in GROUPS[3:]))
        for r in result["confusions"]:
            np.testing.assert_array_equal(np.asarray(r["counts_true_by_predicted"]).sum(axis=1), cache["counts"][r["target"]][2].sum(axis=1))
        self.assertTrue(all(r["harmed"] == 0 for r in result["classes"] if r["APP"] == 34))
        self.assertTrue(all(r["both_met"] for r in result["budget_monthly"]))
        self.assertEqual(len(result["invariants"]), 90)

    def test_worst_block_objective_can_reject_a_pooled_gain_with_all_budgets_met(self):
        selected = select(block_fixture(bad="flat"))
        for r in selected["selections"]:
            if r["group"] == "block_constraints":
                self.assertIsNotNone(r["rule"])
            if r["group"] == "block_minimax":
                self.assertIsNone(r["rule"])

    def test_APP34_parent_forces_structural_identity(self):
        values = block_fixture()
        for token in {c["fit_id"] for c in values[4]["window_spec"]["contexts"]}:
            role = values[3][token]
            role["joint"][0, 2, 0, 0, 1] = role["children"][2, 1]
            role["children"][2, 0], role["children"][2, 1] = role["children"][2, 1], 0
            role["single"] = np.stack((role["joint"][0].sum(axis=2), role["joint"][0].sum(axis=1)))
        values[-1].update(run_joint(values[0], values[3], values[2], values[1], values[4]["window_spec"], protocol(), {}, minimum=1))
        self.assertTrue(all(r["status"] == "identity_APP34_parent_protection" for r in select(values)["selections"] if r["group"] in GROUPS[3:]))

    def test_missing_block_class_forces_identity_without_prior_renormalization(self):
        values = block_fixture()
        _, _, _, roles, collection, _, _ = values
        token = collection["window_spec"]["contexts"][0]["block_ids"][0]
        roles[token]["base"][3] = 0
        selected = select(values)
        affected = [c for c in collection["window_spec"]["contexts"] if token in c["block_ids"]]
        for c in affected:
            rows = [r for r in selected["selections"] if r["target"] == c["target"] and r["model"] == c["model"] and r["group"] in GROUPS[3:]]
            self.assertTrue(all(r["status"] == "identity_missing_block_classes" for r in rows))
            candidates = [r for r in selected["candidates"] if r["target"] == c["target"] and r["model"] == c["model"]]
            self.assertTrue(all(r["worst_block_weighted_change"] is None for r in candidates))
        result = evaluate(values, selected)
        for r in result["metrics"]:
            classes = [v for v in result["classes"] if all(v[k] == r[k] for k in ("scope", "target", "model", "group"))]
            self.assertEqual([v["APP"] for v in classes], values[0]["known"].tolist())

    def test_selection_has_no_target_counts_and_frozen_choices_ignore_future_labels(self):
        values = block_fixture()
        before = select(values)
        changed = copy.deepcopy(values)
        key = "evaluation/2025-05"
        changed[0]["counts"][key][2][:] = 0
        changed[2][key][:] = 0
        changed[1][key][:] = 0
        self.assertEqual(before, select(changed))

    def test_selected_past_budgets_still_can_fail_on_future_drift(self):
        values = block_fixture()
        selected = select(values)
        cache, atoms, joints, _, _, _, _ = values
        key = "evaluation/2025-05"
        joints[key][0, 1, 0, 1, 1] -= 10
        joints[key][0, 1, 0, 0, 1] += 10
        atoms[key][0, :, :, :2], atoms[key][1, :, :, :2] = joints[key][0].sum(axis=2), joints[key][0].sum(axis=1)
        # The cached original control must also reflect the changed target, while past selections stay frozen.
        values[-1].update(run_joint(cache, values[3], joints, atoms, values[4]["window_spec"], protocol(), {}, minimum=1))
        result = evaluate(values, selected)
        rows = [r for r in result["budget_monthly"] if r["target"] == key and r["group"] == "block_minimax"]
        self.assertTrue(all(r["target_APP21_budget_met"] is False for r in rows))

    def test_boundary_counts_and_old_role_tampering_detected(self):
        values = block_fixture()
        roles, collection = values[3], values[4]
        previous = {token: roles[token] for token in roles if token.startswith("w")}
        rows = reconcile_blocks(roles, previous, collection["window_spec"])
        self.assertTrue(all(sum(r["boundary_excluded_n"]) == 0 for r in rows))
        changed = copy.deepcopy(roles)
        changed[next(iter(previous))]["base"][0, 0] += 1
        with self.assertRaisesRegex(ValueError, "original"):
            reconcile_blocks(changed, previous, collection["window_spec"])
        token = collection["window_spec"]["contexts"][0]["block_ids"][0]
        changed = copy.deepcopy(roles)
        changed[token]["joint"] *= 100
        with self.assertRaisesRegex(ValueError, "overlap"):
            reconcile_blocks(changed, previous, collection["window_spec"])

    def test_period_pooling_and_missing_target_class_ranges(self):
        values = block_fixture()
        cache = values[0]
        key = "evaluation/2025-05"
        cache["counts"][key][2][3] = 0
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        values[1][key][:, 3] = 0
        values[2][key][:, 3] = 0
        refresh(cache)
        values[-1].update(run_joint(cache, values[3], values[2], values[1], values[4]["window_spec"], protocol(), {}, minimum=1))
        result = evaluate(values)
        monthly = next(r for r in result["metrics"] if r["target"] == key and r["model"] == MODELS[0] and r["group"] == "block_minimax")
        self.assertIsNone(monthly["weighted_error"]["value"])
        self.assertGreater(monthly["weighted_error"]["unidentified_prior_mass"], 0)
        for r in result["classes"]:
            if r["scope"] == "period":
                rows = [s for s in result["classes"] if s["scope"] == "monthly" and all(s[k] == r[k] for k in ("period", "model", "group", "APP"))]
                self.assertEqual(sum(s["wrong"] for s in rows), r["wrong"])
                self.assertEqual(sum(s["n"] for s in rows), r["n"])

    def test_all_44_classes_and_prior_contributions_retained(self):
        cache, atoms, joints, roles, collection0, local_protocol, _ = block_fixture()
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
        for role in roles.values():
            base, children = np.zeros((44, 1024), dtype=np.int64), np.zeros((44, 3), dtype=np.int64)
            base[index], base[other, 1], children[index] = role["base"], 100, role["children"]
            a, j = np.zeros((2, 44, 2, 2), dtype=np.int64), np.zeros((1, 44, 2, 2, 2), dtype=np.int64)
            a[:, index], j[:, index] = role["single"], role["joint"]
            role.update(base=base, children=children, single=a, joint=j)
        refresh(cache)
        collection = collection_protocol(cache, protocol(), collection0["window_spec"], 4.)
        replay = run_joint(cache, roles, joints, atoms, collection["window_spec"], protocol(), {}, minimum=1)
        result = evaluate((cache, atoms, joints, roles, collection, local_protocol, replay))
        for metric in result["metrics"]:
            rows = [r for r in result["classes"] if all(r[k] == metric[k] for k in ("scope", "target", "model", "group"))]
            self.assertEqual([r["APP"] for r in rows], known.tolist())
            self.assertAlmostEqual(sum(r["weighted_change_vs_time_baseline"] for r in rows), metric["change_vs_time_baseline"]["value"])
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_raw_scan_cache_replay_and_tamper_rejection(self):
        for backend in ("tables", "h5py"):
            try:
                module = importlib.import_module(backend)
                break
            except ImportError:
                continue
        else:
            self.skipTest("an HDF5 writer is needed")
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as tmp:
            path, prepared, experiment, monthly, rolling, refinement, hierarchy, joint, output, reused = (Path(tmp) / name for name in
                ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy", "joint", "blocks", "reused"))
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
            args = argparse.Namespace(h5=path, reuse_counts_dir=None, prepare_dir=prepared, monthly_dir=monthly, refinement_dir=refinement,
                hierarchy_dir=hierarchy, joint_dir=joint, out_dir=output, backend=backend, chunk_rows=2, blocks=3, small_n=200)
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
                run(args)
                path.unlink()
                args.h5, args.reuse_counts_dir, args.out_dir = None, output, reused
                run(args)
            self.assertEqual(json.loads((output / "summary.json").read_text()), json.loads((reused / "summary.json").read_text()))
            self.assertEqual(json.loads((output / "frozen_selections.json").read_text()), json.loads((reused / "frozen_selections.json").read_text()))
            self.assertEqual(json.loads((reused / "run.json").read_text())["rows_read"], 0)
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertIn("remain", (output / "report.md").read_text())
            with (output / "joint_counts.npz").open("ab") as handle:
                handle.write(b"changed")
            args.out_dir = Path(tmp) / "bad"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "hash mismatch"):
                run(args)


if __name__ == "__main__":
    unittest.main()
