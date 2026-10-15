"""Common-support temporal objectives, qualification causes and cached replay."""

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
from eibo.forwardvalidation import evaluate_forward, select_context, select_forward
from eibo.recencyaudit import MATCHED, evaluate_matched, matched_choices, past_table, recency_weights, select_and_audit
from eibo.realdata import DAY
from eibo.rolling import project_fine
from methodology_real_recency import run
from methodology_real_forward import run as run_forward
from methodology_real_blocks import run as run_blocks
from methodology_real_joint import run as run_joint_cli
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run as run_refinement
from methodology_real_hierarchy import run as run_hierarchy
from test_forward_validation_riskcert import forward_fixture
from test_joint_refinement_riskcert import MODELS, refresh
from test_refinement_riskcert import scan_fixture


def score_fixture(gains=((10, 1), (10, 1), (1, 8)), denominators=(100, 100, 100)):
    collection = {"known_service_codes": [2, 21, 34, 50], "known_priors": [.2] * 4}
    protocol = {"APP21_validation_budget_pp": .1, "maximum_validation_raw_wrong_increase": 0}
    rows = [{"candidate_id": i, "eligible": True, "observed_fit_leaves": 2, "kind": "single", "positions": [1], "indices": [i],
             "prediction_indices": [0, 1], "prediction_APPs": [2, 21], "fit_gain": .1} for i in range(2)]
    current = {"rows": rows, "protected_parent": False}
    folds = []
    for counts, n in zip(gains, denominators):
        ns = np.array([n, 100, 100, 100])
        deltas = np.array([[-count, 0, 0, 0] for count in counts])
        scored = [{**r, "validation_complete": True, "validation_weighted_change": float(np.dot(collection["known_priors"], deltas[i] / ns)),
            "validation_raw_wrong_change": int(deltas[i].sum()), "APP21_validation_conditional_change": 0.} for i, r in enumerate(rows)]
        folds.append({"rows": scored, "deltas": deltas, "ns": ns, "protected_parent": False})
    return current, folds, collection, protocol


def recency(values, *, ratio=2.):
    source_selected = select_forward(values[3], values[4], values[5])
    source_result = evaluate_forward(values[0], values[3], values[2], values[1], values[4], values[5], source_selected, values[6])
    selected = select_and_audit(values[3], values[4], values[5], source_selected, ratio=ratio)
    result = evaluate_matched(values[0], values[3], values[2], values[1], values[4], values[5], selected, source_selected, source_result, values[6])
    return selected, result, source_result


