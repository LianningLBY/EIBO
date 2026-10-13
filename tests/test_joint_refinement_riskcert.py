"""True size interactions, chronological isolation, loss budgets and cache reuse."""

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
from eibo.jointrefinement import (MATCHED_GROUPS, JointCounts, check_joint, choose_rule,
                                 fit_candidates, root_model, rule_evaluation, run_joint, validation_windows)
from eibo.realdata import DAY, PreparationAudit
from eibo.refinement import RefinementCounts
from eibo.rolling import project_fine
from methodology_real_joint import run
from methodology_real_hierarchy import run as run_hierarchy
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run as run_refinement
from test_hierarchy_riskcert import competing_cache
from test_refinement_riskcert import scan_fixture
from test_rolling_riskcert import epoch

MODELS = ["fixed_pilot", "rolling_1m", "rolling_3m"]


def protocol():
    return {"symbol_id": 479, "size_positions": [1, 2], "size_candidates_bytes": [1200],
            "IPT2_candidates_ms": [0, 4, 10], "models": MODELS}


def xor_data(scale=1):
    joint = np.zeros((1, 4, 2, 2, 2), dtype=np.int64)
    joint[0, 0, 0, 0, 1] = joint[0, 0, 1, 1, 1] = 20 * scale
    joint[0, 1, 0, 1, 1] = joint[0, 1, 1, 0, 1] = 25 * scale
    children = np.zeros((4, 3), dtype=np.int64)
    children[:, 0], children[:, 1] = [40 * scale, 50 * scale, 0, 0], [0, 0, 80 * scale, 60 * scale]
    base = np.zeros((4, 1024), dtype=np.int64)
    base[:, 479] = children.sum(axis=1)
    base[:, 1] = 100 * scale - base[:, 479]
    return {"base": base, "children": children,
            "single": np.stack((joint[0].sum(axis=2), joint[0].sum(axis=1))), "joint": joint}


def collapsed(data):
    return {**data, "single": data["single"].sum(axis=3), "joint": data["joint"].sum(axis=4),
            "positions": (1, 2), "pairs": ((1, 2),)}


def xor_fixture():
    cache, _ = competing_cache()
    data = xor_data(5)
    cache["counts"] = {s["key"]: {2: data["base"].copy(), 1: project_fine(data["base"], 5)} for s in cache["slices"]}
    refresh(cache)
    atoms = np.zeros((2, 4, 2, 4), dtype=np.int64)
    atoms[:, :, :, :2] = data["single"]
    atoms[:, 2, 0, 2], atoms[:, 3, 1, 2] = 400, 300
    old = {s["key"]: atoms.copy() for s in cache["slices"]}
    joints = {s["key"]: data["joint"].copy() for s in cache["slices"]}
    windows = validation_windows(cache, MODELS)
    fitting = {c["fit_id"] for c in windows["contexts"] if "fit_id" in c}
    roles = {r["id"]: xor_data(3 if r["id"] in fitting else 2) for r in windows["ranges"]}
    return cache, old, joints, roles, windows


def refresh(cache):
    cache["period_counts"] = {period: {r: sum(cache["counts"][s["key"]][r] for s in cache["slices"] if s["period"] == period)
                                      for r in (1, 2)} for period in ("pilot", "certificate", "evaluation")}


