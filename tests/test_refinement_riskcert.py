"""No future selection, exact nesting, all-class competition and H5 lineage."""

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
from eibo.refinement import (GROUPS, RefinementCounts, collapse_atoms, fit_prediction,
                             refine_counts, run_refinements, select_splits, validate_grid)
from eibo.realdata import DAY, PreparationAudit
from eibo.realexperiment import histogram_predictions
from eibo.rolling import rolling_experiment
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run
from test_collision_audit_riskcert import raw_fixture
from test_rolling_riskcert import epoch


def simple_atoms():
    values = np.zeros((2, 3, 2, 3), dtype=np.int64)
    values[:, 0, 0, 0] = 40
    values[:, 1, 1, 1] = 60
    values[:, 2, 0, 1] = 80
    return values


def scan_fixture():
    tables, batches = raw_fixture()
    # Give March an evaluation-period table, so all rolling windows are usable.
    for table, rows in zip(tables, batches):
        if table["path"] == "/flows/D20250301":
            table["path"], table["day_seconds"] = "/flows/D20250310", epoch("2025-03-10")
            rows["TIME_FIRST"], rows["TIME_LAST"] = table["day_seconds"] + 3600, table["day_seconds"] + 3700
    audit = PreparationAudit(tables, sample_size=0)
    for rows in batches:
        audit.add(rows, 30)
    plan = audit.plan(min_pilot_flows=1)
    counts = RefinementCounts(plan, tables, time_scale=1, size_cuts=(1000, 1200), ipt_cuts=(0, 4, 10))
    for rows in batches:
        counts.add(rows, 30)
    cache = {"plan": plan, "known": counts.known, "priors": counts.priors, "slices": counts.slices,
             "counts": counts.monthly, "period_counts": counts.counts}
    counts.reconcile_cache(cache)
    return tables, batches, counts, cache