class TestRecencyAudit(unittest.TestCase):
    def test_geometric_weights_are_prespecified_normalized_and_numerically_stable(self):
        np.testing.assert_allclose(recency_weights(3, 2), [1 / 7, 2 / 7, 4 / 7])
        np.testing.assert_allclose(recency_weights(3, 1), [1 / 3] * 3)
        self.assertTrue(np.isfinite(recency_weights(100, 1e300)).all())
        for value in (0, .5, np.nan, np.inf):
            with self.assertRaises(ValueError):
                recency_weights(3, value)

    def test_uniform_and_recent_change_only_the_month_weights(self):
        current, folds, col, p = score_fixture()
        table = past_table(current, folds, col, p)
        chosen = matched_choices(current, table)
        self.assertEqual(chosen["shared_latest"]["rule"]["candidate_id"], 1)
        self.assertEqual(chosen["shared_uniform"]["rule"]["candidate_id"], 0)
        self.assertEqual(chosen["shared_recent"]["rule"]["candidate_id"], 1)
        self.assertTrue(all(r["common_support"] and r["latest_budget_ok"] for r in table))
        unit = matched_choices(current, past_table(current, folds, col, p, ratio=1))
        self.assertEqual(unit["shared_uniform"]["rule"], unit["shared_recent"]["rule"])

    def test_class_count_pooling_and_equal_month_averaging_can_rank_differently(self):
        current, folds, col, p = score_fixture(((10, 100), (10, 0), (1, 0)), (10000, 100, 100))
        chosen = matched_choices(current, past_table(current, folds, col, p))
        self.assertEqual(chosen["shared_pooled"]["rule"]["candidate_id"], 1)
        self.assertEqual(chosen["shared_uniform"]["rule"]["candidate_id"], 0)

    def test_historical_support_can_remove_a_recent_winner(self):
        current, folds, col, p = score_fixture()
        folds[0]["rows"][1]["eligible"] = False
        source, _ = select_context(current, folds, col, p)
        self.assertEqual(source["latest_month"]["rule"]["candidate_id"], 1)
        table = past_table(current, folds, col, p)
        chosen = matched_choices(current, table)
        self.assertFalse(table[1]["common_support"])
        self.assertEqual(chosen["shared_latest"]["rule"]["candidate_id"], 0)
        self.assertTrue(table[1]["latest_budget_ok"])

    def test_older_budget_failure_is_separate_from_support_and_objective(self):
        current, folds, col, p = score_fixture()
        # Candidate 1 is a recent winner, with an old APP21 cost but good support.
        folds[0]["rows"][1]["APP21_validation_conditional_change"] = .01
        table = past_table(current, folds, col, p)
        chosen = matched_choices(current, table)
        self.assertTrue(table[1]["common_support"] and table[1]["latest_budget_ok"])
        self.assertFalse(table[1]["strict_budget_ok"])
        self.assertEqual(chosen["shared_latest"]["rule"]["candidate_id"], 1)
        self.assertEqual(chosen["strict_latest"]["rule"]["candidate_id"], 0)

    def test_positive_raw_budget_also_keeps_original_pooled_budget(self):
        current, folds, col, p = score_fixture()
        p["maximum_validation_raw_wrong_increase"] = 1
        for fold in folds:
            fold["deltas"][1] = [1, 0, 0, 0]
            fold["rows"][1]["validation_raw_wrong_change"] = 1
        table = past_table(current, folds, col, p)
        self.assertTrue(all(table[1]["month_raw_ok"]))
        self.assertFalse(table[1]["pooled_raw_ok"])
        self.assertFalse(table[1]["strict_budget_ok"])

    def test_missing_history_or_class_retains_identity_and_protection(self):
        current, folds, col, p = score_fixture()
        table = past_table(current, [None, folds[1], folds[2]], col, p)
        self.assertTrue(all(r["status"] == "identity_unavailable_history" for r in matched_choices(current, table).values()))
        folds[0]["ns"][3] = 0
        table = past_table(current, folds, col, p)
        self.assertTrue(all(r["status"] == "identity_missing_history_classes" for r in matched_choices(current, table).values()))
        current["protected_parent"] = True
        self.assertTrue(all(r["status"] == "identity_APP34_parent_protection" for r in matched_choices(current, table).values()))

    def test_actual_old_all_month_rules_and_target_confusions_are_reproduced(self):
        selected, result, original = recency(forward_fixture())
        old = {(r["target"], r["model"]): r["counts_true_by_predicted"] for r in original["confusions"] if r["group"] == "all_months"}
        for r in result["confusions"]:
            if r["group"] == "strict_pooled":
                self.assertEqual(r["counts_true_by_predicted"], old[r["target"], r["model"]])
        self.assertEqual(len(selected["selections"]), 18 * len(MATCHED))
        self.assertTrue(all(r["harmed"] == 0 for r in result["classes"] if r["APP"] == 34))

    def test_future_target_labels_do_not_enter_new_selection(self):
        values = forward_fixture()
        source = select_forward(values[3], values[4], values[5])
        before = select_and_audit(values[3], values[4], values[5], source)
        node = next(n for n in values[4]["window_spec"]["nodes"] if n["id"] == "2025-05/rolling_1m")
        for field in values[3][node["validation_id"]]:
            values[3][node["validation_id"]][field][:] = 0
        after = select_and_audit(values[3], values[4], values[5], source)
        self.assertEqual(before, after)

    def test_class_net_changes_and_period_pooling_are_exact(self):
        values = forward_fixture()
        _, result, _ = recency(values)
        for metric in result["metrics"]:
            rows = [r for r in result["classes"] if all(r[k] == metric[k] for k in ("scope", "target", "model", "group"))]
            self.assertEqual([r["APP"] for r in rows], values[0]["known"].tolist())
            self.assertEqual(sum(r["wrong_change_vs_source_latest"] for r in rows), metric["raw_change_vs_source_latest"])
            self.assertAlmostEqual(sum(r["weighted_change_vs_source_latest"] for r in rows), metric["change_vs_source_latest"]["value"])
        for r in result["classes"]:
            if r["scope"] == "period":
                rows = [s for s in result["classes"] if s["scope"] == "monthly" and all(s[k] == r[k] for k in ("period", "model", "group", "APP"))]
                self.assertEqual(sum(s["wrong"] for s in rows), r["wrong"])

    def test_missing_target_class_keeps_NA_and_original_prior_mass(self):
        values = forward_fixture()
        key = "evaluation/2025-05"
        values[0]["counts"][key][2][3] = 0
        values[0]["counts"][key][1] = project_fine(values[0]["counts"][key][2], 5)
        values[1][key][:, 3], values[2][key][:, 3] = 0, 0
        for token in values[-1]:
            if token[0] == key:
                values[-1][token][3] = 0
        refresh(values[0])
        _, result, _ = recency(values)
        row = next(r for r in result["metrics"] if r["target"] == key and r["group"] == "shared_recent")
        self.assertIsNone(row["weighted_error"]["value"])
        self.assertIsNone(row["change_vs_source_latest"]["value"])
        self.assertGreater(row["change_vs_source_latest"]["unidentified_prior_mass"], 0)

    def test_unavailable_current_fit_is_not_reported_as_identity_success(self):
        values = forward_fixture()
        node = next(n for n in values[4]["window_spec"]["nodes"] if n["id"] == "2025-05/rolling_1m")
        values[3][node["fit_id"]]["base"][0] = 0
        selected, result, _ = recency(values)
        rows = [r for r in selected["selections"] if r["target"] == "evaluation/2025-05" and r["model"] == "rolling_1m"]
        self.assertTrue(all(r["status"] == "unavailable_current_fit" for r in rows))
        metrics = [r for r in result["metrics"] if r["target"] == "evaluation/2025-05" and r["model"] == "rolling_1m"]
        self.assertTrue(all(r["weighted_error"] is None for r in metrics))
        budgets = [r for r in result["budget_summary"] if r["period"] == "evaluation" and r["model"] == "rolling_1m"]
        self.assertTrue(all(r["checked"] == 2 and r["available"] == 2 and r["expected"] == 3 for r in budgets))

    def test_all_44_classes_and_fixed_priors_are_retained(self):
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
            for group in ("previous_time", "previous_blocks"):
                previous[c["target"], c["model"], group] = matrix
        _, result, _ = recency((cache, atoms, joints, roles, collection, protocol, previous))
        for metric in result["metrics"]:
            rows = [r for r in result["classes"] if all(r[k] == metric[k] for k in ("scope", "target", "model", "group"))]
            self.assertEqual([r["APP"] for r in rows], known.tolist())
            self.assertAlmostEqual(sum(r["weighted_change_vs_source_latest"] for r in rows), metric["change_vs_source_latest"]["value"])
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_complete_pipeline_no_H5_and_source_tamper_rejection(self):
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
            path, prepared, experiment, monthly, rolling, refinement, hierarchy, joint, blocks, forward, output = (Path(tmp) / name for name in
                ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy", "joint", "blocks", "forward", "recency"))
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
                joint_dir=joint, blocks_dir=blocks, forward_dir=forward, out_dir=output, recency_ratio=2., small_n=200)
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
                run_forward(argparse.Namespace(h5=path, reuse_counts_dir=None, prepare_dir=prepared, monthly_dir=monthly, refinement_dir=refinement,
                    hierarchy_dir=hierarchy, joint_dir=joint, blocks_dir=blocks, out_dir=forward, backend=backend, chunk_rows=2, history_months=3, small_n=200))
                path.unlink()
                run(args)
            self.assertEqual(json.loads((output / "run.json").read_text())["rows_read"], 0)
            self.assertTrue(json.loads((output / "invariants.json").read_text())["strict_pooled_rule_equals_source_all"])
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertTrue((output / "latest_choice_exclusions.csv").is_file())
            frozen = (forward / "frozen_selections.json").read_bytes()
            with (forward / "frozen_selections.json").open("ab") as handle:
                handle.write(b"changed")
            args.out_dir = Path(tmp) / "bad_artifact"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "hash mismatch"):
                run(args)
            (forward / "frozen_selections.json").write_bytes(frozen)
            metadata = json.loads((forward / "run.json").read_text())
            metadata["code"][0]["sha256"] = "0" * 64
            (forward / "run.json").write_text(json.dumps(metadata))
            args.out_dir = Path(tmp) / "bad_code"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "code lineage"):
                run(args)


if __name__ == "__main__":
    unittest.main()
