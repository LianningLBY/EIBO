from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from eibo.divisibility import DEFAULT_Q_VALUES, tv_lower_bound_divisibility  # noqa: E402
from eibo.statcore import tv_lower_bound  # noqa: E402

from generate_channel_ladder_report import (  # noqa: E402
    ALPHA,
    COMPRESSION_FACTORS,
    LATENT_TV_VALUES,
    LOWER_GRID_POINTS,
    LOWER_THRESHOLD,
    NumpyCentroidClassifier,
    RERUN_K_VALUES,
    RUNG_DEFS,
    pair_samples,
    quantile_summary,
)


SAMPLE_SIZES = [200_000, 3_900_000]
RUN_COMMAND = "pwd && PYTHONPATH=src python scripts/compare_lower_bounds.py"
RUN_TIMESTAMP_UTC = "2026-09-13 13:53:31 UTC"
T_CONSTANT = 2.254


def threshold(n: int) -> float:
    return float(0.0500 + T_CONSTANT / math.sqrt(n))


def upper_values(channel_tvs: list[float], M: int, k: int, n: int) -> dict[str, Any]:
    m = int((2 * M) ** k)
    radius_sum = math.sqrt(m / n) + math.sqrt(2.0 * math.log(2.0 / ALPHA) / n)
    raw = [float(tv + radius_sum) for tv in channel_tvs]
    clipped = [float(min(1.0, max(0.0, value))) for value in raw]
    floors = [float(max(0.0, (1.0 - value) / 2.0)) for value in raw]
    statuses = []
    for value in raw:
        if m > n:
            statuses.append("alphabet-invalid")
        elif value >= 0.5:
            statuses.append("certificate-lost")
        else:
            statuses.append("certified-upper-side")
    return {
        "a_priori_alphabet_m": m,
        "radius_sum": float(radius_sum),
        "strict_tv_hat_upper_limit": float(0.5 - radius_sum),
        "eps_hi_raw": raw,
        "eps_hi_display_clipped": clipped,
        "floor_from_raw_eps_hi": floors,
        "eps_hi_raw_spread": quantile_summary(raw),
        "eps_hi_display_clipped_spread": quantile_summary(clipped),
        "floor_from_raw_eps_hi_spread": quantile_summary(floors),
        "raw_eps_hi_above_1_count": int(sum(value > 1.0 for value in raw)),
        "raw_eps_hi_above_1_fraction": float(np.mean(np.asarray(raw) > 1.0)),
        "status_counts": {status: statuses.count(status) for status in sorted(set(statuses))},
        "cell_status": (
            "alphabet-invalid"
            if m > n
            else "certificate-lost"
            if all(status == "certificate-lost" for status in statuses)
            else "mixed-certificate-status"
            if any(status == "certificate-lost" for status in statuses)
            else "certifiable-upper-side"
        ),
        "eps_hi_clipping_policy": (
            "eps_hi_raw is authoritative and is never substituted by the display-clipped value; "
            "floor is computed from raw eps_hi and is printed as 0 when raw eps_hi >= 1"
        ),
    }


def lower_summary(values: list[float], raw_values: list[float], vacuous_indices: list[int]) -> dict[str, Any]:
    return {
        "spread": quantile_summary(values),
        "fraction_gt_0.05": float(np.mean(np.asarray(values) > LOWER_THRESHOLD)),
        "threshold": LOWER_THRESHOLD,
        "vacuous_pair_count": len(vacuous_indices),
        "vacuous_pair_fraction": float(len(vacuous_indices) / len(values)),
        "vacuous_pair_indices": vacuous_indices,
        "raw_bound_spread": quantile_summary(raw_values),
        "guarantee_type": None,
    }