class TestRefinement(unittest.TestCase):
    def test_main_effects_and_combined_partition_gain(self):
        atoms, priors, ns = simple_atoms(), np.full(3, .25), np.full(3, 100)
        selection, candidates = select_splits(atoms, ns, priors, (1, 2), (500,), (4,), min_leaf=1)
        self.assertEqual(selection["size"]["position"], 1)  # deterministic tie
        self.assertAlmostEqual(selection["size"]["training_empirical_gain"], .15)
        self.assertAlmostEqual(selection["ipt"]["training_empirical_gain"], .1)
        combined, _ = collapse_atoms(atoms, (1, 2), selection, "size_ipt_split")
        self.assertEqual(combined.shape, (3, 6))
        self.assertAlmostEqual((combined * (priors / ns)[:, None]).max(axis=0).sum() - .2, .25)
        self.assertEqual(sum(row["selected"] for row in candidates), 2)

    def test_full_class_normalizers_not_cell_frequencies(self):
        atoms = simple_atoms()
        ns, priors = np.array([400, 60, 100]), np.full(3, .25)
        selection, _ = select_splits(atoms, ns, priors, (1, 2), (500,), (4,), min_leaf=1)
        self.assertAlmostEqual(selection["size"]["training_empirical_gain"], .2)
        # Cell class counts differ, but the smaller class 34 wins by full-class law.
        parent = (atoms[0].sum(axis=(1, 2)) * priors / ns).argmax()
        self.assertEqual(parent, 1)

    def test_empty_candidate_set_retains_all_four_identity_groups(self):
        atoms = simple_atoms()
        selection, _ = select_splits(atoms, np.full(3, 100), np.full(3, .25), (1, 2), (500,), (4,), min_leaf=1000)
        self.assertEqual(selection, {"size": None, "ipt": None})
        for group in GROUPS:
            values, _ = collapse_atoms(atoms, (1, 2), selection, group)
            np.testing.assert_array_equal(values[:, 0], [40, 60, 80])
            self.assertEqual(values.shape[1], 1)

    def test_exact_projection_and_unseen_child_parent_backoff(self):
        atoms, priors = simple_atoms(), np.full(3, .25)
        base = np.zeros((3, 1024), dtype=np.int64)
        base[:, 479], base[:, 0] = [40, 60, 80], [60, 40, 20]
        selection, _ = select_splits(atoms, base.sum(axis=1), priors, (1, 2), (500,), (4,), min_leaf=1)
        children, _ = collapse_atoms(atoms, (1, 2), selection, "size_ipt_split")
        refined = refine_counts(base, children, 479)
        baseline, _ = histogram_predictions(base, priors)
        prediction, leaves, unseen = fit_prediction(refined, priors, baseline, 479, 1024)
        self.assertTrue(unseen.any())
        self.assertTrue(np.all(prediction[leaves[unseen]] == baseline[479]))
        np.testing.assert_array_equal(prediction[:1024][np.arange(1024) != 479], baseline[np.arange(1024) != 479])
        broken = children.copy()
        broken[0, 0] += 1
        with self.assertRaisesRegex(ValueError, "population"):
            refine_counts(base, broken, 479)

    def test_future_changes_cannot_change_earlier_cuts_or_scores(self):
        _, _, counts, cache = scan_fixture()
        left = run_refinements(cache, counts.atoms, positions=counts.positions, size_cuts=counts.size_cuts, ipt_cuts=counts.ipt_cuts, min_leaf=1)
        changed = copy.deepcopy(counts.atoms)
        changed["evaluation/2025-05"] = changed["evaluation/2025-05"][:, :, :, ::-1].copy()
        right = run_refinements(cache, changed, positions=counts.positions, size_cuts=counts.size_cuts, ipt_cuts=counts.ipt_cuts, min_leaf=1)
        self.assertEqual(left["selections"], right["selections"])
        self.assertEqual([row for row in left["monthly"] if row["target"] != "evaluation/2025-05"],
                         [row for row in right["monthly"] if row["target"] != "evaluation/2025-05"])

    def test_all_class_contributions_and_original_confusions_reconcile(self):
        _, _, counts, cache = scan_fixture()
        result = run_refinements(cache, counts.atoms, positions=counts.positions, size_cuts=counts.size_cuts, ipt_cuts=counts.ipt_cuts, min_leaf=1)
        old = rolling_experiment(cache, app=2, repeats=0)
        for row in result["confusions"]:
            if row["group"] == "original":
                np.testing.assert_array_equal(row["counts_true_by_predicted"], old["evaluations"][(row["target"], 2, row["model"])]["confusion"])
        for row in result["monthly"]:
            selected = [item for item in result["classes"] if (item["target"], item["model"], item["group"]) == (row["target"], row["model"], row["group"])]
            self.assertEqual(len(selected), len(cache["known"]))
            self.assertAlmostEqual(sum(item["weighted_error_change"] for item in selected), row["error_change"]["value"])
            self.assertAlmostEqual(sum(item["signed_empirical_representation_gain"] for item in selected), row["empirical_representation_gain"])
            self.assertGreaterEqual(row["empirical_representation_gain"], -1e-12)

    def test_invalid_IPT_and_size_overflow_remain_in_population(self):
        tables, batches = raw_fixture()
        batches[0]["PPI"][0, 0, 1] = np.nan
        batches[0]["PPI"][1, 0, 1] = -1
        audit = PreparationAudit(tables, sample_size=0)
        for rows in batches:
            audit.add(rows, 30)
        counts = RefinementCounts(audit.plan(min_pilot_flows=1), tables, time_scale=1, size_cuts=(1000,), ipt_cuts=(4,))
        for rows in batches:
            counts.add(rows, 30)
        values = counts.atoms["pilot/2024-06"]
        self.assertEqual(values[0, :, :, -1].sum(), 2)
        self.assertEqual(values[4, 0, 1, :].sum(), 3)  # raw sizes >1500 kept above the cut
        np.testing.assert_array_equal(values.sum(axis=(2, 3)), np.tile([3, 2, 0], (5, 1)))

    def test_all_44_classes_keep_order_priors_and_contribution_identities(self):
        _, _, counts, original = scan_fixture()
        cache = copy.deepcopy(original)
        previous = cache["known"]
        extra = [app for app in range(1, 100) if app not in previous][:41]
        known = np.asarray(sorted(previous.tolist() + extra))
        index = np.searchsorted(known, previous)
        extra_index = np.searchsorted(known, extra)
        cache["known"], cache["priors"] = known, np.full(44, 1 / 45)
        atoms = {}
        for key, matrices in cache["counts"].items():
            for rung in (1, 2):
                value = np.zeros((44, matrices[rung].shape[1]), dtype=np.int64)
                value[index] = matrices[rung]
                value[extra_index, 0] = 100
                matrices[rung] = value
            value = np.zeros((len(counts.positions), 44, len(counts.size_cuts) + 1, len(counts.ipt_cuts) + 2), dtype=np.int64)
            value[:, index] = counts.atoms[key]
            atoms[key] = value
        cache["period_counts"] = {period: {rung: sum(cache["counts"][item["key"]][rung] for item in cache["slices"] if item["period"] == period)
                                             for rung in (1, 2)} for period in ("pilot", "certificate", "evaluation")}
        result = run_refinements(cache, atoms, positions=counts.positions, size_cuts=counts.size_cuts, ipt_cuts=counts.ipt_cuts, min_leaf=1)
        for row in result["monthly"]:
            classes = [item for item in result["classes"] if (item["target"], item["model"], item["group"]) == (row["target"], row["model"], row["group"])]
            self.assertEqual([item["APP"] for item in classes], known.tolist())
            self.assertAlmostEqual(sum(item["weighted_error_change"] for item in classes), row["error_change"]["value"])
            self.assertAlmostEqual(sum(item["signed_empirical_representation_gain"] for item in classes), row["empirical_representation_gain"])
        np.testing.assert_array_equal(cache["priors"], np.full(44, 1 / 45))

    def test_missing_target_and_training_classes_keep_priors(self):
        _, _, counts, cache = scan_fixture()
        changed = copy.deepcopy(cache)
        atoms = copy.deepcopy(counts.atoms)
        key = "evaluation/2025-04"
        for rung in (1, 2):
            changed["counts"][key][rung][0] = 0
        atoms[key][:, 0] = 0
        changed["period_counts"]["evaluation"] = {r: sum(changed["counts"][item["key"]][r] for item in changed["slices"] if item["period"] == "evaluation") for r in (1, 2)}
        result = run_refinements(changed, atoms, positions=counts.positions, size_cuts=counts.size_cuts, ipt_cuts=counts.ipt_cuts, min_leaf=1)
        april = [row for row in result["monthly"] if row["target"] == key and row["model"] == "fixed_pilot"]
        self.assertTrue(all(row["empirical_F"] is None and row["error_change"]["unidentified_prior_mass"] == .25 for row in april))
        may = [row for row in result["monthly"] if row["target"] == "evaluation/2025-05" and row["model"] == "rolling_1m"]
        self.assertTrue(all(row["status"] == "unavailable_missing_training_classes" for row in may))
        self.assertEqual(len(may), 4)

    def test_chronology_guard_and_invalid_grids(self):
        _, _, counts, cache = scan_fixture()
        changed = copy.deepcopy(cache)
        first = next(item for item in changed["slices"] if item["period"] == "certificate")
        changed["slices"][5]["end_epoch"] = first["start_epoch"] + 1
        with self.assertRaisesRegex(ValueError, "overlaps"):
            run_refinements(changed, counts.atoms, positions=counts.positions, size_cuts=counts.size_cuts, ipt_cuts=counts.ipt_cuts, min_leaf=1)
        for grid in ((4, 4), (-1, 4), (np.nan, 4)):
            with self.assertRaises(ValueError):
                validate_grid(grid)

    def test_complete_HDF5_four_group_pipeline(self):
        for backend in ("tables", "h5py"):
            try:
                module = importlib.import_module(backend)
                break
            except ImportError:
                continue
        else:
            self.skipTest("HDF5 integration requires tables or h5py")
        (ROOT / "artifacts/tmp").mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "artifacts/tmp") as tmp:
            path, prepared, experiment, monthly, rolling, output = (Path(tmp) / name for name in ("fixture.h5", "prepared", "experiment", "monthly", "rolling", "refinement"))
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
                run(argparse.Namespace(h5=path, prepare_dir=prepared, monthly_dir=monthly, rolling_dir=rolling, out_dir=output, backend=backend,
                    symbol_id=479, size_positions=None, size_cuts=[1000, 1200], ipt_cuts=[0, 4, 10], models=list(("fixed_pilot", "rolling_1m", "rolling_3m")),
                    min_leaf_flows=1, chunk_rows=2, small_n=200))
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(len(summary["monthly"]), 72)
            self.assertTrue(summary["original_models_reproduced"])
            self.assertEqual(summary["known_service_codes"], [2, 34, 50])
            self.assertEqual(json.loads((output / "run.json").read_text())["status"], "complete")
            self.assertNotIn("NaN", (output / "summary.json").read_text())
            self.assertIn("No pooled empirical F", (output / "report.md").read_text())
            for name in ("monthly_atomic_counts.json", "threshold_candidates.csv", "cell_children.csv", "period_class_metrics.csv"):
                self.assertTrue((output / name).is_file())


if __name__ == "__main__":
    unittest.main()
