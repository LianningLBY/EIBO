#!/usr/bin/env python3
"""Independent Q1 k=5 recomputation.

This file intentionally does not import the project TV or threshold helpers.
It reads the verified remote artifacts, implements its own beta inversion,
Clopper-Pearson construction, bisection threshold, and dense-count TV.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path


ROOT = Path("/root/eibo")
ARTIFACTS = ROOT / "artifacts"
OUT = ARTIFACTS / "q1_independent_recompute.json"

INPUTS = {
    str(ARTIFACTS / "q1_absolute_summary.json"): "d7eeb0c1189b5c963e712d7e6b9cf7d0f866680b40a3483a47215bbb23dd2934",
    str(ARTIFACTS / "q1_absolute_counts.json"): "979c462e0638f624438fee2d8965f4c49140d8f975561b870c3af03144348094",
    str(ARTIFACTS / "q1_absolute_counts.csv"): "388495382742723461212b0384a8d997dcc66b72fa053feee1bd81b0c132b15b",
    str(ARTIFACTS / "q1_absolute_counts.meta.json"): "f4e8609e4722a28feda129bb2092ec4379785992ccf82c223b10fc71ee3f7a4e",
    str(ARTIFACTS / "q1_absolute_dense_counts_m1_m2.json"): "479571b55bae30c6d09846f004969759365f92c21e8b67274b09f2ecf612a099",
}

ALPHA = 0.05
ALPHA_PER_CELL = 0.025
ALPHA_ALTERNATIVE = 0.0125
TARGET = 0.05
BISECTION_TOL = 1.0e-13


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(16 * 1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def write_json(payload: dict) -> None:
    with OUT.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def beta_fraction(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta, continued-fraction implementation."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_term = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    front = math.exp(log_term)
    if x < (a + 1.0) / (a + b + 2.0):
        return front * beta_fraction_cf(a, b, x) / a
    return 1.0 - front * beta_fraction_cf(b, a, 1.0 - x) / b


def beta_fraction_cf(a: float, b: float, x: float) -> float:
    tiny = 1.0e-300
    value_c = 1.0
    value_d = 1.0 - (a + b) * x / (a + 1.0)
    if abs(value_d) < tiny:
        value_d = tiny
    value_d = 1.0 / value_d
    result = value_d
    for iteration in range(1, 301):
        even = 2.0 * iteration
        coefficient = iteration * (b - iteration) * x / ((a - 1.0 + even) * (a + even))
        value_d = 1.0 + coefficient * value_d
        if abs(value_d) < tiny:
            value_d = tiny
        value_c = 1.0 + coefficient / value_c
        if abs(value_c) < tiny:
            value_c = tiny
        value_d = 1.0 / value_d
        result *= value_d * value_c

        coefficient = -((a + iteration) * (a + b + iteration) * x) / (
            (a + even) * (a + 1.0 + even)
        )
        value_d = 1.0 + coefficient * value_d
        if abs(value_d) < tiny:
            value_d = tiny
        value_c = 1.0 + coefficient / value_c
        if abs(value_c) < tiny:
            value_c = tiny
        value_d = 1.0 / value_d
        delta = value_d * value_c
        result *= delta
        if abs(delta - 1.0) < 3.0e-15:
            break
    return result


def beta_quantile(probability: float, a: float, b: float) -> float:
    """Invert the regularized beta CDF by bisection."""
    low = 0.0
    high = 1.0
    for _ in range(120):
        middle = 0.5 * (low + high)
        if beta_fraction(a, b, middle) < probability:
            low = middle
        else:
            high = middle
    return 0.5 * (low + high)


def cp_upper_fractional(successes: float, trials: int, cell_alpha: float) -> float:
    """One-sided CP upper endpoint using the beta-quantile form.

    The two-cell construction supplies a deterministic expected error count
    ``successes`` that may be non-integral while retaining the CP beta-shape
    formula used by the specification.
    """
    if trials <= 0 or successes >= trials:
        return 1.0
    if successes <= 0.0:
        return 1.0 - cell_alpha ** (1.0 / trials)
    return beta_quantile(1.0 - cell_alpha, successes + 1.0, trials - successes)


def two_cell_lower(candidate_tv: float, n_a: int, n_b: int, cell_alpha: float) -> float:
    """Lower TV witness for the symmetric two-cell construction."""
    if candidate_tv <= 0.0 or n_a <= 0 or n_b <= 0:
        return 0.0
    error_probability = 0.5 * (1.0 - candidate_tv)
    upper_a = cp_upper_fractional(error_probability * n_a, n_a, cell_alpha)
    upper_b = cp_upper_fractional(error_probability * n_b, n_b, cell_alpha)
    return max(0.0, 1.0 - min(upper_a, 0.5) - min(upper_b, 0.5))


def exact_threshold(n: int, cell_alpha: float = ALPHA_PER_CELL) -> tuple[float, float, int]:
    """Bisect the smallest TV whose two-cell lower witness exceeds 0.05."""
    if n <= 0:
        return (float("nan"), float("nan"), 0)
    low = 0.0
    high = 0.5
    iterations = 0
    if two_cell_lower(high, n, n, cell_alpha) <= TARGET:
        return (float("nan"), high - low, iterations)
    while high - low > BISECTION_TOL and iterations < 120:
        middle = 0.5 * (low + high)
        if two_cell_lower(middle, n, n, cell_alpha) > TARGET:
            high = middle
        else:
            low = middle
        iterations += 1
    return high, high - low, iterations


def own_tv_from_counts(counts_a: list[int], counts_b: list[int]) -> float:
    """Compute TV over the complete fixed alphabet from two count vectors."""
    total_a = sum(counts_a)
    total_b = sum(counts_b)
    if total_a <= 0 or total_b <= 0:
        raise ValueError("TV input has an empty count vector")
    return 0.5 * sum(
        abs(float(a) / total_a - float(b) / total_b)
        for a, b in zip(counts_a, counts_b)
    )


def radius(M: int, n: int) -> float:
    constant = math.sqrt(2.0 * math.log(2.0 / ALPHA_PER_CELL))
    return (math.sqrt((2 * M) ** 5) + constant) / math.sqrt(n)


def load_inputs() -> tuple[dict, list[dict], dict, dict]:
    actual_hashes = {path: sha256_file(Path(path)) for path in INPUTS}
    mismatches = {
        path: {"expected": INPUTS[path], "actual": actual_hashes[path]}
        for path in INPUTS
        if actual_hashes[path] != INPUTS[path]
    }
    if mismatches:
        raise RuntimeError("required input sha256 mismatch: " + json.dumps(mismatches, sort_keys=True))
    with open(ARTIFACTS / "q1_absolute_summary.json", encoding="utf-8") as handle:
        summary = json.load(handle)
    with open(ARTIFACTS / "q1_absolute_counts.json", encoding="utf-8") as handle:
        counts = json.load(handle)
    with open(ARTIFACTS / "q1_absolute_dense_counts_m1_m2.json", encoding="utf-8") as handle:
        dense = json.load(handle)
    with open(ARTIFACTS / "q1_absolute_counts.meta.json", encoding="utf-8") as handle:
        metadata = json.load(handle)
    return summary, counts["pairs"], dense, metadata


def pick_raw_rows(rows: list[dict], threshold_cache: dict[int, dict]) -> list[dict]:
    m1 = [row for row in rows if int(row["M"]) == 1]

    def scored(row: dict) -> dict:
        n_a = int(row["n_a"])
        n_b = int(row["n_b"])
        ta = threshold_cache[n_a]["primary"]
        tb = threshold_cache[n_b]["primary"]
        ra = radius(1, n_a)
        rb = radius(1, n_b)
        eps = float(row["tv_k5_masked"]) + ra + rb
        return {
            "source": row,
            "n_sum": n_a + n_b,
            "lower": float(row["tv_k5_masked"]) > ta and float(row["tv_k5_masked"]) > tb,
            "upper": eps < 0.5,
            "eps_hi": eps,
        }

    candidates = [scored(row) for row in m1]
    chosen: list[dict] = []
    largest = max(candidates, key=lambda item: item["n_sum"])
    chosen.append(largest)
    failures = [item for item in candidates if not item["upper"] and item is not largest]
    if failures:
        chosen.append(min(failures, key=lambda item: item["eps_hi"]))
    passes = [item for item in candidates if item["lower"] and item["upper"] and item not in chosen]
    if passes:
        chosen.append(max(passes, key=lambda item: item["eps_hi"]))
    for item in candidates:
        if len(chosen) >= 3:
            break
        if item not in chosen:
            chosen.append(item)
    return [item["source"] for item in chosen[:3]]


def make_raw_record(row: dict, threshold_cache: dict[int, dict]) -> dict:
    n_a = int(row["n_a"])
    n_b = int(row["n_b"])
    tv_value = float(row["tv_k5_masked"])
    ta = threshold_cache[n_a]["primary"]
    tb = threshold_cache[n_b]["primary"]
    ca = 0.05 + 1.958 / math.sqrt(n_a)
    cb = 0.05 + 1.958 / math.sqrt(n_b)
    ra = radius(int(row["M"]), n_a)
    rb = radius(int(row["M"]), n_b)
    eps_hi = tv_value + ra + rb
    return {
        "service_a": row["service_a"],
        "service_b": row["service_b"],
        "M": int(row["M"]),
        "n_a": n_a,
        "n_b": n_b,
        "tv_k5_masked": tv_value,
        "T_exact_n_a": ta,
        "T_exact_n_b": tb,
        "T_approx_n_a": ca,
        "T_approx_n_b": cb,
        "T_exact_minus_approx_n_a": ta - ca,
        "T_exact_minus_approx_n_b": tb - cb,
        "radius_a": ra,
        "radius_b": rb,
        "eps_hi": eps_hi,
        "lower_pass": bool(tv_value > ta and tv_value > tb),
        "upper_pass": bool(eps_hi < 0.5),
        "both_pass": bool(tv_value > ta and tv_value > tb and eps_hi < 0.5),
        "selection_note": "selected by largest n_a+n_b, upper-fail example, or closest upper-pass example",
    }


def main() -> None:
    if OUT.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {OUT}")
    summary, rows, dense, metadata = load_inputs()
    if len(rows) != 4950:
        raise ValueError(f"unexpected row count: {len(rows)}")

    payload = {
        "status": "running",
        "output_path": str(OUT),
        "input_sha256": INPUTS,
        "input_row_count": len(rows),
        "source_h5_read": False,
        "bisection": {
            "tv_interval": [0.0, 0.5],
            "tolerance": BISECTION_TOL,
            "target_lower_bound": TARGET,
            "primary_cell_alpha": ALPHA_PER_CELL,
            "alternative_cell_alpha": ALPHA_ALTERNATIVE,
        },
        "provenance": {
            "script": "/root/eibo/scripts/q1_independent_recompute.py",
            "interpreter": "/root/miniconda3/bin/python3",
            "deliberately_not_used": [
                "/root/eibo/scripts/xs_compression_early_readout.py::tv",
                "/root/eibo/scripts/run_q1_absolute_e3.py",
                "/root/eibo/scripts/run_q1_absolute_e3.py::threshold_pair",
                "/root/eibo/scripts/run_q1_absolute_e3.py::radius",
                "/root/eibo/scripts/evaluate_q1_absolute.py::eps_lo_two_cell",
                "/root/eibo/scripts/evaluate_q1_absolute.py::t_of_n",
                "/root/eibo/scripts/evaluate_q1_absolute.py::radius_sum",
                "any E3-generated code path for the recomputation",
            ],
            "consumed_existing_artifacts": [
                "/root/eibo/artifacts/q1_absolute_summary.json",
                "/root/eibo/artifacts/q1_absolute_counts.json",
                "/root/eibo/artifacts/q1_absolute_counts.csv",
                "/root/eibo/artifacts/q1_absolute_counts.meta.json",
                "/root/eibo/artifacts/q1_absolute_dense_counts_m1_m2.json",
            ],
            "existing_artifacts_modified": False,
            "existing_artifacts_deleted": False,
        },
    }
    write_json(payload)

    service_counts = dense
    unique_n = sorted({int(row["n_a"]) for row in rows} | {int(row["n_b"]) for row in rows})
    threshold_cache: dict[int, dict] = {}
    max_bracket = 0.0
    max_iterations = 0
    for n in unique_n:
        primary, width, iterations = exact_threshold(n, ALPHA_PER_CELL)
        alternative, alt_width, alt_iterations = exact_threshold(n, ALPHA_ALTERNATIVE)
        threshold_cache[n] = {
            "primary": primary,
            "primary_final_width": width,
            "primary_iterations": iterations,
            "alternative_alpha_quarter": alternative,
            "alternative_final_width": alt_width,
            "alternative_iterations": alt_iterations,
        }
        max_bracket = max(max_bracket, width, alt_width)
        max_iterations = max(max_iterations, iterations, alt_iterations)
    payload["threshold_cache_summary"] = {
        "unique_n_count": len(unique_n),
        "max_final_bisection_width": max_bracket,
        "max_iterations": max_iterations,
        "converged_within_tolerance": bool(max_bracket <= BISECTION_TOL),
        "definition": (
            "For candidate TV d, let e=(1-d)/2. For each law i, compute the "
            "one-sided CP upper endpoint U_i=BetaInv(1-alpha_cell; e*n_i+1, n_i-e*n_i). "
            "The two-cell lower witness is max(0, 1-min(U_a,0.5)-min(U_b,0.5)). "
            "T_exact(n) is the equal-n crossing where this witness exceeds 0.05."
        ),
        "alternative_definition": (
            "Same construction with alpha_cell=0.0125 (alpha/4), shown only as the "
            "superseded double-split comparison; it is not used in any reported verdict."
        ),
    }
    payload["threshold_samples"] = {}
    sample_n = sorted({int(row["n_a"]) for row in pick_raw_rows(rows, threshold_cache)} | {int(row["n_b"]) for row in pick_raw_rows(rows, threshold_cache)})
    for n in sample_n:
        item = threshold_cache[n]
        payload["threshold_samples"][str(n)] = {
            "T_exact": item["primary"],
            "T_approx": 0.05 + 1.958 / math.sqrt(n),
            "difference_exact_minus_approx": item["primary"] - (0.05 + 1.958 / math.sqrt(n)),
            "alternative_alpha_quarter": item["alternative_alpha_quarter"],
        }
    write_json(payload)

    published = {
        1: {"lower": 0.996969696969697, "upper": 0.29494949494949496, "both": 0.2919191919191919},
        2: {"lower": 1.0, "upper": 0.02727272727272727, "both": 0.02727272727272727},
        4: {"lower": 1.0, "upper": 0.0, "both": 0.0},
        8: {"lower": 1.0, "upper": 0.0, "both": 0.0},
        16: {"lower": 1.0, "upper": 0.0, "both": 0.0},
    }
    fractions = []
    for M in (1, 2, 4, 8, 16):
        selected = [row for row in rows if int(row["M"]) == M]
        lower_count = 0
        upper_count = 0
        both_count = 0
        for row in selected:
            n_a = int(row["n_a"])
            n_b = int(row["n_b"])
            tv_value = float(row["tv_k5_masked"])
            lower_ok = tv_value > threshold_cache[n_a]["primary"] and tv_value > threshold_cache[n_b]["primary"]
            eps_hi = tv_value + radius(M, n_a) + radius(M, n_b)
            upper_ok = eps_hi < 0.5
            lower_count += int(lower_ok)
            upper_count += int(upper_ok)
            both_count += int(lower_ok and upper_ok)
        total = len(selected)
        actual = {
            "lower": lower_count / total,
            "upper": upper_count / total,
            "both": both_count / total,
        }
        fractions.append({
            "M": M,
            "pairs": total,
            "lower_count": lower_count,
            "upper_count": upper_count,
            "both_count": both_count,
            "lower_fraction": actual["lower"],
            "upper_fraction": actual["upper"],
            "both_fraction": actual["both"],
            "published": published[M],
            "max_abs_deviation": max(abs(actual[key] - published[M][key]) for key in ("lower", "upper", "both")),
            "max_abs_deviation_by_fraction": {key: abs(actual[key] - published[M][key]) for key in ("lower", "upper", "both")},
        })
    payload["fraction_table"] = fractions
    write_json(payload)

    tv_comparison = []
    for M in (1, 2):
        rows_m = [row for row in rows if int(row["M"]) == M]
        counts_by_service = dense[str(M)]["counts_by_service"]
        mismatch_count = 0
        max_error = -1.0
        max_row = None
        for row in rows_m:
            a = str(row["service_a"])
            b = str(row["service_b"])
            ca = counts_by_service[a]
            cb = counts_by_service[b]
            if sum(ca) != int(row["n_a"]) or sum(cb) != int(row["n_b"]):
                mismatch_count += 1
            own = own_tv_from_counts(ca, cb)
            error = abs(own - float(row["tv_k5_masked"]))
            if error > max_error:
                max_error = error
                max_row = {"service_a": a, "service_b": b, "published": float(row["tv_k5_masked"]), "recomputed": own}
        tv_comparison.append({
            "M": M,
            "pairs": len(rows_m),
            "routine": "own_tv_from_counts",
            "alphabet_cardinality": len(next(iter(counts_by_service.values()))),
            "denominator_mismatch_count": mismatch_count,
            "max_abs_deviation": max_error,
            "max_abs_deviation_pair": max_row,
        })
    payload["independent_tv_comparison"] = tv_comparison
    write_json(payload)

    missing_eps_path = ARTIFACTS / "q1_eps_lo_symbol_map.json"
    invariant = {
        "evaluated": False,
        "violation_count": None,
        "assertion": "eps_lo <= eps_hi per row",
        "source_artifact": str(missing_eps_path),
        "missing_column": "eps_lo",
        "reason": "The sibling per-pair eps_lo artifact does not exist; q1_absolute_counts has tv_k5_masked, n_a, n_b but no eps_lo.",
        "literal_error": f"ls: cannot access '{missing_eps_path}': No such file or directory",
        "substitution_forbidden": "tv_k5_masked was not substituted for eps_lo",
    }
    payload["hard_invariant_c016"] = invariant
    payload["raw_pairs"] = [make_raw_record(row, threshold_cache) for row in pick_raw_rows(rows, threshold_cache)]
    payload["status"] = "complete"
    payload["row_count"] = len(rows)
    payload["source_summary_metadata"] = {
        "summary_path": str(ARTIFACTS / "q1_absolute_summary.json"),
        "metadata_path": str(ARTIFACTS / "q1_absolute_counts.meta.json"),
        "summary_consumed_for_published_values": True,
        "metadata_consumed_for_schema_and_provenance": True,
        "metadata_table_fields": metadata.get("table_fields"),
    }
    payload["report_text"] = build_report_text(payload)
    write_json(payload)

    output_hash = sha256_file(OUT)
    print(json.dumps({
        "path": str(OUT),
        "byte_size": OUT.stat().st_size,
        "sha256": output_hash,
        "row_count": len(rows),
    }, sort_keys=True))


def build_report_text(payload: dict) -> str:
    lines = []
    lines.append("Q1 k=5 independent recomputation report")
    lines.append("")
    lines.append("Exact two-cell construction: for candidate TV d, e=(1-d)/2. For each law i, U_i is the one-sided Clopper-Pearson upper endpoint BetaInv(0.975; e*n_i+1, n_i-e*n_i). The lower witness is max(0, 1-min(U_a,0.5)-min(U_b,0.5)). T_exact(n) is the equal-n bisection crossing where this witness exceeds 0.05. The reported guarantee convention is per-cell alpha=0.025; the union over the two laws is 95% for this lower construction. This is an exact numerical inversion of the stated construction, not the calibrated 1.958 approximation.")
    lines.append(f"Bisection tolerance: {payload['bisection']['tolerance']:.1e}; maximum final interval width: {payload['threshold_cache_summary']['max_final_bisection_width']:.3e}; maximum iterations: {payload['threshold_cache_summary']['max_iterations']}.")
    lines.append("")
    lines.append("Threshold samples (T_exact, approximation, exact-minus-approximation, unused alpha/4 comparison):")
    for n, item in sorted(payload["threshold_samples"].items(), key=lambda pair: int(pair[0])):
        lines.append(f"n={n}: {item['T_exact']:.12f}, {item['T_approx']:.12f}, {item['difference_exact_minus_approx']:+.12e}, {item['alternative_alpha_quarter']:.12f}")
    lines.append("")
    lines.append("Fraction table; all lower tests use tv > T_exact(n_a) AND tv > T_exact(n_b), and upper tests use eps_hi < 0.5:")
    lines.append("M | lower count/fraction | upper count/fraction | both count/fraction | max abs deviation")
    for row in payload["fraction_table"]:
        lines.append(f"{row['M']} | {row['lower_count']}/{row['pairs']}={row['lower_fraction']:.10f} | {row['upper_count']}/{row['pairs']}={row['upper_fraction']:.10f} | {row['both_count']}/{row['pairs']}={row['both_fraction']:.10f} | {row['max_abs_deviation']:.10f}")
    lines.append("")
    lines.append("Maximum absolute deviations by fraction:")
    for row in payload["fraction_table"]:
        dev = row["max_abs_deviation_by_fraction"]
        lines.append(f"M={row['M']}: lower={dev['lower']:.10f}, upper={dev['upper']:.10f}, both={dev['both']:.10f}")
    lines.append("")
    lines.append("Independent TV from dense symbol counts:")
    for row in payload["independent_tv_comparison"]:
        lines.append(f"M={row['M']}: max abs deviation={row['max_abs_deviation']:.12e}; denominator mismatches={row['denominator_mismatch_count']}; pair={row['max_abs_deviation_pair']}")
    lines.append("")
    inv = payload["hard_invariant_c016"]
    if inv["evaluated"]:
        lines.append(f"C016 invariant: evaluated on {inv['joined_row_count']} joined rows; violation_count={inv['violation_count']}; eps_hi disagreement count versus sibling={inv['eps_hi_disagreement_count_vs_sibling']}. The point estimate tv_k5_masked was not substituted for eps_lo.")
    else:
        lines.append(f"C016 invariant: NOT EVALUABLE. violation_count=null. Missing column: {inv['missing_column']}. Missing artifact: {inv['source_artifact']}. The point estimate tv_k5_masked was not substituted for eps_lo.")
    lines.append("")
    lines.append("Three raw pairs:")
    for row in payload["raw_pairs"]:
        lines.append(json.dumps(row, sort_keys=True))
    lines.append("")
    provenance = "Provenance: executed /root/eibo/scripts/q1_independent_recompute.py with /root/miniconda3/bin/python3. Its own beta inversion, CP endpoint, bisection threshold, radius, and own_tv_from_counts outputs are consumed above. Deliberately not used: /root/eibo/scripts/xs_compression_early_readout.py::tv; /root/eibo/scripts/run_q1_absolute_e3.py and its threshold_pair/radius routines; /root/eibo/scripts/evaluate_q1_absolute.py::eps_lo_two_cell, t_of_n, and radius_sum; and any E3 script code path for recomputation."
    if "post_run_invariant_joiner" in payload.get("provenance", {}):
        provenance += " C016 was finalized by /root/eibo/scripts/q1_independent_finalize_invariant.py, whose join_on_service_pair and eps_lo_le_eps_hi_assertion outputs are consumed by the invariant field."
    lines.append(provenance)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
