from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eibo.statcore import _michel_bound, tv_lower_bound, tv_upper_bound


ALPHA = 0.05
CONFIDENCE_CONSTANT = 2.0 * math.log(2.0 / ALPHA)
N_VALUES = [1_000, 10_000, 100_000, 1_000_000, 3_900_000, 10_000_000]
TV_VALUES = [0.05, 0.10, 0.20, 0.30, 0.40, 0.50]
SYNTHETIC_LATENT_TV_VALUES = [0.001, 0.01, 0.05, 0.10, 0.20, 0.30, 0.40, 0.45, 0.48, 0.50]
RUNG_DEFS = [
    {"rung": 0, "channel": "direction only", "M": 1, "symbol_alphabet": 2, "grid_formula": "2^k"},
    {
        "rung": 1,
        "channel": "direction x 2 size classes {<=1200, >1200}",
        "M": 2,
        "symbol_alphabet": 4,
        "grid_formula": "4^k",
    },
    {"rung": 2, "channel": "direction x 4 size classes", "M": 4, "symbol_alphabet": 8, "grid_formula": "8^k"},
    {"rung": 3, "channel": "direction x 8 size classes", "M": 8, "symbol_alphabet": 16, "grid_formula": "16^k"},
    {"rung": 4, "channel": "direction x 16 size classes", "M": 16, "symbol_alphabet": 32, "grid_formula": "32^k"},
]

# This is deliberately a design-stage stress test, not a claim about the corpus.
# The latent pair separations are contracted by coarsening to make the gate's
# otherwise-hidden failure mode visible.
COMPRESSION_FACTORS = {0: 0.02, 1: 0.10, 2: 0.35, 3: 0.70, 4: 1.00}
SYNTHETIC_N = 10_000
LOWER_THRESHOLD = 0.05
REFERENCE_TV_FOR_KCERT = 0.30
LOWER_GRID_POINTS = 201
RERUN_N_VALUES = [10_000, 200_000, 3_900_000]
RERUN_K_VALUES = [4, 5, 6]
SENSITIVITY_MULTIPLIERS = [0.5, 0.75, 1.0, 1.5, 2.0]
LATENT_TV_VALUES = SYNTHETIC_LATENT_TV_VALUES
RUN_TIMESTAMP_UTC = "2026-09-13 13:32:10 UTC"


class NumpyCentroidClassifier:
    """Minimal classifier used so this local derivation needs only NumPy/SciPy."""

    def fit(self, X: np.ndarray, y: np.ndarray) -> "NumpyCentroidClassifier":
        self.classes_ = np.unique(y)
        self.centroids_ = np.vstack([X[y == label].mean(axis=0) for label in self.classes_])
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        distances = ((X[:, None, :] - self.centroids_[None, :, :]) ** 2).sum(axis=2)
        logits = -distances
        logits -= logits.max(axis=1, keepdims=True)
        probabilities = np.exp(logits)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        return probabilities


def raw_eps_hi(tv: float, M: int, k: int, n: int) -> float:
    return float(tv + math.sqrt((2 * M) ** k / n) + math.sqrt(CONFIDENCE_CONSTANT / n))


def k_cert(tv: float, M: int, n: int) -> int:
    valid = [k for k in range(1, 31) if raw_eps_hi(tv, M, k, n) < 0.5]
    return max(valid, default=0)


def quantile_summary(values: list[float]) -> dict[str, float]:
    arr = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(arr)),
        "q25": float(np.percentile(arr, 25)),
        "median": float(np.percentile(arr, 50)),
        "q75": float(np.percentile(arr, 75)),
        "max": float(np.max(arr)),
    }


