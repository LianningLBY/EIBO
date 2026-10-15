#!/usr/bin/env python3
"""Diagnose past retention feasibility gaps; never fit or score target policies."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.costfrontier import GROUPS, pareto_mask  # noqa: E402
from eibo.feasibilitygap import diagnose  # noqa: E402
from methodology_real_costs import CODE as COST_CODE  # noqa: E402
from methodology_real_hierarchy import write_table  # noqa: E402
from methodology_real_monthly import number, save  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_reallocation import finish_run, start_run  # noqa: E402

SOURCE_CODE = ("scripts/methodology_real_costs.py",) + COST_CODE
CODE = SOURCE_CODE + ("src/eibo/feasibilitygap.py",)
REQUIRED = {"past_candidate_classes.npz", "candidate_index.json", "frozen_selections.json",
    "selection_lock.json", "selection_protocol.json", "collection_protocol.json", "plan_snapshot.json", "invariants.json"}


def validate_arrays(index, arrays, collection, protocol, maximum):
    known, priors = index["known_service_codes"], np.asarray(index["known_priors"])
    if len(set(known)) != len(known) or any(app not in known for app in (21,22,15)) or (
        len(priors) != len(known) or not np.isfinite(priors).all() or np.any(priors <= 0) or
        not np.isfinite(index["unknown_prior"]) or index["unknown_prior"] < 0 or
        abs(priors.sum() + index["unknown_prior"] - 1) > 1e-12):
        raise ValueError("original class/prior order or mass invalid")
    if known != collection["known_service_codes"] or index["known_priors"] != collection["known_priors"]:
        raise ValueError("source classes/priors differ from collection")
    windows = collection["window_spec"]
    contexts = {(r["target"],r["model"]):r for r in windows["contexts"]}
    nodes = {r["id"]:r for r in windows["nodes"]}
    if len(contexts) != len(index["contexts"]) or len({(c["target"],c["model"]) for c in index["contexts"]}) != len(contexts):
        raise ValueError("source context index incomplete or duplicated")
    expected = set()
    for num,c in enumerate(index["contexts"]):
        context = contexts[c["target"],c["model"]]
        if c["prefix"] != "context_" + str(num) or c["history_node_ids"] != context["history_node_ids"]:
            raise ValueError("source historical context order differs")
        if not c["available_current"]:
            continue
        prefix, ids = c["prefix"], c["candidate_ids"]
        if ids != list(range(-1,len(ids)-1)):
            raise ValueError("candidate identities are reordered")
        names = ["ns","deltas","support","history_available"] + [
            view + "_" + field for view in ("latest","all") for field in ("points","original","no_harm","keep_gains","frontier","budget_frontier")]
        expected.update(prefix + "_" + n for n in names)
        ns,d,support,available = (arrays[prefix+"_"+n] for n in ("ns","deltas","support","history_available"))
        h,n,k = len(c["history_node_ids"]),len(ids),len(known)
        if ns.shape != (h,k) or d.shape != (h,n,k) or ns.dtype != np.int64 or d.dtype != np.int64 or (
            np.any(ns < 0) or np.any(ns > maximum) or np.any(d < -ns[:,None,:]) or np.any(d > ns[:,None,:]) or np.any(d[:,0])):
            raise ValueError("invalid original historical class counts")
        if support.shape != (n,) or available.shape != (h,) or support.dtype != bool or available.dtype != bool:
            raise ValueError("invalid historical support flags")
        for j,token in enumerate(c["history_node_ids"]):
            node = nodes.get(token)
            if available[j] and (node is None or node["fit_end_epoch"] + windows["gap_seconds"] > node["validation_start_epoch"] or node["validation_end_epoch"] > context["target_start_epoch"]):
                raise ValueError("historical role reaches or exceeds its target")
            if not available[j] and (np.any(ns[j]) or np.any(d[j])):
                raise ValueError("unavailable origin contains fabricated counts")
        complete = bool(available.all() and np.all(ns > 0))
        if bool(support[0]) != complete or not complete and support.any():
            raise ValueError("identity/history support differs")
        reference = ids.index(c["reference_source_latest_candidate"]) if c["reference_source_latest_candidate"] is not None else 0
        focal = [known.index(a) for a in (21,22,15)]
        for view in ("latest","all"):
            points = np.full((n,5),np.nan)
            original,no_harm,retain = (np.zeros(n,dtype=bool) for _ in range(3))
            if complete:
                change = d[-1:] if view == "latest" else np.concatenate((d,d.sum(axis=0,keepdims=True)))
                denominators = ns[-1:] if view == "latest" else np.concatenate((ns,ns.sum(axis=0,keepdims=True)))
                rates = change / denominators[:,None,:]
                points = np.column_stack((rates[-1] @ priors,rates[:,:,focal].max(axis=0),change.sum(axis=2).max(axis=0)))
                original = support & (points[:,1] <= protocol["APP21_validation_budget_pp"]/100+1e-12) & (points[:,-1] <= protocol["maximum_validation_raw_wrong_increase"])
                no_harm = original & np.all(change[:,:,focal[1:]] <= 0,axis=(0,2))
                limits = np.minimum(0,change[:,reference,:][:,focal[1:]])
                retain = original & np.all(change[:,:,focal[1:]] <= limits[:,None,:],axis=(0,2))
            actual_points = arrays[prefix+"_"+view+"_points"]
            if actual_points.shape != points.shape or not np.allclose(actual_points,points,rtol=0,atol=1e-12,equal_nan=True):
                raise ValueError("source cost points do not reconcile with all-class deltas")
            full,budget = np.zeros(n,dtype=bool),np.zeros(n,dtype=bool)
            for out,domain in ((full,support),(budget,original)):
                chosen = np.flatnonzero(domain)
                out[chosen] = pareto_mask(points[chosen])
            for name,values in (("original",original),("no_harm",no_harm),("keep_gains",retain),("frontier",full),("budget_frontier",budget)):
                actual = arrays[prefix+"_"+view+"_"+name]
                if actual.dtype != bool or not np.array_equal(actual,values):
                    raise ValueError("source candidate masks do not reconcile: "+name)
    if set(arrays) != expected:
        raise ValueError("source archive arrays missing or unexpected")


def read_source(directory):
    metadata = json.loads((directory/"run.json").read_text())
    if metadata["status"] != "complete" or metadata["rows_read"] != 0 or not metadata["source_recency_reproduced"]:
        raise ValueError("completed cached stage-17 source required")
    manifest = {r["path"]:r["sha256"] for r in metadata["outputs"]}
    if len(manifest) != len(metadata["outputs"]) or not REQUIRED.issubset(manifest):
        raise ValueError("source manifest incomplete or duplicated")
    for name,digest in manifest.items():
        if Path(name).name != name or sha256(directory/name) != digest:
            raise ValueError("source output hash mismatch: "+name)
    for name in SOURCE_CODE:
        path = ROOT/name
        rows = [r for r in metadata["code"] if Path(r["path"]).name == path.name]
        if len(rows) != 1 or rows[0]["sha256"] != sha256(path):
            raise ValueError("source code lineage differs")
    inputs = [directory/"run.json"]+[directory/n for n in sorted(manifest)]
    for r in metadata["input_artifacts"]:
        path = Path(r["path"])
        if not path.is_file() or sha256(path) != r["sha256"]:
            raise ValueError("source original input lineage differs")
        inputs.append(path)
    index = json.loads((directory/"candidate_index.json").read_text())
    selection = json.loads((directory/"selection_protocol.json").read_text())
    collection = json.loads((directory/"collection_protocol.json").read_text())
    plan = json.loads((directory/"plan_snapshot.json").read_text())
    frozen = json.loads((directory/"frozen_selections.json").read_text())
    lock = json.loads((directory/"selection_lock.json").read_text())
    if index["frontiers_use_target_counts"] is not False or selection["target_oracle"] is not False or selection["target_budget_search"] is not False or (
        selection["common_support"] is not True or selection["groups"] != list(GROUPS) or
        selection["retention_limit"] != "min(0,source_latest_family_historical_delta)" or
        selection["all_budgets"] != "every historical month and pooled"):
        raise ValueError("unsupported past-only source protocol")
    if plan["source"] != metadata["source_lineage"] or index["unknown_prior"] != plan["unknown_prior"]:
        raise ValueError("original source/prior lineage differs")
    if lock["sha256"] != sha256(directory/"frozen_selections.json") or metadata["frozen_selection_sha256"] != lock["sha256"] or lock["protocol_sha256"] != sha256(directory/"selection_protocol.json"):
        raise ValueError("source selection/protocol lock differs")
    with np.load(directory/"past_candidate_classes.npz",allow_pickle=False) as archive:
        arrays = {name:archive[name] for name in archive.files}
    validate_arrays(index,arrays,collection,selection["original_protocol"],metadata["cached_source_rows"])
    keys = [(r["target"],r["model"],r["group"]) for r in frozen]
    expected = {(c["target"],c["model"],g) for c in index["contexts"] for g in GROUPS}
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError("source frozen choices incomplete or duplicated")
    return metadata,index,arrays,frozen,selection,plan,list(dict.fromkeys(inputs))


def report_text(result):
    lines = ["# Past-only retention feasibility gaps", "",
        "This run diagnoses the existing finite grid under unchanged original classes, priors, fitted families, historical support, APP21 budgets and raw-error budgets. It verifies stage-17 output/code/input hashes and reconciles saved candidate costs, masks and frontiers with the original all-class integer deltas. No H5 read, new fitting, target policy scoring, budget sweep or deployment selection.", "",
        "## Definitions and interpretation", "",
        "For each past month and the class-count pooled view, let d be a candidate's class NET-error increment relative to the root. The retention limit is min(0, the actual source_latest family's historical increment). The deficit is max(0, d-limit). It is exactly the sum of forgone reference net gain and new harm relative to root. Count deficits are aggregate NET increments, not identifiable flows, paired rescues or a justified count of samples to delete/relabel.",
        "original_budget preserves every monthly AND pooled APP21/raw cap plus the common support guard. root_no_harm additionally forbids any monthly/pooled APP22/15 increment over root. The latter domain isolates loss of existing benefit while maintaining root protection. Identity is an explicit diagnostic point; it can fail exact retention.",
        "Among positive past pooled-gain candidates, minimum_joint_rate minimizes the maximum conditional deficit over both classes and every month/pooled row. It is the smallest COMMON rate tolerance making this finite domain feasible. minimum_joint_count instead minimizes the largest count deficit and may use a different rule. Separate APP22/APP15 minima also may use different rules and cannot be combined into a fictitious joint solution. Conditional profiles relax one class while retaining the other exactly. Ties maximize past pooled gain then minimize old candidate ID; these are diagnostic representatives, not new frozen deployment rules.", "",
        "## Past opportunity bounds", "",
        "| Target | Model | Domain | Positive candidates | Exact positive | Minimum joint rate pp | Minimum joint count | Status |",
        "|---|---|---|---:|---:|---:|---:|---|"]
    for r in result["summaries"]:
        lines.append(f"| {r['target']} | {r['model']} | {r['domain']} | {r.get('positive_candidates','NA')} | {r.get('exact_positive_candidates','NA')} | {number(r.get('joint_rate_gap'),100)} | {r.get('joint_count_gap','NA')} | {r['status']} |")
    lines += ["", "## Root-protected diagnostic profiles", "",
        "| Target | Model | Profile | ID | Gain pp | APP22 gap pp / count | APP15 gap pp / count | Qualified |",
        "|---|---|---|---:|---:|---|---|---|"]
    for r in result["profiles"]:
        if r["period"] == "evaluation" and r["domain"] == "root_no_harm":
            lines.append(f"| {r['target']} | {r['model']} | {r['profile']} | {r['candidate_id']} | {number(r.get('gain'),100)} | {number(r.get('APP22_worst_rate_gap'),100)} / {r.get('APP22_worst_count_gap','NA')} | {number(r.get('APP15_worst_rate_gap'),100)} / {r.get('APP15_worst_count_gap','NA')} | {r.get('qualified','NA')} |")
    lines += ["", "## Binding rows for the minimum joint-rate profile", "",
        "| Target | Model | Origin | APP | n | Count deficit | Rate deficit pp | One count pp | Forgone net gain | New root harm |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in result["bindings"]:
        if r["period"] == "evaluation" and r["domain"] == "root_no_harm" and r["profile"] == "minimum_joint_rate" and r["joint_rate_binding"]:
            lines.append(f"| {r['target']} | {r['model']} | {r['origin']} | {r['APP']} | {r['n']} | {r['gap']} | {number(r['rate_gap'],100)} | {r['one_net_count_pp']:.5f} | {r['net_gain_foregone']} | {r['new_root_harm']} |")
    lines += ["", "## Files and limits", "",
        "gap_summary.csv separates feasibility, positive gain, class-specific exact coverage and joint exact coverage. diagnostic_profiles.csv retains all fixed diagnostic objectives, identity, the actual stage-17 deployed choice and the source-latest family. Points outside a domain are explicitly unqualified, even when their gap is zero. binding_constraints.csv retains every month AND pooled row for both focal classes, denominators, small-n flags, count/rate/weighted deficits and exact decomposition. pooled counts are never added to the monthly deficit sums.",
        "past_coverage.csv keeps EVERY original class, prior and monthly count; small-n is a marker, never a filter or excuse to remove a constraint. One-count rates show arithmetic sensitivity, not statistical confidence or an observation that only one sampled flow caused infeasibility. gap_frontiers.csv contains gain/rate-deficit and gain/count-deficit frontiers, compacting equivalent displayed vectors while retaining all candidate IDs. gap_candidate_metrics.npz stores every candidate's monthly/pooled deficits and decomposition; candidate_index.json preserves axes and class/prior order. Original all-class candidate deltas remain in the verified stage-17 input; they are not duplicated or reweighted.",
        "This diagnostic depends only on past data and existing source-frozen choices. It introduces no target-driven allowance or policy. All target periods have already informed earlier exploration, so any later relaxed policy still needs a declared selection protocol and uninspected periods for confirmation. Empty finite-grid sets do not imply impossibility for other representations, and no future-risk or independence guarantee is made.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    if args.small_n < 1:
        raise ValueError("positive small-n required")
    print("Verifying stage-17 lineage and reconciling all past candidate arrays; no H5 or target scoring...",flush=True)
    source,index,arrays,frozen,selection,plan,inputs = read_source(args.costs_dir)
    result = diagnose(index,arrays,frozen,small_n=args.small_n)
    metadata = start_run(args,inputs=inputs,code=[Path(__file__)]+[ROOT/n for n in CODE],source=plan["source"])
    save(args.out_dir/"analysis_protocol.json",{"past_only":True,"original_protocol":selection["original_protocol"],
        "domains":["original_budget","root_no_harm"],"positive_gain_threshold":1e-12,
        "joint_rate":"max over APP22/APP15 and months plus pooled","joint_count":"same rows, net-count units",
        "fixed_diagnostic_ties":"highest pooled past gain then smallest original candidate ID",
        "new_deployment_policy":False,"new_target_scoring":False,"budget_sweep":False})
    for name,rows in (("gap_summary",result["summaries"]),("diagnostic_profiles",result["profiles"]),
        ("binding_constraints",result["bindings"]),("past_coverage",result["coverage"]),("gap_frontiers",result["frontiers"])):
        write_table(args.out_dir/(name+".csv"),rows,("target","model","status"))
    np.savez_compressed(args.out_dir/"gap_candidate_metrics.npz",**result["arrays"])
    save(args.out_dir/"candidate_index.json",{"known_service_codes":index["known_service_codes"],"known_priors":index["known_priors"],
        "unknown_prior":index["unknown_prior"],"gap_APP_order":[22,15],"gap_axes":["past_months_then_pooled","candidate_including_identity","focal_APP"],
        "contexts":result["index"],"source_costs_dir":str(args.costs_dir.resolve())})
    save(args.out_dir/"summary.json",{"past_only":True,"new_target_scoring":False,"new_deployment_policy":False,
        "known_service_codes":index["known_service_codes"],"known_priors":index["known_priors"],"unknown_prior":index["unknown_prior"],
        "contexts":result["summaries"]})
    (args.out_dir/"report.md").write_text(report_text(result))
    metadata.update(rows_read=0,cached_source_rows=source["cached_source_rows"],source_costs_verified=True,new_target_scoring=False,new_deployment_policy=False)
    finish_run(args.out_dir,metadata,started)
    for r in result["summaries"]:
        if r["period"] != "evaluation" or r["domain"] != "root_no_harm":
            continue
        p = next((p for p in result["profiles"] if (p["target"],p["model"],p["domain"],p["profile"]) ==
            (r["target"],r["model"],r["domain"],"minimum_joint_rate")),{})
        b = next((b for b in result["bindings"] if (b["target"],b["model"],b["domain"],b["profile"]) ==
            (r["target"],r["model"],r["domain"],"minimum_joint_rate") and b["joint_rate_binding"]),None)
        binding = f"{b['origin']}/APP{b['APP']}:{b['gap']}/{b['n']}" if b else "none"
        print(f"GAP {r['target']} {r['model']} status={r['status']} positive={r.get('positive_candidates','NA')} exact={r.get('exact_positive_candidates','NA')} min_rate_pp={number(r.get('joint_rate_gap'),100)} min_count={r.get('joint_count_gap','NA')} rate_point_gain_pp={number(p.get('gain'),100)} binding={binding}")
    print(f"Report: {(args.out_dir/'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--costs-dir",type=Path,required=True)
    parser.add_argument("--out-dir",type=Path,required=True)
    parser.add_argument("--small-n",type=int,default=200)
    args = parser.parse_args()
    if not args.costs_dir.is_dir() or args.out_dir.exists() or args.small_n < 1:
        parser.error("completed stage-17 source, positive small-n and fresh output directory required")
    run(args)


if __name__ == "__main__":
    main()
