"""Origin refitting, chronological isolation, monthly budgets and cache lineage."""

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
from eibo.forwardvalidation import (GROUPS, check_roles, evaluate_forward, forward_windows, role_data, scored_family, select_context, select_forward)
from eibo.realdata import DAY
from eibo.rolling import project_fine
from methodology_real_forward import run
from methodology_real_blocks import run as run_blocks
from methodology_real_joint import run as run_joint_cli
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run as run_refinement
from methodology_real_hierarchy import run as run_hierarchy
from test_block_validation_riskcert import block_fixture, evaluate as evaluate_blocks
from test_joint_refinement_riskcert import MODELS, refresh, xor_data
from test_refinement_riskcert import scan_fixture


def collapsed(scale=1, *, flip=False):
    data = xor_data(scale)
    if flip:
        data["joint"] = data["joint"][:, :, :, ::-1, :].copy()
        data["single"] = np.stack((data["joint"][0].sum(axis=2), data["joint"][0].sum(axis=1)))
    return {**data, "single": data["single"].sum(axis=3), "joint": data["joint"].sum(axis=4)}


def forward_fixture():
    old = block_fixture()
    cache, atoms, joints, _, collection0, protocol, _ = old
    previous = {(r["target"], r["model"], "previous_time" if r["group"] == "time_baseline" else "previous_blocks"):
                np.asarray(r["counts_true_by_predicted"], dtype=np.int64) for r in evaluate_blocks(old)["confusions"] if r["group"] in ("time_baseline", "block_constraints")}
    windows = forward_windows(cache["slices"], collection0["window_spec"])
    collection = {**collection0, "window_spec": windows}
    roles = {r["id"]: collapsed(2) for r in windows["ranges"]}
    return cache, atoms, joints, roles, collection, protocol, previous


def select(values):
    return select_forward(values[3], values[4], values[5])


def evaluate(values, choices=None):
    return evaluate_forward(values[0], values[3], values[2], values[1], values[4], values[5], choices or select(values), values[6])


