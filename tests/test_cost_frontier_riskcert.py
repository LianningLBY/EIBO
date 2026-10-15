"""Past-only frontiers, preserved gains, class accounting and cache integrity."""

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
from eibo.costfrontier import GROUPS, choose, cost_views, evaluate_tradeoffs, pareto_mask, select_tradeoffs
from eibo.forwardvalidation import evaluate_forward, select_forward
from eibo.recencyaudit import evaluate_matched, select_and_audit
from eibo.realdata import DAY
from eibo.rolling import project_fine
from methodology_real_costs import run
from methodology_real_recency import run as run_recency
from methodology_real_forward import run as run_forward
from methodology_real_blocks import run as run_blocks
from methodology_real_joint import run as run_joint
from methodology_real_prepare import run as run_prepare
from methodology_real_experiment import run as run_experiment
from methodology_real_monthly import run as run_monthly
from methodology_real_rolling import run as run_rolling
from methodology_real_refinement import run as run_refinement
from methodology_real_hierarchy import run as run_hierarchy
from test_forward_validation_riskcert import forward_fixture
from test_joint_refinement_riskcert import MODELS, refresh
from test_refinement_riskcert import scan_fixture


def score_fixture():
    col = {"known_service_codes": [2,15,21,22,34,50], "known_priors": [1/7]*6}
    p = {"APP21_validation_budget_pp": .1, "maximum_validation_raw_wrong_increase": 0}
    rows = [{"candidate_id": i, "eligible": True, "observed_fit_leaves": 2,
             "prediction_APPs": [2,21], "fit_gain": .1} for i in range(3)]
    delta = np.array([[-20,-3,1,-10,0,0],[-19,-1,0,-8,0,0],[-12,0,0,-12,0,0]])
    current = {"rows": rows, "protected_parent": False}
    folds = [{"rows": copy.deepcopy(rows), "protected_parent": False, "deltas": delta.copy(), "ns": np.full(6,1000)} for _ in range(3)]
    # past_table also retains the unchanged source score fields.
    sync(folds, col)
    return current, folds, col, p


def sync(folds, col):
    for f in folds:
        for i,r in enumerate(f["rows"]):
            r.update(validation_weighted_change=float(np.dot(col["known_priors"],f["deltas"][i]/f["ns"])),
                validation_raw_wrong_change=int(f["deltas"][i].sum()),
                APP21_validation_conditional_change=float(f["deltas"][i,2]/f["ns"][2]))


def all_class_fixture():
    cache, atoms, joints, roles, col0, protocol, _ = forward_fixture()
    known = np.array(list(range(43)) + [50])
    ix = np.searchsorted(known, cache["known"])
    other = np.setdiff1d(np.arange(44),ix)
    cache["known"], cache["priors"], cache["plan"]["unknown_prior"] = known, np.full(44,1/45), 1/45
    for key in cache["counts"]:
        base = np.zeros((44,1024),dtype=np.int64)
        base[ix], base[other,1] = cache["counts"][key][2], 500
        cache["counts"][key] = {2:base,1:project_fine(base,5)}
        a,j = np.zeros((2,44,2,4),dtype=np.int64),np.zeros((1,44,2,2,2),dtype=np.int64)
        a[:,ix],j[:,ix] = atoms[key],joints[key]
        atoms[key],joints[key] = a,j
    for role in roles.values():
        base,child = np.zeros((44,1024),dtype=np.int64),np.zeros((44,3),dtype=np.int64)
        base[ix],base[other,1],child[ix] = role["base"],200,role["children"]
        a,j = np.zeros((2,44,2),dtype=np.int64),np.zeros((1,44,2,2),dtype=np.int64)
        a[:,ix],j[:,ix] = role["single"],role["joint"]
        role.update(base=base,children=child,single=a,joint=j)
    refresh(cache)
    col = {**col0,"known_service_codes":known.tolist(),"known_priors":cache["priors"].tolist(),"unknown_prior":1/45}
    previous = {}
    for c in col["window_spec"]["contexts"]:
        matrix = np.zeros((44,44),dtype=np.int64)
        matrix[:,0] = cache["counts"][c["target"]][2].sum(axis=1)
        for g in ("previous_time","previous_blocks"):
            previous[c["target"],c["model"],g] = matrix
    return cache,atoms,joints,roles,col,protocol,previous


