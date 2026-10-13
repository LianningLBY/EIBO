"""Hierarchical transfer identities, frozen decisions, chronology and cache replay."""

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
from eibo.hierarchy import (branch_context, fit_low_prediction, low_children, run_hierarchy, select_low_size)
from eibo.refinement import collapse_atoms, fit_prediction, refine_counts, run_refinements, select_splits
from eibo.realdata import DAY
from eibo.realexperiment import histogram_predictions
from eibo.rolling import project_fine
from methodology_real_hierarchy import (check_baselines, compare_replay, read_refinement, run, validate_atoms)
from methodology_real_prepare import run as run_prepare, sha256
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling, read_cache
from methodology_real_refinement import run as run_refinement
from test_refinement_riskcert import scan_fixture


def competing_atoms():
    values = np.zeros((2, 4, 2, 3), dtype=np.int64)
    values[:, 0, 0, 0] = 30  # APP2: small size, low IPT
    values[:, 1, 1, 0] = 60  # APP21: large size, low IPT
    values[:, 2, 0, 1] = 40  # APP34: high IPT in both size leaves
    values[:, 2, 1, 1] = 40
    values[:, 3, 1, 0] = 20  # APP50 also competes in low IPT
    values[:, 3, 0, 1] = 50  # Crossed size split steals high-IPT APP34 decisions
    return values


def competing_cache():
    _, _, _, cache = scan_fixture()
    cache["known"], cache["priors"] = np.array([2, 21, 34, 50]), np.full(4, .2)
    values = competing_atoms()
    base = np.zeros((4, 1024), dtype=np.int64)
    base[:, 479] = values[0].sum(axis=(1, 2))
    base[:, 1] = 100 - base[:, 479]
    cache["counts"] = {item["key"]: {2: base.copy(), 1: project_fine(base, 5)} for item in cache["slices"]}
    cache["period_counts"] = {period: {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == period)
                                        for r in (1, 2)} for period in ("pilot", "certificate", "evaluation")}
    atoms = {item["key"]: values.copy() for item in cache["slices"]}
    return cache, atoms


def run_competing(cache, atoms, **kwargs):
    return run_hierarchy(cache, atoms, positions=(1, 2), size_cuts=(1200,), ipt_cuts=(4,), root_min_leaf=1, min_leaf=1, **kwargs)