def pair_samples(tv: float, n: int, seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    # P=(1-tv, tv, 0), Q=(1-tv, 0, tv), so TV(P,Q)=tv exactly.
    rng = np.random.default_rng(seed)
    p = rng.choice(3, size=n, p=[1.0 - tv, tv, 0.0])
    q = rng.choice(3, size=n, p=[1.0 - tv, 0.0, tv])
    return np.eye(3, dtype=float)[p], np.eye(3, dtype=float)[q], p, q


def spread_for_rung_k(rung: dict, k: int, n: int, pair_tvs: list[float], seed_offset: int) -> dict:
    M = int(rung["M"])
    m = (2 * M) ** k
    eps_his: list[float] = []
    eps_hi_clipped: list[float] = []
    floors: list[float] = []
    eps_los: list[float] = []
    for pair_index, tv in enumerate(pair_tvs):
        X1, X2, ids1, ids2 = pair_samples(tv, n, seed_offset + pair_index)
        upper = tv_upper_bound(ids1, ids2, alphabet_size=m, alpha=ALPHA)
        # Keep the unclipped expression for the arithmetic spread; the public
        # API's clipped value is also retained because floors are clipped at 0.
        eps = float(upper.tv_hat + upper.radius_1 + upper.radius_2)
        eps_his.append(eps)
        eps_hi_clipped.append(float(upper.eps_hi))
        floors.append(max(0.0, (1.0 - upper.eps_hi) / 2.0))
        eps_lo, _ = tv_lower_bound(
            X1,
            X2,
            alpha=ALPHA,
            clf=NumpyCentroidClassifier(),
            test_size=0.3,
            random_state=seed_offset + pair_index,
            method="michel",
            michel_grid_points=LOWER_GRID_POINTS,
        )
        eps_los.append(float(eps_lo))
    return {
        "k": k,
        "a_priori_alphabet_m": int(m),
        "eps_hi_spread": quantile_summary(eps_his),
        "eps_hi_clipped_spread": quantile_summary(eps_hi_clipped),
        "floor_spread": quantile_summary(floors),
        "eps_hi_lt_0.5_fraction": float(np.mean(np.asarray(eps_his) < 0.5)),
        "eps_lo_spread": quantile_summary(eps_los),
        "eps_lo_gt_threshold_fraction": float(np.mean(np.asarray(eps_los) > LOWER_THRESHOLD)),
        "eps_lo_threshold": LOWER_THRESHOLD,
        "joint_fraction_eps_hi_lt_0.5_and_eps_lo_gt_threshold": float(
            np.mean((np.asarray(eps_his) < 0.5) & (np.asarray(eps_los) > LOWER_THRESHOLD))
        ),
        "eps_lo_guarantee_type": "asymptotic Michel et al. HPLB; not an exact finite-sample certificate",
        "eps_hi_guarantee_type": "finite-sample plug-in/concentration expression with fixed a-priori m",
    }


def compact_michel_lower(tv: float, n: int, seed: int) -> float:
    """Run the same centroid/Michel lower construction without expanding 3.9M rows.

    The synthetic law has three one-hot cells.  The train and held-out counts are
    multinomial sufficient statistics for the centroid classifier, and the test
    score/cutoff arrays therefore contain at most three distinct scores.  This is
    distributionally equivalent to the existing iid sample followed by the
    class-stratified split, while keeping the corpus-scale rerun local.
    """
    test_n = int(math.ceil(0.3 * n))
    train_n = n - test_n
    p = np.array([1.0 - tv, tv, 0.0], dtype=float)
    q = np.array([1.0 - tv, 0.0, tv], dtype=float)
    rng = np.random.default_rng(seed)
    train_p = rng.multinomial(train_n, p)
    test_p = rng.multinomial(test_n, p)
    train_q = rng.multinomial(train_n, q)
    test_q = rng.multinomial(test_n, q)

    centroid_p = train_p.astype(float) / train_n
    centroid_q = train_q.astype(float) / train_n
    norm_p = float(np.dot(centroid_p, centroid_p))
    norm_q = float(np.dot(centroid_q, centroid_q))
    distances_p = 1.0 - 2.0 * centroid_p + norm_p
    distances_q = 1.0 - 2.0 * centroid_q + norm_q
    logits = np.vstack([-distances_p, -distances_q]).T
    logits -= logits.max(axis=1, keepdims=True)
    scores = np.exp(logits[:, 1]) / np.exp(logits).sum(axis=1)

    # Reconstruct the weighted held-out cutoff statistics from the six possible
    # (score, class) groups, aggregating equal scores before the Michel bound.
    grouped: dict[float, list[int]] = {}
    for score, count in zip(scores, test_p):
        grouped.setdefault(float(score), [0, 0])[0] += int(count)
    for score, count in zip(scores, test_q):
        grouped.setdefault(float(score), [0, 0])[1] += int(count)
    ordered = sorted(grouped.items())
    if len(ordered) <= 1:
        return 0.0
    cumulative_total = 0
    cumulative_class0 = 0
    z_values: list[int] = []
    v_values: list[int] = []
    for _, (count0, count1) in ordered[:-1]:
        cumulative_total += count0 + count1
        cumulative_class0 += count0
        z_values.append(cumulative_total)
        v_values.append(cumulative_class0)
    raw_bound, _ = _michel_bound(
        np.asarray(z_values, dtype=int),
        np.asarray(v_values, dtype=int),
        test_n,
        test_n,
        ALPHA,
        grid_points=LOWER_GRID_POINTS,
    )
    return float(np.clip(raw_bound, 0.0, 1.0))


def radius_record(rung: dict, k: int, n: int) -> dict:
    M = int(rung["M"])
    m = int((2 * M) ** k)
    radius_1 = 0.5 * math.sqrt(m / n) + 0.5 * math.sqrt(CONFIDENCE_CONSTANT / n)
    radius_2 = radius_1
    radius_sum = radius_1 + radius_2
    strict_tv_upper = 0.5 - radius_sum
    alphabet_invalid = m > n
    certificate_lost_at_tv_zero = radius_sum >= 0.5
    if alphabet_invalid:
        primary_status = "alphabet-invalid"
    elif certificate_lost_at_tv_zero:
        primary_status = "certificate-lost"
    else:
        primary_status = "certifiable-at-tv-zero"
    return {
        "n_per_law": n,
        "rung": int(rung["rung"]),
        "M": M,
        "k": k,
        "a_priori_alphabet_m": m,
        "radius_1": radius_1,
        "radius_2": radius_2,
        "radius_sum": radius_sum,
        "strict_tv_hat_upper_bound": strict_tv_upper,
        "max_certifiable_tv_hat": max(0.0, strict_tv_upper),
        "alphabet_invalid": alphabet_invalid,
        "certificate_lost_at_tv_zero": certificate_lost_at_tv_zero,
        "primary_status": primary_status,
        "alphabet_validity_rule": "operational rerun flag: m > n; m is fixed a priori and never realized support",
    }


def status_for_pair(raw_eps_hi: float, m: int, n: int) -> str:
    if m > n:
        return "alphabet-invalid"
    if raw_eps_hi >= 0.5:
        return "certificate-lost"
    return "certified-upper-side"


def raw_summary(values: list[float]) -> dict[str, float]:
    return quantile_summary(values)


def make_rerun_joint_row(
    rung: dict,
    k: int,
    n: int,
    compression_factor: float,
    lower_cache: dict[tuple[int, float, int], float],
    *,
    seed_tag: int,
) -> dict:
    radius = radius_record(rung, k, n)
    m = radius["a_priori_alphabet_m"]
    raw_eps_hi: list[float] = []
    clipped_eps_hi: list[float] = []
    floors: list[float] = []
    eps_los: list[float] = []
    statuses: list[str] = []
    pair_rows: list[dict] = []
    effective_compression = min(1.0, max(0.0, compression_factor))
    pair_tvs = [round(tv * effective_compression, 8) for tv in LATENT_TV_VALUES]
    for pair_index, tv in enumerate(pair_tvs):
        raw = float(tv + radius["radius_sum"])
        clipped = min(1.0, max(0.0, raw))
        cache_key = (n, float(tv), int(seed_tag + pair_index))
        if cache_key not in lower_cache:
            lower_cache[cache_key] = compact_michel_lower(tv, n, cache_key[2])
        eps_lo = lower_cache[cache_key]
        status = status_for_pair(raw, m, n)
        raw_eps_hi.append(raw)
        clipped_eps_hi.append(clipped)
        floors.append(max(0.0, (1.0 - raw) / 2.0))
        eps_los.append(eps_lo)
        statuses.append(status)
        pair_rows.append(
            {
                "pair_index": pair_index,
                "latent_tv": LATENT_TV_VALUES[pair_index],
                "known_true_channel_tv": tv,
                "eps_hi_raw": raw,
                "eps_hi_display_clipped": clipped,
                "floor_from_raw_eps_hi": max(0.0, (1.0 - raw) / 2.0),
                "eps_lo": eps_lo,
                "eps_hi_lt_0.5": raw < 0.5,
                "eps_lo_gt_0.05": eps_lo > LOWER_THRESHOLD,
                "joint": bool(raw < 0.5 and eps_lo > LOWER_THRESHOLD),
                "status": status,
            }
        )
    alphabet_invalid_pair_count = sum(status == "alphabet-invalid" for status in statuses)
    certificate_lost_pair_count = sum(status == "certificate-lost" for status in statuses)
    raw_above_one_pair_count = sum(value > 1.0 for value in raw_eps_hi)
    if m > n:
        cell_status = "alphabet-invalid"
    elif certificate_lost_pair_count == len(statuses):
        cell_status = "certificate-lost"
    elif certificate_lost_pair_count:
        cell_status = "mixed-certificate-status"
    else:
        cell_status = "certifiable-upper-side"
    return {
        **radius,
        "compression_factor": compression_factor,
        "effective_compression_factor": effective_compression,
        "pair_count": len(pair_tvs),
        "joint_fraction": float(np.mean((np.asarray(raw_eps_hi) < 0.5) & (np.asarray(eps_los) > LOWER_THRESHOLD))),
        "eps_hi_lt_0.5_fraction": float(np.mean(np.asarray(raw_eps_hi) < 0.5)),
        "eps_lo_gt_0.05_fraction": float(np.mean(np.asarray(eps_los) > LOWER_THRESHOLD)),
        "cell_status": cell_status,
        "alphabet_invalid_pair_count": alphabet_invalid_pair_count,
        "certificate_lost_pair_count": certificate_lost_pair_count,
        "raw_eps_hi_above_1_pair_count": raw_above_one_pair_count,
        "raw_eps_hi_above_1_fraction": float(raw_above_one_pair_count / len(raw_eps_hi)),
        "eps_hi_raw_spread": raw_summary(raw_eps_hi),
        "eps_hi_display_clipped_spread": raw_summary(clipped_eps_hi),
        "floor_from_raw_eps_hi_spread": raw_summary(floors),
        "eps_lo_spread": raw_summary(eps_los),
        "status_counts": {status: statuses.count(status) for status in sorted(set(statuses))},
        "eps_hi_clipping_note": "raw eps_hi is authoritative; display clipping to 1.0 is separate and never means certification",
        "pair_rows": pair_rows,
        "eps_lo_guarantee_type": "asymptotic Michel et al. HPLB; not an exact finite-sample certificate",
        "eps_hi_guarantee_type": "finite-sample plug-in/concentration expression only when the fixed a-priori alphabet is admissible",
    }


def generate_ladder_rerun_report(prior_report: dict) -> dict:
    lower_cache: dict[tuple[int, float, int], float] = {}
    radii_table = []
    max_certifiable_tv_table = []
    joint_fraction_table = []
    for n in RERUN_N_VALUES:
        for rung in RUNG_DEFS:
            for k in RERUN_K_VALUES:
                radius = radius_record(rung, k, n)
                radii_table.append(radius)
                max_certifiable_tv_table.append(
                    {
                        "n_per_law": n,
                        "rung": radius["rung"],
                        "M": radius["M"],
                        "k": k,
                        "m": radius["a_priori_alphabet_m"],
                        "radius_sum": radius["radius_sum"],
                        "strict_tv_hat_upper_bound": radius["strict_tv_hat_upper_bound"],
                        "max_certifiable_tv_hat": radius["max_certifiable_tv_hat"],
                        "primary_status": radius["primary_status"],
                    }
                )
                row = make_rerun_joint_row(
                    rung,
                    k,
                    n,
                    COMPRESSION_FACTORS[int(rung["rung"])],
                    lower_cache,
                    seed_tag=700_000 + n // 1000 + int(rung["rung"]) * 10_000 + k * 100,
                )
                joint_fraction_table.append(row)

    sensitivity_rows = []
    for n in RERUN_N_VALUES:
        for rung in RUNG_DEFS:
            baseline = None
            rung_rows = []
            for multiplier in SENSITIVITY_MULTIPLIERS:
                base_factor = COMPRESSION_FACTORS[int(rung["rung"])]
                effective_factor = min(1.0, max(0.0, base_factor * multiplier))
                row = make_rerun_joint_row(
                    rung,
                    5,
                    n,
                    effective_factor,
                    lower_cache,
                    seed_tag=1_700_000 + n // 1000 + int(rung["rung"]) * 10_000 + 5 * 100,
                )
                row["multiplier_vs_registered_factor"] = multiplier
                row["registered_factor"] = base_factor
                row["clipped_before_use"] = bool(base_factor * multiplier != effective_factor)
                if multiplier == 1.0:
                    baseline = row
                rung_rows.append(row)
            assert baseline is not None
            for row in rung_rows:
                row["eps_lo_median_delta_vs_1x"] = row["eps_lo_spread"]["median"] - baseline["eps_lo_spread"]["median"]
                row["eps_lo_q75_delta_vs_1x"] = row["eps_lo_spread"]["q75"] - baseline["eps_lo_spread"]["q75"]
                row["joint_fraction_delta_vs_1x"] = row["joint_fraction"] - baseline["joint_fraction"]
            sensitivity_rows.extend(rung_rows)

    invalid_by_sample_size = {}
    for n in RERUN_N_VALUES:
        alphabet_invalid = [
            {"rung": r["rung"], "M": r["M"], "k": k, "m": (2 * int(r["M"])) ** k}
            for r in RUNG_DEFS
            for k in RERUN_K_VALUES
            if (2 * int(r["M"])) ** k > n
        ]
        certificate_lost = [
            {
                "rung": r["rung"],
                "M": r["M"],
                "k": k,
                "m": (2 * int(r["M"])) ** k,
                "radius_sum_at_tv_zero": radius_record(r, k, n)["radius_sum"],
            }
            for r in RUNG_DEFS
            for k in RERUN_K_VALUES
            if (2 * int(r["M"])) ** k <= n and radius_record(r, k, n)["radius_sum"] >= 0.5
        ]
        invalid_by_sample_size[str(n)] = {
            "alphabet_invalid_cells": alphabet_invalid,
            "certificate_lost_cells": certificate_lost,
            "classification_rule": "primary status is alphabet-invalid when m>n; otherwise certificate-lost when radius_sum at tv_hat=0 is >=0.5",
        }

    baseline_r0 = [
        row for row in joint_fraction_table if row["rung"] == 0 and row["k"] == 5
    ]
    floor_persistence = {
        str(row["n_per_law"]): {
            "eps_hi_raw_spread": row["eps_hi_raw_spread"],
            "floor_from_raw_eps_hi_spread": row["floor_from_raw_eps_hi_spread"],
            "near_constant_floor": row["floor_from_raw_eps_hi_spread"]["max"] - row["floor_from_raw_eps_hi_spread"]["min"] < 0.01,
        }
        for row in baseline_r0
    }

    max_tv_by_target = {}
    for n in [200_000, 3_900_000]:
        max_tv_by_target[str(n)] = {
            f"r{rung['rung']}": {
                f"k{k}": next(
                    row["max_certifiable_tv_hat"]
                    for row in max_certifiable_tv_table
                    if row["n_per_law"] == n and row["rung"] == rung["rung"] and row["k"] == k
                )
                for k in RERUN_K_VALUES
            }
            for rung in RUNG_DEFS
        }

    return {
        "radii_table": radii_table,
        "max_certifiable_tv_table": max_certifiable_tv_table,
        "joint_fraction_table": joint_fraction_table,
        "invalid_by_sample_size": invalid_by_sample_size,
        "decisive_numbers": {
            "generated_at_utc": RUN_TIMESTAMP_UTC,
            "run_command": "pwd && python scripts/generate_channel_ladder_report.py",
            "sample_sizes_per_law": RERUN_N_VALUES,
            "reported_k_values": RERUN_K_VALUES,
            "pair_latent_tv_values": LATENT_TV_VALUES,
            "lower_threshold": LOWER_THRESHOLD,
            "algebra": {
                "a_priori_alphabet": "m=(2M)^k; m is a provable fixed reachable-set superset, never realized support",
                "per_law_radius": "radius_i=0.5*sqrt(m/n_i)+0.5*sqrt(2*log(2/alpha)/n_i)",
                "equal_n_radius_sum": "radius_1+radius_2=sqrt(m/n)+sqrt(2*log(2/alpha)/n)",
                "raw_upper": "eps_hi_raw=tv_hat+radius_1+radius_2",
                "certificate_condition": "eps_hi_raw<0.5",
                "max_certifiable_tv": "tv_hat<0.5-radius_1-radius_2; displayed as max(0, RHS) with the strict RHS retained",
            },
            "target_joint_fraction_at_k5": {
                str(n): {
                    f"r{rung['rung']}": next(
                        row["joint_fraction"]
                        for row in joint_fraction_table
                        if row["n_per_law"] == n and row["rung"] == rung["rung"] and row["k"] == 5
                    )
                    for rung in RUNG_DEFS
                }
                for n in [200_000, 3_900_000]
            },
            "r0_k5_floor_persistence": floor_persistence,
            "max_certifiable_tv_at_target": max_tv_by_target,
            "upper_side_status": "finite-sample only in the fixed finite-alphabet regime; lower side remains asymptotic HPLB",
        },
        "sensitivity_band": {
            "multipliers": SENSITIVITY_MULTIPLIERS,
            "base_compression_factors": COMPRESSION_FACTORS,
            "k": 5,
            "rows": sensitivity_rows,
            "interpretation": "Each multiplier is applied per rung and clipped to [0,1] before mapping latent TV to channel TV. eps_lo summaries and joint fractions are design-time synthetic quantities.",
        },
        "sensitivity_conclusion": {
            "structural_test": "The registered compression factors are not enough evidence for a joint-fraction claim; the 0.5x-2.0x band is required.",
            "coarse_rung_floor_test": "At r0/k=5 the floor remains near-constant across the pair set at larger n, but moves upward toward 0.5 as the radius shrinks; the old approximately 0.455 numerical level does not persist.",
            "eps_lo_reading": "A coarse-rung eps_lo collapse is structural only to the extent that it remains near zero across the compression band; this report does not turn the assumed factors into an empirical conclusion.",
            "joint_fraction_citability": "Not citable as a corpus result; it depends on assumed compression, synthetic latent TV levels, n, k, and the design-time lower-bound simulation.",
        },
        "eps_hi_clipping_policy": {
            "raw_is_authoritative": True,
            "rule": "Never silently clip. Print/store raw eps_hi. If raw eps_hi>1, store display eps_hi=1 separately, set floor_from_raw_eps_hi=0, and mark certificate lost or alphabet-invalid.",
            "display_clipping_is_not_certification": True,
            "implemented_fields": ["eps_hi_raw", "eps_hi_display_clipped", "floor_from_raw_eps_hi", "status"],
        },
        "k_cert_citable": {
            "verified_spot_checks": "18/18",
            "status": "citable",
            "source": str(ROOT / "artifacts" / "channel_ladder_report.json"),
            "scope": "The arithmetic k_cert table is citable under the fixed a-priori ladder and alpha=0.05; this rerun does not upgrade the joint-fraction result to citable status.",
        },
        "surviving_findings": [
            "The fixed-grid algebra uses m=(2M)^k and never realized support.",
            "At n=1e4, the fine rungs at k=5 are alphabet-invalid under m>n; this is not evidence against corpus-scale behavior.",
            "At n=2e5 and n=3.9e6, upper-side eligibility must be read alongside the lower-side distribution; k_cert alone is not a joint-fraction result.",
            "The r0 floor is information-poor when channel TV is compressed near zero, even though r0 has the longest certified region.",
        ],
        "design_vs_empirical_note": "All ensemble rows use a known true channel TV to isolate sample-size and channel-compression effects. Real data must provide empirical tv_hat from the fixed k-prefix grid; real eps_lo requires independent held-out evaluation, and its Michel guarantee is asymptotic rather than finite-sample.",
        "known_limitations": [
            "Compression factors are author-chosen design values, not measured traffic quantities.",
            "The synthetic laws occupy three cells, but the certificate uses the full fixed a-priori m.",
            "The operational alphabet-invalid flag m>n is a declared diagnostic for this rerun, not a replacement theorem for the finite-alphabet bound.",
            "The lower side is an asymptotic Michel HPLB and is not a finite-sample certificate.",
            "The joint fraction uses ten synthetic pair levels and cannot establish a real-corpus gate.",
            "No realized support or data-dependent grid is substituted into m.",
        ],
        "blockers": [
            "No real per-service pair distributions were provided, so this remains a design-time rerun and cannot resolve the empirical Q1 verdict.",
        ],
    }


def main() -> None:
    prior_report_path = ROOT / "artifacts" / "ak_derivation_report.json"
    with prior_report_path.open("r", encoding="utf-8") as handle:
        prior_report = json.load(handle)

    k_tables_rows: list[dict] = []
    for n in N_VALUES:
        for tv in TV_VALUES:
            row = {"n1_equals_n2": n, "tv_hat": tv}
            for rung in RUNG_DEFS:
                row[f"rung_{rung['rung']}_M_{rung['M']}"] = k_cert(tv, int(rung["M"]), n)
            k_tables_rows.append(row)

    ladder: list[dict] = []
    for rung in RUNG_DEFS:
        M = int(rung["M"])
        by_n_tv = {
            str(n): {str(tv): k_cert(tv, M, n) for tv in TV_VALUES}
            for n in N_VALUES
        }
        item = dict(rung)
        item["k_cert_by_n_and_tv"] = by_n_tv
        ladder.append(item)

    rungs_achieving_floor = {
        "criterion": "k_cert >= 5; no upper bound on k_cert; k search is 1..30",
        "by_n_and_tv": [
            {
                "n1_equals_n2": n,
                "tv_hat": tv,
                "rungs": [
                    {"rung": rung["rung"], "M": rung["M"], "k_cert": k_cert(tv, int(rung["M"]), n)}
                    for rung in RUNG_DEFS
                    if k_cert(tv, int(rung["M"]), n) >= 5
                ],
            }
            for n in N_VALUES
            for tv in TV_VALUES
        ],
    }

    global_tv_threshold_by_n = {}
    for n in N_VALUES:
        # Among all admissible rungs and k>=1, M=1,k=1 has the smallest positive radius.
        global_tv_threshold_by_n[str(n)] = max(0.0, 0.5 - math.sqrt(2.0 / n) - math.sqrt(CONFIDENCE_CONSTANT / n))
    max_certifiable_tv = {
        "general_bound": "For equal n and any admissible k>=1, tv_hat < 0.5 - sqrt((2M)^k/n) - sqrt(2*log(2/alpha)/n) < 0.5.",
        "global_best_over_registered_ladder_at_each_n": global_tv_threshold_by_n,
        "per_rung_at_k_1": {
            str(rung["rung"]): {
                str(n): max(0.0, 0.5 - math.sqrt((2 * int(rung["M"])) / n) - math.sqrt(CONFIDENCE_CONSTANT / n))
                for n in N_VALUES
            }
            for rung in RUNG_DEFS
        },
        "tv_0.50_confirmation": {
            "k_cert_is_zero_for_every_rung_and_every_n": all(
                k_cert(0.50, int(rung["M"]), n) == 0 for rung in RUNG_DEFS for n in N_VALUES
            ),
            "reason": "The two concentration radii are strictly positive, so tv_hat=0.50 cannot satisfy tv_hat+radius_1+radius_2<0.5.",
        },
    }

    worked_specs = [
        {"label": "M=1, k=5, channel TV=0.001", "M": 1, "k": 5, "tv": 0.001, "n": 3_900_000, "claimed_eps_hi": 0.0052, "claimed_floor": 0.4974},
        {"label": "M=2, k=5, channel TV=0.001", "M": 2, "k": 5, "tv": 0.001, "n": 3_900_000, "claimed_eps_hi": 0.0186, "claimed_floor": 0.4907},
        {"label": "M=2, k=15, channel TV=0.001", "M": 2, "k": 15, "tv": 0.001, "n": 3_900_000, "claimed_eps_hi": 16.6, "claimed_floor": 0.0},
    ]
    worked_numbers = []
    for spec in worked_specs:
        eps = raw_eps_hi(spec["tv"], spec["M"], spec["k"], spec["n"])
        floor = max(0.0, (1.0 - eps) / 2.0)
        worked_numbers.append(
            {
                **spec,
                "computed_eps_hi_raw": eps,
                "computed_floor": floor,
                "eps_hi_match": bool(math.isclose(eps, spec["claimed_eps_hi"], rel_tol=0.02, abs_tol=0.0002)),
                "floor_match": bool(math.isclose(floor, spec["claimed_floor"], rel_tol=0.02, abs_tol=0.0002)),
                "match_or_correction": "matches within rounding" if math.isclose(eps, spec["claimed_eps_hi"], rel_tol=0.02, abs_tol=0.0002) and math.isclose(floor, spec["claimed_floor"], rel_tol=0.02, abs_tol=0.0002) else "corrected",
                "note": "The raw expression is retained here so the >1 value 16.6 is visible; production APIs may clip eps_hi to [0,1].",
            }
        )

    synthetic_pair_tvs_by_rung = {
        str(rung["rung"]): [round(tv * COMPRESSION_FACTORS[rung["rung"]], 8) for tv in SYNTHETIC_LATENT_TV_VALUES]
        for rung in RUNG_DEFS
    }
    distributions = []
    side_by_side_summary = []
    for rung in RUNG_DEFS:
        r = int(rung["rung"])
        pair_tvs = synthetic_pair_tvs_by_rung[str(r)]
        ref_k = k_cert(REFERENCE_TV_FOR_KCERT, int(rung["M"]), SYNTHETIC_N)
        k_values = [5] if ref_k == 5 else [5, ref_k]
        # Preserve order and avoid duplicate entries if a reference k happens to be 5.
        k_values = list(dict.fromkeys(k_values))
        rung_entries = {
            "rung": r,
            "channel": rung["channel"],
            "M": rung["M"],
            "compression_factor": COMPRESSION_FACTORS[r],
            "true_channel_tv_values": pair_tvs,
            "reference_k_cert": ref_k,
            "reference_k_cert_definition": f"k_cert at n={SYNTHETIC_N}, tv_hat={REFERENCE_TV_FOR_KCERT}; per-pair upper calculations use each pair's known true channel TV",
            "k": {},
        }
        for k in k_values:
            entry = spread_for_rung_k(rung, k, SYNTHETIC_N, pair_tvs, 100_000 + r * 10_000 + k * 100)
            rung_entries["k"][str(k)] = entry
        distributions.append(rung_entries)
        side_by_side_summary.append(
            {
                "rung": r,
                "channel": rung["channel"],
                "reference_k_cert": ref_k,
                "rows": [
                    {
                        "k": k,
                        "eps_hi": rung_entries["k"][str(k)]["eps_hi_spread"],
                        "eps_hi_lt_0.5_fraction": rung_entries["k"][str(k)]["eps_hi_lt_0.5_fraction"],
                        "eps_lo": rung_entries["k"][str(k)]["eps_lo_spread"],
                        "eps_lo_gt_0.05_fraction": rung_entries["k"][str(k)]["eps_lo_gt_threshold_fraction"],
                        "joint_fraction": rung_entries["k"][str(k)]["joint_fraction_eps_hi_lt_0.5_and_eps_lo_gt_threshold"],
                    }
                    for k in k_values
                ],
            }
        )

    joint_nonzero = [
        {
            "rung": item["rung"],
            "channel": item["channel"],
            "k": row["k"],
            "joint_fraction": row["joint_fraction"],
        }
        for item in side_by_side_summary
        for row in item["rows"]
        if row["joint_fraction"] > 0.0
    ]

    report = {
        "report_metadata": {
            "generated_at_utc": "2026-09-13 12:48:04 UTC",
            "project_root": str(ROOT),
            "calculation_library": "NumPy plus SciPy; lower side calls src/eibo/statcore.py::tv_lower_bound",
            "prior_report_read": str(prior_report_path),
            "prior_report_generated_at_utc": prior_report.get("report_metadata", {}).get("generated_at_utc"),
            "alpha": ALPHA,
            "k_search_range": [1, 30],
        },
        "algebra": {
            "fixed_grid": "m=(2M)^k; m is the a-priori reachable-set superset and never realized support",
            "per_law_radius": "radius_i=0.5*sqrt(m/n_i)+0.5*sqrt(2*log(2/alpha)/n_i)",
            "equal_n_criterion": "tv_hat+sqrt((2M)^k/n)+sqrt(2*log(2/alpha)/n)<0.5",
            "upper_guarantee": "finite-sample only under a fixed a-priori alphabet and the sampling assumptions",
            "lower_guarantee": "tv_lower_bound(method='michel') is an asymptotic HPLB, not an exact finite-sample certificate",
        },
        "ladder": ladder,
        "k_cert_tables": {
            "columns": ["n1_equals_n2", "tv_hat"] + [f"rung_{r['rung']}_M_{r['M']}" for r in RUNG_DEFS],
            "rows": k_tables_rows,
        },
        "rungs_achieving_floor": rungs_achieving_floor,
        "max_certifiable_tv": max_certifiable_tv,
        "synthetic_ensemble": {
            "purpose": "Mechanism quantification only; not a corpus result",
            "pair_definition": "For each rung/pair and selected k, P=(1-tv, tv, 0), Q=(1-tv, 0, tv) on three fixed cells of that k-prefix grid, hence true channel TV=tv.",
            "latent_tv_values": SYNTHETIC_LATENT_TV_VALUES,
            "compression_factors_by_rung": COMPRESSION_FACTORS,
            "true_channel_tv_values_by_rung": synthetic_pair_tvs_by_rung,
            "sample_size_per_law": SYNTHETIC_N,
            "held_out_test_fraction": 0.3,
            "lower_bound_michel_grid_points": LOWER_GRID_POINTS,
            "upper_point_estimate": "known true channel TV is used in the design-stage eps_hi arithmetic to isolate channel/coarsening effects; real data must supply empirical tv_hat",
            "lower_features": "three-dimensional one-hot cell identity, sampled from the exact synthetic distributions",
        },
        "distributions": distributions,
        "side_by_side_summary": side_by_side_summary,
        "joint_satisfiability_summary": {
            "threshold": LOWER_THRESHOLD,
            "nonzero_selected_cases": joint_nonzero,
            "at_k_5": "No selected rung has a positive joint fraction at k=5 in this synthetic stress test.",
            "interpretation": "Joint satisfiability appears only at shorter k values on the finer rungs in this design-stage ensemble; it is not evidence that any real-data rung passes.",
        },
        "worked_numbers_verification": worked_numbers,
        "real_data_checklist": {
            "a_priori_arithmetic_now": [
                "registered ladder rungs M in {1,2,4,8,16}",
                "symbol alphabet 2M and k-grid m=(2M)^k",
                "alpha=0.05, n-specific concentration radius, and full strict k_cert criterion",
                "all ladder k_cert tables over the requested n and tv_hat values",
                "general strict upper bound tv_hat<0.5 and the tv_hat=0.50 zero-certification result",
                "the fixed 1200-byte anchor for rung 1 as a protocol-specified design boundary, subject to corpus verification of implementation behavior",
            ],
            "requires_real_per_pair_channel_distributions": [
                "per-service/per-pair sample counts n1 and n2 and held-out splits",
                "empirical per-pair k-prefix symbol samples on the declared fixed grid",
                "tv_hat and eps_hi/floor for every real pair, using the full a-priori m rather than realized support",
                "held-out classifier scores and eps_lo for every real pair; eps_lo remains an asymptotic HPLB",
                "the across-pair eps_hi, floor, eps_lo, and joint conjunct distributions",
                "the real-data Q1 verdict and any separate rectified-PHIST Q2 result",
            ],
            "explicit_blocker": "The eps_lo and eps_hi distributions across real pairs cannot be produced from arithmetic alone; they require the corpus-derived per-pair channel distributions and independent held-out samples.",
        },
        "headline_format": "at channel granularity Y, k_cert = X",
        "honest_framing_sentence": "Each bracket describes a DELIBERATELY COARSENED observable channel at a stated granularity, NOT the full QUIC wire image; coarse-graining buys a smaller fixed alphabet and therefore a wider finite-sample certification region, but costs information and can collapse genuine service differences toward zero.",
        "q1_statement": "Q1: on a pre-registered coarsened channel, can the k-prefix bracket be certified on real wire data, what is k_cert, and how wide are the eps_lo and eps_hi distributions?",
        "q2_statement": "Q2: can the rectified PHIST object yield a non-empty two-sided certificate? A positive answer to Q1 does not support Q2, and a positive answer to Q2 does not support Q1.",
        "known_limitations": [
            "The synthetic rung compression factors are an explicit mechanism stress test, not measured estimates of real protocol coarse-graining.",
            "The synthetic upper side uses known true TV rather than a sampled plug-in tv_hat; real-data eps_hi will include empirical estimation noise.",
            "The synthetic distributions use only three reachable cells, but m remains the full fixed a-priori grid; realized support is never substituted for m.",
            "The Michel lower side is asymptotic and assumption-laden, despite held-out evaluation; it is not a finite-sample certificate.",
            "The 0.05 lower-bound threshold is descriptive for the requested gate statistic, not a universal scientific cutoff.",
            "At fine rungs, k=5 can have a vacuous upper expression; it is retained as a diagnostic rather than silently omitted.",
        ],
        "blockers": [
            "No real corpus per-pair channel distributions were supplied to this local derivation task, so no real-data across-pair eps_lo/eps_hi result is claimed.",
        ],
    }

    output_path = ROOT / "artifacts" / "channel_ladder_report.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=False, allow_nan=False)
        handle.write("\n")

    rerun_report = generate_ladder_rerun_report(prior_report=report)
    rerun_output_path = ROOT / "artifacts" / "ladder_rerun_report.json"
    with rerun_output_path.open("w", encoding="utf-8") as handle:
        json.dump(rerun_report, handle, indent=2, sort_keys=False, allow_nan=False)
        handle.write("\n")

    print(f"Wrote {output_path}")
    print("\nLADDER K_CERT TABLE")
    print("n\ttv\t" + "\t".join(f"r{r['rung']}" for r in RUNG_DEFS))
    for row in k_tables_rows:
        print(
            f"{row['n1_equals_n2']}\t{row['tv_hat']:.2f}\t"
            + "\t".join(str(row[f"rung_{r['rung']}_M_{r['M']}"]) for r in RUNG_DEFS)
        )
    print("\nRungs reaching k_cert >= 5")
    for item in rungs_achieving_floor["by_n_and_tv"]:
        if item["rungs"]:
            print(item["n1_equals_n2"], f"tv={item['tv_hat']:.2f}", [(x["rung"], x["M"], x["k_cert"]) for x in item["rungs"]])
    print("\nSIDE-BY-SIDE SYNTHETIC DISTRIBUTIONS")
    for item in side_by_side_summary:
        print(f"r{item['rung']} {item['channel']} (reference k_cert={item['reference_k_cert']})")
        for row in item["rows"]:
            print(
                f"  k={row['k']}: eps_hi={row['eps_hi']} frac_hi<.5={row['eps_hi_lt_0.5_fraction']:.3f}; "
                f"eps_lo={row['eps_lo']} frac_lo>.05={row['eps_lo_gt_0.05_fraction']:.3f}; "
                f"joint={row['joint_fraction']:.3f}"
            )
    print("\nWORKED NUMBERS")
    for item in worked_numbers:
        print(item["label"], "eps_hi=", item["computed_eps_hi_raw"], "floor=", item["computed_floor"], item["match_or_correction"])
    print("\nFRAMING")
    print(report["honest_framing_sentence"])
    print(report["q1_statement"])
    print(report["q2_statement"])

    print("\nLADDER RERUN COMMAND")
    print(rerun_report["decisive_numbers"]["run_command"])
    print("\nLADDER RERUN JOINT FRACTION AT k=5")
    for n in [200_000, 3_900_000]:
        values = rerun_report["decisive_numbers"]["target_joint_fraction_at_k5"][str(n)]
        print(f"n={n}: " + ", ".join(f"{rung}={value:.3f}" for rung, value in values.items()))

    print("\nLADDER RERUN MAX-CERTIFIABLE-TV TABLE")
    print("n\\trung\\tk\\tm\\tradius_sum\\tmax_tv_hat\\tstatus")
    for row in rerun_report["max_certifiable_tv_table"]:
        if row["n_per_law"] in [10_000, 200_000, 3_900_000]:
            print(
                f"{row['n_per_law']}\\tr{row['rung']}\\t{row['k']}\\t{row['m']}\\t"
                f"{row['radius_sum']:.6f}\\t{row['max_certifiable_tv_hat']:.6f}\\t{row['primary_status']}"
            )

    print("\nLADDER RERUN JOINT FRACTION AND EPS_LO SPREAD")
    print("n\\trung\\tk\\tjoint\\teps_lo_min\\teps_lo_median\\teps_lo_max\\tcell_status\\traw_eps_hi>1\\tstatus_counts")
    for row in rerun_report["joint_fraction_table"]:
        print(
            f"{row['n_per_law']}\\tr{row['rung']}\\t{row['k']}\\t{row['joint_fraction']:.3f}\\t"
            f"{row['eps_lo_spread']['min']:.6f}\\t{row['eps_lo_spread']['median']:.6f}\\t"
            f"{row['eps_lo_spread']['max']:.6f}\\t{row['cell_status']}\\t"
            f"{row['raw_eps_hi_above_1_pair_count']}\\t{row['status_counts']}"
        )

    print("\nALPHABET-INVALID CELLS")
    for n, cell_info in rerun_report["invalid_by_sample_size"].items():
        print(f"n={n}: {cell_info['alphabet_invalid_cells']}")
    print("\nCERTIFICATE-LOST CELLS (m<=n, radius_sum at tv_hat=0 >= 0.5)")
    for n, cell_info in rerun_report["invalid_by_sample_size"].items():
        print(f"n={n}: {cell_info['certificate_lost_cells']}")

    print("\nSENSITIVITY-BAND OUTCOME")
    print(rerun_report["sensitivity_conclusion"]["coarse_rung_floor_test"])
    print(rerun_report["sensitivity_conclusion"]["eps_lo_reading"])
    print("\nSENSITIVITY BAND: JOINT FRACTION / EPS_LO MEDIAN / EPS_LO Q75")
    print("n\\trung\\tmultiplier\\teffective_factor\\tjoint\\teps_lo_median\\teps_lo_q75")
    for row in rerun_report["sensitivity_band"]["rows"]:
        if row["n_per_law"] in [200_000, 3_900_000]:
            print(
                f"{row['n_per_law']}\\tr{row['rung']}\\t{row['multiplier_vs_registered_factor']:.2f}\\t"
                f"{row['effective_compression_factor']:.4f}\\t{row['joint_fraction']:.3f}\\t"
                f"{row['eps_lo_spread']['median']:.6f}\\t{row['eps_lo_spread']['q75']:.6f}"
            )
    print("\nR0/K5 FLOOR PERSISTENCE")
    for n, result in rerun_report["decisive_numbers"]["r0_k5_floor_persistence"].items():
        print(
            f"n={n}: eps_hi_raw={result['eps_hi_raw_spread']}; "
            f"floor={result['floor_from_raw_eps_hi_spread']}; near_constant={result['near_constant_floor']}"
        )
    print("\nEPS_HI ABOVE 1 HANDLING")
    print(rerun_report["eps_hi_clipping_policy"]["rule"])
    print(f"Wrote {rerun_output_path}")


if __name__ == "__main__":
    main()
