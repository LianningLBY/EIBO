#!/usr/bin/env python3
"""Audit error reallocation among all fixed known classes using stage 6 outputs."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from eibo.collisionaudit import matched_class_wrong, reallocation  # noqa: E402
from eibo.rolling import randomization_summary, rolling_experiment  # noqa: E402
from methodology_real_monthly import number, save, write_csv  # noqa: E402
from methodology_real_prepare import sha256  # noqa: E402
from methodology_real_rolling import read_cache  # noqa: E402


def read_rolling(directory, cache, monthly_dir):
    run = json.loads((directory / "run.json").read_text())
    if run["status"] != "complete" or run["source_lineage"] != cache["plan"]["source"]:
        raise ValueError("completed rolling output with identical source lineage required")
    manifest = {item["path"]: item["sha256"] for item in run["outputs"]}
    for name in ("summary.json", "plan_snapshot.json", "confusion_matrices.json"):
        if sha256(directory / name) != manifest[name]:
            raise ValueError(f"rolling artifact hash mismatch: {name}")
    previous_inputs = {Path(item["path"]).name: item["sha256"] for item in run["input_artifacts"]}
    for name in ("monthly_symbol_counts.json", "summary.json", "plan_snapshot.json"):
        if previous_inputs[name] != sha256(monthly_dir / name):
            raise ValueError("rolling run used different monthly inputs")
    summary = json.loads((directory / "summary.json").read_text())
    if json.loads((directory / "plan_snapshot.json").read_text()) != cache["plan"] or summary["known_service_codes"] != cache["known"].tolist() or summary["known_priors"] != cache["priors"].tolist():
        raise ValueError("rolling class order, prior or plan differs from cache")
    expected = rolling_experiment(cache, app=summary["focal_APP"], repeats=0)
    matrices = {}
    for row in json.loads((directory / "confusion_matrices.json").read_text()):
        token = (row["target"], row["log_M"], row["model"])
        if token in matrices or token not in expected["evaluations"] or row["known_service_codes"] != cache["known"].tolist():
            raise ValueError("duplicated, unexpected or reordered confusion matrix")
        matrix = np.asarray(row["counts_true_by_predicted"], dtype=float)
        if matrix.shape != (len(cache["known"]),) * 2 or not np.isfinite(matrix).all() or np.any(matrix < 0) or np.any(matrix != np.floor(matrix)):
            raise ValueError("invalid confusion counts")
        matrices[token] = matrix.astype(np.int64)
        if not np.array_equal(matrices[token], expected["evaluations"][token]["confusion"]):
            raise ValueError("stored confusion differs from reconstructed past-only model")
    if set(matrices) != set(expected["evaluations"]):
        raise ValueError("rolling confusion matrices are missing")
    for collection, key_fields in (("full", ("target", "log_M", "model")), ("periods", ("period", "log_M", "model"))):
        actual = {tuple(row[field] for field in key_fields): row for row in summary["rolling"][collection]}
        reference = {tuple(row[field] for field in key_fields): row for row in expected[collection]}
        if len(actual) != len(summary["rolling"][collection]) or set(actual) != set(reference):
            raise ValueError("rolling summary rows are missing or duplicated")
        for token, row in reference.items():
            if actual[token]["weighted_error"] != row["weighted_error"] or actual[token]["focal_error"] != row["focal_error"]:
                raise ValueError("rolling summary differs from reconstructed confusion counts")
    return run, summary, expected["predictions"], matrices


def validate_matched(cache, summary, wrong):
    focal = int(np.flatnonzero(cache["known"] == summary["focal_APP"])[0])
    checks = []
    for row in summary["rolling"]["matched"]:
        token = (row["target"], row["log_M"], row["model"])
        if row["log_M"] is None:
            continue
        ns = cache["counts"][row["target"]][row["log_M"]].sum(axis=1)
        errors = np.divide(wrong[token], ns[None, :], out=np.full(wrong[token].shape, np.nan), where=ns[None, :] > 0)
        checks.extend(((randomization_summary(errors @ cache["priors"]), row["weighted_error"]),
                       (randomization_summary(errors[:, focal]), row["focal_error"])))
    for row in summary["rolling"]["periods"]:
        tokens = [(item["key"], row["log_M"], row["model"]) for item in cache["slices"] if item["period"] == row["period"]]
        if not all(token in wrong for token in tokens):
            if row["matched_weighted_error"] is not None or row["matched_focal_error"] is not None:
                raise ValueError("matched period availability differs from stage 6")
            continue
        ns = cache["period_counts"][row["period"]][row["log_M"]].sum(axis=1)
        pooled = sum(wrong[token] for token in tokens)
        errors = np.divide(pooled, ns[None, :], out=np.full(pooled.shape, np.nan), where=ns[None, :] > 0)
        checks.extend(((randomization_summary(errors @ cache["priors"]), row["matched_weighted_error"]),
                       (randomization_summary(errors[:, focal]), row["matched_focal_error"])))
    for actual, expected in checks:
        if actual is None or expected is None:
            if actual is not expected:
                raise ValueError("matched missing-class status differs from stage 6")
            continue
        for field in actual:
            if (actual[field] is None) != (expected[field] is None) or (actual[field] is not None and abs(actual[field] - expected[field]) > 1e-12):
                raise ValueError("matched randomization does not reproduce stage 6")


def start_run(args, *, inputs, code, source):
    args.out_dir.mkdir(parents=True, exist_ok=False)
    metadata = {"status": "running", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "parameters": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
                "source_lineage": source, "python": platform.python_version(), "numpy": np.__version__,
                "input_artifacts": [{"path": str(path.resolve()), "sha256": sha256(path)} for path in inputs],
                "code": [{"path": str(path.resolve()), "sha256": sha256(path)} for path in code],
                "privacy": "aggregated counts and metrics; no per-flow records, IPs, IDs or CIDs"}
    (args.out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def finish_run(out_dir, metadata, started):
    metadata.update({"status": "complete", "elapsed_seconds": time.monotonic() - started,
                     "outputs": [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
                                 for path in sorted(out_dir.iterdir()) if path.name != "run.json"]})
    (out_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n")


def write_rows(path, rows, empty_fields):
    if rows:
        write_csv(path, rows)
    else:
        with path.open("x", newline="") as handle:
            csv.DictWriter(handle, fieldnames=empty_fields).writeheader()


def report_text(result, cache):
    lines = ["# All-class error reallocation", "",
             f"All {len(cache['known'])} fixed known APPs compete under unchanged priors. Unknown-class error is excluded.",
             "This reproduces the completed rolling experiment before decomposing updates on identical target flows.",
             "Positive changes mean harm; negative changes mean improvement. Rescued flows change from wrong to correct; harmed flows change from correct to wrong. Wrong-to-wrong changes affect confusion without changing error.", "",
             "## Monthly and period changes, log M=2", "",
             "| Scope | Target | Model | Error change pp | Positive contributions pp | Negative contributions pp | Harmed / improved classes | Matched change pp |",
             "|---|---|---|---:|---:|---:|---:|---:|"]
    for row in result["summary"]:
        if row["log_M"] != 2:
            continue
        lines.append(f"| {row['scope']} | {row['target']} | {row['model']} | {number(row.get('error_change',{}).get('value'),100)} | {number(row.get('positive_class_contributions'),100)} | {number(row.get('negative_class_contributions'),100)} | {row.get('classes_harmed','NA')} / {row.get('classes_improved','NA')} | {number((row.get('matched_weighted_change') or {}).get('mean'),100)} |")
    for name, label in (("largest_increases", "Largest evaluation-period harms"), ("largest_decreases", "Largest evaluation-period improvements")):
        lines += ["", "## " + label, "", "| Model | APP | n | Status | Conditional change pp | Weighted change pp | Rescued | Harmed | Wrong-to-wrong |", "|---|---:|---:|---|---:|---:|---:|---:|---:|"]
        for row in result["summary"]:
            if row["scope"] == "period" and row["target"] == "evaluation" and row["log_M"] == 2:
                for item in row.get(name, []):
                    lines.append(f"| {row['model']} | {item['APP']} | {item['target_n']} | {item['sample_status']} | {number(item['conditional_error_change'],100)} | {number(item['weighted_error_change'],100)} | {item['rescued_count']} | {item['harmed_count']} | {item['wrong_to_wrong_changed_count']} |")
    lines += ["", "## Interpretation and files", "",
              "class_error_changes.csv retains every fixed class, both representations and every scope; confusion_changes.csv retains every true/predicted pair including diagonals. prediction_transfers.csv identifies exact old-to-new prediction transfers from the common symbol cache.",
              "Period errors pool wrong counts within each class, then apply fixed priors. Each class can therefore have different month weights; a period improvement need not imply improvement in every monthly macro error. Monthly rows are reported separately.",
              "Matched results replay the original seed, repetitions and class budgets. Their spread is conditional training-subset sensitivity, not a population confidence interval or a dependence correction. Missing classes retain their priors and identification ranges; small-n is a reporting flag, not a filter.", ""]
    return "\n".join(lines)


def run(args):
    started = time.monotonic()
    cache = read_cache(args.monthly_dir)
    _, original, predictions, matrices = read_rolling(args.rolling_dir, cache, args.monthly_dir)
    inputs = [directory / name for directory, names in ((args.monthly_dir, ("run.json", "monthly_symbol_counts.json", "summary.json", "plan_snapshot.json")),
              (args.rolling_dir, ("run.json", "summary.json", "plan_snapshot.json", "confusion_matrices.json"))) for name in names]
    code = [Path(__file__), ROOT / "src/eibo/collisionaudit.py", ROOT / "src/eibo/rolling.py", ROOT / "src/eibo/monthlydrift.py",
            ROOT / "src/eibo/realexperiment.py", ROOT / "src/eibo/statcore.py", ROOT / "src/eibo/riskcert.py",
            ROOT / "scripts/methodology_real_rolling.py", ROOT / "scripts/methodology_real_monthly.py", ROOT / "scripts/methodology_real_prepare.py"]
    metadata = start_run(args, inputs=inputs, code=code, source=cache["plan"]["source"])
    print("Rolling lineage and every confusion matrix reproduced from the verified monthly cache.", flush=True)
    repeats, seed = original["matched_repetitions"], original["seed"]
    wrong = matched_class_wrong(cache, repeats, seed, progress=lambda key: print(f"Matched all-class replay: {key}", flush=True))
    validate_matched(cache, original, wrong)
    result = reallocation(cache, predictions, matrices, matched=wrong, small_n=args.small_n, top=args.top)
    save(args.out_dir / "summary.json", {"known_service_codes": cache["known"].tolist(), "known_priors": cache["priors"].tolist(),
         "unknown_prior": cache["plan"]["unknown_prior"], "comparisons": result["summary"], "matched_repetitions": repeats,
         "seed": seed, "status": "descriptive; no new risk certificate"})
    for name, key in (("class_error_changes", "classes"), ("confusion_changes", "confusion_changes"), ("matched_class_changes", "matched_classes")):
        if result[key]:
            write_csv(args.out_dir / (name + ".csv"), result[key])
    write_rows(args.out_dir / "prediction_transfers.csv", result["prediction_transfers"],
               ["scope", "target", "log_M", "model", "true_APP", "old_prediction", "new_prediction", "count", "target_n", "kind", "weighted_error_change"])
    save(args.out_dir / "plan_snapshot.json", cache["plan"])
    (args.out_dir / "report.md").write_text(report_text(result, cache))
    finish_run(args.out_dir, metadata, started)
    for row in result["summary"]:
        if row["scope"] == "period" and row["log_M"] == 2:
            print(f"REALLOCATION {row['target']} {row['model']} delta_pp={number(row.get('error_change',{}).get('value'),100)} harmed={row.get('classes_harmed')} improved={row.get('classes_improved')}")
            for label in ("largest_increases", "largest_decreases"):
                for item in row.get(label, [])[:5]:
                    print(f"  {label} APP={item['APP']} n={item['target_n']} weighted_delta_pp={number(item['weighted_error_change'],100)} conditional_delta_pp={number(item['conditional_error_change'],100)} rescued={item['rescued_count']} harmed={item['harmed_count']}")
    print(f"Report: {(args.out_dir / 'report.md').resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--monthly-dir", type=Path, required=True)
    parser.add_argument("--rolling-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--small-n", type=int, default=200)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    if not args.monthly_dir.is_dir() or not args.rolling_dir.is_dir() or args.out_dir.exists() or min(args.small_n, args.top) < 1:
        parser.error("completed input directories, a fresh output directory and positive small-n/top required")
    run(args)


if __name__ == "__main__":
    main()
