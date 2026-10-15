"""Gap units, joint feasibility, missingness and verified cached diagnostics."""

import argparse
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"),str(ROOT/"scripts")]
from eibo.costfrontier import GROUPS, select_tradeoffs
from eibo.feasibilitygap import diagnose, gap_metrics, profile_indices
from eibo.forwardvalidation import select_forward
from methodology_real_gap import SOURCE_CODE, read_source, run, validate_arrays
from methodology_real_monthly import save
from methodology_real_prepare import sha256
from test_cost_frontier_riskcert import all_class_fixture


def simple():
    known,priors = [2,21,22,15],[.2]*4
    ns = np.array([[1000,1000,10000,10]]*2,dtype=np.int64)
    d = np.array([[[0,0,0,0],[-100,0,-8,-1],[-100,0,-10,0],[-100,2,-10,-1]]]*2,dtype=np.int64)
    return d,ns,priors,known


def source_fixture(path):
    values = all_class_fixture()
    cache,_,_,roles,col,protocol,_ = values
    cache["plan"]["source"] = {"path":str(path/"raw_missing.h5"),"sha256":"0"*64}
    old = select_forward(roles,col,protocol)
    selected = select_tradeoffs(roles,col,protocol,old)
    path.mkdir()
    np.savez_compressed(path/"past_candidate_classes.npz",**selected["arrays"])
    index = {"known_service_codes":cache["known"].tolist(),"known_priors":cache["priors"].tolist(),
        "unknown_prior":cache["plan"]["unknown_prior"],"contexts":selected["array_index"],"frontiers_use_target_counts":False}
    save(path/"candidate_index.json",index)
    save(path/"frozen_selections.json",selected["selections"])
    save(path/"collection_protocol.json",col)
    save(path/"plan_snapshot.json",cache["plan"])
    save(path/"invariants.json",{"source_recency_reproduced":True})
    save(path/"selection_protocol.json",{"groups":list(GROUPS),"original_protocol":protocol,
        "target_oracle":False,"target_budget_search":False,"common_support":True,
        "retention_limit":"min(0,source_latest_family_historical_delta)","all_budgets":"every historical month and pooled"})
    save(path/"selection_lock.json",{"sha256":sha256(path/"frozen_selections.json"),"protocol_sha256":sha256(path/"selection_protocol.json")})
    original = path/"original_input.json"
    save(original,{"counts":"a hash-verified past input"})
    manifest = [{"path":p.name,"sha256":sha256(p)} for p in path.iterdir()]
    metadata = {"status":"complete","rows_read":0,"cached_source_rows":10000000,"source_recency_reproduced":True,
        "source_lineage":cache["plan"]["source"],"frozen_selection_sha256":sha256(path/"frozen_selections.json"),
        "outputs":manifest,"code":[{"path":str(ROOT/n),"sha256":sha256(ROOT/n)} for n in SOURCE_CODE],
        "input_artifacts":[{"path":str(original),"sha256":sha256(original)}]}
    save(path/"run.json",metadata)
    return selected,index,col,protocol


