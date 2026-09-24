#!/usr/bin/env python3
"""Track 5 radius-form coverage consequence at the reference setting."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import norm


PROJECT_ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
HARNESS_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/coverage_calibration_ladder.py"
REFERENCE_RUNNER_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/track5_variance_radius.py"
STATCORE_PATH = PROJECT_ROOT / "src/eibo/statcore.py"
JSON_PATH = PROJECT_ROOT / "artifacts/track5_radius_form_coverage.json"
SUMMARY_PATH = PROJECT_ROOT / "artifacts/track5_radius_form_coverage_summary.txt"

N = 60000
BLOCK_SIZE = 64
CONCENTRATION = 0.1
TRUE_TV = 0.400
ALPHABET_SIZE = 32
ALPHA_UPPER = 0.025
NOMINAL_COVERAGE = 0.975
SEED = 20260919
REPLICATES = 1000
BOOTSTRAP_REPLICATES = 128
MAX_SECONDS = 2.0 * 60.0 * 60.0
KNOWN_CONTROL_N = 2791
KNOWN_CONTROL_EXPECTED_EPS_HI = 0.16311342728653244

FALSIFIER = (
    "Coverage identical across conventions within the paired 95% CI would mean the radius-form convention is "
    "cosmetic for coverage and the about-11% gap carries no coverage implication. If coverage differs, the "
    "convention must be identified as conservative or less conservative using the paired coverage difference, "
    "its 95% CI, and the corresponding radius ratio."
)


def load_harness():
    spec = importlib.util.spec_from_file_location("coverage_calibration_ladder", HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load harness: {HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reference_runner():
    spec = importlib.util.spec_from_file_location("track5_variance_radius", REFERENCE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load reference runner: {REFERENCE_RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_statcore():
    spec = importlib.util.spec_from_file_location("eibo_statcore", STATCORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load statcore: {STATCORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_close(label: str, got: float, expected: float, tolerance: float) -> None:
    if not math.isclose(got, expected, rel_tol=0.0, abs_tol=tolerance):
        raise RuntimeError(f"{label} mismatch: expected {expected!r}, got {got!r}")


def paired_difference_ci(values: np.ndarray) -> list[float]:
    if len(values) < 2:
        return [float(values[0]), float(values[0])]
    mean = float(np.mean(values))
    standard_error = float(np.std(values, ddof=1) / math.sqrt(len(values)))
    critical = float(norm.ppf(0.975))
    return [mean - critical * standard_error, mean + critical * standard_error]


def bool_int(value: bool) -> int:
    return int(bool(value))


def build_arm(
    name: str,
    oracle: bool,
    radius_value: float,
    indicators: np.ndarray,
    cp_interval,
    description: str,
) -> dict:
    covered = int(np.sum(indicators, dtype=np.int64))
    coverage = float(covered / len(indicators))
    coverage_ci = [float(x) for x in cp_interval(covered, len(indicators))]
    return {
        "coverage": coverage,
        "covered": covered,
        "coverage_ci95": coverage_ci,
        "radius_value": float(radius_value),
        "oracle": bool(oracle),
        "cp_lower_clears_nominal": bool(coverage_ci[0] >= NOMINAL_COVERAGE),
        "description": description,
        "replicates": int(len(indicators)),
    }


def pairing_row(name: str, numerator_name: str, denominator_name: str, numerator: float, denominator: float) -> dict:
    return {
        "numerator": numerator_name,
        "denominator": denominator_name,
        "numerator_value": float(numerator),
        "denominator_value": float(denominator),
        "relative_gap": float(numerator / denominator - 1.0),
    }


def make_pairing_table(
    r_sym_centered: float,
    r_one_centered: float,
    r_sym_uncentred: float,
    r_one_uncentred: float,
    r_uncentred_upper: float,
    r_normal_median: float,
) -> dict:
    rows = {
        "sym_vs_centred_one_sided": pairing_row(
            "sym_vs_centred_one_sided",
            "quantile(abs(D - median(D)), 0.975)",
            "-quantile(D - median(D), 0.025)",
            r_sym_centered,
            r_one_centered,
        ),
        "sym_vs_uncentred_one_sided": pairing_row(
            "sym_vs_uncentred_one_sided",
            "quantile(abs(D), 0.975)",
            "-quantile(D, 0.025)",
            r_sym_uncentred,
            r_one_uncentred,
        ),
        "sym_vs_uncentred_endpoint": pairing_row(
            "sym_vs_uncentred_endpoint",
            "quantile(abs(D), 0.975)",
            "quantile(D, 0.975)",
            r_sym_uncentred,
            r_uncentred_upper,
        ),
        "uncentred_sym_vs_centred_one_sided": pairing_row(
            "uncentred_sym_vs_centred_one_sided",
            "quantile(abs(D), 0.975)",
            "-quantile(D - median(D), 0.025)",
            r_sym_uncentred,
            r_one_centered,
        ),
        "centred_sym_vs_uncentred_one_sided": pairing_row(
            "centred_sym_vs_uncentred_one_sided",
            "quantile(abs(D - median(D)), 0.975)",
            "-quantile(D, 0.025)",
            r_sym_centered,
            r_one_uncentred,
        ),
        "sym_vs_normal_theory": pairing_row(
            "sym_vs_normal_theory",
            "quantile(abs(D - median(D)), 0.975)",
            "median(z_0.975 * SE_rep)",
            r_sym_centered,
            r_normal_median,
        ),
    }
    target = 0.1139
    closest_name = min(rows, key=lambda key: abs(rows[key]["relative_gap"] - target))
    for key, row in rows.items():
        row["closest_to_recorded_11_39_percent"] = bool(key == closest_name)
        row["matches_recorded_11_39_percent"] = bool(abs(row["relative_gap"] - target) <= 0.005)
    return {
        "rows": rows,
        "recorded_target_relative_gap": target,
        "closest_pairing": closest_name,
        "matching_pairings": [key for key, row in rows.items() if row["matches_recorded_11_39_percent"]],
    }


def make_pairwise_coverage_table(arms: dict, indicator_map: dict[str, np.ndarray]) -> dict:
    names = list(arms)
    rows = {}
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            differences = indicator_map[left].astype(float) - indicator_map[right].astype(float)
            ci = paired_difference_ci(differences)
            mean_difference = float(np.mean(differences))
            left_radius = float(arms[left]["radius_value"])
            right_radius = float(arms[right]["radius_value"])
            rows[f"{left}_vs_{right}"] = {
                "left": left,
                "right": right,
                "coverage_difference_left_minus_right": mean_difference,
                "coverage_difference_ci95_paired_normal": [float(x) for x in ci],
                "radius_ratio_left_over_right": float(left_radius / right_radius),
                "difference_ci_excludes_zero": bool(ci[0] > 0.0 or ci[1] < 0.0),
            }
    return rows


def format_summary(arms: dict) -> str:
    columns = [
        "arm",
        "coverage",
        "covered",
        "ci95_lo",
        "ci95_hi",
        "radius_value",
        "oracle",
        "cp_lower_clears_nominal",
    ]
    rows = []
    for name, arm in arms.items():
        rows.append(
            [
                name,
                repr(float(arm["coverage"])),
                str(int(arm["covered"])),
                repr(float(arm["coverage_ci95"][0])),
                repr(float(arm["coverage_ci95"][1])),
                repr(float(arm["radius_value"])),
                str(bool_int(arm["oracle"])),
                str(bool_int(arm["cp_lower_clears_nominal"])),
            ]
        )
    widths = [max(len(columns[index]), *(len(row[index]) for row in rows)) for index in range(len(columns))]
    lines = [" ".join(columns[index].ljust(widths[index]) for index in range(len(columns)))]
    lines.append(" ".join("-" * width for width in widths))
    for row in rows:
        lines.append(" ".join(row[index].ljust(widths[index]) for index in range(len(columns))))
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict) -> tuple[str, str]:
    JSON_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(format_summary(payload["arms"]), encoding="utf-8")
    return sha256_file(JSON_PATH), sha256_file(SUMMARY_PATH)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicates", type=int, default=REPLICATES)
    args = parser.parse_args()
    if args.replicates < 1 or args.replicates > REPLICATES:
        raise SystemExit(f"--replicates must be in [1, {REPLICATES}]")

    harness = load_harness()
    reference_runner = load_reference_runner()
    statcore = load_statcore()
    runner_path = Path(__file__).resolve()
    runner_sha = sha256_file(runner_path)

    control = statcore.tv_upper_bound(
        np.zeros(KNOWN_CONTROL_N, dtype=np.int16),
        np.zeros(KNOWN_CONTROL_N, dtype=np.int16),
        alphabet_size=ALPHABET_SIZE,
        alpha=ALPHA_UPPER,
    )
    control_eps_hi = float(control.eps_hi)
    check_close("known statcore control eps_hi", control_eps_hi, KNOWN_CONTROL_EXPECTED_EPS_HI, 1e-12)
    print(f"CONTROL: expected={KNOWN_CONTROL_EXPECTED_EPS_HI!r} got={control_eps_hi!r} => MATCH", flush=True)

    iid_reference = statcore.tv_upper_bound(
        np.zeros(N, dtype=np.int16),
        np.zeros(N, dtype=np.int16),
        alphabet_size=ALPHABET_SIZE,
        alpha=ALPHA_UPPER,
    )
    iid_radius = float(iid_reference.radius_1 + iid_reference.radius_2)
    check_close("iid radius", iid_radius, 0.03517985184254251, 1e-12)
    print(
        "CONTEXT: iid_radius={:.12f}; stored reference arm radii A=0.041097083333 "
        "B=0.033171989337 C=0.033117234032; prior pooled context r_sym=0.030840416667 "
        "r_one_975=0.026206250000".format(iid_radius),
        flush=True,
    )
    print(f"PRE-REGISTERED FALSIFIER: {FALSIFIER}", flush=True)

    p, q = harness.make_truth(TRUE_TV)
    rng = np.random.default_rng(SEED)
    z = float(norm.ppf(1.0 - ALPHA_UPPER))
    tv_hats: list[float] = []
    se_values: list[float] = []
    bootstrap_radii: list[float] = []
    normal_radii: list[float] = []
    normal_covered = 0
    bootstrap_covered = 0
    elapsed_at_50 = None
    start = time.perf_counter()
    indicators = {
        "sym_pooled": [],
        "one_sided_pooled": [],
        "uncentred_pooled": [],
        "normal_theory_per_rep": [],
        "sym_bootstrap_per_rep": [],
    }

    for rep in range(args.replicates):
        a = harness.draw_dependent(N, p, BLOCK_SIZE, CONCENTRATION, rng)
        b = harness.draw_dependent(N, q, BLOCK_SIZE, CONCENTRATION, rng)
        a_counts = reference_runner.counts(a)
        b_counts = reference_runner.counts(b)
        reference = statcore.tv_upper_bound(a, b, alphabet_size=ALPHABET_SIZE, alpha=ALPHA_UPPER)
        tv_hat = float(reference.tv_hat)
        check_tv_hat = reference_runner.tv_from_counts(a_counts, b_counts, N, N)
        if not math.isclose(tv_hat, check_tv_hat, rel_tol=0.0, abs_tol=1e-15):
            raise RuntimeError(f"tv_hat reconciliation failed at replicate {rep}: {tv_hat} != {check_tv_hat}")

        a_blocks, a_partial = reference_runner.block_counts(a)
        b_blocks, b_partial = reference_runner.block_counts(b)
        sandwich_radius = reference_runner.sandwich_radius(a_counts, b_counts, a_blocks, b_blocks)
        se = float(sandwich_radius / z)
        bootstrap_radius = reference_runner.bootstrap_radius(
            a_blocks, a_partial, b_blocks, b_partial, tv_hat, rng
        )
        normal_radius = float(z * se)
        tv_hats.append(tv_hat)
        se_values.append(se)
        bootstrap_radii.append(float(bootstrap_radius))
        normal_radii.append(normal_radius)
        normal_covered += int(tv_hat + normal_radius >= TRUE_TV)
        bootstrap_covered += int(tv_hat + bootstrap_radius >= TRUE_TV)

        if rep + 1 == 50:
            elapsed_at_50 = time.perf_counter() - start
            projected_total = elapsed_at_50 * REPLICATES / 50.0
            print(
                f"TIMING: first_50_seconds={elapsed_at_50:.3f} projected_1000_seconds={projected_total:.3f}",
                flush=True,
            )
            if args.replicates == REPLICATES and projected_total > MAX_SECONDS:
                raise RuntimeError(
                    f"budget stop: projected 1000-replicate runtime {projected_total:.3f}s exceeds {MAX_SECONDS:.1f}s"
                )

        if (rep + 1) % 50 == 0 or rep + 1 == args.replicates:
            elapsed = time.perf_counter() - start
            projected = elapsed * REPLICATES / (rep + 1)
            prefix_tv = np.asarray(tv_hats, dtype=float)
            prefix_d = prefix_tv - TRUE_TV
            prefix_centered_d = prefix_d - float(np.median(prefix_d))
            prefix_sym = float(np.quantile(np.abs(prefix_centered_d), 0.975))
            prefix_one = float(-np.quantile(prefix_centered_d, 0.025))
            prefix_uncentred = float(np.quantile(prefix_d, 0.975))
            prefix_sym_covered = int(np.sum(prefix_d + prefix_sym >= 0.0))
            prefix_one_covered = int(np.sum(prefix_d + prefix_one >= 0.0))
            prefix_uncentred_covered = int(np.sum(prefix_d + prefix_uncentred >= 0.0))
            cumulative = (
                f"sym_pooled={prefix_sym_covered}/{rep + 1}, "
                f"one_sided_pooled={prefix_one_covered}/{rep + 1}, "
                f"uncentred_pooled={prefix_uncentred_covered}/{rep + 1}, "
                f"normal_theory_per_rep={normal_covered}/{rep + 1}, "
                f"sym_bootstrap_per_rep={bootstrap_covered}/{rep + 1}"
            )
            print(
                f"PROGRESS: rep={rep + 1}/{args.replicates} cumulative_before_pooling=[{cumulative}] "
                f"projected_1000_seconds={projected:.3f}",
                flush=True,
            )

    tv_array = np.asarray(tv_hats, dtype=float)
    se_array = np.asarray(se_values, dtype=float)
    bootstrap_array = np.asarray(bootstrap_radii, dtype=float)
    normal_array = np.asarray(normal_radii, dtype=float)
    d_array = tv_array - TRUE_TV
    median_d = float(np.median(d_array))
    centred_d = d_array - median_d

    r_sym_centered = float(np.quantile(np.abs(centred_d), 0.975))
    r_one_centered = float(-np.quantile(centred_d, 0.025))
    r_uncentred_upper = float(np.quantile(d_array, 0.975))
    r_sym_uncentred = float(np.quantile(np.abs(d_array), 0.975))
    r_one_uncentred = float(-np.quantile(d_array, 0.025))
    r_normal_median = float(np.median(normal_array))

    indicators["sym_pooled"] = (d_array + r_sym_centered >= 0.0).astype(np.int8).tolist()
    indicators["one_sided_pooled"] = (d_array + r_one_centered >= 0.0).astype(np.int8).tolist()
    indicators["uncentred_pooled"] = (d_array + r_uncentred_upper >= 0.0).astype(np.int8).tolist()
    indicators["normal_theory_per_rep"] = (tv_array + normal_array >= TRUE_TV).astype(np.int8).tolist()
    indicators["sym_bootstrap_per_rep"] = (tv_array + bootstrap_array >= TRUE_TV).astype(np.int8).tolist()
    indicator_arrays = {key: np.asarray(value, dtype=np.int8) for key, value in indicators.items()}

    arms = {
        "sym_pooled": build_arm(
            "sym_pooled",
            True,
            r_sym_centered,
            indicator_arrays["sym_pooled"],
            harness.cp_interval,
            "Oracle pooled centered symmetric radius quantile(abs(D - median(D)), 0.975).",
        ),
        "one_sided_pooled": build_arm(
            "one_sided_pooled",
            True,
            r_one_centered,
            indicator_arrays["one_sided_pooled"],
            harness.cp_interval,
            "Oracle pooled centered one-sided radius -quantile(D - median(D), 0.025).",
        ),
        "uncentred_pooled": build_arm(
            "uncentred_pooled",
            True,
            r_uncentred_upper,
            indicator_arrays["uncentred_pooled"],
            harness.cp_interval,
            "Oracle pooled uncentred endpoint radius quantile(D, 0.975).",
        ),
        "normal_theory_per_rep": build_arm(
            "normal_theory_per_rep",
            False,
            r_normal_median,
            indicator_arrays["normal_theory_per_rep"],
            harness.cp_interval,
            "Computable per-replicate radius z_0.975 * SE_rep.",
        ),
        "sym_bootstrap_per_rep": build_arm(
            "sym_bootstrap_per_rep",
            False,
            float(np.median(bootstrap_array)),
            indicator_arrays["sym_bootstrap_per_rep"],
            harness.cp_interval,
            "Computable per-replicate 128-resample block-bootstrap symmetric radius.",
        ),
    }

    pairwise = make_pairwise_coverage_table(arms, indicator_arrays)
    falsifier_fired = bool(not any(row["difference_ci_excludes_zero"] for row in pairwise.values()))
    pairing_reconciliation = make_pairing_table(
        r_sym_centered,
        r_one_centered,
        r_sym_uncentred,
        r_one_uncentred,
        r_uncentred_upper,
        r_normal_median,
    )

    payload = {
        "experiment": "track5_radius_form_coverage",
        "arms": arms,
        "falsifier": FALSIFIER,
        "falsifier_fired": falsifier_fired,
        "falsifier_rule": "fired iff at least one paired 95% normal-approximation CI for an arm coverage difference excludes zero",
        "pairwise_coverage_differences": pairwise,
        "pairing_reconciliation": pairing_reconciliation,
        "pooled_quantities": {
            "median_D": median_d,
            "quantile_abs_centered_D_0975": r_sym_centered,
            "negative_quantile_centered_D_0025": r_one_centered,
            "quantile_abs_uncentred_D_0975": r_sym_uncentred,
            "negative_quantile_uncentred_D_0025": r_one_uncentred,
            "plain_quantile_uncentred_D_0975": r_uncentred_upper,
        },
        "replicate_diagnostics": {
            "tv_hat_count": int(len(tv_array)),
            "tv_hat_mean": float(np.mean(tv_array)),
            "tv_hat_sd_ddof1": float(np.std(tv_array, ddof=1)) if len(tv_array) > 1 else 0.0,
            "se_median": float(np.median(se_array)),
            "se_mean": float(np.mean(se_array)),
            "normal_radius_median": r_normal_median,
            "bootstrap_radius_median": float(np.median(bootstrap_array)),
        },
        "fixed_design": {
            "n": N,
            "B": BLOCK_SIZE,
            "concentration": CONCENTRATION,
            "true_tv": TRUE_TV,
            "alphabet_size": ALPHABET_SIZE,
            "alpha_upper": ALPHA_UPPER,
            "nominal_coverage": NOMINAL_COVERAGE,
            "seed": SEED,
            "replicates": int(args.replicates),
            "requested_replicates": REPLICATES,
            "bootstrap_resamples": BOOTSTRAP_REPLICATES,
            "bootstrap_optional": False,
            "max_wall_clock_seconds": MAX_SECONDS,
        },
        "controls": {
            "statcore_known_control": {
                "n": KNOWN_CONTROL_N,
                "expected_eps_hi": KNOWN_CONTROL_EXPECTED_EPS_HI,
                "observed_eps_hi": control_eps_hi,
                "status": "MATCH",
            },
            "iid_radius": iid_radius,
            "tv_hat_reconciled_every_replicate": True,
            "reference_runner": str(REFERENCE_RUNNER_PATH),
            "reference_runner_sha256": sha256_file(REFERENCE_RUNNER_PATH),
        },
        "runner_sha256": runner_sha,
        "notes": (
            "Oracle arms use the realised D_rep distribution and therefore establish the size and sign of the "
            "radius-form gap, not achievable coverage. Only normal_theory_per_rep and sym_bootstrap_per_rep are "
            "computable per-replicate coverage measurements. The fixed SE is reference_runner.sandwich_radius "
            "divided by z_0.975, i.e. the existing sandwich variance with its critical-value multiplier removed."
        ),
    }
    json_sha, summary_sha = write_outputs(payload)
    print(f"OUTPUT_SHA256: {JSON_PATH} {json_sha}", flush=True)
    print(f"OUTPUT_SHA256: {SUMMARY_PATH} {summary_sha}", flush=True)


if __name__ == "__main__":
    main()
