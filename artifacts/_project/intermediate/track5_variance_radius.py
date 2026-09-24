#!/usr/bin/env python3
"""Track 5: dependence-aware radii at the fixed n=60000 calibration rung.

The data-generating and CP machinery is imported from the existing coverage
calibration harness. This runner only adds the three dependence-aware radius
estimators and the requested artifact serialization.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm, t


PROJECT_ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
HARNESS_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/coverage_calibration_ladder.py"
SRC_ROOT = PROJECT_ROOT / "src"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"

ALPHABET_SIZE = 32
ALPHA_UPPER = 0.025
NOMINAL_COVERAGE = 0.975
TRUE_TV = 0.40
BLOCK_SIZE = 64
CONCENTRATION = 0.1
SEED = 20260919
N = 60000
REPLICATES = 1000
BOOTSTRAP_REPLICATES = 128


def load_harness():
    spec = importlib.util.spec_from_file_location("coverage_calibration_ladder", HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load harness: {HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def counts(x: np.ndarray) -> np.ndarray:
    return np.bincount(x, minlength=ALPHABET_SIZE).astype(np.int64, copy=False)


def tv_from_counts(a: np.ndarray, b: np.ndarray, n_a: int, n_b: int) -> float:
    return float(0.5 * np.abs(a / n_a - b / n_b).sum())


def block_counts(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    blocks = [x[start : start + BLOCK_SIZE] for start in range(0, len(x), BLOCK_SIZE)]
    full = np.vstack([counts(block) for block in blocks])
    residual = np.vstack([counts(block[: min(BLOCK_SIZE, len(block))]) for block in blocks])
    return full, residual


def bootstrap_radius(
    a_blocks: np.ndarray,
    a_partial: np.ndarray,
    b_blocks: np.ndarray,
    b_partial: np.ndarray,
    tv_hat: float,
    rng: np.random.Generator,
) -> float:
    block_count = len(a_blocks)
    complete_count = N // BLOCK_SIZE
    residual_length = N % BLOCK_SIZE
    full_indices_a = rng.integers(0, complete_count, size=(BOOTSTRAP_REPLICATES, complete_count))
    full_indices_b = rng.integers(0, complete_count, size=(BOOTSTRAP_REPLICATES, complete_count))
    boot_a = a_blocks[full_indices_a].sum(axis=1)
    boot_b = b_blocks[full_indices_b].sum(axis=1)
    if residual_length:
        partial_indices_a = rng.integers(0, block_count, size=BOOTSTRAP_REPLICATES)
        partial_indices_b = rng.integers(0, block_count, size=BOOTSTRAP_REPLICATES)
        boot_a += a_partial[partial_indices_a]
        boot_b += b_partial[partial_indices_b]
    boot_tv = 0.5 * np.abs(boot_a / N - boot_b / N).sum(axis=1)
    return float(np.quantile(np.abs(boot_tv - tv_hat), 1.0 - ALPHA_UPPER))


def sandwich_radius(
    a_counts: np.ndarray,
    b_counts: np.ndarray,
    a_blocks: np.ndarray,
    b_blocks: np.ndarray,
) -> float:
    p = a_counts / N
    q = b_counts / N
    signs = np.sign(p - q)
    mean_sign_a = float(np.dot(p, signs))
    mean_sign_b = float(np.dot(q, signs))
    influence_a = 0.5 * (signs - mean_sign_a)
    influence_b = -0.5 * (signs - mean_sign_b)
    cluster_a = (a_blocks @ influence_a) / N
    cluster_b = (b_blocks @ influence_b) / N
    var_a = len(cluster_a) / (len(cluster_a) - 1) * np.sum((cluster_a - cluster_a.mean()) ** 2)
    var_b = len(cluster_b) / (len(cluster_b) - 1) * np.sum((cluster_b - cluster_b.mean()) ** 2)
    return float(norm.ppf(1.0 - ALPHA_UPPER) * math.sqrt(max(var_a + var_b, 0.0)))


def lobo_radius(
    a_counts: np.ndarray,
    b_counts: np.ndarray,
    a_blocks: np.ndarray,
    b_blocks: np.ndarray,
    block_lengths: np.ndarray,
) -> float:
    total_a = a_counts[None, :] - a_blocks
    total_b = b_counts[None, :] - b_blocks
    remaining = (N - block_lengths).astype(float)
    lobo_tv = 0.5 * np.abs(total_a / remaining[:, None] - total_b / remaining[:, None]).sum(axis=1)
    jackknife_variance = (len(lobo_tv) - 1) / len(lobo_tv) * np.sum((lobo_tv - lobo_tv.mean()) ** 2)
    critical = float(t.ppf(1.0 - ALPHA_UPPER, len(lobo_tv) - 1))
    return float(critical * math.sqrt(max(jackknife_variance, 0.0)))


def power_requirement() -> int:
    p0 = 0.95
    p1 = 0.9825
    z_alpha = float(norm.ppf(1.0 - 0.05 / 2.0))
    z_power = float(norm.ppf(0.95))
    pooled = (p0 + p1) / 2.0
    numerator = z_alpha * math.sqrt(2.0 * pooled * (1.0 - pooled))
    numerator += z_power * math.sqrt(p0 * (1.0 - p0) + p1 * (1.0 - p1))
    required = numerator**2 / (p1 - p0) ** 2
    return int(math.ceil(required))


def summarize_arm(
    name: str,
    method_description: str,
    radius_description: str,
    radii: list[float],
    covered_count: int,
    iid_radius: float,
    falsifier: str,
    runner_sha: str,
    extra_notes: str,
    cp_interval,
) -> dict:
    coverage = covered_count / REPLICATES
    coverage_ci = cp_interval(covered_count, REPLICATES)
    below_nominal = bool(coverage_ci[0] < NOMINAL_COVERAGE)
    above_nominal = bool(coverage_ci[0] > NOMINAL_COVERAGE)
    excludes_nominal = bool(coverage_ci[1] < NOMINAL_COVERAGE or coverage_ci[0] > NOMINAL_COVERAGE)
    median_radius = float(np.median(np.asarray(radii)))
    radius_relation = "larger" if median_radius > iid_radius else "smaller" if median_radius < iid_radius else "comparable"
    falsifier_fired = bool(below_nominal or median_radius <= iid_radius)
    direction = (
        "from_above"
        if coverage_ci[0] > NOMINAL_COVERAGE
        else "from_below"
        if coverage_ci[1] < NOMINAL_COVERAGE
        else "not_excluded"
    )
    return {
        "arm": name,
        "method_description": method_description,
        "radius_description": radius_description,
        "radius_value": median_radius,
        "iid_radius_value": iid_radius,
        "radius_relation_to_iid": radius_relation,
        "radius_mean": float(np.mean(np.asarray(radii))),
        "radius_min": float(np.min(np.asarray(radii))),
        "radius_max": float(np.max(np.asarray(radii))),
        "n": N,
        "B": BLOCK_SIZE,
        "conc": CONCENTRATION,
        "true_tv": TRUE_TV,
        "replicates": REPLICATES,
        "required_replicates": power_requirement(),
        "coverage": coverage,
        "covered": covered_count,
        "coverage_ci95": coverage_ci,
        "below_nominal": below_nominal,
        "cp_lower_clears_nominal": not below_nominal,
        "excludes_nominal": excludes_nominal,
        "excludes_nominal_direction": direction,
        "falsifier": falsifier,
        "falsifier_fired": falsifier_fired,
        "notes": (
            f"Median radius is {radius_relation} than the i.i.d. reference; "
            f"CP lower endpoint {'clears' if not below_nominal else 'does not clear'} nominal 0.975; "
            f"{extra_notes}"
        ),
        "runner_sha256": runner_sha,
    }


def main() -> None:
    sys.path.insert(0, str(SRC_ROOT))
    from eibo import statcore

    harness = load_harness()
    runner_sha = sha256_file(Path(__file__).resolve())
    control = statcore.tv_upper_bound(
        np.zeros(2791, dtype=np.int16),
        np.zeros(2791, dtype=np.int16),
        alphabet_size=ALPHABET_SIZE,
        alpha=ALPHA_UPPER,
    )
    expected_control = 0.16311342728653244
    if not math.isclose(float(control.eps_hi), expected_control, rel_tol=0.0, abs_tol=1e-12):
        raise RuntimeError(f"known control mismatch: expected {expected_control}, got {control.eps_hi}")

    iid = statcore.tv_upper_bound(
        np.zeros(N, dtype=np.int16),
        np.zeros(N, dtype=np.int16),
        alphabet_size=ALPHABET_SIZE,
        alpha=ALPHA_UPPER,
    )
    iid_radius = float(iid.radius_1 + iid.radius_2)
    p, q = harness.make_truth(TRUE_TV)
    rng = np.random.default_rng(SEED)
    block_lengths = np.asarray(
        [min(BLOCK_SIZE, N - start) for start in range(0, N, BLOCK_SIZE)], dtype=np.int64
    )
    radii_a: list[float] = []
    radii_b: list[float] = []
    radii_c: list[float] = []
    covered_a = covered_b = covered_c = 0
    bootstrap_falsifier = (
        "Fails if the CP lower endpoint remains below nominal 0.975, or if the median block-bootstrap radius "
        "is not larger than the i.i.d. radius at n=60000."
    )
    sandwich_falsifier = (
        "Fails if the CP lower endpoint remains below nominal 0.975, or if the median cluster-robust radius "
        "is not larger than the i.i.d. radius at n=60000."
    )
    lobo_falsifier = (
        "Fails if the CP lower endpoint remains below nominal 0.975, or if the median LOBO Studentized radius "
        "is not larger than the i.i.d. radius at n=60000."
    )

    for rep in range(REPLICATES):
        a = harness.draw_dependent(N, p, BLOCK_SIZE, CONCENTRATION, rng)
        b = harness.draw_dependent(N, q, BLOCK_SIZE, CONCENTRATION, rng)
        a_counts = counts(a)
        b_counts = counts(b)
        reference = statcore.tv_upper_bound(a, b, alphabet_size=ALPHABET_SIZE, alpha=ALPHA_UPPER)
        tv_hat = float(reference.tv_hat)
        check_tv_hat = tv_from_counts(a_counts, b_counts, N, N)
        if not math.isclose(tv_hat, check_tv_hat, rel_tol=0.0, abs_tol=1e-15):
            raise RuntimeError(f"tv_hat reconciliation failed at replicate {rep}: {tv_hat} != {check_tv_hat}")

        a_blocks, a_partial = block_counts(a)
        b_blocks, b_partial = block_counts(b)
        radius_a = bootstrap_radius(a_blocks, a_partial, b_blocks, b_partial, tv_hat, rng)
        radius_b = sandwich_radius(a_counts, b_counts, a_blocks, b_blocks)
        radius_c = lobo_radius(a_counts, b_counts, a_blocks, b_blocks, block_lengths)
        radii_a.append(radius_a)
        radii_b.append(radius_b)
        radii_c.append(radius_c)
        covered_a += int(min(1.0, tv_hat + radius_a) >= TRUE_TV)
        covered_b += int(min(1.0, tv_hat + radius_b) >= TRUE_TV)
        covered_c += int(min(1.0, tv_hat + radius_c) >= TRUE_TV)
        if (rep + 1) % 50 == 0:
            print(
                f"rep={rep + 1}/{REPLICATES} covered="
                f"A:{covered_a} B:{covered_b} C:{covered_c} "
                f"radii_med={np.median(radii_a):.5f},{np.median(radii_b):.5f},{np.median(radii_c):.5f}",
                flush=True,
            )

    required = power_requirement()
    power_note = (
        "Required replicates recomputed from p0=0.95, p1=0.9825, two-sided alpha=0.05, "
        f"target power=0.95: ceil(N)={required}; the displayed dispatcher approximation 897 does not "
        "follow from the displayed formula, which evaluates to 799.44."
    )
    arms = [
        summarize_arm(
            "Arm A - block bootstrap",
            "Each sample is partitioned into contiguous B=64 blocks; B-sized blocks are resampled with replacement, "
            "with a residual block to preserve n=60000. The radius is recomputed per replicate.",
            "r_boot = Quantile_0.975(|TV_hat_boot - TV_hat|) over 128 block-bootstrap resamples.",
            radii_a,
            covered_a,
            iid_radius,
            bootstrap_falsifier,
            runner_sha,
            power_note,
            harness.cp_interval,
        ),
        summarize_arm(
            "Arm B - cluster-robust sandwich",
            "The plug-in TV influence function is aggregated by dependence block; the two law-specific cluster-robust "
            "variance estimates are summed.",
            "r_sandwich = z_0.975 * sqrt(V_cluster,A + V_cluster,B), with block-level finite-sample variance correction.",
            radii_b,
            covered_b,
            iid_radius,
            sandwich_falsifier,
            runner_sha,
            power_note,
            harness.cp_interval,
        ),
        summarize_arm(
            "Arm C - LOBO",
            "For every contiguous B=64 block, TV_hat is recomputed after removing that block from both laws; the "
            "LOBO spread estimates the sampling variance.",
            "r_LOBO = t_0.975,K-1 * sqrt((K-1)/K * sum_j(TV_hat_-j - mean(TV_hat_-j))^2).",
            radii_c,
            covered_c,
            iid_radius,
            lobo_falsifier,
            runner_sha,
            power_note,
            harness.cp_interval,
        ),
    ]

    output_paths = []
    for arm in arms:
        filename = {
            "Arm A - block bootstrap": "track5_armA_block_bootstrap.json",
            "Arm B - cluster-robust sandwich": "track5_armB_sandwich.json",
            "Arm C - LOBO": "track5_armC_lobo.json",
        }[arm["arm"]]
        path = ARTIFACT_DIR / filename
        path.write_text(json.dumps(arm, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        output_paths.append(path)

    lines = [
        "# Track 5: dependence-aware radius calibration",
        "",
        f"Fixed design: n={N}, B={BLOCK_SIZE}, concentration={CONCENTRATION}, true TV={TRUE_TV}, seed={SEED}.",
        f"i.i.d. reference radius: `{iid_radius:.12f}`.",
        "",
        "Power calculation",
        "-----------------",
        power_note,
        "",
        "The interval coverage is the two-sided 95% Clopper-Pearson interval over outer replicates. "
        "The verdict criterion is the CP lower endpoint versus nominal 0.975; interval non-exclusion is only "
        "a reporting distinction, not the verdict.",
        "",
        "| Arm | Coverage | CP95 | CP lower clears 0.975 | Radius median | i.i.d. radius | Relation | Falsifier |",
        "|---|---:|---|---|---:|---:|---|---|",
    ]
    for arm in arms:
        ci = arm["coverage_ci95"]
        lines.append(
            f"| {arm['arm']} | {arm['coverage']:.4f} ({arm['covered']}/{arm['replicates']}) | "
            f"[{ci[0]:.4f}, {ci[1]:.4f}] | {'yes' if arm['cp_lower_clears_nominal'] else 'no'} | "
            f"{arm['radius_value']:.6f} | {iid_radius:.6f} | {arm['radius_relation_to_iid']} | "
            f"{'fired' if arm['falsifier_fired'] else 'did not fire'} |"
        )
        lines.extend(
            [
                "",
                f"**{arm['arm']}**: {arm['method_description']}",
                f"Radius: {arm['radius_description']} Median/mean/min/max = "
                f"{arm['radius_value']:.6f}/{arm['radius_mean']:.6f}/{arm['radius_min']:.6f}/{arm['radius_max']:.6f}.",
                f"Falsifier: {arm['falsifier']} Result: {'fired' if arm['falsifier_fired'] else 'did not fire'}.",
            ]
        )
    all_clear = all(arm["cp_lower_clears_nominal"] for arm in arms)
    lines.extend(
        [
            "",
            "Overall verdict",
            "---------------",
            (
                "All three arms clear nominal coverage by the CP lower endpoint; the result is resolved at this "
                "replicate count."
                if all_clear
                else "At least one arm does not clear nominal coverage by the CP lower endpoint; the result is not "
                "resolved as a universal restoration at this replicate count."
            ),
            "",
        ]
    )
    for path in output_paths:
        lines.append(f"- `{path.name}` sha256 `{sha256_file(path)}`")
    lines.append(
        "content_sha256: "
        + "; ".join(f"{path.name}={sha256_file(path)}" for path in output_paths)
    )
    summary_path = ARTIFACT_DIR / "track5_summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"iid_radius": iid_radius, "required_replicates": required, "outputs": [str(p) for p in output_paths + [summary_path]]}, sort_keys=True))


if __name__ == "__main__":
    main()