class TestFeasibilityGap(unittest.TestCase):
    def test_rate_and_count_optima_can_be_different_rules(self):
        d,ns,p,k = simple()
        m = gap_metrics(d,ns,p,k,3)
        domain = np.array([True,True,True,False])
        chosen = profile_indices(m,domain,[-1,0,1,2],0,3)
        self.assertEqual(chosen["minimum_joint_rate"],1)
        self.assertEqual(chosen["minimum_joint_count"],2)
        self.assertAlmostEqual(m["worst_rate"][1].max(),.0002)
        self.assertEqual(m["worst_count"][2].max(),2)

    def test_independent_class_minima_do_not_imply_joint_zero_gap(self):
        d,ns,p,k = simple()
        m = gap_metrics(d,ns,p,k,3)
        chosen = profile_indices(m,np.array([True,True,True,False]),[-1,0,1,2],0,3)
        self.assertEqual(m["worst_rate"][chosen["minimum_APP22_rate"],0],0)
        self.assertEqual(m["worst_rate"][chosen["minimum_APP15_rate"],1],0)
        self.assertGreater(m["worst_rate"][chosen["minimum_joint_rate"]].max(),0)
        self.assertEqual(chosen["relax_APP22_keep_APP15"],1)
        self.assertEqual(chosen["relax_APP15_keep_APP22"],2)

    def test_deficit_decomposes_reference_gain_foregone_and_new_root_harm(self):
        d,ns,p,k = simple()
        d[0,1,3] = 3
        m = gap_metrics(d,ns,p,k,3)
        self.assertEqual(m["gaps"][0,1,1],4)
        self.assertEqual(m["foregone"][0,1,1],1)
        self.assertEqual(m["new_harm"][0,1,1],3)
        np.testing.assert_array_equal(m["gaps"],m["foregone"]+m["new_harm"])
        self.assertEqual(m["gaps"][0,0,0],10)  # identity loses old net gains

    def test_class_count_pooling_and_monthly_gaps_are_distinct(self):
        d,ns,p,k = simple()
        d[0,1,2],d[1,1,2] = -7,-15
        ns[0,2] = 20000
        m = gap_metrics(d,ns,p,k,3)
        self.assertEqual(m["gaps"][:-1,1,0].sum(),3)
        self.assertEqual(m["gaps"][-1,1,0],0)
        expected = -np.dot(p,d[:,1].sum(axis=0)/ns.sum(axis=0))
        self.assertAlmostEqual(m["gain"][1],expected)

    def test_exact_count_constraints_never_disappear_under_rate_tolerance(self):
        d,ns,p,k = simple()
        ns[:,2:] = 10**15
        d[:,1,2] = -9
        m = gap_metrics(d,ns,p,k,3)
        self.assertGreater(m["worst_rate"][1,0],0)
        self.assertLess(m["worst_rate"][1,0],1e-12)
        self.assertGreater(m["worst_count"][1,0],0)

    def test_no_positive_candidates_is_not_identity_qualification(self):
        d,ns,p,k = simple()
        m = gap_metrics(d,ns,p,k,3)
        chosen = profile_indices(m,np.array([True,False,False,False]),[-1,0,1,2],0,3)
        self.assertIsNone(chosen["minimum_joint_rate"])
        self.assertEqual(chosen["identity"],0)
        self.assertIsNone(chosen["relax_APP22_keep_APP15"])
        bad = ns.copy()
        bad[0,0] = 0
        with self.assertRaises(ValueError):
            gap_metrics(d,bad,p,k,3)

    def test_diagnostics_preserve_all_classes_and_exact_stage17_feasibility(self):
        cache,_,_,roles,col,p,_ = all_class_fixture()
        old = select_forward(roles,col,p)
        source = select_tradeoffs(roles,col,p,old)
        index = {"contexts":source["array_index"],"known_service_codes":cache["known"].tolist(),"known_priors":cache["priors"].tolist()}
        result = diagnose(index,source["arrays"],source["selections"])
        self.assertEqual(set(r["APP"] for r in result["coverage"]),set(cache["known"]))
        for r in result["coverage"]:
            self.assertEqual(r["prior"],1/45)
        for r in result["summaries"]:
            if r["status"] == "ready":
                previous = next(s for s in source["selections"] if (s["target"],s["model"],s["group"]) == (r["target"],r["model"],"all_keep_gains"))
                self.assertEqual(r["exact_candidates"],previous["past_feasible_count"])
                self.assertEqual(r["exact_positive_candidates"],previous["past_positive_feasible_count"])
        for r in result["bindings"]:
            self.assertEqual(r["gap"],r["net_gain_foregone"]+r["new_root_harm"])
        # No histogram/target outcome appears in this API or its results.
        self.assertNotIn("confusions",result)
        self.assertNotIn("target_scores",result)

    def test_missing_history_keeps_unknown_gap_status_and_class_coverage(self):
        cache,_,_,roles,col,p,_ = all_class_fixture()
        old = select_forward(roles,col,p)
        source = select_tradeoffs(roles,col,p,old)
        c = next(c for c in source["array_index"] if c["target"] == "evaluation/2025-05" and c["model"] == "rolling_1m")
        a = copy.deepcopy(source["arrays"])
        a[c["prefix"]+"_ns"][0,15] = 0
        index = {"contexts":source["array_index"],"known_service_codes":cache["known"].tolist(),"known_priors":cache["priors"].tolist()}
        result = diagnose(index,a,source["selections"])
        rows = [r for r in result["summaries"] if (r["target"],r["model"]) == (c["target"],c["model"])]
        self.assertTrue(all(r["status"] == "incomplete_history" for r in rows))
        self.assertTrue(all("joint_rate_gap" not in r for r in rows))
        self.assertTrue(any(r["APP"] == 15 and r["n"] == 0 for r in result["coverage"]))

    def test_cached_cli_source_integrity_and_no_target_inputs(self):
        (ROOT/"artifacts/tmp").mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/tmp") as tmp:
            source,output = Path(tmp)/"source",Path(tmp)/"gap"
            source_fixture(source)
            args = argparse.Namespace(costs_dir=source,out_dir=output,small_n=200)
            with contextlib.redirect_stdout(io.StringIO()):
                run(args)
            meta = json.loads((output/"run.json").read_text())
            self.assertEqual(meta["rows_read"],0)
            self.assertFalse(meta["new_target_scoring"])
            self.assertFalse(meta["new_deployment_policy"])
            index = json.loads((output/"candidate_index.json").read_text())
            self.assertEqual(len(index["known_service_codes"]),44)
            self.assertEqual(index["known_priors"],[1/45]*44)
            self.assertNotIn("NaN",(output/"summary.json").read_text())
            self.assertFalse((output/"confusion_matrices.json").exists())
            frozen = source/"frozen_selections.json"
            saved = frozen.read_bytes()
            frozen.write_bytes(saved+b" ")
            with self.assertRaisesRegex(ValueError,"source output hash mismatch"):
                read_source(source)
            frozen.write_bytes(saved)
            metadata = json.loads((source/"run.json").read_text())
            metadata["code"][0]["sha256"] = "0"*64
            (source/"run.json").write_text(json.dumps(metadata))
            with self.assertRaisesRegex(ValueError,"source code lineage"):
                read_source(source)

    def test_arithmetic_reconciliation_detects_changed_masks_even_with_new_hash(self):
        (ROOT/"artifacts/tmp").mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/"artifacts/tmp") as tmp:
            source = Path(tmp)/"source"
            selected,index,col,p = source_fixture(source)
            a = copy.deepcopy(selected["arrays"])
            name = next(n for n in a if n.endswith("_all_keep_gains"))
            a[name][0] = ~a[name][0]
            with self.assertRaisesRegex(ValueError,"candidate masks"):
                validate_arrays(index,a,col,p,10000000)
            c = next(c for c in index["contexts"] if c["available_current"])
            b = copy.deepcopy(selected["arrays"])
            b[c["prefix"]+"_deltas"][:,0,0] = 1
            with self.assertRaisesRegex(ValueError,"historical class counts"):
                validate_arrays(index,b,col,p,10000000)
            b = copy.deepcopy(selected["arrays"])
            b[c["prefix"]+"_all_points"] = b[c["prefix"]+"_all_points"][:1]
            with self.assertRaisesRegex(ValueError,"cost points"):
                validate_arrays(index,b,col,p,10000000)
            bad = copy.deepcopy(col)
            token = next(i["history_node_ids"][0] for i in index["contexts"] if i["available_current"] and
                selected["arrays"][i["prefix"]+"_history_available"][0])
            node = next(n for n in bad["window_spec"]["nodes"] if n["id"] == token)
            node["validation_end_epoch"] = 10**15
            with self.assertRaisesRegex(ValueError,"historical role"):
                validate_arrays(index,selected["arrays"],bad,p,10000000)


if __name__ == "__main__":
    unittest.main()