def evaluate(values):
    cache,atoms,joints,roles,col,p,previous = values
    source = select_forward(roles,col,p)
    old = evaluate_forward(cache,roles,joints,atoms,col,p,source,previous)
    matched = select_and_audit(roles,col,p,source)
    replayed = evaluate_matched(cache,roles,joints,atoms,col,p,matched,source,old,previous)
    selected = select_tradeoffs(roles,col,p,source)
    return selected,evaluate_tradeoffs(cache,roles,joints,atoms,col,p,selected,source,replayed,previous)


class TestCostFrontier(unittest.TestCase):
    def test_frontier_matches_exhaustive_dominance_and_preserves_equivalent_points(self):
        rng = np.random.default_rng(7)
        points = rng.integers(-3,4,(120,5)).astype(float)
        points = np.concatenate((points,points[:5]))
        expected = [not np.any(np.all(points <= p,axis=1) & np.any(points < p,axis=1)) for p in points]
        np.testing.assert_array_equal(pareto_mask(points),expected)
        self.assertEqual(pareto_mask(np.zeros((3,5))).tolist(),[True]*3)
        with self.assertRaises(ValueError):
            pareto_mask([[np.nan,0]])

    def test_retaining_existing_gains_is_stronger_than_not_harming_root(self):
        current,folds,col,p = score_fixture()
        data = cost_views(current,folds,col,p,1)
        a = choose(current,data["views"]["latest"],"latest_no_harm")
        b = choose(current,data["views"]["latest"],"latest_keep_gains")
        # Candidate 0 rescues more in total but candidate 1 has already helped
        # both protected classes, and candidate 0 retains those gains here.
        self.assertEqual(a["rule"]["candidate_id"],0)
        self.assertEqual(b["rule"]["candidate_id"],0)
        self.assertTrue(a["past_identity_feasible"])
        self.assertFalse(b["past_identity_feasible"])
        self.assertFalse(data["views"]["latest"]["keep_gains"][3])  # loses APP15's gain
        folds[-1]["deltas"][0,3] = -7
        sync(folds,col)
        data = cost_views(current,folds,col,p,1)
        self.assertEqual(choose(current,data["views"]["latest"],"latest_no_harm")["rule"]["candidate_id"],0)
        self.assertEqual(choose(current,data["views"]["latest"],"latest_keep_gains")["rule"]["candidate_id"],1)

    def test_no_feasible_retention_rule_is_not_a_successful_identity(self):
        current,folds,col,p = score_fixture()
        folds[0]["deltas"][0,2] = 5  # old APP21 cap excludes the reference
        sync(folds,col)
        data = cost_views(current,folds,col,p,0)
        choice = choose(current,data["views"]["all"],"all_keep_gains")
        self.assertIsNone(choice["rule"])
        self.assertEqual(choice["status"],"identity_no_feasible_rule")
        self.assertEqual(choice["past_feasible_count"],0)
        self.assertFalse(choice["past_selected_feasible"])
        self.assertFalse(choice["past_identity_feasible"])
        self.assertIsNotNone(choose(current,data["views"]["latest"],"latest_keep_gains")["rule"])

    def test_no_positive_gain_and_empty_feasible_set_have_distinct_statuses(self):
        current,folds,col,p = score_fixture()
        for f in folds:
            f["deltas"][:] = 0
        sync(folds,col)
        data = cost_views(current,folds,col,p,None)
        choice = choose(current,data["views"]["all"],"all_no_harm")
        self.assertIsNone(choice["rule"])
        self.assertEqual(choice["status"],"identity_no_positive_feasible_gain")
        self.assertTrue(choice["past_selected_feasible"])
        self.assertEqual(choice["past_positive_feasible_count"],0)

    def test_all_view_pools_class_counts_and_uses_worst_month_costs(self):
        current,folds,col,p = score_fixture()
        folds[0]["ns"] *= 5
        sync(folds,col)
        data = cost_views(current,folds,col,p,0)
        pooled = sum(f["deltas"][0] for f in folds)/sum(f["ns"] for f in folds)
        self.assertAlmostEqual(-data["views"]["all"]["points"][1,0],-np.dot(col["known_priors"],pooled))
        self.assertAlmostEqual(data["views"]["all"]["points"][1,1],.001)
        self.assertFalse(np.isclose(-data["views"]["all"]["points"][1,0],
            np.mean([-f["rows"][0]["validation_weighted_change"] for f in folds])))

    def test_positive_raw_budget_is_also_checked_on_pooled_counts(self):
        current,folds,col,p = score_fixture()
        p["maximum_validation_raw_wrong_increase"] = 1
        for f in folds:
            f["deltas"][0] = [1,0,0,0,0,0]
        sync(folds,col)
        data = cost_views(current,folds,col,p,0)
        self.assertTrue(data["views"]["latest"]["original"][1])
        self.assertFalse(data["views"]["all"]["original"][1])

    def test_history_support_missing_class_and_parent_protection(self):
        current,folds,col,p = score_fixture()
        folds[0]["rows"][0]["eligible"] = False
        data = cost_views(current,folds,col,p,0)
        self.assertFalse(data["support"][1])
        current["protected_parent"] = True
        data = cost_views(current,folds,col,p,0)
        self.assertEqual(data["support"].tolist(),[True,False,False,False])
        folds[0]["ns"][0] = 0
        data = cost_views(current,folds,col,p,0)
        self.assertFalse(data["support"].any())
        self.assertEqual(choose(current,data["views"]["all"],"all_no_harm")["status"],"identity_incomplete_history")
        folds[0] = None
        self.assertEqual(cost_views(current,folds,col,p,0)["history_available"].tolist(),[False,True,True])

    def test_strict_zero_class_budget_uses_integer_counts_even_for_huge_denominators(self):
        current,folds,col,p = score_fixture()
        folds[-1]["ns"][:] = 10**15
        folds[-1]["deltas"][0,3] = 1
        sync(folds,col)
        data = cost_views(current,folds,col,p,None)
        self.assertTrue(data["views"]["latest"]["original"][1])
        self.assertFalse(data["views"]["latest"]["no_harm"][1])

    def test_target_validation_roles_cannot_change_selections_or_past_frontiers(self):
        values = all_class_fixture()
        source = select_forward(values[3],values[4],values[5])
        before = select_tradeoffs(values[3],values[4],values[5],source)
        node = next(n for n in values[4]["window_spec"]["nodes"] if n["id"] == "2025-05/rolling_1m")
        for a in values[3][node["validation_id"]].values():
            a[:] = 0
        after = select_tradeoffs(values[3],values[4],values[5],source)
        for field in ("selections","frontiers","frontier_summary","past_classes","array_index"):
            self.assertEqual(before[field],after[field])
        for name in before["arrays"]:
            np.testing.assert_array_equal(before["arrays"][name],after["arrays"][name])

    def test_all_44_classes_priors_integer_transfers_and_period_pooling(self):
        values = all_class_fixture()
        selected,result = evaluate(values)
        for metric in result["metrics"]:
            rows = [r for r in result["classes"] if all(r[k] == metric[k] for k in ("scope","target","model","group"))]
            self.assertEqual([r["APP"] for r in rows],values[0]["known"].tolist())
            self.assertAlmostEqual(sum(r["weighted_change_vs_source_latest"] for r in rows),metric["change_vs_source_latest"]["value"])
            self.assertEqual(sum(r["wrong_change_vs_source_latest"] for r in rows),metric["raw_change_vs_source_latest"])
        for r in result["classes"]:
            if r["group"] in GROUPS:
                self.assertEqual(r["harmed"]-r["rescued"],r["wrong_change_vs_time_baseline"])
                if r["APP"] == 34:
                    self.assertEqual(r["harmed"],0)
                if r["scope"] == "period":
                    monthly = [m for m in result["classes"] if m["scope"] == "monthly" and all(m[k] == r[k] for k in ("period","model","group","APP"))]
                    self.assertEqual(sum(m["wrong"] for m in monthly),r["wrong"])
        for r in selected["past_classes"]:
            self.assertEqual(r["prior"],1/45)
        np.testing.assert_array_equal(values[0]["priors"],np.full(44,1/45))
        # The small fixture has unchanged eligible classes; root guards should
        # reproduce the corresponding common-support source control exactly.
        matrices = {(r["target"],r["model"],r["group"]):r["counts_true_by_predicted"] for r in result["confusions"]}
        for t,m,g in matrices:
            if g == "latest_no_harm":
                self.assertEqual(matrices[t,m,g],matrices[t,m,"shared_latest"])

    def test_missing_target_class_retains_NA_and_original_identification_mass(self):
        values = all_class_fixture()
        key,ix = "evaluation/2025-05",15
        values[0]["counts"][key][2][ix] = 0
        values[0]["counts"][key][1] = project_fine(values[0]["counts"][key][2],5)
        values[1][key][:,ix],values[2][key][:,ix] = 0,0
        for token,matrix in values[-1].items():
            if token[0] == key:
                matrix[ix] = 0
        refresh(values[0])
        _,result = evaluate(values)
        for r in result["metrics"]:
            if r["scope"] == "monthly" and r["target"] == key:
                self.assertIsNone(r["weighted_error"]["value"])
                lo,hi = r["weighted_error"]["range_from_unobserved_values"]
                self.assertAlmostEqual(hi-lo,1/45)
        for r in result["compatibility"]:
            if r["target"] == key:
                self.assertIsNone(r["root_joint_met"])
                self.assertIsNone(r["keep_joint_met"])
                self.assertIsNotNone(r["legacy_met"])

    def test_unavailable_current_model_never_claims_budget_success(self):
        values = all_class_fixture()
        node = next(n for n in values[4]["window_spec"]["nodes"] if n["id"] == "2025-05/rolling_1m")
        for a in values[3][node["fit_id"]].values():
            a[:] = 0
        selected,result = evaluate(values)
        for r in selected["selections"]:
            if (r["target"],r["model"]) == ("evaluation/2025-05","rolling_1m"):
                self.assertEqual(r["status"],"unavailable_current_fit")
        for r in result["compatibility"]:
            if (r["target"],r["model"]) == ("evaluation/2025-05","rolling_1m"):
                self.assertIsNone(r["legacy_met"])

    def test_complete_cached_pipeline_and_recency_tamper_rejection(self):
        for backend in ("tables","h5py"):
            try:
                module = importlib.import_module(backend)
                break
            except ImportError:
                continue
        else:
            self.skipTest("an HDF5 writer is needed")
        (ROOT/"artifacts/tmp").mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/tmp") as tmp:
            names = ("fixture.h5","prepared","experiment","monthly","rolling","refinement","hierarchy","joint","blocks","forward","recency","costs")
            path,prepared,experiment,monthly,rolling,refinement,hierarchy,joint,blocks,forward,recency,output = (Path(tmp)/n for n in names)
            tables,batches,_,_ = scan_fixture()
            # Ensure the three protected classes are present in the ORIGINAL
            # preparation plan, rather than introducing/reweighting them later.
            batches = [np.concatenate([r] + [np.repeat(r[:1],2).copy() for _ in range(3)]) for r in batches]
            for rows in batches:
                for j,app in enumerate((15,21,22)):
                    rows["APP"][-6+j*2:-4+j*2 if j < 2 else None] = app
            if backend == "tables":
                with module.open_file(str(path),mode="w") as handle:
                    group = handle.create_group("/","flows")
                    for table,rows in zip(tables,batches):
                        handle.create_table(group,table["path"].split("/")[-1],obj=rows)
            else:
                with module.File(path,"w") as handle:
                    for table,rows in zip(tables,batches):
                        handle.create_dataset(table["path"],data=rows)
            common = dict(prepare_dir=prepared,monthly_dir=monthly,refinement_dir=refinement,hierarchy_dir=hierarchy,joint_dir=joint,blocks_dir=blocks,forward_dir=forward,small_n=200)
            args = argparse.Namespace(**common,recency_dir=recency,out_dir=output)
            with contextlib.redirect_stdout(io.StringIO()):
                run_prepare(argparse.Namespace(h5=path,out_dir=prepared,backend=backend,sha256=True,expected_sha256=None,time_unit="seconds",k=5,gap_seconds=DAY,rounding_seconds=3600,identifier_sample=0,seed=0,block_seconds=[3600,21600,DAY],max_rows=None,chunk_rows=2,min_pilot_flows=1,alpha=.05))
                run_experiment(argparse.Namespace(h5=path,prepare_dir=prepared,out_dir=experiment,backend=backend,chunk_rows=2,block_seconds=[3600,21600,DAY]))
                run_monthly(argparse.Namespace(h5=path,prepare_dir=prepared,experiment_dir=experiment,out_dir=monthly,backend=backend,chunk_rows=2,small_n=200,top=3))
                run_rolling(argparse.Namespace(monthly_dir=monthly,out_dir=rolling,app=2,reference_months=["2024-12","2025-01"],matched_repeats=0,seed=7,small_n=200,top=3))
                run_refinement(argparse.Namespace(h5=path,prepare_dir=prepared,monthly_dir=monthly,rolling_dir=rolling,out_dir=refinement,backend=backend,symbol_id=479,size_positions=None,size_cuts=[1000,1200],ipt_cuts=[0,4,10],models=MODELS,min_leaf_flows=1,chunk_rows=2,small_n=200))
                run_hierarchy(argparse.Namespace(monthly_dir=monthly,refinement_dir=refinement,out_dir=hierarchy,min_leaf_flows=1,small_n=200))
                run_joint(argparse.Namespace(h5=path,reuse_counts_dir=None,prepare_dir=prepared,monthly_dir=monthly,refinement_dir=refinement,hierarchy_dir=hierarchy,out_dir=joint,backend=backend,chunk_rows=2,ipt_threshold_ms=4.,validation_day=21,validation_gap_seconds=DAY,min_leaf_flows=1,app21_budget_pp=.1,max_validation_raw_increase=0,small_n=200))
                run_blocks(argparse.Namespace(h5=path,reuse_counts_dir=None,prepare_dir=prepared,monthly_dir=monthly,refinement_dir=refinement,hierarchy_dir=hierarchy,joint_dir=joint,out_dir=blocks,backend=backend,chunk_rows=2,blocks=3,small_n=200))
                run_forward(argparse.Namespace(**{k:v for k,v in common.items() if k!="forward_dir"},h5=path,reuse_counts_dir=None,out_dir=forward,backend=backend,chunk_rows=2,history_months=3))
                run_recency(argparse.Namespace(**common,out_dir=recency,recency_ratio=2.))
                path.unlink()
                run(args)
            metadata = json.loads((output/"run.json").read_text())
            self.assertEqual(metadata["rows_read"],0)
            self.assertTrue(metadata["source_recency_reproduced"])
            self.assertNotIn("NaN",(output/"summary.json").read_text())
            index = json.loads((output/"candidate_index.json").read_text())
            self.assertTrue({15,21,22}.issubset(index["known_service_codes"]))
            with np.load(output/"past_candidate_classes.npz",allow_pickle=False) as archive:
                self.assertTrue(archive.files)
                for context in index["contexts"]:
                    if context["available_current"]:
                        self.assertEqual(archive[context["prefix"]+"_deltas"].shape[-1],len(index["known_service_codes"]))
            with (recency/"latest_choice_audit.csv").open("a") as handle:
                handle.write("tampered\n")
            args.out_dir = Path(tmp)/"bad_recency"
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError,"recency artifact hash mismatch"):
                run(args)
            self.assertFalse(args.out_dir.exists())


if __name__ == "__main__":
    unittest.main()
