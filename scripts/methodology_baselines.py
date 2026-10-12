#!/usr/bin/env python3
"""Recompute exploratory multiclass risk baselines from tracked count tables."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.riskcert import direct_risk_bounds, tree_risk_bound  # noqa: E402


def file_record(path: Path) -> dict:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", type=Path, default=ROOT / "artifacts/_project/data/q1_absolute_dense_counts_m1_m2.json")
    parser.add_argument("--ledger", type=Path, default=ROOT / "artifacts/_project/data/d181_joint_coverage_reaggregation.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--rungs", type=int, nargs="+", default=[1, 2])
    parser.add_argument("--min-flows", type=int, default=2000)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--unknown-prior", type=float, help="default: 1/(number of known services + 1)")
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"output exists; select a fresh --out path: {args.out}")
    if args.min_flows < 1:
        parser.error("--min-flows must be positive")
    payload = json.loads(args.counts.read_text())
    ledger = json.loads(args.ledger.read_text())
    if not np.isclose(ledger["parameters"]["overall_alpha"], args.alpha):
        parser.error("ledger alpha differs from --alpha; recompute its simultaneous bounds first")
    services = sorted({int(r["service_a"]) for r in ledger["rows"]} | {int(r["service_b"]) for r in ledger["rows"]})
    if args.unknown_prior is not None and not 0 <= args.unknown_prior < 1:
        parser.error("--unknown-prior must lie in [0, 1)")
    unknown = args.unknown_prior if args.unknown_prior is not None else 1 / (len(services) + 1)
    priors = np.full(len(services), (1 - unknown) / len(services))
    results = {}
    for rung in args.rungs:
        if str(rung) not in payload:
            parser.error(f"count table has no M={rung} rung")
        block = payload[str(rung)]
        if int(block["alphabet_cardinality"]) != (2 * rung) ** 5:
            parser.error("this first-stage runner accepts only declared k=5 count tables")
        try:
            counts = np.asarray([block["counts_by_service"][str(s)] for s in services], dtype=float)
        except KeyError as exc:
            parser.error(f"count table does not cover the ledger service set: {exc}")
        if np.any(counts.sum(axis=1) < args.min_flows):
            parser.error("the fixed service set fails --min-flows; use a separately declared selection")
        result = direct_risk_bounds(counts, priors, alphabet_size=int(block["alphabet_cardinality"]), alpha=args.alpha)
        result.update({"k": 5, "M": rung, "service_labels": services})
        if rung == 1:
            position = {s: i for i, s in enumerate(services)}
            upper = np.zeros((len(services), len(services)))
            laws = counts / counts.sum(axis=1)[:, None]
            seen_pairs = set()
            for row in ledger["rows"]:
                i, j = position[int(row["service_a"])], position[int(row["service_b"])]
                pair = tuple(sorted((i, j)))
                if i == j or pair in seen_pairs:
                    parser.error("ledger has a duplicate or self pair")
                seen_pairs.add(pair)
                if int(counts[i].sum()) != row["n_a"] or int(counts[j].sum()) != row["n_b"]:
                    parser.error("count table and ledger sample sizes disagree")
                tv = float(0.5 * np.abs(laws[i] - laws[j]).sum())
                if not np.isclose(tv, row["tv_hat"], rtol=0, atol=1e-12):
                    parser.error("count table and ledger empirical TV disagree")
                upper[i, j] = upper[j, i] = row["eps_hi_mfree"]
            if len(ledger["rows"]) != len(services) * (len(services) - 1) // 2:
                parser.error("ledger must contain the complete service graph")
            result["tree"] = tree_risk_bound(upper, priors)
            result["legacy_reference"] = {
                "uniform_floor": ledger["summary"]["uniform_floor_M46_open_set"],
                "lp_floor": ledger["summary"]["lp_floor_M46_open_set"],
                "scope": "original ledger's uniform 46-class prior; reference only if --unknown-prior changes",
            }
        results[str(rung)] = result
    report = {
        "status": "exploratory_baseline_recomputation",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": platform.python_version(), "numpy": np.__version__,
        "inputs": [file_record(args.counts), file_record(args.ledger)],
        "code": [file_record(Path(__file__)), file_record(ROOT / "src/eibo/riskcert.py"), file_record(ROOT / "src/eibo/statcore.py")],
        "results": results,
        "limitations": ["Aggregate counts cannot establish temporal disjointness or independence.",
                        "These classical baselines are not a novelty claim or a validation on real traffic.",
                        "Register and review outputs before citing them as new paper evidence."],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    for rung, result in results.items():
        print(f"k=5 M={rung}: classwise={result['classwise']['lower_floor']:.6f}, "
              f"joint_extra_independence={result['joint']['lower_floor']:.6f}")
        if "tree" in result:
            print(f"  tree={result['tree']['lower_floor']:.6f}")
    print(f"Report: {args.out.resolve()}")


if __name__ == "__main__":
    main()
