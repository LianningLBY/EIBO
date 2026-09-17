#!/usr/bin/env python3
"""Re-derive and backfill X12 k=5 binomial violation counts."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_ARTIFACT = Path("/root/eibo/artifacts/x12_detector_validation_k5.json")
DEFAULT_CSV = Path("/root/eibo/artifacts/x12_detector_validation_per_pair_k5.csv")
DEFAULT_X1_CANDIDATES = (
    Path("/root/eibo/artifacts/x1_headline_table.json"),
    Path("/root/eibo/artifacts/q1_lower_side_full_n.json"),
)
NULL_RATE = 0.05
P_VALUE_TOLERANCE = 1e-6
EXPECTED_TRIALS = 340
ERROR_COLUMNS = ("pair_error", "pair_error_surrogate", "detector_error")


def binom_sf(k: int, n: int, p: float) -> float:
    """One-sided binomial survival function P[X >= k]."""
    return sum(
        math.comb(n, i) * p**i * (1.0 - p) ** (n - i)
        for i in range(k, n + 1)
    )


def binomial_p_value(k: int, n: int, p: float) -> tuple[float, str]:
    try:
        from scipy.stats import binomtest
    except ImportError:
        return binom_sf(k, n, p), "manual math.comb survival function"
    return float(binomtest(k, n, p, alternative="greater").pvalue), "scipy.stats.binomtest"


def holdout_key(value: Any) -> str:
    return format(float(value), ".15g")


def pair_key(service_a: Any, service_b: Any) -> tuple[int, int]:
    return int(service_a), int(service_b)


def extract_eps_rows(payload: Any) -> dict[tuple[int, int], float]:
    """Extract (service_a, service_b) -> upper eps_hi from an X1 artifact."""
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return {}

    result: dict[tuple[int, int], float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "service_a" not in row or "service_b" not in row:
            continue
        upper = row.get("upper_recomputed")
        eps = upper.get("eps_hi") if isinstance(upper, dict) else row.get("eps_hi")
        if eps is None:
            continue
        key = pair_key(row["service_a"], row["service_b"])
        value = float(eps)
        previous = result.get(key)
        if previous is not None and not math.isclose(previous, value, rel_tol=0.0, abs_tol=1e-12):
            raise RuntimeError(f"conflicting eps_hi values for pair {key}: {previous} vs {value}")
        result[key] = value
    return result


def load_x1_eps_map(candidates: tuple[Path, ...]) -> tuple[Path, dict[tuple[int, int], float]]:
    attempted: list[str] = []
    for path in candidates:
        attempted.append(str(path))
        if not path.is_file():
            continue
        with path.open() as handle:
            eps_map = extract_eps_rows(json.load(handle))
        if eps_map:
            print(f"X1 eps_hi source: {path} ({len(eps_map)} service pairs)")
            return path, eps_map
    raise RuntimeError("no usable X1 eps_hi source found; tried: " + ", ".join(attempted))


def choose_error(row: dict[str, str]) -> tuple[float | None, str | None]:
    for column in ERROR_COLUMNS:
        raw = (row.get(column) or "").strip()
        if raw:
            value = float(raw)
            if not math.isfinite(value):
                raise RuntimeError(f"non-finite {column} value in row {row.get('pair_id')}")
            return value, column
    return None, None


def load_rows(csv_path: Path, eps_map: dict[tuple[int, int], float]) -> tuple[list[dict[str, Any]], set[str]]:
    records: list[dict[str, Any]] = []
    detectors: set[str] = set()
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RuntimeError("CSV has no header")
        required = {"service_a", "service_b", "holdout_level", "detector", "detector_status"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise RuntimeError(f"CSV is missing required columns: {sorted(missing)}")
        print("CSV columns:", ", ".join(reader.fieldnames))

        for row_number, row in enumerate(reader, start=2):
            detector = row["detector"].strip()
            detectors.add(detector)
            services = pair_key(row["service_a"], row["service_b"])
            if services not in eps_map:
                raise RuntimeError(f"CSV row {row_number} pair {services} missing from X1 eps source")
            eps_hi = eps_map[services]
            csv_eps = (row.get("eps_hat_k_hi") or "").strip()
            if csv_eps and not math.isclose(float(csv_eps), eps_hi, rel_tol=0.0, abs_tol=1e-10):
                raise RuntimeError(
                    f"CSV/X1 eps mismatch at row {row_number}, pair {services}: "
                    f"CSV {csv_eps} vs X1 {eps_hi}"
                )
            status = row["detector_status"].strip()
            if status == "computed":
                error, error_column = choose_error(row)
            else:
                error, error_column = None, None
            records.append(
                {
                    "row_number": row_number,
                    "pair_id": row.get("pair_id", ""),
                    "pair": services,
                    "detector": detector,
                    "holdout": holdout_key(row["holdout_level"]),
                    "status": status,
                    "error": error,
                    "error_column": error_column,
                    "csv_floor_violation": row.get("floor_violation", ""),
                    "eps_hi": eps_hi,
                }
            )
    return records, detectors


def derive_counts(
    artifact: dict[str, Any],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    test = artifact["floor_violation_test"]
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for detector, detector_block in test["per_detector"].items():
        for holdout, block in detector_block["holdouts"].items():
            key = (detector, holdout_key(holdout), holdout)
            matching = [
                row
                for row in records
                if row["detector"] == detector and row["holdout"] == holdout_key(holdout)
            ]
            if detector_block.get("error") or block.get("binomial_test") is None:
                print(f"{detector:12} {holdout:>4} SKIP status={block.get('status')!r}")
                continue
            if not matching:
                raise RuntimeError(f"no CSV rows for {detector} holdout {holdout}")

            pair_ids = [row["pair_id"] for row in matching]
            if len(set(pair_ids)) != len(pair_ids):
                raise RuntimeError(f"duplicate pair rows for {detector} holdout {holdout}")
            usable = [row for row in matching if row["status"] == "computed" and row["error"] is not None]
            if len(usable) != len(matching):
                raise RuntimeError(
                    f"missing detector errors for {detector} holdout {holdout}: "
                    f"{len(matching) - len(usable)} of {len(matching)} rows"
                )

            informative = [row for row in usable if row["eps_hi"] < 0.5]
            for row in informative:
                csv_flag = (row.get("csv_floor_violation") or "").strip().lower()
                expected_flag = row["error"] < (1.0 - row["eps_hi"]) / 2.0
                if csv_flag in {"true", "false"} and (csv_flag == "true") != expected_flag:
                    raise RuntimeError(
                        f"CSV floor_violation mismatch at row {row['row_number']}: "
                        f"recorded={csv_flag}, recomputed={expected_flag}"
                    )
            # The live X12 producer defines a floor violation as error below
            # the claimed lower floor. This is the direction that reproduces
            # the artifact's recorded counts and p-values.
            violations = sum(
                row["error"] < (1.0 - row["eps_hi"]) / 2.0
                for row in informative
            )
            trials = len(informative)
            if trials != EXPECTED_TRIALS:
                raise RuntimeError(
                    f"unexpected informative trial count for {detector} holdout {holdout}: "
                    f"{trials} != {EXPECTED_TRIALS}"
                )

            recorded_p = block["binomial_test"].get("p_value")
            if recorded_p is None:
                raise RuntimeError(f"missing recorded p-value for {detector} holdout {holdout}")
            rederived_p, method = binomial_p_value(violations, trials, NULL_RATE)
            delta = abs(float(recorded_p) - rederived_p)
            existing_count = block.get("floor_violation_count")
            existing_trials = block.get("informative_pair_count")
            if existing_count is not None and int(existing_count) != violations:
                raise RuntimeError(
                    f"existing floor_violation_count mismatch for {detector} holdout {holdout}: "
                    f"{existing_count} != {violations}"
                )
            if existing_trials is not None and int(existing_trials) != trials:
                raise RuntimeError(
                    f"existing informative_pair_count mismatch for {detector} holdout {holdout}: "
                    f"{existing_trials} != {trials}"
                )
            if delta > P_VALUE_TOLERANCE:
                raise RuntimeError(
                    f"p-value mismatch for {detector} holdout {holdout}: "
                    f"recorded={recorded_p:.15g}, rederived={rederived_p:.15g}, delta={delta:.3g}"
                )

            output.append(
                {
                    "detector": detector,
                    "holdout": holdout,
                    "violations": violations,
                    "trials": trials,
                    "recorded_p": float(recorded_p),
                    "rederived_p": rederived_p,
                    "delta": delta,
                    "method": method,
                    "block": block,
                }
            )
            seen.add(key)
    if not output:
        raise RuntimeError("no runnable detector/holdout blocks were verified")
    return output


def patch_artifact(path: Path, results: list[dict[str, Any]]) -> None:
    with path.open() as handle:
        artifact = json.load(handle)
    for result in results:
        block = artifact["floor_violation_test"]["per_detector"][result["detector"]]["holdouts"][
            result["holdout"]
        ]
        block["violations"] = result["violations"]
        block["trials"] = result["trials"]

    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(artifact, handle, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--x1", type=Path, action="append", dest="x1_candidates")
    args = parser.parse_args()
    candidates = tuple(args.x1_candidates) if args.x1_candidates else DEFAULT_X1_CANDIDATES

    with args.artifact.open() as handle:
        artifact = json.load(handle)
    print(f"artifact: {args.artifact}")
    print(f"per-pair CSV: {args.csv}")
    x1_path, eps_map = load_x1_eps_map(candidates)
    records, detectors = load_rows(args.csv, eps_map)
    print(f"CSV rows: {len(records)}; detectors: {', '.join(sorted(detectors))}")
    print("Violation rule: pair_error_surrogate < (1 - eps_hi) / 2, matching the live X12 producer.")
    results = derive_counts(artifact, records)

    print("\nVerification table")
    print("detector     holdout  violations  trials  recorded_p           rederived_p          abs_delta")
    for result in results:
        print(
            f"{result['detector']:12} {result['holdout']:>7} "
            f"{result['violations']:11d} {result['trials']:7d} "
            f"{result['recorded_p']:.15g} {result['rederived_p']:.15g} "
            f"{result['delta']:.3g}"
        )
    print(f"\nAll {len(results)} p-values verified within {P_VALUE_TOLERANCE:g}.")
    print(f"Binomial null violation rate: {NULL_RATE}")
    print(f"X1 source used: {x1_path}")

    patch_artifact(args.artifact, results)
    print("\nPatched fields:")
    for result in results:
        print(
            f"  floor_violation_test.per_detector.{result['detector']}.holdouts."
            f"{result['holdout']}: violations={result['violations']}, trials={result['trials']}"
        )
    print(f"Patched artifact: {args.artifact}")


if __name__ == "__main__":
    main()
