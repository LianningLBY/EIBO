#!/usr/bin/env python3
"""Known-truth coverage and correlated-sampling stress tests for risk baselines."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.riskcert import (direct_risk_bounds, grouped_joint_risk_bound,
                           joint_radius_from_change_budget, tree_risk_bound)  # noqa: E402
from eibo.statcore import tv_upper_bound  # noqa: E402
from eibo.synthetic import (CASE_SPECS, batch_known_risk, failure_interval, make_case,
                            markov_variance_factor, sample_counts_with_units)  # noqa: E402


def stable_seed(seed, cell_id):
    digest = hashlib.sha256(cell_id.encode("utf-8")).digest()
    return np.random.SeedSequence([seed, *np.frombuffer(digest[:16], dtype="<u4").tolist()])


def reference_bounds(case, ns, alpha):
    dummy = np.zeros((len(ns), case["alphabet_size"]), dtype=np.int64)
    dummy[:, 0] = ns
    return direct_risk_bounds(dummy, case["known_priors"], alphabet_size=case["alphabet_size"], alpha=alpha)


def prepare_methods(case, ns, config, alpha, include_tree, tree_max_services):
    reference = reference_bounds(case, ns, alpha)
    mode = config["mode"]
    within_iid = mode in ("iid", "cross_service") or (mode == "block" and config["block_size"] == 1)
    within_iid = within_iid or (mode in ("markov", "cross_markov") and config["rho"] == 0)
    within_iid = within_iid or (mode == "hidden_blocks" and config["block_size"] == 1)
    all_iid = within_iid and mode not in ("cross_service", "cross_markov")
    methods = {
        "classwise_naive": {"radius": reference["classwise"]["radius"], "assumptions_met": within_iid,
                            "basis": "statcore marginal TV radii at alpha/K; raw flow count"},
        "joint_naive": {"radius": reference["joint"]["radius"], "assumptions_met": all_iid,
                        "basis": "joint iid bounded differences; raw flow count"},
    }
    if mode == "block":
        oracle = reference_bounds(case, ns // config["block_size"], alpha)
        for method in ("classwise", "joint"):
            methods[f"{method}_oracle_blocks"] = {
                "radius": oracle[method]["radius"], "assumptions_met": True,
                "basis": "known equal-size independent repeated blocks; one representative per block",
            }
    if mode == "cross_service":
        # One independent shock at each t affects all still-active services.
        positions = np.arange(int(ns.max()))
        changes = ((positions[None, :] < ns[:, None]) *
                   (case["known_priors"] / ns)[:, None]).sum(axis=0)
        dummy = np.zeros((len(ns), case["alphabet_size"]), dtype=np.int64)
        dummy[:, 0] = ns
        oracle = grouped_joint_risk_bound(dummy, case["known_priors"], changes, alpha=alpha)
        methods["joint_oracle_shared_units"] = {
            "radius": oracle["radius"], "assumptions_met": True,
            "basis": "known independent shocks across positions; replace one entire cross-service column",
        }
        methods["joint_observed_shared_runs"] = {
            "radius": None, "dynamic_budget": "observed_budget", "assumptions_met": True,
            "basis": "observed shared constant runs coarsen independent shocks; pathwise budget domination",
        }
    if mode == "markov":
        methods["joint_oracle_regeneration"] = {
            "radius": None, "dynamic_budget": "oracle_budget", "assumptions_met": True,
            "basis": "conditional on latent exogenous regeneration lengths; independent labels across services",
        }
        methods["joint_observed_runs"] = {
            "radius": None, "dynamic_budget": "observed_budget", "assumptions_met": True,
            "basis": "observed constant runs coarsen latent regeneration segments in the sticky iid-refresh model",
        }
    if mode == "cross_markov":
        methods["joint_oracle_shared_regeneration"] = {
            "radius": None, "dynamic_budget": "oracle_budget", "assumptions_met": True,
            "basis": "shared sticky-refresh shocks; sum class contributions in each latent segment before squaring",
        }
        methods["joint_observed_shared_runs"] = {
            "radius": None, "dynamic_budget": "observed_budget", "assumptions_met": True,
            "basis": "observed global shock runs coarsen shared latent regeneration segments",
        }
        methods["joint_separate_run_heuristic"] = {
            "radius": None, "dynamic_budget": "separate_observed_budget", "assumptions_met": False,
            "basis": "negative control: ignores cross-service dependence when squaring changes",
        }
    if mode == "hidden_blocks":
        methods["joint_oracle_hidden_blocks"] = {
            "radius": None, "dynamic_budget": "oracle_budget", "assumptions_met": True,
            "basis": "known independent latent blocks; within-block symbols need not be constant",
        }
        methods["joint_observed_runs"] = {
            "radius": None, "dynamic_budget": "observed_budget", "assumptions_met": config["block_size"] == 1,
            "basis": "negative control: observed changes can split one dependent hidden block; sticky-refresh assumptions fail for b>1",
        }
    if include_tree and case["services"] <= tree_max_services:
        pairs = case["services"] * (case["services"] - 1) // 2
        radii = [tv_upper_bound(np.zeros(int(n), dtype=np.uint8), [0],
                               alphabet_size=case["alphabet_size"], alpha=alpha / pairs).radius_1 for n in ns]
        methods["tree_naive"] = {
            "radius": None, "assumptions_met": within_iid,
            "basis": "finite-alphabet statcore pair upper bounds at alpha/number_of_pairs; adaptive tree on simultaneous event",
            "pair_radii": radii,
        }
    return methods


def tree_floors(counts, priors, radii):
    laws = counts / counts.sum(axis=2)[:, :, None]
    batch, k, _ = laws.shape
    upper = np.zeros((batch, k, k))
    for i in range(k):
        for j in range(i + 1, k):
            values = np.minimum(1, 0.5 * np.abs(laws[:, i] - laws[:, j]).sum(axis=1) + radii[i] + radii[j])
            upper[:, i, j] = upper[:, j, i] = values
    return np.asarray([tree_risk_bound(matrix, priors)["lower_floor"] for matrix in upper])


def evaluate_cell(case, ns, config, methods, args):
    cell_id = f"{case['name']}|n={config['base_n']}|{config['mode']}|b={config['block_size']}|rho={config['rho']}"
    seed_sequence = stable_seed(args.seed, cell_id)
    rng = np.random.default_rng(seed_sequence)
    empirical = []
    floors = {name: [] for name in methods}
    sampled_radii = {name: [] for name in methods if name != "tree_naive"}
    unit_counts, domination = [], []
    example = None
    for start in range(0, args.trials, args.batch_size):
        counts, units = sample_counts_with_units(rng, case, ns, min(args.batch_size, args.trials - start),
                                                mode=config["mode"], block_size=config["block_size"], rho=config["rho"])
        points = batch_known_risk(counts, case["known_priors"])
        empirical.append(points)
        unit_counts.append(units["oracle_unit_counts"])
        if example is None:
            example = units["geometry_example"]
        if units["observed_budget"] is not None:
            delta = units["observed_budget"] - units["oracle_budget"]
            domination.append(delta >= -1e-12)
            if config["mode"] in ("markov", "cross_service", "cross_markov") and np.any(delta < -1e-12):
                raise RuntimeError("observed runs failed to dominate the latent regeneration budget")
        for name, method in methods.items():
            if name == "tree_naive":
                values = tree_floors(counts, case["known_priors"], method["pair_radii"])
            else:
                radii = (joint_radius_from_change_budget(units[method["dynamic_budget"]], alpha=args.alpha)
                         if "dynamic_budget" in method else np.full(len(points), method["radius"]))
                sampled_radii[name].append(radii)
                values = np.maximum(0, points - radii)
            floors[name].append(values)
    truth = case["true_known_risk"]
    point_mean = float(np.concatenate(empirical).mean())
    rows = []
    for name, method in methods.items():
        values = np.concatenate(floors[name])
        failures = int(np.count_nonzero(values > truth + args.violation_tolerance))
        radii = np.concatenate(sampled_radii[name]) if name in sampled_radii else None
        rows.append({
            "cell_id": cell_id, "case": case["name"], **config,
            "services": case["services"], "alphabet_size": case["alphabet_size"],
            "sample_counts": ns.tolist(), "trials": args.trials,
            "seed_entropy": seed_sequence.entropy, "method": name,
            "assumptions_met": method["assumptions_met"], "basis": method["basis"],
            "nominal_failure_budget": args.alpha, "true_known_risk": truth,
            "failures": failures, "failure_rate": failures / args.trials,
            "coverage_rate": 1 - failures / args.trials,
            "failure_ci95": failure_interval(failures, args.trials),
            "mean_empirical_risk": point_mean, "empirical_bias": point_mean - truth,
            "mean_lower_floor": float(values.mean()), "median_lower_floor": float(np.median(values)),
            "lower_floor_q05": float(np.quantile(values, 0.05)),
            "lower_floor_q95": float(np.quantile(values, 0.95)),
            "mean_gap_to_truth": float((truth - values).mean()),
            "max_excess_over_truth": max(0.0, float(values.max() - truth)),
            "zero_floor_rate": float(np.mean(values <= args.violation_tolerance)),
            "radius": method["radius"],
            "mean_radius": float(radii.mean()) if radii is not None else None,
            "radius_q05": float(np.quantile(radii, 0.05)) if radii is not None else None,
            "radius_q95": float(np.quantile(radii, 0.95)) if radii is not None else None,
            "radius_basis": method.get("dynamic_budget", "fixed"),
        })
    counts_all = np.concatenate(unit_counts)
    diagnostics = {"mean_latent_independent_units": float(counts_all.mean()),
                   "latent_unit_count_q05": float(np.quantile(counts_all, 0.05)),
                   "latent_unit_count_q95": float(np.quantile(counts_all, 0.95)),
                   "observed_budget_domination_rate": float(np.concatenate(domination).mean()) if domination else None,
                   "first_replication_geometry": example}
    return rows, diagnostics


def finalize_intervals(rows, mc_alpha):
    # Bonferroni over every reported method/configuration, including stress
    # rows: within-row replications are independent; rows need not be.
    confidence = 1 - mc_alpha / len(rows)
    for row in rows:
        ci = failure_interval(row["failures"], row["trials"], confidence)
        row["failure_ci_simultaneous"] = ci
        row["mc_simultaneous_confidence_per_row"] = confidence
        if ci[0] > row["nominal_failure_budget"]:
            verdict = "failure_rate_above_budget"
        elif ci[1] <= row["nominal_failure_budget"]:
            verdict = "failure_rate_below_budget_on_this_fixed_case"
        else:
            verdict = "inconclusive"
        row["mc_verdict"] = verdict


def write_csv(path, rows):
    keys = ["case", "mode", "base_n", "block_size", "rho", "services", "alphabet_size", "method",
            "assumptions_met", "trials", "true_known_risk", "failures", "failure_rate", "coverage_rate",
            "mean_lower_floor", "mean_gap_to_truth", "zero_floor_rate", "mean_radius", "radius_q05", "radius_q95",
            "empirical_bias", "max_excess_over_truth", "mc_verdict"]
    keys += ["failure_ci95_lo", "failure_ci95_hi", "failure_ci_simultaneous_lo", "failure_ci_simultaneous_hi"]
    with path.open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            flattened = {key: row[key] for key in keys if key in row}
            for field in ("failure_ci95", "failure_ci_simultaneous"):
                flattened[field + "_lo"], flattened[field + "_hi"] = row[field]
            writer.writerow(flattened)


def write_report(path, rows, args):
    valid_bad = [r for r in rows if r["assumptions_met"] and r["mc_verdict"] == "failure_rate_above_budget"]
    stress_bad = [r for r in rows if not r["assumptions_met"] and r["mc_verdict"] == "failure_rate_above_budget"]
    inconclusive = sum(r["mc_verdict"] == "inconclusive" for r in rows)
    lines = ["# Synthetic risk-certificate coverage report", "",
             f"Independent Monte Carlo replications per configuration: {args.trials}; certificate alpha: {args.alpha}.",
             f"Rows: {len(rows)}; valid-assumption rows above budget: {len(valid_bad)}; stress rows above budget: {len(stress_bad)}; inconclusive rows: {inconclusive}.", "",
             "The verdict uses exact binomial intervals with a Bonferroni correction over all rows. This checks fixed synthetic cases; it is not a proof of uniform coverage or an independence check for real traffic.", "",
             "The exact target is the known-class Bayes-risk contribution on the declared alphabet. Unknown-class error is discarded. Tree tests here use finite-alphabet pair upper bounds, not the m-free ledger bounds used in the previous count-table recomputation.", "",
             "Regeneration corrections condition on latent segment lengths that are independent of iid regenerated labels. Observable-run corrections use pathwise domination by coarsening those segments; they do not require the latent boundaries or rho, but do require the sticky iid-refresh model and appropriate cross-service grouping. Hidden blocks are a negative control for that model. n/tau remains a variance diagnostic only.", "",
             "## Rows with failure rates demonstrably above the budget", "",
             "| Case | Mode | n | b / rho | Method | Assumptions met | Failure rate | Simultaneous failure CI |",
             "|---|---|---:|---|---|---|---:|---|" ]
    for row in valid_bad + stress_bad:
        lo, hi = row["failure_ci_simultaneous"]
        lines.append(f"| {row['case']} | {row['mode']} | {row['base_n']} | {row['block_size']} / {row['rho']} | "
                     f"{row['method']} | {row['assumptions_met']} | {row['failure_rate']:.4f} | [{lo:.4f}, {hi:.4f}] |")
    if not valid_bad and not stress_bad:
        lines.extend(["", "No row's simultaneous lower confidence endpoint exceeds the nominal failure budget. This does not establish robustness to arbitrary dependence."])
    lines.extend(["", "## Dependence corrections: 45-class private/common-symbol case", "",
                  "| Mode | n | b / rho | Method | Assumptions met | Coverage | Mean lower floor | Zero-floor fraction | Mean radius |",
                  "|---|---:|---|---|---|---:|---:|---:|---:|"])
    for row in rows:
        if row["case"] == "private_45_64" and row["mode"] in ("markov", "cross_markov", "hidden_blocks"):
            radius = f"{row['mean_radius']:.4f}" if row["mean_radius"] is not None else "-"
            lines.append(f"| {row['mode']} | {row['base_n']} | {row['block_size']} / {row['rho']} | {row['method']} | "
                         f"{row['assumptions_met']} | {row['coverage_rate']:.4f} | {row['mean_lower_floor']:.4f} | {row['zero_floor_rate']:.4f} | {radius} |")
    lines.extend(["", "All rows, including zero-floor rates and gaps to truth, are in summary.csv and summary.json.", ""])
    with path.open("x") as handle:
        handle.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True, help="new directory; existing paths are rejected")
    parser.add_argument("--trials", type=int, default=2000)
    parser.add_argument("--samples-per-service", type=int, nargs="+", default=[128, 512, 2048])
    parser.add_argument("--cases", nargs="+", choices=sorted(CASE_SPECS), default=list(CASE_SPECS))
    parser.add_argument("--modes", nargs="+", choices=["iid", "block", "markov", "cross_service", "cross_markov", "hidden_blocks"], default=["iid", "block", "markov", "cross_service"])
    parser.add_argument("--block-sizes", type=int, nargs="+", default=[8, 32, 128])
    parser.add_argument("--markov-rhos", type=float, nargs="+", default=[0.9, 0.99])
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--mc-alpha", type=float, default=0.05, help="familywise error budget for MC interval conclusions")
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--include-tree", action="store_true", help="also test finite-alphabet trees in small-service cases")
    parser.add_argument("--tree-max-services", type=int, default=8)
    parser.add_argument("--violation-tolerance", type=float, default=1e-12)
    args = parser.parse_args()
    if args.out_dir.exists():
        parser.error(f"output path exists; use a fresh --out-dir: {args.out_dir}")
    if min(args.trials, args.batch_size, args.tree_max_services) < 1 or args.seed < 0:
        parser.error("trials, batch size and tree limit must be positive; seed must be nonnegative")
    if not 0 < args.alpha < 1 or not 0 < args.mc_alpha < 1:
        parser.error("alpha and mc-alpha must lie in (0, 1)")
    if not np.isfinite(args.violation_tolerance) or args.violation_tolerance < 0:
        parser.error("violation tolerance must be finite and nonnegative")
    if any(n < 1 for n in args.samples_per_service) or any(b < 1 for b in args.block_sizes):
        parser.error("sample counts and block sizes must be positive")
    if any(not 0 <= rho < 1 for rho in args.markov_rhos):
        parser.error("markov-rhos must lie in [0, 1)")
    for values in (args.cases, args.modes, args.samples_per_service, args.block_sizes, args.markov_rhos):
        if len(set(values)) != len(values):
            parser.error("duplicate grid values are not allowed")
    cases = [make_case(name) for name in args.cases]
    cells = []
    for case in cases:
        for base_n in args.samples_per_service:
            ns = base_n * case["sample_factors"]
            configs = []
            if "iid" in args.modes:
                configs.append({"mode": "iid", "block_size": 1, "rho": 0.0})
            if "block" in args.modes:
                for block_size in args.block_sizes:
                    if np.any(ns % block_size):
                        parser.error(f"block size {block_size} does not divide sample counts for {case['name']} n={base_n}")
                    configs.append({"mode": "block", "block_size": block_size, "rho": 0.0})
            if "markov" in args.modes:
                configs.extend({"mode": "markov", "block_size": 1, "rho": rho} for rho in args.markov_rhos)
            if "cross_service" in args.modes and case["family"] == "private_common":
                configs.append({"mode": "cross_service", "block_size": 1, "rho": 0.0})
            if "cross_markov" in args.modes and case["family"] == "private_common":
                configs.extend({"mode": "cross_markov", "block_size": 1, "rho": rho} for rho in args.markov_rhos)
            if "hidden_blocks" in args.modes and case["family"] == "private_common":
                for block_size in args.block_sizes:
                    if np.any(ns % block_size):
                        parser.error(f"hidden block size {block_size} does not divide sample counts")
                    configs.append({"mode": "hidden_blocks", "block_size": block_size, "rho": 0.0})
            for config in configs:
                config["base_n"] = base_n
                cells.append((case, ns, config))
    if not cells:
        parser.error("no eligible configurations; shared/hidden sampling requires a private_* case")
    started = time.monotonic()
    args.out_dir.mkdir(parents=True, exist_ok=False)
    parameters = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
    metadata = {"status": "running", "protocol_version": "2-regeneration-and-observed-run-domination",
                "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "parameters": parameters, "python": platform.python_version(), "numpy": np.__version__,
                "scipy": scipy.__version__, "planned_configurations": len(cells),
                "seed_policy": "SHA256 stable cell id + base seed; batch size and library versions also affect the stream",
                "code": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in
                         (Path(__file__), ROOT / "src/eibo/synthetic.py", ROOT / "src/eibo/riskcert.py", ROOT / "src/eibo/statcore.py")],
                "scope": "exploratory known-truth simulation; no real-traffic coverage or novelty claim"}
    (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    serial_cases = [{key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in case.items()} for case in cases]
    (args.out_dir / "laws.json").write_text(json.dumps(serial_cases, indent=2) + "\n")
    rows = []
    with (args.out_dir / "progress.jsonl").open("x") as progress:
        for index, (case, ns, config) in enumerate(cells, 1):
            methods = prepare_methods(case, ns, config, args.alpha, args.include_tree, args.tree_max_services)
            cell_rows, unit_diagnostics = evaluate_cell(case, ns, config, methods, args)
            rows.extend(cell_rows)
            diagnostics = {"independent_units": None}
            if config["mode"] == "iid":
                diagnostics["independent_units"] = int(ns.sum())
            elif config["mode"] == "block":
                diagnostics["independent_units"] = int((ns // config["block_size"]).sum())
            elif config["mode"] == "cross_service":
                diagnostics["independent_units"] = int(ns.max())
            elif config["mode"] in ("markov", "cross_markov"):
                tau = [markov_variance_factor(int(n), config["rho"]) for n in ns]
                diagnostics.update({"variance_inflation_per_service": tau,
                                    "variance_effective_n_diagnostic_only": (ns / np.asarray(tau)).tolist()})
            diagnostics.update(unit_diagnostics)
            progress.write(json.dumps({"cell_id": cell_rows[0]["cell_id"], "diagnostics": diagnostics, "rows": cell_rows}) + "\n")
            progress.flush()
            text = ", ".join(f"{r['method']}={r['failures']}/{args.trials}" for r in cell_rows)
            print(f"[{index}/{len(cells)}] {cell_rows[0]['cell_id']}: failures {text}", flush=True)
    finalize_intervals(rows, args.mc_alpha)
    summary = {"status": "complete", "target": "sum_i pi_i - sum_x max_i pi_i p_i(x)",
               "failure_event": "reported lower floor > exact known-class target + tolerance",
               "mc_familywise_confidence": 1 - args.mc_alpha, "rows": rows,
               "interpretation": "assumptions_met is assigned from the simulator, not inferred from data; stress undercoverage does not refute the iid theorem"}
    with (args.out_dir / "summary.json").open("x") as handle:
        json.dump(summary, handle, indent=2)
        handle.write("\n")
    write_csv(args.out_dir / "summary.csv", rows)
    write_report(args.out_dir / "report.md", rows, args)
    metadata.update({"status": "complete", "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                     "elapsed_seconds": time.monotonic() - started, "reported_rows": len(rows),
                     "tree_scope": f"enabled only for K <= {args.tree_max_services}" if args.include_tree else "disabled"})
    metadata["outputs"] = [{"path": name, "sha256": hashlib.sha256((args.out_dir / name).read_bytes()).hexdigest(),
                            "bytes": (args.out_dir / name).stat().st_size}
                           for name in ("laws.json", "progress.jsonl", "summary.json", "summary.csv", "report.md")]
    (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    valid_bad = sum(r["assumptions_met"] and r["mc_verdict"] == "failure_rate_above_budget" for r in rows)
    stress_bad = sum(not r["assumptions_met"] and r["mc_verdict"] == "failure_rate_above_budget" for r in rows)
    print(f"Complete: {len(rows)} rows; valid-assumption alerts={valid_bad}; stress above budget={stress_bad}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")
    # Assumption-breaking stress rows are expected diagnostics, not a job error.
    if valid_bad:
        sys.exit(2)


if __name__ == "__main__":
    main()