def route_comparison(classifier_values: list[float], divisibility_values: list[float]) -> dict[str, Any]:
    clf = np.asarray(classifier_values, dtype=float)
    div = np.asarray(divisibility_values, dtype=float)
    delta = div - clf
    tolerance = 1e-12
    return {
        "divisibility_minus_classifier_spread": quantile_summary(delta.tolist()),
        "divisibility_stronger_fraction": float(np.mean(delta > tolerance)),
        "classifier_stronger_fraction": float(np.mean(delta < -tolerance)),
        "tie_fraction": float(np.mean(np.abs(delta) <= tolerance)),
        "divisibility_stronger_count": int(np.sum(delta > tolerance)),
        "classifier_stronger_count": int(np.sum(delta < -tolerance)),
        "tie_count": int(np.sum(np.abs(delta) <= tolerance)),
        "winner_by_median": (
            "divisibility"
            if float(np.median(div)) > float(np.median(clf)) + tolerance
            else "classifier"
            if float(np.median(clf)) > float(np.median(div)) + tolerance
            else "tie"
        ),
        "classifier_median": float(np.median(clf)),
        "divisibility_median": float(np.median(div)),
        "median_gain_divisibility_minus_classifier": float(np.median(div) - np.median(clf)),
    }


def main() -> None:
    # One sampled pair is shared by both lower routes for each rung, n, and
    # pair. The existing ladder rerun uses this k-independent synthetic law and
    # caches it; the same values are reused across the reported k cells.
    lower_cache: dict[tuple[int, int], dict[str, Any]] = {}
    pair_data: dict[tuple[int, int, int], dict[str, Any]] = {}
    for n in SAMPLE_SIZES:
        for rung in RUNG_DEFS:
            r = int(rung["rung"])
            compression = float(COMPRESSION_FACTORS[r])
            channel_tvs = [round(float(tv * compression), 8) for tv in LATENT_TV_VALUES]
            classifier_values: list[float] = []
            classifier_raw_values: list[float] = []
            classifier_vacuous: list[int] = []
            divisibility_values: list[float] = []
            divisibility_raw_values: list[float] = []
            divisibility_vacuous: list[int] = []
            for pair_index, tv in enumerate(channel_tvs):
                seed = 700_000 + n // 1000 + r * 10_000 + pair_index
                X1, X2, ids1, ids2 = pair_samples(tv, n, seed)
                clf_lo, clf_diag = tv_lower_bound(
                    X1,
                    X2,
                    alpha=ALPHA,
                    clf=NumpyCentroidClassifier(),
                    test_size=0.3,
                    random_state=seed,
                    method="michel",
                    michel_grid_points=LOWER_GRID_POINTS,
                )
                div_lo, div_diag = tv_lower_bound_divisibility(
                    ids1.reshape(-1, 1),
                    ids2.reshape(-1, 1),
                    alpha=ALPHA,
                    mode="realizable",
                    q_values=DEFAULT_Q_VALUES,
                    random_state=seed,
                )
                classifier_values.append(float(clf_lo))
                classifier_raw_values.append(float(clf_diag["bound_before_clipping"]))
                if float(clf_diag["bound_before_clipping"]) <= 0.0:
                    classifier_vacuous.append(pair_index)
                divisibility_values.append(float(div_lo))
                divisibility_raw_values.append(float(div_diag["raw_bound"]))
                if bool(div_diag["vacuous"]):
                    divisibility_vacuous.append(pair_index)
                pair_data[(n, r, pair_index)] = {
                    "seed": seed,
                    "latent_tv": float(LATENT_TV_VALUES[pair_index]),
                    "known_true_channel_tv": float(tv),
                }
            lower_cache[(n, r)] = {
                "channel_tvs": channel_tvs,
                "classifier_values": classifier_values,
                "classifier_raw_values": classifier_raw_values,
                "classifier_vacuous": classifier_vacuous,
                "divisibility_values": divisibility_values,
                "divisibility_raw_values": divisibility_raw_values,
                "divisibility_vacuous": divisibility_vacuous,
            }

    per_rung_per_k: list[dict[str, Any]] = []
    distributions: list[dict[str, Any]] = []
    when_each_wins: list[dict[str, Any]] = []
    vacuous_cells: list[dict[str, Any]] = []
    for n in SAMPLE_SIZES:
        for rung in RUNG_DEFS:
            r = int(rung["rung"])
            M = int(rung["M"])
            for k in RERUN_K_VALUES:
                cached = lower_cache[(n, r)]
                upper = upper_values(cached["channel_tvs"], M, k, n)
                clf_values = cached["classifier_values"]
                div_values = cached["divisibility_values"]
                joint_clf = [
                    raw < 0.5 and lo > LOWER_THRESHOLD
                    for raw, lo in zip(upper["eps_hi_raw"], clf_values)
                ]
                joint_div = [
                    raw < 0.5 and lo > LOWER_THRESHOLD
                    for raw, lo in zip(upper["eps_hi_raw"], div_values)
                ]
                row = {
                    "M": M,
                    "rung": r,
                    "channel": rung["channel"],
                    "k": int(k),
                    "n": int(n),
                    "a_priori_alphabet_m": upper["a_priori_alphabet_m"],
                    "compression_factor_design_time": float(COMPRESSION_FACTORS[r]),
                    "channel_tv_design_time": quantile_summary(cached["channel_tvs"]),
                    "eps_lo_classifier": quantile_summary(clf_values),
                    "eps_lo_divisibility": quantile_summary(div_values),
                    "eps_lo_classifier_gt_0.05_fraction": float(np.mean(np.asarray(clf_values) > LOWER_THRESHOLD)),
                    "eps_lo_divisibility_gt_0.05_fraction": float(np.mean(np.asarray(div_values) > LOWER_THRESHOLD)),
                    "joint_classifier": float(np.mean(joint_clf)),
                    "joint_divisibility": float(np.mean(joint_div)),
                    "upper": upper,
                    "classifier_vacuous": {
                        "value_is_zero": True,
                        "pair_count": len(cached["classifier_vacuous"]),
                        "pair_indices": cached["classifier_vacuous"],
                    },
                    "divisibility_vacuous": {
                        "value_is_zero": True,
                        "pair_count": len(cached["divisibility_vacuous"]),
                        "pair_indices": cached["divisibility_vacuous"],
                    },
                    "lower_bound_guarantees": {
                        "classifier": "asymptotic Michel et al. HPLB; not an exact finite-sample certificate",
                        "divisibility": (
                            "finite-sample held-out Clopper-Pearson witness conditional on the learned test and iid samples, "
                            "but assumption-laden under realizability and not distribution-free"
                        ),
                    },
                    "realizability_assumption_applies_to": "divisibility",
                    "same_cells_used_by_both_routes": True,
                }
                per_rung_per_k.append(row)
                winner = route_comparison(clf_values, div_values)
                winner.update({"M": M, "rung": r, "k": int(k), "n": int(n)})
                when_each_wins.append(winner)
                if cached["divisibility_vacuous"]:
                    vacuous_cells.append(
                        {
                            "M": M,
                            "rung": r,
                            "k": int(k),
                            "n": int(n),
                            "route": "divisibility",
                            "value": 0.0,
                            "vacuous_pair_count": len(cached["divisibility_vacuous"]),
                            "vacuous_pair_fraction": float(len(cached["divisibility_vacuous"]) / len(div_values)),
                            "vacuous_pair_indices": cached["divisibility_vacuous"],
                        }
                    )

                distributions.append(
                    {
                        "M": M,
                        "rung": r,
                        "k": int(k),
                        "n": int(n),
                        "classifier": {
                            "eps_lo": quantile_summary(clf_values),
                            "fraction_exceeding_0.05": float(np.mean(np.asarray(clf_values) > LOWER_THRESHOLD)),
                            "vacuous_pair_count": len(cached["classifier_vacuous"]),
                            "vacuous_pair_fraction": float(len(cached["classifier_vacuous"]) / len(clf_values)),
                            "vacuous_pair_indices": cached["classifier_vacuous"],
                            "raw_bound": quantile_summary(cached["classifier_raw_values"]),
                            "guarantee_type": "asymptotic Michel et al. HPLB; not an exact finite-sample certificate",
                        },
                        "divisibility": {
                            "eps_lo": quantile_summary(div_values),
                            "fraction_exceeding_0.05": float(np.mean(np.asarray(div_values) > LOWER_THRESHOLD)),
                            "vacuous_pair_count": len(cached["divisibility_vacuous"]),
                            "vacuous_pair_fraction": float(len(cached["divisibility_vacuous"]) / len(div_values)),
                            "vacuous_pair_indices": cached["divisibility_vacuous"],
                            "raw_bound": quantile_summary(cached["divisibility_raw_values"]),
                            "guarantee_type": (
                                "finite-sample held-out Clopper-Pearson witness conditional on the learned test and iid samples; "
                                "requires realizability and is not distribution-free"
                            ),
                            "realizability_assumption": (
                                "The selected classifier family must contain, or sufficiently approximate, a useful binary rejection test "
                                "for the pair; this assumption is required for interpreting the divisibility route and is not distribution-free."
                            ),
                        },
                        "upper": upper,
                        "joint_classifier": float(np.mean(joint_clf)),
                        "joint_divisibility": float(np.mean(joint_div)),
                    }
                )

    decisive: list[dict[str, Any]] = []
    for n in SAMPLE_SIZES:
        Tn = threshold(n)
        for M in (1, 2):
            r = next(int(item["rung"]) for item in RUNG_DEFS if int(item["M"]) == M)
            row = next(item for item in per_rung_per_k if item["n"] == n and item["M"] == M and item["k"] == 5)
            comp = float(COMPRESSION_FACTORS[r])
            decisive.append(
                {
                    "n": n,
                    "M": M,
                    "k": 5,
                    "T_n": Tn,
                    "compression_factor_design_time": comp,
                    "compression_exceeds_T_n": bool(comp > Tn),
                    "classifier_median": row["eps_lo_classifier"]["median"],
                    "divisibility_median": row["eps_lo_divisibility"]["median"],
                    "classifier_median_crosses_0.05": bool(row["eps_lo_classifier"]["median"] > LOWER_THRESHOLD),
                    "divisibility_median_crosses_0.05": bool(row["eps_lo_divisibility"]["median"] > LOWER_THRESHOLD),
                    "verdict": (
                        "M=1 lower-side INFEASIBLE because compression_factor <= T(n)"
                        if M == 1 and comp <= Tn
                        else "M=2 lower-side arithmetic-feasible, but neither route median crosses 0.05"
                    ),
                }
            )

    compression_rows = []
    for rung in RUNG_DEFS:
        r = int(rung["rung"])
        factor = float(COMPRESSION_FACTORS[r])
        ratios = [
            float(pair_data[(n, r, pair_index)]["known_true_channel_tv"] / pair_data[(n, r, pair_index)]["latent_tv"])
            for n in SAMPLE_SIZES
            for pair_index in range(len(LATENT_TV_VALUES))
            if pair_data[(n, r, pair_index)]["latent_tv"] > 0
        ]
        compression_rows.append(
            {
                "M": int(rung["M"]),
                "rung": r,
                "channel": rung["channel"],
                "design_time_registered_factor": factor,
                "implied_ratio_from_known_cells": quantile_summary(ratios),
                "ratios_exactly_equal_registered_factor": bool(all(math.isclose(value, factor, abs_tol=1e-12) for value in ratios)),
                "bounds_feasibility": {
                    str(n): {
                        "T_n": threshold(n),
                        "compression_exceeds_T_n": bool(factor > threshold(n)),
                        "statement": "lower-side reachability requires compression_factor > T(n)",
                    }
                    for n in SAMPLE_SIZES
                },
                "measurement_status": "design-time implied ratio from synthetic known TVs; not an empirical real-traffic measurement",
            }
        )

    median_summary = [
        {
            "M": row["M"],
            "n": row["n"],
            "classifier_median": row["eps_lo_classifier"]["median"],
            "divisibility_median": row["eps_lo_divisibility"]["median"],
            "joint_classifier": row["joint_classifier"],
            "joint_divisibility": row["joint_divisibility"],
        }
        for row in per_rung_per_k
        if row["k"] == 5
    ]

    report: dict[str, Any] = {
        "report_metadata": {
            "generated_at_utc": RUN_TIMESTAMP_UTC,
            "project_root": str(ROOT),
            "calculation_library": "NumPy plus SciPy and the project's own statcore.py/divisibility.py modules",
            "source_reports_read": [
                str(ROOT / "scripts/generate_channel_ladder_report.py"),
                str(ROOT / "artifacts/channel_ladder_report.json"),
                str(ROOT / "artifacts/ladder_rerun_report.json"),
            ],
            "alpha": ALPHA,
            "sample_sizes_per_law": SAMPLE_SIZES,
            "reported_k_values": list(RERUN_K_VALUES),
            "pair_count": len(LATENT_TV_VALUES),
            "run_command": RUN_COMMAND,
        },
        "per_rung_per_k": per_rung_per_k,
        "distributions": distributions,
        "when_each_wins": {
            "rows": when_each_wins,
            "interpretation": (
                "A route is stronger on a row when its lower-bound value is numerically larger on the same sampled cell pair. "
                "The two routes are not expected to be ordered in general."
            ),
        },
        "decisive_M1_M2_k5": {
            "threshold_formula": "T(n) = 0.0500 + 2.254/sqrt(n)",
            "rows": decisive,
            "headline": (
                "At both M=1 and M=2, k=5, and both requested sample sizes, the divisibility median remains below 0.05; "
                "it does not lift M=1 or M=2 across the threshold. M=1 is additionally lower-side infeasible by the compression test."
            ),
        },
        "implied_compression_by_rung": compression_rows,
        "vacuous_cells": vacuous_cells,
        "eps_hi_clipping_policy": {
            "raw_is_authoritative": True,
            "rule": (
                "Never clip eps_hi for arithmetic or certification. Store and print eps_hi_raw, store a separate display-clipped value, "
                "compute floor=max(0,(1-eps_hi_raw)/2), and mark certificate-lost or alphabet-invalid."
            ),
            "raw_above_one_means_certificate_loss_signal": True,
            "realized_support_never_used_for_m": True,
            "a_priori_m_formula": "m=(2M)^k",
        },
        "design_vs_empirical_note": (
            "All rows are design-time synthetic ensemble calculations using known true channel TV values and registered compression factors. "
            "A real-data run must replace known true TV by empirical tv_hat on the fixed pre-registered grid; no row here is an empirical traffic result."
        ),
        "realizability_assumption": (
            "Every divisibility number assumes independent iid samples and that the selected classifier family contains, or sufficiently "
            "approximates, a useful binary rejection test for the pair. The held-out Clopper-Pearson witness is conditional on the learned "
            "classifier; this route is assumption-laden and not distribution-free."
        ),
        "known_limitations": [
            "The synthetic pair law occupies three fixed cells while the upper-side m is the full fixed a-priori grid.",
            "The classifier route is the one-hot Michel construction used by the ladder; the divisibility route receives the identical sampled cell IDs directly.",
            "The classifier lower route is an asymptotic HPLB, not an exact finite-sample certificate.",
            "The divisibility route has a finite-sample held-out binomial construction conditional on the learned test, but requires realizability and is not distribution-free.",
            "The ten pair levels, compression factors, and sample sizes are design-time choices and cannot establish real-corpus pair distributions.",
            "The comparison changes lower-bound tightness, not the verdict form: upper-side feasibility still uses raw eps_hi and the lower-side reachability condition remains compression_factor > T(n).",
        ],
        "blockers": [
            "No real per-service pair distributions were supplied; the report cannot answer the empirical traffic verdict.",
        ],
        "wrap_up": {
            "k5_n3900000_medians_by_rung": median_summary,
            "M1_M2_k5_medians_both_routes": decisive,
            "divisibility_crosses_where_classifier_does_not": [
                {
                    "M": row["M"],
                    "n": row["n"],
                    "classifier_median": row["classifier_median"],
                    "divisibility_median": row["divisibility_median"],
                }
                for row in decisive
                if row["divisibility_median_crosses_0.05"] and not row["classifier_median_crosses_0.05"]
            ],
            "joint_statistics_k5": [
                {
                    "M": row["M"],
                    "n": row["n"],
                    "joint_classifier": row["joint_classifier"],
                    "joint_divisibility": row["joint_divisibility"],
                }
                for row in per_rung_per_k
                if row["k"] == 5
            ],
            "implied_compression": compression_rows,
            "vacuous_cells": vacuous_cells,
        },
    }

    output_lines = [
        "SIDE-BY-SIDE LOWER MEDIAN SUMMARY (k=5, n=3.9e6)",
        "M\tclassifier_median\tdivisibility_median\tjoint_classifier\tjoint_divisibility",
    ]
    for row in per_rung_per_k:
        if row["k"] == 5 and row["n"] == 3_900_000:
            output_lines.append(
                f"{row['M']}\t{row['eps_lo_classifier']['median']:.9f}\t{row['eps_lo_divisibility']['median']:.9f}\t"
                f"{row['joint_classifier']:.3f}\t{row['joint_divisibility']:.3f}"
            )
    output_lines.extend(
        [
            "",
            "DECISIVE M=1/M=2, k=5",
            "n\tM\tT(n)\tclassifier_median\tdivisibility_median\tclassifier_gt_0.05\tdivisibility_gt_0.05\tverdict",
        ]
    )
    for row in decisive:
        output_lines.append(
            f"{row['n']}\t{row['M']}\t{row['T_n']:.9f}\t{row['classifier_median']:.9f}\t{row['divisibility_median']:.9f}\t"
            f"{row['classifier_median_crosses_0.05']}\t{row['divisibility_median_crosses_0.05']}\t{row['verdict']}"
        )
    output_lines.extend(["", "ROUTE WINNER BY CELL (median; all requested n,k)"])
    for row in when_each_wins:
        output_lines.append(
            f"n={row['n']} M={row['M']} k={row['k']} winner={row['winner_by_median']} "
            f"clf_med={row['classifier_median']:.9f} div_med={row['divisibility_median']:.9f} "
            f"div_pairwise_win={row['divisibility_stronger_fraction']:.3f} clf_pairwise_win={row['classifier_stronger_fraction']:.3f}"
        )
    output_lines.extend(["", "JOINT STATISTIC AT k=5"])
    for row in per_rung_per_k:
        if row["k"] == 5:
            output_lines.append(
                f"n={row['n']} M={row['M']} classifier={row['joint_classifier']:.3f} divisibility={row['joint_divisibility']:.3f}"
            )
    output_lines.extend(["", "IMPLIED DESIGN-TIME COMPRESSION"])
    for row in compression_rows:
        output_lines.append(
            f"M={row['M']} factor={row['design_time_registered_factor']:.3f} "
            + " ".join(
                f"T({n})={row['bounds_feasibility'][str(n)]['T_n']:.6f},comp>T={row['bounds_feasibility'][str(n)]['compression_exceeds_T_n']}"
                for n in SAMPLE_SIZES
            )
        )
    output_lines.extend(["", "RAW EPS_HI ABOVE 1 (never clipped for arithmetic)"])
    raw_above_one_rows = [
        row for row in per_rung_per_k if row["upper"]["raw_eps_hi_above_1_count"] > 0
    ]
    for row in raw_above_one_rows:
        output_lines.append(
            f"n={row['n']} M={row['M']} k={row['k']} cell_status={row['upper']['cell_status']} "
            f"raw_eps_hi_spread={row['upper']['eps_hi_raw_spread']} "
            f"floor_from_raw_spread={row['upper']['floor_from_raw_eps_hi_spread']} "
            f"display_clipped_spread={row['upper']['eps_hi_display_clipped_spread']}"
        )
    if not raw_above_one_rows:
        output_lines.append("none")
    output_lines.extend(["", "VACUOUS DIVISIBILITY CELLS (explicit zero rows)"])
    if vacuous_cells:
        for cell in vacuous_cells:
            output_lines.append(
                f"n={cell['n']} M={cell['M']} k={cell['k']} value=0.0 "
                f"pairs={cell['vacuous_pair_count']}/{len(LATENT_TV_VALUES)} indices={cell['vacuous_pair_indices']}"
            )
    else:
        output_lines.append("none")
    output_lines.append("Lower-route comparison changes TIGHTNESS, not the verdict form.")
    run_output = "\n".join(output_lines)
    report["run_output"] = f"{ROOT}\n{run_output}"

    output_path = ROOT / "artifacts/lower_side_comparison_report.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=False, allow_nan=False)
        handle.write("\n")

    print(RUN_COMMAND)
    print(report["run_output"])
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
