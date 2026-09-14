# X5 validates EIBO TV estimation and bracketing on synthetic categorical laws.
# Inputs: none; fixed probability vectors and deterministic random seeds.
# Outputs: artifacts/x5_estimator_ground_truth.json and a console validation report.
# Dependencies: Python standard library, numpy, and the local eibo.statcore module.

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from eibo.statcore import tv_lower_bound, tv_upper_bound  # noqa: E402


OVERALL_ALPHA = 0.05
PER_LAW_ALPHA = OVERALL_ALPHA / 2.0
ORIGINAL_LOWER_ALPHA = OVERALL_ALPHA
ALPHABET_SIZE = 4
CONVERGENCE_SIZES = (32, 128, 512, 2048)
CONVERGENCE_REPLICATES = 200
BRACKET_SIZES = (64, 256, 1024)
BRACKET_REPLICATES = 20
SEED = 5105

PAIR_A = {
    "name": "shifted_four_symbol",
    "p": np.array([0.55, 0.25, 0.15, 0.05], dtype=float),
    "q": np.array([0.25, 0.25, 0.25, 0.25], dtype=float),
}
PAIR_B = {
    "name": "disjoint_heavy_tails",
    "p": np.array([0.70, 0.20, 0.10, 0.00], dtype=float),
    "q": np.array([0.00, 0.10, 0.20, 0.70], dtype=float),
}
PAIR_IDENTICAL = {
    "name": "identical_four_symbol",
    "p": np.array([0.40, 0.30, 0.20, 0.10], dtype=float),
    "q": np.array([0.40, 0.30, 0.20, 0.10], dtype=float),
}


def closed_form_tv(p: np.ndarray, q: np.ndarray) -> float:
    """Return the exact TV of two categorical probability vectors."""
    return float(0.5 * np.abs(p - q).sum())


def draw_pair(
    rng: np.random.Generator, pair: dict[str, Any], n: int
) -> tuple[np.ndarray, np.ndarray]:
    """Draw two independent categorical samples from one synthetic pair."""
    return rng.choice(ALPHABET_SIZE, size=n, p=pair["p"]), rng.choice(
        ALPHABET_SIZE, size=n, p=pair["q"]
    )


def one_hot(values: np.ndarray) -> np.ndarray:
    """Encode categorical symbols as one-hot vectors without changing TV."""
    result = np.zeros((len(values), ALPHABET_SIZE), dtype=float)
    result[np.arange(len(values)), values] = 1.0
    return result