class TestForwardValidation(unittest.TestCase):
    def test_each_fit_precedes_whole_validation_month_and_history_precedes_target(self):
        values = forward_fixture()
        windows = values[4]["window_spec"]
        nodes = {n["id"]: n for n in windows["nodes"]}
        for node in nodes.values():
            if node["status"] == "ready":
                self.assertLessEqual(node["fit_end_epoch"] + DAY, node["validation_start_epoch"])
        for c in windows["contexts"]:
            for token in c["history_node_ids"]:
                if token in nodes:
                    self.assertLessEqual(nodes[token]["validation_end_epoch"], c["target_start_epoch"])
        march = next(c for c in windows["contexts"] if c["target"] == "evaluation/2025-03" and c["model"] == "rolling_1m")
        self.assertEqual(march["history_node_ids"], [m + "/rolling_1m" for m in ("2024-12", "2025-01", "2025-02")])
        self.assertEqual(nodes["2025-01/rolling_1m"]["training_slices"], ["certificate/2024-12"])

    def test_historical_labels_are_refitted_and_never_copied_to_current_rule(self):
        values = forward_fixture()
        col, p = values[4:6]
        current_data = role_data(collapsed(), col)
        reversed_data = role_data(collapsed(flip=True), col)
        current = scored_family(current_data, current_data, col, 1)
        a = scored_family(current_data, current_data, col, 1)
        b = scored_family(reversed_data, reversed_data, col, 1)
        chosen, _ = select_context(current, [a, b, a], col, p)
        rule = chosen["all_months"]["rule"]
        self.assertIsNotNone(rule)
        i = rule["candidate_id"]
        self.assertNotEqual(a["rows"][i]["prediction_APPs"], b["rows"][i]["prediction_APPs"])
        self.assertEqual(rule["prediction_APPs"], current["rows"][i]["prediction_APPs"])
        self.assertNotIn("validation_weighted_change", rule)

    def test_pooled_months_can_hide_APP21_budget_violation(self):
        values = forward_fixture()
        col, p = values[4], {**values[5], "APP21_validation_budget_pp": .5}
        fit = role_data(collapsed(), col)
        bad = copy.deepcopy(fit)
        bad["joint"][0, 1, 0, 1] -= 1
        bad["joint"][0, 1, 0, 0] += 1
        current = scored_family(fit, fit, col, 1)
        normal, diluted = scored_family(fit, fit, col, 1), scored_family(fit, bad, col, 1)
        choices, _ = select_context(current, [diluted, normal, normal], col, p)
        self.assertIsNotNone(choices["pooled_months"]["rule"])
        self.assertIsNone(choices["all_months"]["rule"])

    def test_pooled_months_can_hide_positive_raw_errors(self):
        values = forward_fixture()
        col, p = values[4], {**values[5], "APP21_validation_budget_pp": 100}
        fit = role_data(collapsed(), col)
        bad = copy.deepcopy(fit)
        bad["joint"][0, 0, 0, 0] = bad["joint"][0, 0, 1, 1] = 0
        bad["joint"][0, 0, 0, 1] = 40
        bad["joint"][0, 1, 0, 1] -= 1
        bad["joint"][0, 1, 0, 0] += 1
        current = scored_family(fit, fit, col, 1)
        normal, harmful = scored_family(fit, fit, col, 1), scored_family(fit, bad, col, 1)
        choices, _ = select_context(current, [harmful, normal, normal], col, p)
        self.assertIsNotNone(choices["pooled_months"]["rule"])
        self.assertIsNone(choices["all_months"]["rule"])

    def test_missing_history_classes_and_historical_fit_support_force_identity(self):
        values = forward_fixture()
        col, p = values[4:6]
        fit, val = role_data(collapsed(2), col), role_data(collapsed(), col)
        current = scored_family(fit, fit, col, 25)
        strong, weak = scored_family(fit, val, col, 25), scored_family(val, val, col, 25)
        chosen, _ = select_context(current, [weak, strong, strong], col, p)
        self.assertIsNotNone(chosen["latest_month"]["rule"])
        self.assertIsNone(chosen["all_months"]["rule"])
        missing = copy.deepcopy(strong)
        missing["ns"][3] = 0
        chosen, _ = select_context(current, [missing, strong, strong], col, p)
        self.assertEqual(chosen["all_months"]["status"], "identity_missing_validation_classes")

    def test_missing_calendar_history_does_not_use_target_or_shrink_month_count(self):
        values = forward_fixture()
        selected = select(values)
        fixed_dec = [r for r in selected["selections"] if r["target"] == "certificate/2024-12" and r["model"] == "fixed_pilot" and r["group"] == "all_months"]
        self.assertEqual(fixed_dec[0]["status"], "identity_unavailable_past_month")
        self.assertEqual(len(fixed_dec[0]["history_node_ids"]), 3)

    def test_target_month_labels_cannot_change_own_or_earlier_choices(self):
        values = forward_fixture()
        before = select(values)
        node = next(n for n in values[4]["window_spec"]["nodes"] if n["id"] == "2025-03/rolling_1m")
        values[3][node["validation_id"]] = collapsed(0)
        after = select(values)
        earlier = lambda r: r["target"] <= "evaluation/2025-03"
        self.assertEqual([r for r in before["selections"] if earlier(r)], [r for r in after["selections"] if earlier(r)])
        self.assertNotEqual([r for r in before["selections"] if r["target"] == "evaluation/2025-05"], [r for r in after["selections"] if r["target"] == "evaluation/2025-05"])

    def test_population_transfers_and_reference_controls_are_exact(self):
        values = forward_fixture()
        check_roles(values[3], values[4])
        result = evaluate(values)
        for r in result["confusions"]:
            np.testing.assert_array_equal(np.asarray(r["counts_true_by_predicted"]).sum(axis=1), values[0]["counts"][r["target"]][2].sum(axis=1))
            if r["group"] in GROUPS[:2]:
                np.testing.assert_array_equal(r["counts_true_by_predicted"], values[-1][r["target"], r["model"], r["group"]])
        self.assertTrue(all(r["harmed"] == 0 for r in result["classes"] if r["APP"] == 34 and r["group"] in GROUPS[2:]))
        self.assertTrue(all(r["both_met"] for r in result["budget_monthly"]))
        for r in result["classes"]:
            if r["rescued"] is not None:
                self.assertEqual(r["harmed"] - r["rescued"], r["wrong_change_vs_time_baseline"])

    def test_parent_protection_applies_to_current_and_historical_origins(self):
        values = forward_fixture()
        fit = role_data(collapsed(), values[4])
        current = scored_family(fit, fit, values[4], 1)
        protected = copy.deepcopy(current)
        protected["protected_parent"] = True
        chosen, _ = select_context(protected, [current] * 3, values[4], values[5])
        self.assertTrue(all(r["status"] == "identity_APP34_parent_protection" for r in chosen.values()))
        chosen, _ = select_context(current, [protected, current, current], values[4], values[5])
        self.assertIsNotNone(chosen["latest_month"]["rule"])
        self.assertIsNone(chosen["pooled_months"]["rule"])
        self.assertIsNone(chosen["all_months"]["rule"])

    def test_missing_current_fit_keeps_previous_controls_and_all_class_rows(self):
        values = forward_fixture()
        node = next(n for n in values[4]["window_spec"]["nodes"] if n["id"] == "2025-05/rolling_1m")
        values[3][node["fit_id"]]["base"][0] = 0
        result = evaluate(values)
        rows = [r for r in result["metrics"] if r["target"] == "evaluation/2025-05" and r["model"] == "rolling_1m"]
        self.assertTrue(all(r["status"] == "complete" for r in rows if r["group"] in GROUPS[:2]))
        self.assertTrue(all(r["status"] == "unavailable_fit_model" for r in rows if r["group"] in GROUPS[2:]))
        for row in rows:
            classes = [r for r in result["classes"] if all(r[k] == row[k] for k in ("scope", "target", "model", "group"))]
            self.assertEqual([r["APP"] for r in classes], values[0]["known"].tolist())

    def test_unavailable_old_control_does_not_block_a_complete_current_fit(self):
        values = forward_fixture()
        del values[-1]["evaluation/2025-05", "rolling_1m", "previous_blocks"]
        result = evaluate(values)
        rows = [r for r in result["metrics"] if r["target"] == "evaluation/2025-05" and r["model"] == "rolling_1m"]
        self.assertTrue(all(r["status"] == "complete" for r in rows if r["group"] in GROUPS[2:]))
        self.assertEqual(next(r for r in rows if r["group"] == "previous_blocks")["status"], "unavailable_fit_model")
        self.assertTrue(all(r["change_vs_previous_blocks"] is None for r in rows))

    def test_all_44_classes_and_fixed_prior_contributions(self):
        cache, atoms, joints, roles, collection0, protocol, _ = forward_fixture()
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
            base[index], base[other, 1], children[index] = role["base"], 200, role["children"]
            a, j = np.zeros((2, 44, 2), dtype=np.int64), np.zeros((1, 44, 2, 2), dtype=np.int64)
            a[:, index], j[:, index] = role["single"], role["joint"]
            role.update(base=base, children=children, single=a, joint=j)
        refresh(cache)
        collection = {**collection0, "known_service_codes": known.tolist(), "known_priors": cache["priors"].tolist(), "unknown_prior": 1 / 45}
        previous = {}
        for c in collection["window_spec"]["contexts"]:
            matrix = np.zeros((44, 44), dtype=np.int64)
            matrix[:, 0] = cache["counts"][c["target"]][2].sum(axis=1)
            for group in GROUPS[:2]:
                previous[c["target"], c["model"], group] = matrix
        result = evaluate((cache, atoms, joints, roles, collection, protocol, previous))
        for metric in result["metrics"]:
            rows = [r for r in result["classes"] if all(r[k] == metric[k] for k in ("scope", "target", "model", "group"))]
            self.assertEqual([r["APP"] for r in rows], known.tolist())
            self.assertAlmostEqual(sum(r["weighted_change_vs_time_baseline"] for r in rows), metric["change_vs_time_baseline"]["value"])
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_future_drift_can_still_break_all_month_constraints(self):
        values = forward_fixture()
        choices = select(values)
        key = "evaluation/2025-05"
        values[2][key][0, 1, 0, 1, 1] -= 10
        values[2][key][0, 1, 0, 0, 1] += 10
        values[1][key][0, :, :, :2], values[1][key][1, :, :, :2] = values[2][key][0].sum(axis=2), values[2][key][0].sum(axis=1)
        result = evaluate(values, choices)
        self.assertTrue(all(r["APP21_met"] is False for r in result["budget_monthly"] if r["target"] == key and r["group"] == "all_months"))

    def test_period_pooling_and_target_missing_class_keep_prior_range(self):
        values = forward_fixture()
        key = "evaluation/2025-05"
        values[0]["counts"][key][2][3] = 0
        values[0]["counts"][key][1] = project_fine(values[0]["counts"][key][2], 5)
        values[1][key][:, 3], values[2][key][:, 3] = 0, 0
        for token in values[-1]:
            if token[0] == key:
                values[-1][token][3] = 0
        refresh(values[0])
        result = evaluate(values)
        monthly = next(r for r in result["metrics"] if r["target"] == key and r["group"] == "all_months")
        self.assertIsNone(monthly["weighted_error"]["value"])
        self.assertGreater(monthly["weighted_error"]["unidentified_prior_mass"], 0)
        for r in result["classes"]:
            if r["scope"] == "period":
                rows = [s for s in result["classes"] if s["scope"] == "monthly" and all(s[k] == r[k] for k in ("period", "model", "group", "APP"))]
                self.assertEqual(sum(s["wrong"] for s in rows), r["wrong"])

    def test_full_pipeline_fixed_audit_raw_cache_parity_and_tampering(self):
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
            path, prepared, experiment, monthly, rolling, refinement, hierarchy, joint, blocks, output, reused = (Path(tmp) / name for name in
                ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy", "joint", "blocks", "forward", "reused"))
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
                hierarchy_dir=hierarchy, joint_dir=joint, blocks_dir=blocks, out_dir=output, backend=backend, chunk_rows=2, history_months=3, small_n=200)
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
                run_blocks(argparse.Namespace(h5=path, reuse_counts_dir=None, prepare_dir=prepared, monthly_dir=monthly, refinement_dir=refinement,
                    hierarchy_dir=hierarchy, joint_dir=joint, out_dir=blocks, backend=backend, chunk_rows=2, blocks=3, small_n=200))
                run(args)
                path.unlink()
                args.h5, args.reuse_counts_dir, args.out_dir = None, output, reused
                run(args)
            self.assertEqual(json.loads((output / "summary.json").read_text()), json.loads((reused / "summary.json").read_text()))
            self.assertEqual(json.loads((output / "frozen_selections.json").read_text()), json.loads((reused / "frozen_selections.json").read_text()))
            self.assertEqual(json.loads((reused / "run.json").read_text())["rows_read"], 0)
            self.assertTrue((output / "fixed_pilot_past_audit.csv").is_file())
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertIn("FAMILY", (output / "report.md").read_text())
            with (output / "role_counts.npz").open("ab") as handle:
                handle.write(b"changed")
            args.out_dir = Path(tmp) / "bad"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "hash mismatch"):
                run(args)


if __name__ == "__main__":
    unittest.main()
