#!/usr/bin/env python3
"""Compare certification power in a shared-block model and audit two QUIC pilots."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import median

import numpy as np
from scipy.optimize import brentq
from scipy.special import rel_entr
from scipy.stats import binom

import quic_timing_pilot as timing
from eibo.riskcert import joint_radius_from_change_budget


ROOT = Path(__file__).resolve().parents[1]
TIMING_SUMMARY = ROOT / "artifacts/quic_timing_pilot_20261111/summary.json"
XS_RESULT = ROOT / "artifacts/methodology/if_e1_fusion_20261111_184554.json"
TAIL_ALPHA = 0.025
TARGET_POWER = 0.80
GAIN_GRID = (0.01, 0.02, 0.0476)
BLOCK_HOURS = (1, 6, 24, 48)


def binary_kl(p, q):
    return float(rel_entr(p, q) + rel_entr(1 - p, 1 - q))


def binary_power(gains):
    """Find the first n reaching target power, including discrete jumps in power."""
    # At the scan limit, the generic radius plus a lower-tail Hoeffding margin
    # is smaller than the smallest alternative's true gain.
    beta = 1 - TARGET_POWER
    coefficient = math.sqrt(2 * math.log(1 / TAIL_ALPHA)) + math.sqrt(0.5 * math.log(1 / beta))
    units = np.arange(1, math.floor((coefficient / min(gains)) ** 2) + 2)
    generic_radius = joint_radius_from_change_budget(4 / units, alpha=TAIL_ALPHA)
    known_range_radius = joint_radius_from_change_budget(1 / units, alpha=TAIL_ALPHA)
    critical = {
        "exact_binomial": binom.isf(TAIL_ALPHA, units, 0.5).astype(int) + 1,
        "known_range_hoeffding": np.floor(units * (0.5 + known_range_radius)).astype(int) + 1,
        "generic_hoeffding": np.floor(units * (0.5 + generic_radius)).astype(int) + 1,
    }
    exact_cut = critical["exact_binomial"]
    exact_size = binom.sf(exact_cut - 1, units, 0.5)
    if not (np.all(exact_size <= TAIL_ALPHA)
            and np.all(binom.sf(exact_cut - 2, units, 0.5) > TAIL_ALPHA)):
        raise RuntimeError("the binomial quantile failed the exact size check")
    # The likelihood ratio is increasing in the success count. Filling the
    # unused null budget at the boundary gives the most powerful size-alpha test.
    boundary_probability = (TAIL_ALPHA - exact_size) / binom.pmf(exact_cut - 1, units, 0.5)
    results = []
    for gain in gains:
        p = 0.5 + gain
        necessity = math.ceil(binary_kl(TARGET_POWER, TAIL_ALPHA) / binary_kl(p, 0.5))
        optimal_power = (binom.sf(exact_cut - 1, units, p)
                         + boundary_probability * binom.pmf(exact_cut - 1, units, p))
        optimal_first = int(np.flatnonzero(optimal_power >= TARGET_POWER)[0])
        benchmarks = {}
        for method, cut in critical.items():
            power = binom.sf(cut - 1, units, p)
            first = int(np.flatnonzero(power >= TARGET_POWER)[0])
            benchmarks[method] = {
                "first_units_at_target_power": int(units[first]),
                "critical_successes": int(cut[first]),
                "null_rejection_probability": float(binom.sf(cut[first] - 1, units[first], 0.5)),
                "alternative_rejection_probability": float(power[first]),
            }
        results.append({
            "bayes_gain": gain,
            "kl_necessary_units": necessity,
            "neyman_pearson_minimum_units": int(units[optimal_first]),
            "neyman_pearson_power_at_minimum": float(optimal_power[optimal_first]),
            "benchmarks": benchmarks,
        })
    return results


def null_replay_probability(observed_correct_mass, null_budget):
    """Maximize replay probability in the clean-or-all-mutable-wrong null family."""
    positive = observed_correct_mass[observed_correct_mass > 0]
    if not 0 < null_budget < positive.sum():
        raise ValueError("the shock construction requires a positive gap and a reachable null")
    level = brentq(lambda value: np.minimum(positive, value).sum() - null_budget,
                   0, float(positive.max()), xtol=1e-15)
    clean_probabilities = np.minimum(1, level / positive)
    if not np.isclose(positive @ clean_probabilities, null_budget, rtol=0, atol=1e-12):
        raise RuntimeError("the constructed law must have zero conditional gain")
    return float(np.prod(clean_probabilities)), int(np.count_nonzero(clean_probabilities < 1))


def timing_audit(prefix_dir):
    """Reconstruct the archived timing pilot and condition on its coarse inputs."""
    summary = json.loads(TIMING_SUMMARY.read_text())
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    offsets = timing.archive_members(prefix_dir / "quic22-tail.bin")
    days = {}
    for date, manifest in summary["files"].items():
        data, observed = timing.read_day(prefix_dir / f"{date}.prefix", date, encoder, offsets)
        if observed != manifest:
            raise ValueError(f"archive segment does not match the timing pilot: {date}")
        days[date] = data
    classes = np.asarray(summary["classes_in_count_order"])
    priors = np.asarray(summary["priors"])
    fit = timing.combine([days[date] for date in summary["fit_dates"]], classes)
    coarse, fused, fit_counts = timing.fit_rules(*fit[:3], priors, encoder.alphabet)
    if fit_counts.tolist() != summary["fit_counts"]:
        raise ValueError("timing fit counts do not match the archived pilot")

    archived = summary["results"]["all"]
    data = timing.combine([days[date] for date in archived["dates"]], classes)
    original = timing.assess(data, priors, encoder.alphabet, coarse, fused)
    y, x, z, hour = data
    weights = (priors / np.bincount(y))[y]
    correct_by_timing = fused.reshape(-1, timing.TIMING_BINS)[x] == y[:, None]
    always_correct = correct_by_timing.all(axis=1)
    mutable = correct_by_timing.any(axis=1) & ~always_correct
    mutable_correct = weights * mutable * (fused[z] == y)
    null_budget = original["coarse_ceiling"] - float(weights[always_correct].sum())
    gap = float(mutable_correct.sum()) - null_budget
    if not (np.isclose(gap, original["fused_minus_coarse_sample_optimum"], rtol=0, atol=1e-12)
            and np.isclose(gap, archived["fused_minus_coarse_sample_optimum"], rtol=0, atol=1e-12)):
        raise RuntimeError("the conditional decomposition did not reproduce the archived witness")

    blocks = {}
    for hours in BLOCK_HOURS:
        key = f"{hours}h"
        _, index = np.unique(hour // hours, return_inverse=True)
        changes = np.bincount(index, weights=weights * mutable)
        observed_correct = np.bincount(index, weights=mutable_correct)
        squared_changes = float(changes @ changes)
        radius = float(joint_radius_from_change_budget([squared_changes], alpha=timing.ALPHA)[0])
        historical = original["bounds"][key]["radius"]
        if not np.isclose(historical, archived["bounds"][key]["radius"], rtol=0, atol=1e-12):
            raise RuntimeError(f"could not reproduce the archived timing radius for {key}")
        replay, affected = null_replay_probability(observed_correct, null_budget)
        blocks[key] = {
            "units": len(changes),
            "historical_effective_units": original["bounds"][key]["effective_blocks"],
            "historical_hoeffding_radius": historical,
            "conditional_hoeffding_radius": radius,
            "conditional_hoeffding_lower": gap - radius,
            "zero_gain_model_replay_probability": replay,
            "units_with_positive_shock_probability": affected,
            "rules_out_deterministic_positive_lower_at_timing_alpha": replay > timing.ALPHA,
        }
    return {
        "target": "Frozen timing rule versus optimal coarse rule, conditional on holdout coarse inputs and labels",
        "conditional_assumption": "Independent blocks; arbitrary within-block timing dependence and heterogeneous block laws",
        "source_summary_sha256": hashlib.sha256(TIMING_SUMMARY.read_bytes()).hexdigest(),
        "pointwise_alpha": timing.ALPHA,
        "holdout_flows": len(y),
        "sample_bayes_ceiling_gain": original["sample_ceiling_gain"],
        "frozen_rule_minus_sample_coarse_optimum": gap,
        "mutable_weight": float(weights[mutable].sum()),
        "observed_mutable_correct_weight": float(mutable_correct.sum()),
        "blocks": blocks,
    }


def xs_audit(path):
    """Summarize recorded pairwise witnesses and effective block counts at B=8."""
    source = path.read_bytes()
    discovery = json.loads(source)
    windows = {}
    for window in ("certificate", "evaluation"):
        rows = [pair["budgets"]["8"]["holdouts"][window] for pair in discovery["pairs"]]
        windows[window] = {}
        for scenario in ("iid_flow", "start_24h", "span_merged_24h"):
            bounds = [row["bounds"][scenario] for row in rows]
            panel = [bound["simultaneous_panel"] for bound in bounds]
            windows[window][scenario] = {
                "pairs": len(rows),
                "median_effective_units": median(bound["effective_blocks"] for bound in bounds),
                "median_radius": median(bound["radius"] for bound in panel),
                "positive_late_bayes_gain_lower_bounds": sum(
                    bound["bayes_gain_lower_vs_best_single"]["late"] > 0 for bound in panel),
                "late_tv_upper_equal_to_one": sum(bound["tv_intervals"]["late"][1] == 1 for bound in panel),
            }
    return {
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "budget": 8,
        "simultaneous_panel_alpha": discovery["alpha"],
        "tails_in_panel": discovery["panel_tails_per_scenario"],
        "windows": windows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix-dir", type=Path, default=ROOT / "data/quic_timing_pilot")
    parser.add_argument("--xs-result", type=Path, default=XS_RESULT)
    args = parser.parse_args()
    audited_timing = timing_audit(args.prefix_dir)
    result = {
        "design": "Exploratory fusion certification limits",
        "shared_bit_model": {
            "alpha": TAIL_ALPHA,
            "target_power": TARGET_POWER,
            "null_success_probability": 0.5,
            "alternative": "success probability 0.5 + gain; one predeclared fusion orientation",
            "rows": binary_power((*GAIN_GRID, audited_timing["frozen_rule_minus_sample_coarse_optimum"])),
        },
        "quic22_timing": audited_timing,
        "quicext25_xs": xs_audit(args.xs_result),
    }
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
