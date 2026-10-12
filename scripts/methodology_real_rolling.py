#!/usr/bin/env python3
"""Use the verified monthly count cache for focal attribution and rolling models."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.monthlydrift import month_slices  # noqa: E402
from eibo.realexperiment import PERIODS, histogram_predictions  # noqa: E402
from eibo.riskcert import empirical_known_risk, validate_priors  # noqa: E402
from eibo.rolling import MODELS, evaluate, focal_attribution, month_index, project_fine, rolling_experiment  # noqa: E402
from eibo.statcore import grid_cardinality  # noqa: E402
from methodology_real_monthly import number, save, write_csv  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402


def read_cache(directory):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete" or run["rows_read"] < 1:
        raise ValueError("a completed monthly experiment is required")
    previous_code = {Path(item["path"]).name: item["sha256"] for item in run["code"]}
    for name in ("statcore.py", "realexperiment.py"):
        if previous_code.get(name) != sha256(ROOT / "src/eibo" / name):
            raise ValueError(f"canonical codec lineage changed: {name}")
    manifest = {item["path"]: item["sha256"] for item in run["outputs"]}
    for name in ("monthly_symbol_counts.json", "plan_snapshot.json", "summary.json"):
        if sha256(directory / name) != manifest[name]:
            raise ValueError(f"monthly cache artifact hash mismatch: {name}")
    plan = json.loads((directory / "plan_snapshot.json").read_text())
    payload = json.loads((directory / "monthly_symbol_counts.json").read_text())
    summary = json.loads((directory / "summary.json").read_text())
    if plan["status"] != "prepared" or not plan["full_scan"]:
        raise ValueError("cache does not contain a complete prepared plan")
    if any(plan["source"][field] != run["source"][field] for field in ("sha256", "bytes")):
        raise ValueError("source lineage differs between monthly run and plan")
    known = np.asarray(plan["known_service_codes"], dtype=np.int64)
    if len(known) < 2 or np.any(np.diff(known) <= 0):
        raise ValueError("APP order must be sorted and distinct")
    if known.tolist() != payload["known_service_codes"] or known.tolist() != summary["known_service_codes"]:
        raise ValueError("APP order differs among cache artifacts")
    priors = validate_priors(summary["known_priors"], len(known))
    if not np.allclose(priors, plan["known_prior_per_service"], atol=1e-12, rtol=0) or abs(priors.sum() + plan["unknown_prior"] - 1) > 1e-12:
        raise ValueError("cache priors differ from the fixed plan")
    k = int(plan["k"])
    if k < 1:
        raise ValueError("positive prefix length required")
    alphabets = {r: grid_cardinality("log", log_bins=r) ** k for r in (1, 2)}
    specifications = [{"scheme": "log", "M": r, "k": k, "alphabet_size": alphabets[r]} for r in (1, 2)]
    if plan["fixed_representations"] != specifications or alphabets[2] > 1048576:
        raise ValueError("unsupported fixed representation in cache")
    slices = payload["slices"]
    expected = month_slices(plan, [])
    if len(slices) != len(expected) or len({item["key"] for item in slices}) != len(slices):
        raise ValueError("calendar slices are missing or duplicated")
    for actual, target in zip(slices, expected):
        if any(actual[field] != target[field] for field in ("key", "period", "month_utc", "start_epoch", "end_epoch", "calendar_days")):
            raise ValueError("calendar slices differ from the fixed period boundaries")
    if set(payload["counts"]) != {item["key"] for item in slices}:
        raise ValueError("count-cache slice keys differ from calendar metadata")
    counts = {}
    for item in slices:
        values = {}
        for rung in (1, 2):
            matrix = np.asarray(payload["counts"][item["key"]][str(rung)], dtype=float)
            if matrix.shape != (len(known), alphabets[rung]) or not np.isfinite(matrix).all() or np.any(matrix < 0) or np.any(matrix != np.floor(matrix)) or np.any(matrix > run["rows_read"]):
                raise ValueError("invalid monthly count matrix")
            values[rung] = matrix.astype(np.int64)
        if not np.array_equal(project_fine(values[2], k), values[1]):
            raise ValueError("monthly refinement projection differs from canonical codec")
        counts[item["key"]] = values
    periods = {p: {r: sum((counts[item["key"]][r] for item in slices if item["period"] == p),
                         np.zeros((len(known), alphabets[r]), dtype=np.int64)) for r in (1, 2)} for p in PERIODS}
    if sum(matrix[2].sum() for matrix in periods.values()) > run["rows_read"] or any(np.any(periods[p][2].sum(axis=1) == 0) for p in PERIODS):
        raise ValueError("pooled cache population differs from a prepared full scan")
    expected_months = {(item["slice"], item["log_M"]): item for item in summary["monthly"]}
    if len(summary["monthly"]) != len(slices) * 2 or len(expected_months) != len(slices) * 2:
        raise ValueError("monthly summary rows are missing or duplicated")
    focal = 0
    for item in slices:
        for rung in (1, 2):
            matrix = counts[item["key"]][rung]
            ns = matrix.sum(axis=1)
            expected_row = expected_months[(item["key"], rung)]
            if int(ns.sum()) != expected_row["sample_count"] or int(ns.min()) != expected_row["minimum_class_n"] or known[ns == 0].tolist() != expected_row["missing_service_codes"]:
                raise ValueError("monthly sample counts differ from stored summary")
            prediction, _ = histogram_predictions(periods["pilot"][rung], priors)
            actual = evaluate(matrix, priors, prediction, focal)["summary"]["weighted_error"]["value"]
            expected_error = expected_row["pilot_classifier"]["value"]
            point = empirical_known_risk(matrix, priors) if np.all(ns > 0) else None
            for left, right in ((actual, expected_error), (point, expected_row["empirical_F"])):
                if (left is None) != (right is None) or (left is not None and abs(left - right) > 1e-12):
                    raise ValueError("cache baseline metrics differ from monthly summary")
    for period in PERIODS:
        loss = empirical_known_risk(periods[period][1], priors) - empirical_known_risk(periods[period][2], priors)
        if abs(loss - summary["period_coarsening_loss"][period]) > 1e-12:
            raise ValueError("cache pooled coarsening loss differs from monthly summary")
    return {"run": run, "plan": plan, "known": known, "priors": priors, "slices": slices,
            "counts": counts, "period_counts": periods, "source_summary": summary}


def report_text(summary):
    rolling, attribution = summary["rolling"], summary["attribution"]
    lines = ["# Focal symbols, confusion and supervised rolling histograms", "",
             f"Focal APP={summary['focal_APP']}. All {len(summary['known_service_codes'])} fixed known classes compete under unchanged priors.",
             "Counts are reused from the verified cache; no H5 read or new representation is used. Results remain exploratory.",
             "Rolling updates assume past months' labels are available. Current empirical winners use target labels for attribution only and are never rolling predictors.", "",
             "## Full-training monthly comparison, log M=2", "",
             "Errors are fixed-prior weighted contributions; focal errors are conditional on the focal class. NA keeps unavailable history/classes visible.",
             "| Target | Model | Status | Weighted error % | Focal error % | Total training flows | Min training class n |",
             "|---|---|---|---:|---:|---:|---:|"]
    for row in rolling["full"]:
        if row["log_M"] == 2:
            error = row["weighted_error"]["value"] if row["weighted_error"] is not None else None
            lines.append(f"| {row['target']} | {row['model']} | {row['status']} | {number(error,100)} | {number(row['focal_error'],100)} | {sum(row['training_sample_counts'])} | {min(row['training_sample_counts'])} |")
    lines += ["", "## Period comparison", "",
              "Period error pools wrong counts per class over target months before applying fixed priors. It is not a flow-weighted mean of monthly macro errors.",
              "| Period | Log M | Model | Full weighted error % | Full focal error % | Matched mean error % | Matched mean focal error % |",
              "|---|---:|---|---:|---:|---:|---:|"]
    for row in rolling["periods"]:
        error = row["weighted_error"]["value"] if row["weighted_error"] is not None else None
        matched = row["matched_weighted_error"]["mean"] if row["matched_weighted_error"] else None
        focal = row["matched_focal_error"]["mean"] if row["matched_focal_error"] else None
        lines.append(f"| {row['period']} | {row['log_M']} | {row['model']} | {number(error,100)} | {number(row['focal_error'],100)} | {number(matched,100)} | {number(focal,100)} |")
    lines += ["", "Matched comparisons use the same per-class training budgets across all three models, sampling without replacement. Fine counts are projected to coarse counts so both representations use identical selected flows. Repetition spread describes training-subset sensitivity only; it is not a population confidence interval or a dependence correction.",
              "", "## Focal attribution", "",
              "Reference calendar months: " + ", ".join(attribution["reference_months"]) + ". Reference focal flows: " + str(attribution["reference_sample_count"]) + ".",
              "The reference was motivated by previous results; this is retrospective diagnostic work.",
              "| Target | Focal n | Empirical focal TV % | Fixed-pilot error change pp | Oracle mass term pp | Oracle reassignment term pp | Signed coarsening change pp |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for row in attribution["summary"]:
        lines.append(f"| {row['target']} | {row['sample_count']} | {number(row.get('empirical_TV'),100)} | {number(row.get('weighted_pilot_error_change'),100)} | {number(row.get('weighted_oracle_distribution_term'),100)} | {number(row.get('weighted_oracle_reassignment_term'),100)} | {number(row.get('signed_coarsening_contribution_change'),100)} |")
    lines += ["", "The oracle mass term holds the reference empirical rule fixed; the reassignment term changes that rule under the target empirical laws. Their sum equals the focal empirical-oracle error change. This is an algebraic sample decomposition, not a causal effect. Signed per-class coarsening contributions can decrease through error reallocation among classes.",
              "", "## Symbols contributing most to fixed-pilot focal error increases", "",
              "C/S denote the original +1/-1 PPI directions. Size labels describe canonical log bins, not exact packet sizes. For the current log M=2 grid they are 1-38 and 39+ bytes, with canonical saturation above 1500.",
             f"| Target | ID | {summary['prefix_length']}-packet symbol | Probability change | Error change pp | Pilot predicts | Reference empirical winner | Target empirical winner | Strongest target rival |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for item in attribution["summary"]:
        for row in item.get("largest_error_increase_symbols", []):
            lines.append(f"| {item['target']} | {row['symbol_id']} | {row['decoded']} | {number(row['probability_change'])} | {number(row['weighted_pilot_error_change'],100)} | {row['pilot_prediction']} | {row['reference_empirical_winner']} | {row['target_empirical_winner']} | {row['target_strongest_competitor']} |")
    lines += ["", "## Interpretation limits", "",
              "Every calendar window is fixed to preceding calendar months; empty/missing months are not replaced with older data. Missing training classes make a model unavailable; target missing-class ranges retain the fixed priors. Rankings and posterior estimates are descriptive, and known-only precision/posteriors exclude the unknown class. Packet-position marginal TVs are not additive contributions to joint-prefix TV. No new independence claim, significance test or risk certificate is produced.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    cache = read_cache(args.monthly_dir)
    if args.app not in cache["known"]:
        raise ValueError("requested APP is outside the fixed known-class set")
    for month in args.reference_months:
        month_index(month)
    args.out_dir.mkdir(parents=True, exist_ok=False)
    code = [Path(__file__), ROOT / "src/eibo/rolling.py", ROOT / "src/eibo/monthlydrift.py",
            ROOT / "src/eibo/realexperiment.py", ROOT / "src/eibo/statcore.py", ROOT / "src/eibo/riskcert.py",
            ROOT / "scripts/methodology_real_monthly.py", ROOT / "scripts/methodology_real_prepare.py"]
    metadata = {"status": "running", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "parameters": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                "python": platform.python_version(), "numpy": np.__version__, "source_lineage": cache["run"]["source"],
                "input_artifacts": [{"path": str(path.resolve()), "sha256": sha256(path)} for path in sorted(args.monthly_dir.iterdir()) if path.is_file()],
                "code": [{"path": str(path), "sha256": sha256(path)} for path in code],
                "privacy": "aggregated categorical counts/metrics only; no raw identifiers or per-flow data"}
    (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Cache hashes, class priors, chronology, refinement and baseline metrics verified. No H5 scan.", flush=True)
    rolling = rolling_experiment(cache, app=args.app, repeats=args.matched_repeats, seed=args.seed, small_n=args.small_n,
                                 progress=lambda key: print(f"Scored {key}", flush=True))
    attribution = focal_attribution(cache, rolling, app=args.app, reference_months=args.reference_months, top=args.top)
    public_rolling = {key: rolling[key] for key in ("full", "matched", "periods")}
    public_attribution = {key: attribution[key] for key in ("reference_months", "reference_slices", "reference_sample_count", "summary")}
    summary = {"status": "exploratory; retrospective attribution and supervised past-only comparisons",
               "focal_APP": args.app, "prefix_length": cache["plan"]["k"], "known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(),
               "unknown_prior": cache["plan"]["unknown_prior"], "rolling": public_rolling, "attribution": public_attribution,
               "matched_repetitions": args.matched_repeats, "seed": args.seed,
               "assumptions": ["Past-month labels are available for rolling updates.",
                               "Current-month empirical winners are diagnostics, not models used for prediction.",
                               "Matched randomization is conditional on observed training counts, not a population confidence interval.",
                               "All fixed known classes compete; unknown-class error is discarded."]}
    save(args.out_dir / "summary.json", summary)
    save(args.out_dir / "plan_snapshot.json", cache["plan"])
    monthly_rows = []
    for row in rolling["full"]:
        error = row["weighted_error"]
        interval = error["range_from_unobserved_values"] if error is not None else [None, None]
        monthly_rows.append({"target": row["target"], "log_M": row["log_M"], "model": row["model"], "status": row["status"],
            "training_slices": ";".join(row["training_slices"]), "training_total_n": sum(row["training_sample_counts"]),
            "minimum_training_class_n": min(row["training_sample_counts"]),
            "weighted_error": error["value"] if error is not None else None, "missing_value_error_min": interval[0], "missing_value_error_max": interval[1],
            "focal_error": row["focal_error"], "known_only_focal_precision": row.get("known_only_focal_precision")})
    write_csv(args.out_dir / "rolling_monthly_summary.csv", monthly_rows)
    period_rows = []
    for row in rolling["periods"]:
        matched, focal = row["matched_weighted_error"], row["matched_focal_error"]
        period_rows.append({"period": row["period"], "log_M": row["log_M"], "model": row["model"], "status": row["status"],
            "weighted_error": row["weighted_error"]["value"] if row["weighted_error"] is not None else None, "focal_error": row["focal_error"],
            "matched_weighted_error_mean": matched["mean"] if matched else None, "matched_weighted_error_sd": matched["sd_across_training_subsets"] if matched else None,
            "matched_focal_error_mean": focal["mean"] if focal else None, "matched_focal_error_sd": focal["sd_across_training_subsets"] if focal else None})
    write_csv(args.out_dir / "rolling_period_summary.csv", period_rows)
    if rolling["matched"]:
        matched_rows = []
        for row in rolling["matched"]:
            budget, error, focal = row["per_class_training_budgets"], row["weighted_error"], row["focal_error"]
            matched_rows.append({"target": row["target"], "log_M": row["log_M"], "model": row["model"], "status": row["status"],
                "repetitions": row["repetitions"], "minimum_class_budget": min(budget) if budget else None, "total_budget": sum(budget) if budget else None,
                "weighted_error_mean": error["mean"] if error else None, "weighted_error_randomization_sd": error["sd_across_training_subsets"] if error else None,
                "weighted_error_randomization_q05": error["randomization_q05"] if error else None, "weighted_error_randomization_q95": error["randomization_q95"] if error else None,
                "focal_error_mean": focal["mean"] if focal else None, "focal_error_randomization_sd": focal["sd_across_training_subsets"] if focal else None})
        write_csv(args.out_dir / "matched_training_summary.csv", matched_rows)
    write_csv(args.out_dir / "rolling_class_metrics.csv", rolling["classes"])
    write_csv(args.out_dir / "focal_model_confusions.csv", rolling["focal_confusions"])
    write_csv(args.out_dir / "focal_attribution_confusions.csv", attribution["confusions"])
    write_csv(args.out_dir / "focal_symbol_attribution.csv", attribution["symbols"])
    write_csv(args.out_dir / "focal_packet_marginals.csv", attribution["packet_marginals"])
    write_csv(args.out_dir / "focal_packet_TV.csv", attribution["packet_TV"])
    save(args.out_dir / "confusion_matrices.json", [{"target": key[0], "log_M": key[1], "model": key[2],
          "known_service_codes": cache["known"].tolist(), "counts_true_by_predicted": value["confusion"].tolist()}
          for key, value in rolling["evaluations"].items()], compact=True)
    (args.out_dir / "report.md").write_text(report_text(summary))
    metadata.update({"status": "complete", "elapsed_seconds": time.monotonic() - started,
                     "outputs": [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in sorted(args.out_dir.iterdir()) if path.name != "run.json"]})
    (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print("Monthly log M=2: (weighted error, focal conditional error).")
    targets = sorted({row["target"] for row in rolling["full"]})
    for target in targets:
        parts = []
        for model in MODELS:
            row = next(row for row in rolling["full"] if row["target"] == target and row["model"] == model and row["log_M"] == 2)
            error = row["weighted_error"]["value"] if row["weighted_error"] is not None else None
            parts.append(f"{model}=({number(error)},{number(row['focal_error'])})")
        print("MONTH " + target + " " + " ".join(parts))
    print("Complete. Log M=2 period comparisons (fixed-prior weighted fractions; focal error conditional on APP):")
    for row in rolling["periods"]:
        if row["log_M"] == 2:
            error = row["weighted_error"]["value"] if row["weighted_error"] is not None else None
            matched = row["matched_weighted_error"]["mean"] if row["matched_weighted_error"] else None
            focal = row["matched_focal_error"]["mean"] if row["matched_focal_error"] else None
            print(f"PERIOD {row['period']} {row['model']} status={row['status']} error={number(error)} APP_error={number(row['focal_error'])} matched_error={number(matched)} matched_APP_error={number(focal)}")
    for row in attribution["summary"]:
        print(f"APP={args.app} {row['target']} n={row['sample_count']} TV={number(row.get('empirical_TV'))} delta_pilot_error_pp={number(row.get('weighted_pilot_error_change'),100)} oracle_mass_pp={number(row.get('weighted_oracle_distribution_term'),100)} oracle_reassign_pp={number(row.get('weighted_oracle_reassignment_term'),100)} coarsening_delta_pp={number(row.get('signed_coarsening_contribution_change'),100)}")
        for symbol in row.get("largest_error_increase_symbols", [])[:3]:
            print(f"  SYMBOL {symbol['symbol_id']} {symbol['decoded']} delta_p={number(symbol['probability_change'])} error_pp={number(symbol['weighted_pilot_error_change'],100)} pilot={symbol['pilot_prediction']} ref_winner={symbol['reference_empirical_winner']} target_winner={symbol['target_empirical_winner']} rival={symbol['target_strongest_competitor']}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monthly-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--app", type=int, default=2)
    parser.add_argument("--reference-months", nargs="+", default=["2024-12", "2025-01"])
    parser.add_argument("--matched-repeats", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261012)
    parser.add_argument("--small-n", type=int, default=200)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    if not args.monthly_dir.is_dir() or args.out_dir.exists():
        parser.error("completed monthly directory must exist; output directory must be fresh")
    if min(args.seed, args.matched_repeats) < 0 or min(args.small_n, args.top) < 1:
        parser.error("nonnegative seed/repetition count and positive small-n/top required")
    run(args)


if __name__ == "__main__":
    main()