class FixedScoreClassifier:
    """Provide a deterministic scalar score for the project's lower-bound API."""

    def __init__(self, scores: list[float]) -> None:
        self.scores = np.asarray(scores, dtype=float)

    def fit(self, X: np.ndarray, y: np.ndarray) -> FixedScoreClassifier:
        """Return the scorer unchanged because its score map is fixed."""
        del X, y
        self.classes_ = np.array([0, 1], dtype=int)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return two-class probabilities induced by the fixed score map."""
        scores = np.clip(X @ self.scores, 0.0, 1.0)
        return np.column_stack((1.0 - scores, scores))


def upper_result(sample1: np.ndarray, sample2: np.ndarray) -> Any:
    """Call the project upper-bound implementation with the declared split."""
    return tv_upper_bound(
        sample1.tolist(),
        sample2.tolist(),
        alphabet_size=ALPHABET_SIZE,
        alpha=PER_LAW_ALPHA,
    )


def convergence_rows(pair: dict[str, Any], seed_offset: int) -> list[dict[str, Any]]:
    """Measure empirical TV-estimator convergence over increasing sample sizes."""
    rows: list[dict[str, Any]] = []
    for n_index, n in enumerate(CONVERGENCE_SIZES):
        rng = np.random.default_rng(SEED + seed_offset + n_index)
        estimates: list[float] = []
        returned_alphas: list[float] = []
        for _ in range(CONVERGENCE_REPLICATES):
            sample1, sample2 = draw_pair(rng, pair, n)
            result = upper_result(sample1, sample2)
            estimates.append(float(result.tv_hat))
            returned_alphas.append(float(result.alpha))
        truth = closed_form_tv(pair["p"], pair["q"])
        estimates_array = np.asarray(estimates, dtype=float)
        rows.append(
            {
                "n_per_law": n,
                "replicates": CONVERGENCE_REPLICATES,
                "closed_form_tv": truth,
                "mean_tv_hat": float(estimates_array.mean()),
                "median_tv_hat": float(np.median(estimates_array)),
                "mean_absolute_error": float(np.abs(estimates_array - truth).mean()),
                "rmse": float(np.sqrt(np.mean((estimates_array - truth) ** 2))),
                "returned_alpha_values": sorted(set(returned_alphas)),
            }
        )
    return rows


def coverage_rows(pair: dict[str, Any], seed_offset: int) -> list[dict[str, Any]]:
    """Measure upper-bound coverage at the declared per-law alpha split."""
    rows: list[dict[str, Any]] = []
    truth = closed_form_tv(pair["p"], pair["q"])
    for n_index, n in enumerate(CONVERGENCE_SIZES):
        rng = np.random.default_rng(SEED + seed_offset + n_index)
        covered = 0
        estimates: list[float] = []
        eps_hi_values: list[float] = []
        returned_alphas: list[float] = []
        for _ in range(CONVERGENCE_REPLICATES):
            sample1, sample2 = draw_pair(rng, pair, n)
            result = upper_result(sample1, sample2)
            estimates.append(float(result.tv_hat))
            eps_hi_values.append(float(result.eps_hi))
            returned_alphas.append(float(result.alpha))
            covered += int(result.eps_hi + 1e-15 >= truth)
        mean_tv_hat = float(np.mean(estimates))
        mean_eps_hi = float(np.mean(eps_hi_values))
        rows.append(
            {
                "pair": pair["name"],
                "n_per_law": n,
                "replicates": CONVERGENCE_REPLICATES,
                "closed_form_tv": truth,
                "covered_count": covered,
                "violation_count": CONVERGENCE_REPLICATES - covered,
                "coverage": float(covered / CONVERGENCE_REPLICATES),
                "mean_tv_hat": mean_tv_hat,
                "mean_eps_hi": mean_eps_hi,
                "mean_eps_hi_interpretation": (
                    "vacuous_by_clipping"
                    if mean_eps_hi >= 1.0 - 1e-15
                    else "not_clipped"
                ),
                "returned_alpha_values": sorted(set(returned_alphas)),
            }
        )
    return rows


def bracket_rows(pair: dict[str, Any], seed_offset: int) -> list[dict[str, Any]]:
    """Compute same-object lower and upper bounds for invariant checking."""
    rows: list[dict[str, Any]] = []
    truth = closed_form_tv(pair["p"], pair["q"])
    strong_scores = [0.10, 0.35, 0.65, 0.90]
    for n_index, n in enumerate(BRACKET_SIZES):
        rng = np.random.default_rng(SEED + seed_offset + n_index)
        for replicate in range(BRACKET_REPLICATES):
            sample1, sample2 = draw_pair(rng, pair, n)
            upper = upper_result(sample1, sample2)
            original_lower, original_diagnostics = tv_lower_bound(
                one_hot(sample1),
                one_hot(sample2),
                alpha=ORIGINAL_LOWER_ALPHA,
                clf=FixedScoreClassifier(strong_scores),
                test_size=0.30,
                random_state=SEED + seed_offset + n_index * 100 + replicate,
                method="michel",
            )
            lower, diagnostics = tv_lower_bound(
                one_hot(sample1),
                one_hot(sample2),
                alpha=PER_LAW_ALPHA,
                clf=FixedScoreClassifier(strong_scores),
                test_size=0.30,
                random_state=SEED + seed_offset + n_index * 100 + replicate,
                method="michel",
            )
            rows.append(
                {
                    "pair": pair["name"],
                    "n_per_law": n,
                    "replicate": replicate,
                    "closed_form_tv": truth,
                    "tv_hat": float(upper.tv_hat),
                    "eps_lo": float(lower),
                    "eps_lo_canonical_per_law_alpha_0_025": float(lower),
                    "eps_lo_original_overall_alpha_0_05": float(original_lower),
                    "eps_hi": float(upper.eps_hi),
                    "upper_returned_alpha": float(upper.alpha),
                    "lower_nominal_alpha": float(diagnostics["alpha"]),
                    "lower_canonical_nominal_alpha": float(diagnostics["alpha"]),
                    "lower_original_nominal_alpha": float(
                        original_diagnostics["alpha"]
                    ),
                    "lower_method": diagnostics["method"],
                    "lower_confidence_statement": diagnostics[
                        "confidence_statement"
                    ],
                    "lower_original_confidence_statement": original_diagnostics[
                        "confidence_statement"
                    ],
                    "same_object_encoding": "one-hot encoding of the same four-symbol law",
                }
            )
    return rows


def scorer_rows(pair: dict[str, Any], seed_offset: int) -> list[dict[str, Any]]:
    """Compare fixed weak and strong scorers on identical sampled laws."""
    rows: list[dict[str, Any]] = []
    weak_scores = [0.5, 0.5, 0.5, 0.5]
    strong_scores = [0.10, 0.35, 0.65, 0.90]
    n = 1024
    for replicate in range(BRACKET_REPLICATES):
        rng = np.random.default_rng(SEED + seed_offset + replicate)
        sample1, sample2 = draw_pair(rng, pair, n)
        weak_original, weak_original_diagnostics = tv_lower_bound(
            one_hot(sample1),
            one_hot(sample2),
            alpha=ORIGINAL_LOWER_ALPHA,
            clf=FixedScoreClassifier(weak_scores),
            test_size=0.30,
            random_state=SEED + seed_offset + replicate,
            method="michel",
        )
        strong_original, strong_original_diagnostics = tv_lower_bound(
            one_hot(sample1),
            one_hot(sample2),
            alpha=ORIGINAL_LOWER_ALPHA,
            clf=FixedScoreClassifier(strong_scores),
            test_size=0.30,
            random_state=SEED + seed_offset + replicate,
            method="michel",
        )
        weak, weak_diagnostics = tv_lower_bound(
            one_hot(sample1),
            one_hot(sample2),
            alpha=PER_LAW_ALPHA,
            clf=FixedScoreClassifier(weak_scores),
            test_size=0.30,
            random_state=SEED + seed_offset + replicate,
            method="michel",
        )
        strong, strong_diagnostics = tv_lower_bound(
            one_hot(sample1),
            one_hot(sample2),
            alpha=PER_LAW_ALPHA,
            clf=FixedScoreClassifier(strong_scores),
            test_size=0.30,
            random_state=SEED + seed_offset + replicate,
            method="michel",
        )
        rows.append(
            {
                "pair": pair["name"],
                "n_per_law": n,
                "replicate": replicate,
                "closed_form_tv": closed_form_tv(pair["p"], pair["q"]),
                "weak_lower_bound": float(weak),
                "strong_lower_bound": float(strong),
                "weak_lower_bound_canonical_per_law_alpha_0_025": float(weak),
                "strong_lower_bound_canonical_per_law_alpha_0_025": float(strong),
                "weak_lower_bound_original_overall_alpha_0_05": float(
                    weak_original
                ),
                "strong_lower_bound_original_overall_alpha_0_05": float(
                    strong_original
                ),
                "weak_method": weak_diagnostics["method"],
                "strong_method": strong_diagnostics["method"],
                "weak_nominal_alpha": float(weak_diagnostics["alpha"]),
                "strong_nominal_alpha": float(strong_diagnostics["alpha"]),
                "weak_canonical_nominal_alpha": float(weak_diagnostics["alpha"]),
                "strong_canonical_nominal_alpha": float(strong_diagnostics["alpha"]),
                "weak_original_nominal_alpha": float(
                    weak_original_diagnostics["alpha"]
                ),
                "strong_original_nominal_alpha": float(
                    strong_original_diagnostics["alpha"]
                ),
            }
        )
    return rows


def shrinking_identical_rows() -> list[dict[str, Any]]:
    """Check near-zero estimation and shrinking upper bounds for identical laws."""
    rows: list[dict[str, Any]] = []
    truth = closed_form_tv(PAIR_IDENTICAL["p"], PAIR_IDENTICAL["q"])
    for n_index, n in enumerate(CONVERGENCE_SIZES):
        rng = np.random.default_rng(SEED + 3000 + n_index)
        estimates: list[float] = []
        eps_hi_values: list[float] = []
        returned_alphas: list[float] = []
        for _ in range(CONVERGENCE_REPLICATES):
            sample1, sample2 = draw_pair(rng, PAIR_IDENTICAL, n)
            result = upper_result(sample1, sample2)
            estimates.append(float(result.tv_hat))
            eps_hi_values.append(float(result.eps_hi))
            returned_alphas.append(float(result.alpha))
        rows.append(
            {
                "n_per_law": n,
                "replicates": CONVERGENCE_REPLICATES,
                "closed_form_tv": truth,
                "mean_tv_hat": float(np.mean(estimates)),
                "max_tv_hat": float(np.max(estimates)),
                "mean_eps_hi": float(np.mean(eps_hi_values)),
                "returned_alpha_values": sorted(set(returned_alphas)),
            }
        )
    return rows


def main() -> None:
    """Run all five validation checks and write the single JSON artifact."""
    pair_specs = []
    for pair in (PAIR_A, PAIR_B, PAIR_IDENTICAL):
        pair_specs.append(
            {
                "name": pair["name"],
                "p": pair["p"].tolist(),
                "q": pair["q"].tolist(),
                "closed_form_tv": closed_form_tv(pair["p"], pair["q"]),
                "truth_definition": "0.5 * sum_i(abs(p_i - q_i))",
            }
        )

    convergence = convergence_rows(PAIR_A, 0)
    check_1_pass = (
        convergence[-1]["mean_absolute_error"]
        < convergence[0]["mean_absolute_error"]
        and abs(convergence[-1]["mean_tv_hat"] - convergence[-1]["closed_form_tv"])
        < abs(convergence[0]["mean_tv_hat"] - convergence[0]["closed_form_tv"])
    )

    coverage = coverage_rows(PAIR_A, 1000) + coverage_rows(PAIR_B, 2000)
    coverage_violation_count = sum(row["violation_count"] for row in coverage)
    check_2_pass = all(row["coverage"] >= 1.0 - OVERALL_ALPHA for row in coverage)

    brackets = bracket_rows(PAIR_A, 4000) + bracket_rows(PAIR_IDENTICAL, 5000)
    bracket_violation_count = sum(
        int(row["eps_lo"] > row["eps_hi"] + 1e-12) for row in brackets
    )
    check_3_pass = bracket_violation_count == 0

    scorer_comparison = scorer_rows(PAIR_A, 6000)
    scorer_violation_count = sum(
        int(row["weak_lower_bound"] > row["strong_lower_bound"] + 1e-12)
        for row in scorer_comparison
    )
    check_4_pass = scorer_violation_count == 0

    identical = shrinking_identical_rows()
    check_5_pass = (
        identical[-1]["mean_tv_hat"] <= 0.05
        and identical[-1]["mean_eps_hi"] < identical[0]["mean_eps_hi"]
        and identical[-1]["mean_tv_hat"] < identical[0]["mean_tv_hat"]
    )

    returned_alpha_values = sorted(
        {
            alpha
            for group in (convergence, coverage, identical)
            for row in group
            for alpha in row["returned_alpha_values"]
        }
        | {row["upper_returned_alpha"] for row in brackets}
    )
    lower_canonical_alpha_values = sorted(
        {row["lower_canonical_nominal_alpha"] for row in brackets}
        | {
            row["weak_canonical_nominal_alpha"]
            for row in scorer_comparison
        }
        | {
            row["strong_canonical_nominal_alpha"]
            for row in scorer_comparison
        }
    )
    lower_original_alpha_values = sorted(
        {row["lower_original_nominal_alpha"] for row in brackets}
        | {row["weak_original_nominal_alpha"] for row in scorer_comparison}
        | {row["strong_original_nominal_alpha"] for row in scorer_comparison}
    )
    coverage_example = next(
        row
        for row in coverage
        if row["pair"] == PAIR_A["name"] and row["n_per_law"] == 32
    )
    convergence_mae = " -> ".join(
        f"{row['mean_absolute_error']:.4f}".rstrip("0").rstrip(".")
        for row in convergence
    )
    coverage_interpretation = (
        "Coverage values of 1.000000 are no contradiction observed validity "
        "checks, not tightness checks; for n=32 in shifted_four_symbol the "
        f"mean upper bound is {coverage_example['mean_eps_hi']:.9f} against "
        f"truth {coverage_example['closed_form_tv']:.9f} (slack "
        f"+{coverage_example['mean_eps_hi'] - coverage_example['closed_form_tv']:.9f}), "
        f"and the genuine convergence evidence is shrinking mean absolute "
        f"error: {convergence_mae}."
    )
    lower_alpha_statement = (
        "Canonical lower-side numbers use alpha=0.025 because both bracket "
        "sides use the per-law alpha split; alpha=0.05 lower-side numbers are "
        "retained beside them as the original run and as evidence that the "
        "non-crossing result was not fragile."
    )
    artifact = {
        "experiment": "X5_estimator_ground_truth",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "implementation": {
            "upper_function": "src/eibo/statcore.py::tv_upper_bound",
            "upper_result_type": "TVUpperBoundResult",
            "alpha_source": "result.alpha returned by each tv_upper_bound call",
            "overall_alpha_declared": OVERALL_ALPHA,
            "per_law_split": "overall_alpha / 2",
            "per_law_alpha_requested": PER_LAW_ALPHA,
            "per_law_alpha_returned": returned_alpha_values,
            "alphabet_size": ALPHABET_SIZE,
            "alphabet_size_source": "fixed a priori four-symbol synthetic protocol, never realized support",
            "lower_function": "src/eibo/statcore.py::tv_lower_bound",
            "lower_alpha_source": "diagnostics['alpha'] returned by each tv_lower_bound call",
            "lower_alpha_original_requested": ORIGINAL_LOWER_ALPHA,
            "lower_alpha_original_returned": lower_original_alpha_values,
            "lower_alpha_canonical_requested": PER_LAW_ALPHA,
            "lower_alpha_canonical_returned": lower_canonical_alpha_values,
            "lower_alpha_statement": lower_alpha_statement,
            "lower_guarantee_status": "nominal/asymptotic Michel lower-side construction; not a finite-sample certificate",
            "upper_guarantee_status": "finite-sample distribution-free categorical upper bound",
        },
        "synthetic_pairs": pair_specs,
        "checks": {
            "check_1_tv_hat_convergence": {
                "pass": bool(check_1_pass),
                "verdict": "PASS" if check_1_pass else "FAIL",
                "pair": PAIR_A["name"],
                "rows": convergence,
                "criterion": "mean absolute error and mean bias distance are smaller at the largest n",
            },
            "check_2_upper_bound_coverage": {
                "pass": bool(check_2_pass),
                "verdict": "PASS" if check_2_pass else "FAIL",
                "per_law_alpha": PER_LAW_ALPHA,
                "overall_alpha": OVERALL_ALPHA,
                "criterion": "coverage >= 1 - overall_alpha for every pair and sample size",
                "interpretation": coverage_interpretation,
                "rows": coverage,
                "total_violation_count": coverage_violation_count,
            },
            "check_3_bracket_non_crossing": {
                "pass": bool(check_3_pass),
                "verdict": "PASS" if check_3_pass else "FAIL",
                "criterion": "eps_lo <= eps_hi for every reported bracket row",
                "lower_alpha_comparison": lower_alpha_statement,
                "rows_checked": len(brackets),
                "violation_count": bracket_violation_count,
                "rows": brackets,
            },
            "check_4_weak_vs_strong_scorer": {
                "pass": bool(check_4_pass),
                "verdict": "PASS" if check_4_pass else "FAIL",
                "criterion": "weak lower bound <= strong lower bound on every same-sample comparison",
                "lower_alpha_comparison": lower_alpha_statement,
                "rows_checked": len(scorer_comparison),
                "violation_count": scorer_violation_count,
                "rows": scorer_comparison,
            },
            "check_5_identical_distributions": {
                "pass": bool(check_5_pass),
                "verdict": "PASS" if check_5_pass else "FAIL",
                "pair": PAIR_IDENTICAL["name"],
                "criterion": "largest-n mean tv_hat <= 0.05 and both mean tv_hat and mean eps_hi shrink",
                "rows": identical,
            },
        },
        "limitation": (
            "This validation is synthetic only: it validates the estimator and the "
            "finite-sample categorical upper-bound implementation on the specified "
            "synthetic distributions. It does not validate the real-traffic results "
            "or real channels. In particular, the existing lower-side falsification "
            "result concerns a synthetic ensemble sharing the same assumed factors, "
            "not real channels; this experiment provides no evidence about real channels."
        ),
    }

    artifact_path = PROJECT_ROOT / "artifacts" / "x5_estimator_ground_truth.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    artifact_bytes = artifact_path.stat().st_size

    print("X5 estimator ground-truth validation")
    print(f"overall_alpha_declared={OVERALL_ALPHA}")
    print(f"per_law_alpha_split={PER_LAW_ALPHA}")
    print(f"per_law_alpha_returned_from_tv_upper_bound={returned_alpha_values}")
    print(
        f"lower_alpha_returned_original={lower_original_alpha_values} "
        f"canonical={lower_canonical_alpha_values}"
    )
    print(f"fixed_a_priori_alphabet_size={ALPHABET_SIZE}")
    print(f"check_1={'PASS' if check_1_pass else 'FAIL'}")
    for row in convergence:
        print(
            "check_1_row "
            f"n={row['n_per_law']} truth={row['closed_form_tv']:.9f} "
            f"mean_tv_hat={row['mean_tv_hat']:.9f} "
            f"mean_absolute_error={row['mean_absolute_error']:.9f}"
        )
    print(
        f"check_2={'PASS' if check_2_pass else 'FAIL'} "
        f"total_violation_count={coverage_violation_count}"
    )
    for row in coverage:
        print(
            "check_2_row "
            f"pair={row['pair']} n={row['n_per_law']} truth={row['closed_form_tv']:.9f} "
            f"mean_tv_hat={row['mean_tv_hat']:.9f} "
            f"coverage={row['coverage']:.6f} violations={row['violation_count']} "
            f"mean_eps_hi={row['mean_eps_hi']:.9f} "
            f"mean_eps_hi_interpretation={row['mean_eps_hi_interpretation']}"
        )
    print("check_2_interpretation=" + coverage_interpretation)
    print(
        f"check_3={'PASS' if check_3_pass else 'FAIL'} rows_checked={len(brackets)} "
        f"violation_count={bracket_violation_count}"
    )
    for pair_name in sorted({row["pair"] for row in brackets}):
        for n in BRACKET_SIZES:
            subset = [
                row
                for row in brackets
                if row["pair"] == pair_name and row["n_per_law"] == n
            ]
            truth = subset[0]["closed_form_tv"]
            tv_hats = [row["tv_hat"] for row in subset]
            eps_los = [row["eps_lo"] for row in subset]
            eps_los_original = [
                row["eps_lo_original_overall_alpha_0_05"] for row in subset
            ]
            eps_his = [row["eps_hi"] for row in subset]
            print(
                "check_3_summary "
                f"pair={pair_name} n={n} truth={truth:.9f} "
                f"mean_tv_hat={np.mean(tv_hats):.9f} "
                f"mean_eps_lo_original_alpha_0_05={np.mean(eps_los_original):.9f} "
                f"mean_eps_lo_canonical_alpha_0_025={np.mean(eps_los):.9f} "
                f"mean_eps_hi={np.mean(eps_his):.9f}"
            )
    print(
        f"check_3_alpha_values upper={sorted({row['upper_returned_alpha'] for row in brackets})} "
        f"lower_original={sorted({row['lower_original_nominal_alpha'] for row in brackets})} "
        f"lower_canonical={sorted({row['lower_nominal_alpha'] for row in brackets})}"
    )
    print("check_3_lower_alpha_comparison=" + lower_alpha_statement)
    print(
        f"check_4={'PASS' if check_4_pass else 'FAIL'} rows_checked={len(scorer_comparison)} "
        f"violation_count={scorer_violation_count}"
    )
    print(
        "check_4_summary "
        f"truth={scorer_comparison[0]['closed_form_tv']:.9f} "
        f"weak_min_original_alpha_0_05={min(row['weak_lower_bound_original_overall_alpha_0_05'] for row in scorer_comparison):.9f} "
        f"weak_max_original_alpha_0_05={max(row['weak_lower_bound_original_overall_alpha_0_05'] for row in scorer_comparison):.9f} "
        f"weak_min_canonical_alpha_0_025={min(row['weak_lower_bound'] for row in scorer_comparison):.9f} "
        f"weak_max_canonical_alpha_0_025={max(row['weak_lower_bound'] for row in scorer_comparison):.9f} "
        f"strong_min_original_alpha_0_05={min(row['strong_lower_bound_original_overall_alpha_0_05'] for row in scorer_comparison):.9f} "
        f"strong_max_original_alpha_0_05={max(row['strong_lower_bound_original_overall_alpha_0_05'] for row in scorer_comparison):.9f} "
        f"strong_min_canonical_alpha_0_025={min(row['strong_lower_bound'] for row in scorer_comparison):.9f} "
        f"strong_max_canonical_alpha_0_025={max(row['strong_lower_bound'] for row in scorer_comparison):.9f}"
    )
    print(
        f"check_4_strict_improvement_count={sum(row['strong_lower_bound'] > row['weak_lower_bound'] + 1e-12 for row in scorer_comparison)}"
    )
    print(f"check_5={'PASS' if check_5_pass else 'FAIL'}")
    for row in identical:
        print(
            "check_5_row "
            f"n={row['n_per_law']} truth={row['closed_form_tv']:.9f} "
            f"mean_tv_hat={row['mean_tv_hat']:.9f} "
            f"mean_eps_hi={row['mean_eps_hi']:.9f}"
        )
    print(f"artifact={artifact_path}")
    print(f"artifact_bytes={artifact_bytes}")
    print("limitation=" + artifact["limitation"])

    if not all((check_1_pass, check_2_pass, check_3_pass, check_4_pass, check_5_pass)):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
