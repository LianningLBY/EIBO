#!/usr/bin/env python3
"""Re-aggregate X12 k=5 containment counts under the REJECTED upper constant.

NOT CITABLE for any published number. This runner implements the unsplit
sqrt(2 ln(1/alpha_law)) = 2.7162 convention, which the project REJECTED.
The frozen convention is sqrt(2 ln(2/alpha_law)) = 2.9604, giving 340 upper
/ 336 joint at k=5, M=1 (D124/D125). Retained as an archive of the rejected
convention and for the known-truth reproduction gate it contains.

This runner implements the unsplit 2.7162 convention and MUST NOT source a
published number; the reproduction gate inside it is the valuable part and is
preserved.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "artifacts/X12_k5/data/x12_detector_validation_per_pair_k5.csv"
X1_PATH = ROOT / "artifacts/_project/data/q1_lower_side_full_n.json"
OUTPUT_PATH = ROOT / "artifacts/_project/data/x12_k5_containment_corrected_342.json"
SOURCE_CSV = "artifacts/X12_k5/data/x12_detector_validation_per_pair_k5.csv"

DETECTORS = ("lightgbm", "prototype", "ronetc")
HOLDOUTS = ("0.05", "0.1", "0.2")
NULL_RATE = 0.05
ALPHA = 0.05
ALPHA_LAW = ALPHA / 2.0
CONSTANT_OLD_DISPLAY = 2.9604
CONSTANT_NEW_DISPLAY = 2.7162
EXPECTED_OLD_COUNTS = {
    ("lightgbm", "0.05"): 8,
    ("lightgbm", "0.1"): 8,
    ("lightgbm", "0.2"): 10,
    ("prototype", "0.05"): 3,
    ("prototype", "0.1"): 4,
    ("prototype", "0.2"): 4,
    ("ronetc", "0.05"): 3,
    ("ronetc", "0.1"): 3,
    ("ronetc", "0.2"): 2,
}
REQUIRED_CSV_COLUMNS = {
    "pair_id",
    "service_a",
    "service_b",
    "holdout_level",
    "detector",
    "detector_status",
    "pair_error_surrogate",
    "eps_hat_k_hi",
    "floor_violation",
}


def fail(message: str) -> None:
    raise RuntimeError(message)


def pair_key(service_a: Any, service_b: Any) -> tuple[int, int]:
    return int(service_a), int(service_b)


def holdout_key(value: Any) -> str:
    return format(float(value), ".15g")


def binom_sf(k: int, n: int, p: float) -> float:
    return sum(
        math.comb(n, i) * p**i * (1.0 - p) ** (n - i)
        for i in range(k, n + 1)
    )


def p_value(violations: int, trials: int) -> float:
    try:
        from scipy.stats import binomtest
    except ImportError as exc:
        fail(f"scipy.stats.binomtest unavailable: {exc}")
    result = float(binomtest(violations, trials, NULL_RATE, alternative="greater").pvalue)
    independent = binom_sf(violations, trials, NULL_RATE)
    if not math.isclose(result, independent, rel_tol=0.0, abs_tol=1e-12):
        fail(
            f"binomial p-value disagreement: scipy={result:.17g}, "
            f"independent={independent:.17g}, k={violations}, n={trials}"
        )
    return result


def load_x1() -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    with X1_PATH.open() as handle:
        payload = json.load(handle)
    rows = payload.get("rows") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != 990:
        fail(f"X1 source must contain 990 rows: {X1_PATH}")

    by_pair: dict[tuple[int, int], dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            fail("X1 source contains a non-object row")
        required = {"service_a", "service_b", "eps_lo", "upper_recomputed"}
        missing = required - set(row)
        if missing:
            fail(f"X1 row missing required fields: {sorted(missing)}")
        upper = row["upper_recomputed"]
        if not isinstance(upper, dict):
            fail("X1 row upper_recomputed is not an object")
        upper_required = {
            "eps_hi",
            "tv_hat",
            "alphabet_size",
            "n1",
            "n2",
            "radius_1",
            "radius_2",
        }
        missing = upper_required - set(upper)
        if missing:
            fail(f"X1 upper_recomputed missing fields: {sorted(missing)}")
        key = pair_key(row["service_a"], row["service_b"])
        if key in by_pair:
            fail(f"duplicate X1 service pair: {key}")
        by_pair[key] = row
    return by_pair, payload


def load_csv() -> list[dict[str, Any]]:
    if not CSV_PATH.is_file():
        fail(f"CSV file is missing: {CSV_PATH}")
    if CSV_PATH.stat().st_size == 0:
        fail(f"CSV file is empty: {CSV_PATH}")

    with CSV_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            fail("CSV has no header")
        missing = REQUIRED_CSV_COLUMNS - set(reader.fieldnames)
        if missing:
            fail(f"CSV is missing required columns: {sorted(missing)}")
        rows = list(reader)
    if len(rows) != 11880:
        fail(f"CSV row count is {len(rows)}, expected 11880")

    parsed: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        status = row["detector_status"].strip()
        detector = row["detector"].strip()
        holdout = holdout_key(row["holdout_level"])
        try:
            services = pair_key(row["service_a"], row["service_b"])
        except (TypeError, ValueError) as exc:
            fail(f"invalid service ids at CSV row {row_number}: {exc}")
        error_raw = row["pair_error_surrogate"].strip()
        error = None if not error_raw else float(error_raw)
        if error is not None and not math.isfinite(error):
            fail(f"non-finite pair_error_surrogate at CSV row {row_number}")
        csv_eps_raw = row["eps_hat_k_hi"].strip()
        csv_eps = None if not csv_eps_raw else float(csv_eps_raw)
        parsed.append(
            {
                "row_number": row_number,
                "pair_id": row["pair_id"].strip(),
                "pair": services,
                "detector": detector,
                "holdout": holdout,
                "status": status,
                "error": error,
                "csv_eps": csv_eps,
                "csv_floor_violation": row["floor_violation"].strip().lower(),
            }
        )
    return parsed


def check_reference_implementation(x1_by_pair: dict[tuple[int, int], dict[str, Any]]) -> None:
    sys.path.insert(0, str(ROOT / "src"))
    from eibo.statcore import tv_upper_bound

    first = next(iter(x1_by_pair.values()))
    upper = first["upper_recomputed"]
    m = float(upper["alphabet_size"])
    n1 = int(upper["n1"])
    n2 = int(upper["n2"])
    reference = tv_upper_bound(
        itertools.repeat(0, n1),
        itertools.repeat(0, n2),
        alphabet_size=m,
        alpha=ALPHA,
    )
    expected_1 = radius(m, n1, math.sqrt(2.0 * math.log(1.0 / ALPHA_LAW)))
    expected_2 = radius(m, n2, math.sqrt(2.0 * math.log(1.0 / ALPHA_LAW)))
    if not math.isclose(reference.radius_1, expected_1, rel_tol=0.0, abs_tol=1e-15):
        fail("tv_upper_bound reference reconciliation failed for radius_1")
    if not math.isclose(reference.radius_2, expected_2, rel_tol=0.0, abs_tol=1e-15):
        fail("tv_upper_bound reference reconciliation failed for radius_2")


def radius(m: float, n: int, constant: float) -> float:
    return 0.5 * math.sqrt(m / n) + 0.5 * constant / math.sqrt(n)


def recompute_eps(row: dict[str, Any], constant: float) -> float:
    upper = row["upper_recomputed"]
    m = float(upper["alphabet_size"])
    n1 = int(upper["n1"])
    n2 = int(upper["n2"])
    value = float(upper["tv_hat"]) + radius(m, n1, constant) + radius(m, n2, constant)
    return min(1.0, max(0.0, value))


def validate_x1_constants(x1_by_pair: dict[tuple[int, int], dict[str, Any]]) -> None:
    constant_old = math.sqrt(2.0 * math.log(2.0 / ALPHA_LAW))
    constant_new = math.sqrt(2.0 * math.log(1.0 / ALPHA_LAW))
    if not math.isclose(constant_old, CONSTANT_OLD_DISPLAY, abs_tol=1e-4):
        fail(f"old constant mismatch: {constant_old}")
    if not math.isclose(constant_new, CONSTANT_NEW_DISPLAY, abs_tol=1e-4):
        fail(f"new constant mismatch: {constant_new}")

    for key, row in x1_by_pair.items():
        upper = row["upper_recomputed"]
        m = float(upper["alphabet_size"])
        n1 = int(upper["n1"])
        n2 = int(upper["n2"])
        old_r1 = radius(m, n1, constant_old)
        old_r2 = radius(m, n2, constant_old)
        if not math.isclose(float(upper["radius_1"]), old_r1, rel_tol=0.0, abs_tol=1e-12):
            fail(f"old radius_1 mismatch for pair {key}")
        if not math.isclose(float(upper["radius_2"]), old_r2, rel_tol=0.0, abs_tol=1e-12):
            fail(f"old radius_2 mismatch for pair {key}")
        old_eps = float(upper["eps_hi"])
        recomputed_old = recompute_eps(row, constant_old)
        if not math.isclose(old_eps, recomputed_old, rel_tol=0.0, abs_tol=1e-12):
            fail(f"old eps_hi mismatch for pair {key}: {old_eps} vs {recomputed_old}")


def verify_csv_join(
    records: list[dict[str, Any]],
    x1_by_pair: dict[tuple[int, int], dict[str, Any]],
) -> None:
    seen: set[tuple[str, str, tuple[int, int]]] = set()
    for row in records:
        key = row["pair"]
        if key not in x1_by_pair:
            fail(f"CSV pair missing from X1 source at row {row['row_number']}: {key}")
        join_key = (row["detector"], row["holdout"], key)
        if join_key in seen:
            fail(f"duplicate CSV detector/holdout/pair row: {join_key}")
        seen.add(join_key)
        old_eps = float(x1_by_pair[key]["upper_recomputed"]["eps_hi"])
        if row["csv_eps"] is not None and not math.isclose(
            row["csv_eps"], old_eps, rel_tol=0.0, abs_tol=1e-10
        ):
            fail(
                f"CSV/X1 eps mismatch at row {row['row_number']}: "
                f"{row['csv_eps']} vs {old_eps}"
            )
    expected_keys = {
        (detector, holdout, pair)
        for detector in ("lightgbm", "prototype", "ronetc", "pcap_encoder")
        for holdout in HOLDOUTS
        for pair in x1_by_pair
    }
    if seen != expected_keys:
        fail(f"CSV join coverage mismatch: got {len(seen)}, expected {len(expected_keys)}")


def verify_old_floor_flags(
    records: list[dict[str, Any]],
    x1_by_pair: dict[tuple[int, int], dict[str, Any]],
    old_pairs: set[tuple[int, int]],
) -> None:
    for row in records:
        if row["detector"] not in DETECTORS or row["holdout"] not in HOLDOUTS:
            continue
        if row["pair"] not in old_pairs:
            continue
        if row["status"] != "computed" or row["error"] is None:
            fail(f"old informative row has missing detector error: {row['row_number']}")
        eps_hi = float(x1_by_pair[row["pair"]]["upper_recomputed"]["eps_hi"])
        expected = row["error"] < (1.0 - eps_hi) / 2.0
        if row["csv_floor_violation"] not in {"true", "false"}:
            fail(f"invalid CSV floor_violation at row {row['row_number']}")
        recorded = row["csv_floor_violation"] == "true"
        if recorded != expected:
            fail(
                f"CSV floor_violation mismatch at row {row['row_number']}: "
                f"recorded={recorded}, recomputed={expected}"
            )


def cell_rows(
    records: list[dict[str, Any]], detector: str, holdout: str
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in records
        if row["detector"] == detector and row["holdout"] == holdout
    ]
    if len(rows) != 990:
        fail(f"{detector}/{holdout} has {len(rows)} rows, expected 990")
    return rows


def aggregate_cell(
    rows: list[dict[str, Any]],
    x1_by_pair: dict[tuple[int, int], dict[str, Any]],
    pair_set: set[tuple[int, int]],
    constant: float,
) -> dict[str, Any]:
    selected = [row for row in rows if row["pair"] in pair_set]
    if len(selected) != len(pair_set):
        fail(f"selected row count {len(selected)} != pair count {len(pair_set)}")
    if any(row["status"] != "computed" or row["error"] is None for row in selected):
        fail("selected stratum contains a missing detector error")

    violations = 0
    for row in selected:
        eps_hi = recompute_eps(x1_by_pair[row["pair"]], constant)
        if row["error"] < (1.0 - eps_hi) / 2.0:
            violations += 1
    trials = len(selected)
    return {
        "informative_count": trials,
        "violations": violations,
        "p_value": p_value(violations, trials),
    }


def reproduction(
    records: list[dict[str, Any]],
    x1_by_pair: dict[tuple[int, int], dict[str, Any]],
    old_pairs: set[tuple[int, int]],
) -> tuple[dict[str, list[dict[str, Any]]], bool]:
    output: dict[str, list[dict[str, Any]]] = {}
    matches = True
    for detector in DETECTORS:
        cells: list[dict[str, Any]] = []
        for holdout in HOLDOUTS:
            cell = aggregate_cell(
                cell_rows(records, detector, holdout),
                x1_by_pair,
                old_pairs,
                math.sqrt(2.0 * math.log(2.0 / ALPHA_LAW)),
            )
            cell["holdout"] = holdout
            cells.append(cell)
            if cell["violations"] != EXPECTED_OLD_COUNTS[(detector, holdout)]:
                matches = False
        output[detector] = cells
    return output, matches


def corrected_table(
    records: list[dict[str, Any]],
    x1_by_pair: dict[tuple[int, int], dict[str, Any]],
    new_pairs: set[tuple[int, int]],
) -> dict[str, dict[str, dict[str, Any]]]:
    constant_new = math.sqrt(2.0 * math.log(1.0 / ALPHA_LAW))
    return {
        detector: {
            holdout: aggregate_cell(
                cell_rows(records, detector, holdout),
                x1_by_pair,
                new_pairs,
                constant_new,
            )
            for holdout in HOLDOUTS
        }
        for detector in DETECTORS
    }


def newly_included(
    records: list[dict[str, Any]],
    x1_by_pair: dict[tuple[int, int], dict[str, Any]],
    old_pairs: set[tuple[int, int]],
    new_pairs: set[tuple[int, int]],
) -> list[dict[str, Any]]:
    added = sorted(new_pairs - old_pairs)
    output: list[dict[str, Any]] = []
    for pair in added:
        pair_rows = [
            row
            for row in records
            if row["pair"] == pair and row["detector"] in DETECTORS
        ]
        errors: dict[str, dict[str, float]] = {
            detector: {} for detector in DETECTORS
        }
        for row in pair_rows:
            if row["status"] != "computed" or row["error"] is None:
                fail(f"newly included pair has missing error: {pair}, {row}")
            errors[row["detector"]][row["holdout"]] = row["error"]
        for detector in DETECTORS:
            if set(errors[detector]) != set(HOLDOUTS):
                fail(f"newly included pair missing detector/holdout error: {pair}/{detector}")
        output.append(
            {
                "pair": f"{pair[0]}:{pair[1]}",
                "service_a": pair[0],
                "service_b": pair[1],
                "detector_errors": errors,
            }
        )
    return output


def verdict_changes(
    old_table: dict[str, list[dict[str, Any]]],
    new_table: dict[str, dict[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for detector in DETECTORS:
        old_by_holdout = {cell["holdout"]: cell for cell in old_table[detector]}
        for holdout in HOLDOUTS:
            old_p = float(old_by_holdout[holdout]["p_value"])
            new_p = float(new_table[detector][holdout]["p_value"])
            old_reject = old_p <= ALPHA
            new_reject = new_p <= ALPHA
            if old_reject != new_reject:
                changes.append(
                    {
                        "detector": detector,
                        "holdout": holdout,
                        "p_value_old": old_p,
                        "p_value_new": new_p,
                        "reject_old": old_reject,
                        "reject_new": new_reject,
                    }
                )
    return changes


def write_json(payload: dict[str, Any]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=OUTPUT_PATH.name + ".", suffix=".tmp", dir=OUTPUT_PATH.parent
    )
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=False)
            handle.write("\n")
        os.replace(temporary, OUTPUT_PATH)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def runner_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def main() -> None:
    x1_by_pair, _ = load_x1()
    records = load_csv()
    check_reference_implementation(x1_by_pair)
    validate_x1_constants(x1_by_pair)
    verify_csv_join(records, x1_by_pair)

    constant_old = math.sqrt(2.0 * math.log(2.0 / ALPHA_LAW))
    constant_new = math.sqrt(2.0 * math.log(1.0 / ALPHA_LAW))
    old_pairs = {
        pair
        for pair, row in x1_by_pair.items()
        if float(row["upper_recomputed"]["eps_hi"]) < 0.5
    }
    new_pairs = {
        pair
        for pair, row in x1_by_pair.items()
        if recompute_eps(row, constant_new) < 0.5
    }
    old_joint = {
        pair
        for pair in old_pairs
        if float(x1_by_pair[pair]["eps_lo"]) > 0.05
    }
    new_joint = {
        pair
        for pair in new_pairs
        if float(x1_by_pair[pair]["eps_lo"]) > 0.05
    }
    if len(old_pairs) != 340:
        fail(f"original upper stratum has {len(old_pairs)} pairs, expected 340")
    if len(old_joint) != 336:
        fail(f"original joint stratum has {len(old_joint)} pairs, expected 336")
    if len(new_pairs) != 342:
        fail(f"corrected upper stratum has {len(new_pairs)} pairs, expected 342")
    if len(new_joint) != 338:
        fail(f"corrected joint stratum has {len(new_joint)} pairs, expected 338")

    verify_old_floor_flags(records, x1_by_pair, old_pairs)
    old_table, reproduction_matches = reproduction(records, x1_by_pair, old_pairs)
    if not reproduction_matches:
        fail("original 340-stratum reproduction mismatch")
    new_table = corrected_table(records, x1_by_pair, new_pairs)
    added = newly_included(records, x1_by_pair, old_pairs, new_pairs)
    if len(added) != 2:
        fail(f"newly included pair count is {len(added)}, expected 2")

    payload = {
        "constant_old": CONSTANT_OLD_DISPLAY,
        "constant_new": CONSTANT_NEW_DISPLAY,
        "stratum": {
            "old_pairs": 340,
            "new_pairs": 342,
            "upper_corrected": len(new_pairs),
            "joint_corrected": len(new_joint),
        },
        "reproduction_of_original_340": old_table,
        "corrected_342": {"per_detector": new_table},
        "newly_included_pairs": added,
        "verdict_changes": verdict_changes(old_table, new_table),
        "source_csv": SOURCE_CSV,
        "runner_path": "scripts/x12_k5_containment_corrected_342.py",
        "runner_sha256": runner_sha256(),
        "method": {
            "eps_hi_old_field": "upper_recomputed.eps_hi",
            "eps_hi_new": "tv_hat + radius_new(n1) + radius_new(n2), clipped to [0,1]",
            "radius_reference": "eibo.statcore.tv_upper_bound",
            "floor_violation": "pair_error_surrogate < (1 - eps_hi) / 2",
            "binomial_test": {
                "null_rate": NULL_RATE,
                "alpha": ALPHA,
                "alternative": "greater",
                "split_convention": "one-sided; alpha is not split",
            },
            "joint_gate": "eps_hi < 0.5 and eps_lo > 0.05",
            "constant_exact_old": constant_old,
            "constant_exact_new": constant_new,
        },
    }
    write_json(payload)

    print(json.dumps({
        "output": str(OUTPUT_PATH),
        "reproduction_matches": reproduction_matches,
        "old_pairs": len(old_pairs),
        "old_joint": len(old_joint),
        "new_pairs": len(new_pairs),
        "new_joint": len(new_joint),
        "newly_included": added,
        "corrected_342": new_table,
        "verdict_changes": payload["verdict_changes"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
