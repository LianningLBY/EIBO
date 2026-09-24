#!/usr/bin/env python3
"""Track 5 diagnosis and conditional Arm D.

The existing Track 5 runner and coverage harness are imported unchanged.  This
companion runner exposes the latent block probabilities with a tracing RNG so
the conditional within-block multinomial variance can be measured directly.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm


PROJECT_ROOT = Path(
    "/efs/workspace/projects/"
    "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade"
)
HARNESS_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/coverage_calibration_ladder.py"
EXISTING_RUNNER_PATH = PROJECT_ROOT / "artifacts/_project/intermediate/track5_variance_radius.py"
SRC_ROOT = PROJECT_ROOT / "src"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"

ALPHABET_SIZE = 32
ALPHA_UPPER = 0.025
NOMINAL_COVERAGE = 0.975
TRUE_TV = 0.40
BLOCK_SIZE = 64
CONCENTRATION = 0.1
N = 60000
K = (N + BLOCK_SIZE - 1) // BLOCK_SIZE
DIAGNOSIS_REPLICATES = 200
WITHIN_REPLICATES = 32
DIAGNOSIS_SEED = 20260919
ARM_D_SEED = 20260920
ARM_D_REPLICATES = 1000


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


class TracingRNG:
    """Delegate Generator methods while recording Dirichlet block parameters."""

    def __init__(self, generator: np.random.Generator):
        self.generator = generator
        self.thetas: list[np.ndarray] = []

    def dirichlet(self, alpha):
        theta = self.generator.dirichlet(alpha)
        self.thetas.append(np.asarray(theta, dtype=float).copy())
        return theta

    def choice(self, *args, **kwargs):
        return self.generator.choice(*args, **kwargs)


def counts(x: np.ndarray) -> np.ndarray:
    return np.bincount(x, minlength=ALPHABET_SIZE).astype(np.int64, copy=False)


def block_counts(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    blocks = [x[start : start + BLOCK_SIZE] for start in range(0, len(x), BLOCK_SIZE)]
    lengths = np.asarray([len(block) for block in blocks], dtype=np.int64)
    result = np.vstack([counts(block) for block in blocks])
    return result, lengths


def block_tv_contributions(
    a_blocks: np.ndarray, b_blocks: np.ndarray
) -> np.ndarray:
    # This follows the requested c_k definition, including the final residual
    # block being scaled by B as in the existing Track 5 partition.
    return 0.5 * np.abs(a_blocks / BLOCK_SIZE - b_blocks / BLOCK_SIZE).sum(axis=1)


def iid_radius(statcore) -> float:
    zeros = np.zeros(N, dtype=np.int16)
    reference = statcore.tv_upper_bound(
        zeros, zeros, alphabet_size=ALPHABET_SIZE, alpha=ALPHA_UPPER
    )
    return float(reference.radius_1 + reference.radius_2)


def sandwich_sd(a_counts, b_counts, a_blocks, b_blocks) -> float:
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
    return float(math.sqrt(max(var_a + var_b, 0.0)))


def lobo_sd(a_counts, b_counts, a_blocks, b_blocks, lengths) -> float:
    total_a = a_counts[None, :] - a_blocks
    total_b = b_counts[None, :] - b_blocks
    remaining = (N - lengths).astype(float)
    lobo_tv = 0.5 * np.abs(total_a / remaining[:, None] - total_b / remaining[:, None]).sum(axis=1)
    variance = (len(lobo_tv) - 1) / len(lobo_tv) * np.sum((lobo_tv - lobo_tv.mean()) ** 2)
    return float(math.sqrt(max(variance, 0.0)))


def measure_diagnosis(harness, statcore) -> dict:
    p, q = harness.make_truth(TRUE_TV)
    rng = np.random.default_rng(DIAGNOSIS_SEED)
    between_values = []
    within_values = []
    tv_values = []
    sandwich_values = []
    lobo_values = []

    for rep in range(DIAGNOSIS_REPLICATES):
        trace_a = TracingRNG(rng)
        a = harness.draw_dependent(N, p, BLOCK_SIZE, CONCENTRATION, trace_a)
        theta_a = np.asarray(trace_a.thetas)
        trace_b = TracingRNG(rng)
        b = harness.draw_dependent(N, q, BLOCK_SIZE, CONCENTRATION, trace_b)
        theta_b = np.asarray(trace_b.thetas)
        if theta_a.shape != (K, ALPHABET_SIZE) or theta_b.shape != (K, ALPHABET_SIZE):
            raise RuntimeError(f"unexpected theta shapes: {theta_a.shape}, {theta_b.shape}")

        a_counts = counts(a)
        b_counts = counts(b)
        reference = statcore.tv_upper_bound(a, b, alphabet_size=ALPHABET_SIZE, alpha=ALPHA_UPPER)
        tv_hat = float(reference.tv_hat)
        a_blocks, lengths = block_counts(a)
        b_blocks, b_lengths = block_counts(b)
        if not np.array_equal(lengths, b_lengths):
            raise RuntimeError("A/B block lengths differ")

        c = block_tv_contributions(a_blocks, b_blocks)
        between_values.append(float(np.var(c, ddof=1)))
        tv_values.append(tv_hat)
        sandwich_values.append(sandwich_sd(a_counts, b_counts, a_blocks, b_blocks))
        lobo_values.append(lobo_sd(a_counts, b_counts, a_blocks, b_blocks, lengths))

        conditional_c = np.empty((WITHIN_REPLICATES, K), dtype=float)
        for inner in range(WITHIN_REPLICATES):
            inner_a = rng.multinomial(lengths, theta_a)
            inner_b = rng.multinomial(lengths, theta_b)
            conditional_c[inner] = block_tv_contributions(inner_a, inner_b)
        within_values.append(float(np.var(conditional_c, axis=0, ddof=1).mean()))

        if (rep + 1) % 25 == 0:
            print(f"diagnosis_rep={rep + 1}/{DIAGNOSIS_REPLICATES}", flush=True)

    empirical_sd = float(np.std(np.asarray(tv_values), ddof=1))
    iid_sd_value = iid_radius(statcore)
    mean_between = float(np.mean(np.asarray(between_values)))
    mean_within = float(np.mean(np.asarray(within_values)))
    arm_b_sd = float(np.mean(np.asarray(sandwich_values)))
    arm_c_sd = float(np.mean(np.asarray(lobo_values)))
    mean_dependence_sd = 0.5 * (arm_b_sd + arm_c_sd)
    observed_factor = float(empirical_sd / mean_dependence_sd)
    empirical_to_iid_radius = float(empirical_sd / iid_sd_value)
    # B/C support the missing-term hypothesis only if their implied SDs fail
    # to recover the directly measured SD.  A 10% diagnostic tolerance is
    # fixed before interpreting the result; it is not used to tune Arm D.
    supports_between = bool(
        abs(arm_b_sd / empirical_sd - 1.0) > 0.10
        or abs(arm_c_sd / empirical_sd - 1.0) > 0.10
    )
    if supports_between:
        verdict = (
            "At least one of the B/C implied SDs misses the directly measured tv_hat SD by more than 10%; "
            "a missing between-block component remains supported under the predeclared diagnostic gate."
        )
    else:
        verdict = (
            "B and C recover the directly measured tv_hat SD to within 10% (approximately 1.0x), so the diagnosis "
            "supports neither a wrong denominator nor an absent between-block term. The large block-level spread is "
            "not evidence that B/C omitted a variance component; Arm D must not be run."
        )

    diagnosis = {
        "mean_between": mean_between,
        "mean_within": mean_within,
        "total_var_of_tvhat": float(np.var(np.asarray(tv_values), ddof=1)),
        "empirical_sd": empirical_sd,
        "iid_sd": iid_sd_value,
        "armB_implied_sd": arm_b_sd,
        "armC_implied_sd": arm_c_sd,
        "armB_ratio_to_empirical": float(arm_b_sd / empirical_sd),
        "armC_ratio_to_empirical": float(arm_c_sd / empirical_sd),
        "wrong_denominator_predicted_factor": 8.0,
        "observed_factor": observed_factor,
        "empirical_to_iid_radius_factor": empirical_to_iid_radius,
        "diagnosis_verdict": verdict,
        "supports_between_block_arm": supports_between,
        "notes": (
            "mean_between is the outer-replicate mean of sample var(c_k, ddof=1); mean_within is the outer and block "
            "mean of an unbiased sample variance over 32 conditional multinomial redraws given each captured theta. "
            "K=938 includes the final 32-flow residual block, and c_k uses the requested /B scaling. "
            "Arm B/C implied SDs remove their critical values and use the formulas already in the Track 5 runner. "
            "The observed_factor is empirical_sd divided by the mean of the B/C implied SDs; it is the relevant "
            "wrong-denominator comparison. The empirical_to_iid_radius_factor is reported separately because the "
            "i.i.d. value is a finite-alphabet confidence radius, not a Gaussian SD."
        ),
        "design": {
            "n": N,
            "B": BLOCK_SIZE,
            "K": K,
            "conc": CONCENTRATION,
            "true_tv": TRUE_TV,
            "alpha_upper": ALPHA_UPPER,
            "nominal_coverage": NOMINAL_COVERAGE,
            "diagnosis_seed": DIAGNOSIS_SEED,
            "diagnosis_replicates": DIAGNOSIS_REPLICATES,
            "within_replicates": WITHIN_REPLICATES,
        },
        "formula_reconciliation": {
            "armB_variance": "K/(K-1) * sum((cluster - mean(cluster))^2), summed over A and B laws",
            "armB_cluster": "(a_blocks @ influence) / N",
            "armC_variance": "(K-1)/K * sum((lobo_tv - mean(lobo_tv))^2)",
            "reference_runner": str(EXISTING_RUNNER_PATH),
            "reference_runner_sha256": sha256_file(EXISTING_RUNNER_PATH),
        },
    }
    return diagnosis


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_arm_d(harness, statcore, diagnosis: dict) -> dict:
    p, q = harness.make_truth(TRUE_TV)
    rng = np.random.default_rng(ARM_D_SEED)
    iid = iid_radius(statcore)
    z = float(norm.ppf(1.0 - ALPHA_UPPER))
    radii = []
    covered = 0
    tv_values = []
    for rep in range(ARM_D_REPLICATES):
        a = harness.draw_dependent(N, p, BLOCK_SIZE, CONCENTRATION, rng)
        b = harness.draw_dependent(N, q, BLOCK_SIZE, CONCENTRATION, rng)
        a_counts = counts(a)
        b_counts = counts(b)
        reference = statcore.tv_upper_bound(a, b, alphabet_size=ALPHABET_SIZE, alpha=ALPHA_UPPER)
        tv_hat = float(reference.tv_hat)
        a_blocks, lengths = block_counts(a)
        b_blocks, b_lengths = block_counts(b)
        if not np.array_equal(lengths, b_lengths):
            raise RuntimeError("A/B block lengths differ in Arm D")
        c = block_tv_contributions(a_blocks, b_blocks)
        between_variance = float(np.var(c, ddof=1) / len(c))
        between_radius = z * math.sqrt(max(between_variance, 0.0))
        radius = math.sqrt(iid**2 + between_radius**2)
        if radius <= 0.0:
            raise RuntimeError("non-positive Arm D radius")
        radii.append(radius)
        tv_values.append(tv_hat)
        covered += int(min(1.0, tv_hat + radius) >= TRUE_TV)
        if (rep + 1) % 100 == 0:
            print(f"armD_rep={rep + 1}/{ARM_D_REPLICATES} covered={covered}", flush=True)

    coverage = covered / ARM_D_REPLICATES
    cp = harness.cp_interval(covered, ARM_D_REPLICATES)
    median_radius = float(np.median(np.asarray(radii)))
    if cp[0] > NOMINAL_COVERAGE:
        direction = "from_above"
    elif cp[1] < NOMINAL_COVERAGE:
        direction = "from_below"
    else:
        direction = "not_excluded"
    excludes = bool(cp[0] > NOMINAL_COVERAGE or cp[1] < NOMINAL_COVERAGE)
    falsifier = bool(median_radius <= iid or excludes)
    arm_d = {
        "arm": "Arm D - i.i.d. radius plus between-block variance component",
        "seed": ARM_D_SEED,
        "n": N,
        "B": BLOCK_SIZE,
        "K": K,
        "conc": CONCENTRATION,
        "true_tv": TRUE_TV,
        "alpha_upper": ALPHA_UPPER,
        "nominal_coverage": NOMINAL_COVERAGE,
        "replicates": ARM_D_REPLICATES,
        "covered": covered,
        "coverage": coverage,
        "coverage_ci95": cp,
        "radius_median": median_radius,
        "radius_mean": float(np.mean(np.asarray(radii))),
        "radius_min": float(np.min(np.asarray(radii))),
        "radius_max": float(np.max(np.asarray(radii))),
        "iid_radius": iid,
        "radius_ratio_to_iid": float(median_radius / iid),
        "cp_excludes_nominal": excludes,
        "cp_excludes_nominal_direction": direction,
        "falsifier": (
            "Fails if the median Arm D radius is not larger than the i.i.d. radius, or if the two-sided CP95 "
            "interval for coverage excludes nominal 0.975 from either side."
        ),
        "falsifier_fired": falsifier,
        "combination_formula": (
            "v_between = var(c_k, ddof=1)/K; r_between = z_0.975*sqrt(v_between); "
            "r_D = sqrt(r_iid^2 + r_between^2), with eps_hi=min(1, tv_hat+r_D)."
        ),
        "prediction": (
            "Before the run: the Arm D radius will be larger than the i.i.d. radius and its CP95 coverage "
            "interval will be nearer nominal 0.975 than Arm A's 0.9940, without clearing from above."
        ),
        "claim_boundary": "At most, a between-block variance component restores nominal coverage under the modelled block law.",
        "diagnosis_supports_arm": bool(diagnosis["supports_between_block_arm"]),
        "runner_sha256": sha256_file(Path(__file__).resolve()),
    }
    return arm_d


def write_summary(path: Path, diagnosis: dict, arm_d: dict | None) -> None:
    lines = [
        "# Track 5b: between-block diagnosis and conditional Arm D",
        "",
        "## Step 1 diagnosis",
        "",
        f"- Design: n={N}, B={BLOCK_SIZE}, K={K}, concentration={CONCENTRATION}, true TV={TRUE_TV}.",
        f"- Diagnosis seed: `{DIAGNOSIS_SEED}`; outer replicates: `{DIAGNOSIS_REPLICATES}`; within-block redraws: `{WITHIN_REPLICATES}`.",
        f"- Mean between-block variance of c_k: `{diagnosis['mean_between']:.9g}`.",
        f"- Mean conditional within-block variance of c_k: `{diagnosis['mean_within']:.9g}`.",
        f"- Empirical SD of tv_hat: `{diagnosis['empirical_sd']:.9g}`; i.i.d. reference SD/radius: `{diagnosis['iid_sd']:.9g}`.",
        f"- Arm B implied SD: `{diagnosis['armB_implied_sd']:.9g}` ({diagnosis['armB_ratio_to_empirical']:.4f}x empirical).",
        f"- Arm C implied SD: `{diagnosis['armC_implied_sd']:.9g}` ({diagnosis['armC_ratio_to_empirical']:.4f}x empirical).",
        f"- Wrong-denominator prediction: factor `{diagnosis['wrong_denominator_predicted_factor']:.1f}`; observed empirical/mean(B,C implied SD) factor: `{diagnosis['observed_factor']:.4f}`.",
        f"- Verdict: {diagnosis['diagnosis_verdict']}",
        "",
    ]
    if arm_d is None:
        lines += ["## Step 2", "", "Arm D was not run because the Step 1 diagnosis did not support it.", ""]
    else:
        ci = arm_d["coverage_ci95"]
        lines += [
            "## Step 2 and 3: Arm D",
            "",
            f"- Seed `{arm_d['seed']}`; replicates `{arm_d['replicates']}`; coverage `{arm_d['coverage']:.4f}` ({arm_d['covered']}/{arm_d['replicates']}).",
            f"- CP95: `[{ci[0]:.6f}, {ci[1]:.6f}]`; nominal excluded: `{arm_d['cp_excludes_nominal']}` ({arm_d['cp_excludes_nominal_direction']}).",
            f"- Median radius `{arm_d['radius_median']:.9g}`; ratio to i.i.d. `{arm_d['radius_ratio_to_iid']:.6f}`.",
            f"- Falsifier fired: `{arm_d['falsifier_fired']}`.",
            f"- Formula: `{arm_d['combination_formula']}`",
            f"- Claim boundary: {arm_d['claim_boundary']}",
            "",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    sys.path.insert(0, str(SRC_ROOT))
    from eibo import statcore

    harness = load_harness()
    diagnosis_path = ARTIFACT_DIR / "track5_diagnosis_between_block.json"
    diagnosis = measure_diagnosis(harness, statcore)
    prediction = (
        "Arm D prediction before run: radius larger than the i.i.d. radius, with CP95 coverage nearer nominal "
        "0.975 than Arm A's 0.9940; a CP interval excluding nominal from either side is a falsifier."
    )
    diagnosis["prediction_for_armD_before_run"] = prediction
    write_json(diagnosis_path, diagnosis)
    print(json.dumps(diagnosis, indent=2, sort_keys=True), flush=True)

    arm_d = None
    if diagnosis["supports_between_block_arm"]:
        arm_d = run_arm_d(harness, statcore, diagnosis)
        diagnosis["armD_result"] = arm_d
        write_json(diagnosis_path, diagnosis)
        write_json(ARTIFACT_DIR / "track5_armD_between_block.json", arm_d)
    write_summary(ARTIFACT_DIR / "track5b_summary.md", diagnosis, arm_d)
    print(json.dumps({
        "diagnosis": str(diagnosis_path),
        "armD_run": arm_d is not None,
        "armD_falsifier_fired": None if arm_d is None else arm_d["falsifier_fired"],
        "summary": str(ARTIFACT_DIR / "track5b_summary.md"),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