class TestHierarchy(unittest.TestCase):
    def test_low_split_rescues_APP2_and_freezes_high_APP34(self):
        cache, atoms = competing_cache()
        result = run_competing(cache, atoms)
        previous = run_refinements(cache, atoms, positions=(1, 2), size_cuts=(1200,), ipt_cuts=(4,), min_leaf=1)
        check_baselines(result, previous)
        for row in result["selections"]:
            self.assertEqual(row["low_branch_prediction_APP"], 21)
            self.assertEqual(row["low_size_cut"]["child_predictions_APP"], [2, 21])
            self.assertEqual(row["low_size_cut"]["size_position"], 1)
            self.assertAlmostEqual(row["low_size_cut"]["training_empirical_gain"], .06)
            self.assertTrue(row["APP34_pointwise_no_harm_relative_to_IPT"])
            self.assertEqual(row["pointwise_no_harm_APPs_relative_to_IPT"], [2, 34, 50])
        for row in result["classes"]:
            if row["group"] == "low_size_split":
                self.assertEqual(row["harmed_from_IPT"], 0)
                if row["APP"] == 2:
                    self.assertEqual(row["rescued_from_IPT"], 30)
            if row["group"] == "crossed_size_ipt" and row["APP"] == 34:
                self.assertAlmostEqual(row["conditional_change_from_IPT"], .4)
        for row in result["monthly"]:
            if row["group"] == "low_size_split":
                self.assertAlmostEqual(row["empirical_gain_from_IPT"], .06)
                self.assertAlmostEqual(row["error_change_from_IPT"]["value"], -.06)

    def test_full_class_denominators_and_deterministic_ties(self):
        values, known, ns, priors = competing_atoms(), np.array([2, 21, 34, 50]), np.full(4, 100), np.full(4, .2)
        root, _ = select_splits(values, ns, priors, (1, 2), (1200,), (4,), min_leaf=1)
        cut, rows = select_low_size(values, ns, priors, known, (1, 2), (1200,), root["ipt"], 1, min_leaf=1)
        self.assertEqual(cut["size_position"], 1)
        self.assertAlmostEqual(cut["training_empirical_gain"], .06)
        self.assertEqual(sum(row["selected"] for row in rows), 1)
        # Renormalizing by low-cell class counts would tie classes; full-class
        # denominators instead make APP2's score 30 * .2 / 100 = .06.
        self.assertAlmostEqual(cut["APP2_training_weighted_gain"], .06)

    def test_no_positive_gain_or_leaf_budget_keeps_identity(self):
        values, known, ns, priors = competing_atoms(), np.array([2, 21, 34, 50]), np.full(4, 100), np.full(4, .2)
        root, _ = select_splits(values, ns, priors, (1, 2), (1200,), (4,), min_leaf=1)
        cut, _ = select_low_size(values, ns, priors, known, (1, 2), (1200,), root["ipt"], 1, min_leaf=1000)
        self.assertIsNone(cut)
        a, labels, mapping = low_children(values, (1, 2), root, cut)
        b, _ = collapse_atoms(values, (1, 2), root, "ipt_split")
        np.testing.assert_array_equal(a, b)
        np.testing.assert_array_equal(mapping, [0, 1, 2])
        # Put every low-IPT class in the same size atom: eligible zero-gain
        # candidates must not introduce a gratuitous split.
        values[:, :, 0, 0] += values[:, :, 1, 0]
        values[:, :, 1, 0] = 0
        cut, _ = select_low_size(values, ns, priors, known, (1, 2), (1200,), root["ipt"], 1, min_leaf=1)
        self.assertIsNone(cut)
        values[:, :, :, 0] = 0
        values[:, 0, :, 0], values[:, 1, :, 0] = 10, 30
        cut, rows = select_low_size(values, ns, priors, known, (1, 2), (1200,), root["ipt"], 1, min_leaf=1)
        self.assertTrue(all(row["eligible"] for row in rows))
        self.assertTrue(all(abs(row["training_empirical_gain"]) < 1e-12 for row in rows))
        self.assertIsNone(cut)
        self.assertEqual(select_low_size(values, ns, priors, known, (1, 2), (1200,), None, 1), (None, []))

    def test_only_former_low_winner_can_be_harmed_under_future_shift(self):
        cache, atoms = competing_cache()
        key = "evaluation/2025-05"
        # APP21 moves into the low size child won by APP2 in past training.
        atoms[key][:, 1, 0, 0], atoms[key][:, 1, 1, 0] = 30, 30
        # Invalid IPT is also retained, with its IPT-only parent decision.
        atoms[key][:, 2, 0, 1] -= 10
        atoms[key][:, 2, 0, 2] += 10
        result = run_competing(cache, atoms)
        rows = [r for r in result["classes"] if r["target"] == key and r["model"] == "fixed_pilot" and r["group"] == "low_size_split"]
        self.assertEqual(next(r for r in rows if r["APP"] == 21)["harmed_from_IPT"], 30)
        self.assertEqual(next(r for r in rows if r["APP"] == 2)["rescued_from_IPT"], 30)
        self.assertTrue(all(r["harmed_from_IPT"] == 0 for r in rows if r["APP"] != 21))
        parent = [r for r in result["competition"] if r["target"] == key and r["model"] == "fixed_pilot" and r["view"] == "IPT_parent"]
        children = [r for r in result["competition"] if r["target"] == key and r["model"] == "fixed_pilot" and r["view"] == "hierarchical_child"]
        for branch in (1, 2):
            a = next(r for r in parent if r["child"] == branch)
            b = next(r for r in children if r["child"] == branch + 1)
            self.assertEqual(a["trained_prediction_APP"], b["trained_prediction_APP"])

    def test_unseen_low_child_backs_off_to_IPT_parent(self):
        values = competing_atoms()
        ns, priors = np.full(4, 100), np.full(4, .2)
        selection, _ = select_splits(values, ns, priors, (1, 2), (1200,), (4,), min_leaf=1)
        cut = {"size_position": 1, "size_threshold_bytes": 1200, "atom_index": 0}
        values[:, :, 0, 0] = 0  # New left low child unobserved in training
        base = np.zeros((4, 1024), dtype=np.int64)
        base[:, 479] = values[0].sum(axis=(1, 2))
        base[:, 1] = ns - base[:, 479]
        original, _ = histogram_predictions(base, priors)
        self.assertEqual(original[479], 2)  # APP34 coarse prediction
        root, _ = collapse_atoms(values, (1, 2), selection, "ipt_split")
        prediction, leaves, _ = fit_prediction(refine_counts(base, root, 479), priors, original, 479, 1024)
        self.assertEqual(prediction[leaves[0]], 1)  # APP21 low parent
        children, _, parent_map = low_children(values, (1, 2), selection, cut)
        refined, new_leaves, unseen = fit_low_prediction(refine_counts(base, children, 479), priors, prediction, leaves, parent_map, 479, 1024)
        self.assertTrue(unseen[0])
        self.assertEqual(refined[new_leaves[0]], 1)
        np.testing.assert_array_equal(refined[new_leaves[2:]], prediction[leaves[1:]])

    def test_target_changes_do_not_change_past_cut_and_scores(self):
        cache, atoms = competing_cache()
        left = run_competing(cache, atoms)
        changed = copy.deepcopy(atoms)
        changed["evaluation/2025-05"] = changed["evaluation/2025-05"][:, :, :, ::-1].copy()
        right = run_competing(cache, changed)
        fields = ("training_slices", "IPT2_threshold_ms", "low_size_cut", "low_branch_prediction_APP", "APP2_training_rank_in_low")
        self.assertEqual([{field: row[field] for field in fields} for row in left["selections"]],
                         [{field: row[field] for field in fields} for row in right["selections"]])
        self.assertEqual([row for row in left["monthly"] if row["target"] != "evaluation/2025-05"],
                         [row for row in right["monthly"] if row["target"] != "evaluation/2025-05"])
        changed_cache = copy.deepcopy(cache)
        target = next(row for row in cache["slices"] if row["period"] == "certificate")
        changed_cache["slices"][5]["end_epoch"] = target["start_epoch"] + 1
        with self.assertRaisesRegex(ValueError, "overlaps"):
            run_competing(changed_cache, atoms)

    def test_all44_contributions_and_confusion_rows_reconcile(self):
        cache, atoms = competing_cache()
        previous = cache["known"]
        extras = [app for app in range(1, 100) if app not in previous][:40]
        known = np.array(sorted(previous.tolist() + extras))
        index, extra_index = np.searchsorted(known, previous), np.searchsorted(known, extras)
        cache["known"], cache["priors"] = known, np.full(44, 1 / 45)
        for key, values in cache["counts"].items():
            base = np.zeros((44, 1024), dtype=np.int64)
            base[index] = values[2]
            base[extra_index, 0] = 100
            cache["counts"][key] = {2: base, 1: project_fine(base, 5)}
            full = np.zeros((2, 44, 2, 3), dtype=np.int64)
            full[:, index] = atoms[key]
            atoms[key] = full
        cache["period_counts"] = {period: {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == period)
                                            for r in (1, 2)} for period in ("pilot", "certificate", "evaluation")}
        result = run_competing(cache, atoms)
        for row in result["monthly"]:
            selected = [r for r in result["classes"] if (r["target"], r["model"], r["group"]) == (row["target"], row["model"], row["group"])]
            self.assertEqual([r["APP"] for r in selected], known.tolist())
            self.assertAlmostEqual(sum(r["weighted_change_from_IPT"] for r in selected), row["error_change_from_IPT"]["value"])
            self.assertAlmostEqual(sum(r["signed_empirical_gain_from_IPT"] for r in selected), row["empirical_gain_from_IPT"])
        for row in result["confusions"]:
            np.testing.assert_array_equal(np.asarray(row["counts_true_by_predicted"]).sum(axis=1), cache["counts"][row["target"]][2].sum(axis=1))
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_missing_class_preserves_prior_and_unavailable_window(self):
        cache, atoms = competing_cache()
        key = "evaluation/2025-04"
        cache["counts"][key][2][0] = 0
        cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
        atoms[key][:, 0] = 0
        cache["period_counts"]["evaluation"] = {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == "evaluation") for r in (1, 2)}
        result = run_competing(cache, atoms)
        april = [r for r in result["monthly"] if r["target"] == key and r["model"] == "fixed_pilot"]
        self.assertTrue(all(r["empirical_F"] is None and r["weighted_error"]["unidentified_prior_mass"] == .2 for r in april))
        may = [r for r in result["monthly"] if r["target"] == "evaluation/2025-05" and r["model"] == "rolling_1m"]
        self.assertEqual(len(may), 4)
        self.assertTrue(all(r["status"] == "unavailable_missing_training_classes" for r in may))
        missing = [r for r in result["classes"] if r["target"] == key and r["APP"] == 2]
        self.assertTrue(all(r["status"] == "missing" and r["error"] is None for r in missing))

    def test_class_absent_for_entire_period_has_NA_error_and_retains_mass(self):
        cache, atoms = competing_cache()
        for item in cache["slices"]:
            if item["period"] == "evaluation":
                key = item["key"]
                cache["counts"][key][2][0] = 0
                cache["counts"][key][1] = project_fine(cache["counts"][key][2], 5)
                atoms[key][:, 0] = 0
        cache["period_counts"]["evaluation"] = {r: sum(cache["counts"][item["key"]][r] for item in cache["slices"] if item["period"] == "evaluation") for r in (1, 2)}
        result = run_competing(cache, atoms)
        rows = [r for r in result["periods"] if r["period"] == "evaluation" and r["model"] == "fixed_pilot"]
        self.assertTrue(all(r["weighted_error"]["value"] is None and r["weighted_error"]["unidentified_prior_mass"] == .2 for r in rows))
        classes = [r for r in result["period_classes"] if r["period"] == "evaluation" and r["model"] == "fixed_pilot" and r["APP"] == 2]
        self.assertTrue(all(r["error"] is None and r["status"] == "missing" for r in classes))

    def test_atomic_schema_count_and_position_marginal_validation(self):
        cache, atoms = competing_cache()
        cache["run"] = {"rows_read": 10000}
        protocol = {"symbol_id": 479, "size_positions": [1, 2], "size_candidates_bytes": [1200], "IPT2_candidates_ms": [4]}
        payload = {**protocol, "known_service_codes": cache["known"].tolist(),
                   "axis_order": ["size_position", "fixed_APP_order", "size_atom", "IPT2_atom_with_invalid_last"],
                   "counts": {key: values.tolist() for key, values in atoms.items()}}
        validated = validate_atoms(payload, protocol, cache)
        self.assertEqual(set(validated), set(atoms))
        bad = copy.deepcopy(payload)
        key = next(iter(atoms))
        bad["counts"][key][0][0][0][0] += 1
        with self.assertRaisesRegex(ValueError, "population"):
            validate_atoms(bad, protocol, cache)
        bad = copy.deepcopy(payload)
        bad["counts"][key][1][0][0][0], bad["counts"][key][1][0][0][1] = 0, 30
        with self.assertRaisesRegex(ValueError, "marginal"):
            validate_atoms(bad, protocol, cache)
        bad = copy.deepcopy(payload)
        bad["counts"][key][0][0][0][0] = 1.5
        with self.assertRaisesRegex(ValueError, "integer"):
            validate_atoms(bad, protocol, cache)
        bad = copy.deepcopy(payload)
        bad["known_service_codes"] = list(reversed(cache["known"].tolist()))
        with self.assertRaisesRegex(ValueError, "order"):
            validate_atoms(bad, protocol, cache)

    def test_replay_rejects_metric_or_count_changes(self):
        compare_replay({"gain": .1 + 1e-14, "counts": [1, 2]}, {"gain": .1, "counts": [1, 2]})
        with self.assertRaisesRegex(ValueError, "metric"):
            compare_replay({"gain": .11}, {"gain": .1})
        with self.assertRaisesRegex(ValueError, "value"):
            compare_replay([1, 3], [1, 2])
        with self.assertRaisesRegex(ValueError, "schema"):
            compare_replay({"gain": .1}, {"gain": .1, "cut": 4})
        self.assertIsNone(branch_context(np.zeros(4), np.full(4, 100), np.full(4, .2), np.array([2, 21, 34, 50]))["winner"])

    def test_complete_cache_only_pipeline_without_H5(self):
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
            path, prepared, experiment, monthly, rolling, refinement, output = (Path(tmp) / name for name in ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement", "hierarchy"))
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
                path.unlink()  # The next stage must need no raw-data access.
                run(argparse.Namespace(monthly_dir=monthly, refinement_dir=refinement, out_dir=output, min_leaf_flows=1, small_n=200))
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(len(summary["monthly"]), 72)
            self.assertTrue(summary["stage8_reproduced"])
            self.assertTrue(summary["high_invalid_decisions_frozen"])
            self.assertFalse(summary["raw_H5_rescan"])
            metadata = json.loads((output / "run.json").read_text())
            self.assertEqual(metadata["status"], "complete")
            self.assertEqual(metadata["rows_read"], 0)
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertIn("No pooled empirical F", (output / "report.md").read_text())
            for name in ("low_threshold_candidates.csv", "branch_competition.csv", "low_threshold_selections.csv", "period_class_metrics.csv"):
                self.assertTrue((output / name).is_file())
            cache = read_cache(monthly)
            original = (refinement / "monthly_atomic_counts.json").read_text()
            (refinement / "monthly_atomic_counts.json").write_text(original + " ")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                read_refinement(refinement, cache, monthly)
            (refinement / "monthly_atomic_counts.json").write_text(original)
            # Even a self-consistent new hash cannot conceal changed stage 8 metrics.
            saved = json.loads((refinement / "summary.json").read_text())
            saved["monthly"][0]["APP2_error"] += .01
            (refinement / "summary.json").write_text(json.dumps(saved))
            previous = json.loads((refinement / "run.json").read_text())
            next(item for item in previous["outputs"] if item["path"] == "summary.json")["sha256"] = sha256(refinement / "summary.json")
            (refinement / "run.json").write_text(json.dumps(previous))
            with self.assertRaisesRegex(ValueError, "replay metric"):
                read_refinement(refinement, cache, monthly)


if __name__ == "__main__":
    unittest.main()