class TestJointRefinement(unittest.TestCase):
    def candidates(self, validation=None, minimum=1):
        fit = collapsed(xor_data())
        return fit_candidates(fit, validation or fit, np.full(4, .2), np.array([2, 21, 34, 50]), 1,
                              (1, 2), ((1, 2),), (1200,), minimum=minimum)

    def test_joint_finds_xor_without_single_main_effect(self):
        rows = self.candidates()
        self.assertTrue(all(abs(r["fit_gain"]) < 1e-12 for r in rows if r["kind"] == "single"))
        self.assertIsNone(choose_rule(rows, "single_fit")[0])
        rule = choose_rule(rows, "joint_fit")[0]
        self.assertEqual(rule["prediction_APPs"], [2, 21, 21, 2])
        self.assertAlmostEqual(rule["fit_gain"], .08)
        self.assertEqual(choose_rule(rows, "validation_constrained")[0], rule)

    def test_raw_budget_rejects_macro_gain_with_more_wrong_flows(self):
        validation = collapsed(xor_data())
        validation["base"][0] = 0
        validation["base"][0, 479] = 8
        validation["joint"][0, 0] = [[4, 0], [0, 4]]
        validation["joint"][0, 1] = [[9, 20], [21, 0]]
        validation["single"] = np.stack((validation["joint"][0].sum(axis=2), validation["joint"][0].sum(axis=1)))
        rows = self.candidates(validation)
        rule = choose_rule(rows, "validation_weighted")[0]
        self.assertGreater(-rule["validation_weighted_change"], 0)
        self.assertEqual(rule["validation_raw_wrong_change"], 1)
        self.assertIsNone(choose_rule(rows, "validation_constrained", app21_budget=.1)[0])
        self.assertIsNotNone(choose_rule(rows, "validation_constrained", app21_budget=.1, raw_budget=1)[0])

    def test_APP21_budget_rejects_gain_even_when_raw_error_improves(self):
        validation = collapsed(xor_data())
        validation["joint"][0, 1] = [[30, 10], [10, 0]]
        rows = self.candidates(validation)
        rule = choose_rule(rows, "validation_weighted")[0]
        self.assertEqual(rule["validation_raw_wrong_change"], -10)
        self.assertAlmostEqual(rule["APP21_validation_conditional_change"], .3)
        self.assertIsNone(choose_rule(rows, "validation_constrained", app21_budget=.001)[0])
        self.assertIsNotNone(choose_rule(rows, "validation_constrained", app21_budget=.3)[0])

    def test_missing_validation_class_and_APP34_parent_force_identity(self):
        validation = collapsed(xor_data())
        validation["base"][3] = 0
        rows = self.candidates(validation)
        for mode in ("validation_weighted", "validation_constrained"):
            self.assertEqual(choose_rule(rows, mode), (None, "identity_missing_validation_classes"))
        for mode in MATCHED_GROUPS[1:]:
            self.assertEqual(choose_rule(self.candidates(), mode, protected_parent=True),
                             (None, "identity_APP34_parent_protection"))

    def test_empty_leaf_backoff_budget_and_frozen_fit_labels(self):
        fit = collapsed(xor_data())
        fit["joint"][0, :, 1, 1] = 0
        fit["single"] = np.stack((fit["joint"][0].sum(axis=2), fit["joint"][0].sum(axis=1)))
        rows = fit_candidates(fit, fit, np.full(4, .2), np.array([2, 21, 34, 50]), 1, (1, 2), ((1, 2),), (1200,), minimum=1)
        rule = next(r for r in rows if r["kind"] == "joint")
        self.assertEqual(rule["prediction_APPs"][-1], 21)
        self.assertEqual(rule["observed_fit_leaves"], 3)
        self.assertTrue(rule["eligible"])
        self.assertIsNone(choose_rule(self.candidates(minimum=1000), "joint_fit")[0])
        validation = collapsed(xor_data())
        validation["joint"][0, 0], validation["joint"][0, 1] = validation["joint"][0, 1].copy(), validation["joint"][0, 0].copy()
        a, b = self.candidates(), self.candidates(validation)
        self.assertEqual([r["prediction_APPs"] for r in a], [r["prediction_APPs"] for r in b])
        self.assertEqual(choose_rule(a, "joint_fit")[0]["candidate_id"], choose_rule(b, "joint_fit")[0]["candidate_id"])

    def test_calendar_splits_and_boundary_guard(self):
        cache, _, _, _, windows = xor_fixture()
        fixed = next(c for c in windows["contexts"] if c["model"] == "fixed_pilot")
        self.assertEqual(fixed["fit_end_epoch"], epoch("2024-11-01"))
        self.assertEqual(fixed["validation_start_epoch"], epoch("2024-11-02"))
        one = next(c for c in windows["contexts"] if c["target"] == "evaluation/2025-03" and c["model"] == "rolling_1m")
        self.assertEqual(one["fit_end_epoch"], epoch("2025-02-21"))
        self.assertEqual(one["validation_start_epoch"], epoch("2025-02-22"))
        self.assertTrue(all(c["validation_end_epoch"] <= c["target_start_epoch"] for c in windows["contexts"]))
        self.assertEqual(validation_windows(cache, MODELS, gap=0)["gap_seconds"], 0)
        with self.assertRaises(ValueError):
            validation_windows(cache, MODELS, validation_day=1)

    def test_same_marginals_can_hide_different_true_joint_counts(self):
        tables, batches, _, cache = scan_fixture()
        prior = {**protocol(), "size_candidates_bytes": [1000, 1200], "size_positions": [1, 2, 3, 4, 5]}
        windows = validation_windows(cache, MODELS)
        copies = [copy.deepcopy(batches) for _ in range(2)]
        for index, batches2 in enumerate(copies):
            for rows in batches2:
                rows["PPI"][0, 2, :2] = [800, 800 if index == 0 else 1300]
                rows["PPI"][1, 2, :2] = [1300, 1300 if index == 0 else 800]
        counters = []
        for batches2 in copies:
            counter = JointCounts(cache["plan"], tables, time_scale=1, previous_protocol=prior, windows=windows)
            for rows in batches2:
                counter.add(rows, 30)
            counters.append(counter)
        key = "certificate/2024-12"
        np.testing.assert_array_equal(counters[0].atoms[key], counters[1].atoms[key])
        np.testing.assert_array_equal(counters[0].monthly[key][2], counters[1].monthly[key][2])
        self.assertFalse(np.array_equal(counters[0].joints[key][0], counters[1].joints[key][0]))
        for counter in counters:
            check_joint(counter.joints[key], counter.atoms[key][:, :, :, :counter.low_time_atoms], counter.pairs, counter.positions)

    def test_flow_crossing_internal_boundary_keeps_original_population(self):
        tables, batches, _, _ = scan_fixture()
        for table, rows in zip(tables, batches):
            if "D202502" in table["path"]:
                rows["TIME_FIRST"], rows["TIME_LAST"] = epoch("2025-02-20") + 3600, epoch("2025-02-22") + 3600
        audit = PreparationAudit(tables, sample_size=0)
        for rows in batches:
            audit.add(rows, 30)
        plan = audit.plan(min_pilot_flows=1)
        old = RefinementCounts(plan, tables, time_scale=1, size_cuts=(1200,), ipt_cuts=(0, 4, 10), positions=(1, 2))
        for rows in batches:
            old.add(rows, 30)
        cache = {"plan": plan, "known": old.known, "priors": old.priors, "slices": old.slices, "counts": old.monthly, "period_counts": old.counts}
        windows = validation_windows(cache, MODELS)
        counter = JointCounts(plan, tables, time_scale=1, previous_protocol=protocol(), windows=windows)
        for rows in batches:
            counter.add(rows, 30)
        counter.reconcile_joint(cache, old.atoms)
        c = next(c for c in windows["contexts"] if c["target"] == "evaluation/2025-03" and c["model"] == "rolling_1m")
        self.assertGreater(counter.monthly["certificate/2025-02"][2].sum(), 0)
        self.assertEqual(counter.roles[c["fit_id"]]["base"].sum() + counter.roles[c["validation_id"]]["base"].sum(), 0)

    def test_all_class_transfers_period_pooling_and_no_future_selection(self):
        cache, atoms, joints, roles, windows = xor_fixture()
        result = run_joint(cache, roles, joints, atoms, windows, protocol(), {}, minimum=1)
        for row in result["classes"]:
            if row["group"] == "validation_constrained":
                self.assertEqual(row["harmed"], 0)
                self.assertEqual(row["rescued"], 200 if row["APP"] == 2 else 0)
        for r in result["periods"]:
            if r["group"] in MATCHED_GROUPS:
                rows = [c for c in result["period_classes"] if all(c[key] == r[key] for key in ("period", "model", "group"))]
                self.assertEqual([c["APP"] for c in rows], cache["known"].tolist())
                self.assertAlmostEqual(sum(c["weighted_change_vs_time_fit"] for c in rows), r["change_vs_time_fit"]["value"])
        for r in result["confusions"]:
            np.testing.assert_array_equal(np.asarray(r["counts_true_by_predicted"]).sum(axis=1), cache["counts"][r["target"]][2].sum(axis=1))
        joints["evaluation/2025-05"][0, 0] = np.roll(joints["evaluation/2025-05"][0, 0], 1, axis=0)
        later = run_joint(cache, roles, joints, atoms, windows, protocol(), {}, minimum=1)
        self.assertEqual(result["selections"], later["selections"])

    def test_44_fixed_priors_and_missing_fit_class_remain_explicit(self):
        cache, atoms, joints, roles, windows = xor_fixture()
        known = np.array(list(range(43)) + [50])
        index = np.searchsorted(known, cache["known"])
        other = np.setdiff1d(np.arange(44), index)
        cache["known"], cache["priors"] = known, np.full(44, 1 / 45)
        for key in atoms:
            base = np.zeros((44, 1024), dtype=np.int64)
            base[index], base[other, 1] = cache["counts"][key][2], 500
            cache["counts"][key] = {2: base, 1: project_fine(base, 5)}
            a, j = np.zeros((2, 44, 2, 4), dtype=np.int64), np.zeros((1, 44, 2, 2, 2), dtype=np.int64)
            a[:, index], j[:, index] = atoms[key], joints[key]
            atoms[key], joints[key] = a, j
        for role in roles.values():
            base, child = np.zeros((44, 1024), dtype=np.int64), np.zeros((44, 3), dtype=np.int64)
            base[index], base[other, 1], child[index] = role["base"], 200, role["children"]
            a, j = np.zeros((2, 44, 2, 2), dtype=np.int64), np.zeros((1, 44, 2, 2, 2), dtype=np.int64)
            a[:, index], j[:, index] = role["single"], role["joint"]
            role.update(base=base, children=child, single=a, joint=j)
        refresh(cache)
        result = run_joint(cache, roles, joints, atoms, windows, protocol(), {}, minimum=1)
        self.assertTrue(all(len([c for c in result["period_classes"] if all(c[k] == r[k] for k in ("period", "model", "group"))]) == 44 for r in result["periods"]))
        first = windows["contexts"][0]
        roles[first["fit_id"]]["base"][other[0]] = 0
        result = run_joint(cache, roles, joints, atoms, windows, protocol(), {}, minimum=1)
        row = next(r for r in result["selections"] if r["target"] == first["target"] and r["model"] == first["model"])
        self.assertEqual(row["status"], "unavailable_missing_fit_classes")
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_invalid_IPT_frozen_and_missing_target_prior_not_renormalized(self):
        cache, atoms, joints, roles, windows = xor_fixture()
        key = "evaluation/2025-03"
        atoms[key][:, 2, 0, 2] -= 10
        atoms[key][:, 2, 0, 3] += 10
        absent = "evaluation/2025-05"
        cache["counts"][absent][2][0] = 0
        cache["counts"][absent][1] = project_fine(cache["counts"][absent][2], 5)
        atoms[absent][:, 0], joints[absent][:, 0] = 0, 0
        refresh(cache)
        result = run_joint(cache, roles, joints, atoms, windows, protocol(), {}, minimum=1)
        for r in result["monthly"]:
            if r["target"] == absent and r["group"] in MATCHED_GROUPS:
                self.assertIsNone(r["weighted_error"]["value"])
                self.assertAlmostEqual(r["weighted_error"]["unidentified_prior_mass"], .2)
        for r in result["classes"]:
            if r["target"] == absent and r["APP"] == 2:
                self.assertEqual(r["n"], 0)
                self.assertIsNone(r["error"])
            if r["target"] == key and r["APP"] == 34 and r["group"] in MATCHED_GROUPS:
                self.assertEqual(r["harmed"], 0)
        matrices = [np.asarray(r["counts_true_by_predicted"]) for r in result["confusions"]
                    if r["target"] == key and r["model"] == "fixed_pilot" and r["group"] in MATCHED_GROUPS]
        for matrix in matrices[1:]:
            np.testing.assert_array_equal(matrix[2], matrices[0][2])

    def test_full_h5_pipeline_archive_reuse_and_tamper_rejection(self):
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
            path, prepared, experiment, monthly, rolling, refinement, hierarchy, output, reused = (Path(tmp) / name for name in
                ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy", "joint", "reused"))
            tables, batches, _, _ = scan_fixture()
            expanded = []
            for table, rows in zip(tables, batches):
                rows = np.concatenate((rows, rows[:3].copy()))
                rows["APP"][-3:] = 21
                rows["PPI"][0:3, 2, :2] = [[800, 800], [1300, 1300], [800, 800]]
                rows["PPI"][-3:, 2, :2] = [[800, 1300], [1300, 800], [800, 1300]]
                expanded.append((table["path"], rows))
                date = table["path"].split("D")[-1]
                if date[-2:] != "31":
                    late = rows.copy()
                    stamp = epoch(date[:4] + "-" + date[4:6] + "-25")
                    late["TIME_FIRST"], late["TIME_LAST"] = stamp + 3600, stamp + 3700
                    expanded.append(("/flows/D" + date[:6] + "25", late))
            if backend == "tables":
                with module.open_file(str(path), mode="w") as handle:
                    group = handle.create_group("/", "flows")
                    for name, rows in expanded:
                        handle.create_table(group, name.split("/")[-1], obj=rows)
            else:
                with module.File(path, "w") as handle:
                    for name, rows in expanded:
                        handle.create_dataset(name, data=rows)
            args = argparse.Namespace(h5=path, reuse_counts_dir=None, prepare_dir=prepared, monthly_dir=monthly, refinement_dir=refinement,
                hierarchy_dir=hierarchy, out_dir=output, backend=backend, chunk_rows=2, ipt_threshold_ms=4., validation_day=21,
                validation_gap_seconds=DAY, min_leaf_flows=1, app21_budget_pp=.1, max_validation_raw_increase=0, small_n=200)
            with contextlib.redirect_stdout(io.StringIO()):
                run_prepare(argparse.Namespace(h5=path, out_dir=prepared, backend=backend, sha256=True, expected_sha256=None, time_unit="seconds", k=5,
                    gap_seconds=DAY, rounding_seconds=3600, identifier_sample=0, seed=0, block_seconds=[3600, 21600, DAY], max_rows=None, chunk_rows=2, min_pilot_flows=1, alpha=.05))
                run_experiment(argparse.Namespace(h5=path, prepare_dir=prepared, out_dir=experiment, backend=backend, chunk_rows=2, block_seconds=[3600, 21600, DAY]))
                run_monthly(argparse.Namespace(h5=path, prepare_dir=prepared, experiment_dir=experiment, out_dir=monthly, backend=backend, chunk_rows=2, small_n=200, top=3))
                run_rolling(argparse.Namespace(monthly_dir=monthly, out_dir=rolling, app=2, reference_months=["2024-12", "2025-01"], matched_repeats=0, seed=7, small_n=200, top=3))
                run_refinement(argparse.Namespace(h5=path, prepare_dir=prepared, monthly_dir=monthly, rolling_dir=rolling, out_dir=refinement, backend=backend,
                    symbol_id=479, size_positions=None, size_cuts=[1000, 1200], ipt_cuts=[0, 4, 10], models=MODELS, min_leaf_flows=1, chunk_rows=2, small_n=200))
                run_hierarchy(argparse.Namespace(monthly_dir=monthly, refinement_dir=refinement, out_dir=hierarchy, min_leaf_flows=1, small_n=200))
                run(args)
                path.unlink()
                args.h5, args.reuse_counts_dir, args.out_dir = None, output, reused
                run(args)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary, json.loads((reused / "summary.json").read_text()))
            self.assertTrue(summary["counts_reconciled"])
            self.assertEqual(json.loads((reused / "run.json").read_text())["rows_read"], 0)
            self.assertEqual(json.loads((output / "run.json").read_text())["rows_read"], sum(len(rows) for _, rows in expanded))
            self.assertTrue(any(r["rule"] and r["rule"]["kind"] == "joint" for r in summary["selections"]))
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            args.out_dir, args.app21_budget_pp = Path(tmp) / "new_budget", .2
            with contextlib.redirect_stdout(io.StringIO()):
                run(args)
            self.assertEqual(json.loads((args.out_dir / "selection_protocol.json").read_text())["APP21_validation_budget_pp"], .2)
            args.out_dir, args.validation_day = Path(tmp) / "bad_geometry", 20
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "geometry"):
                run(args)
            args.out_dir, args.validation_day = Path(tmp) / "bad_hash", 21
            with (output / "joint_counts.npz").open("ab") as handle:
                handle.write(b"changed")
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "hash mismatch"):
                run(args)


if __name__ == "__main__":
    unittest.main()
