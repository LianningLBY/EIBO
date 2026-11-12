#!/usr/bin/env python3
"""Compare frozen rules and class priors on both registered XS holdouts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp

import quic_timing_pilot as timing
import quic_timing_pilot_h5 as h5_pilot
from eibo.realdata import DAY, FlowSource, chronological_windows, utc
from if_e1_fusion_validate import file_state, write_json
from quic_timing_cell_certificate import ALPHA, ROUNDING_SECONDS, evaluate_frozen_cohort, print_block_results
from quic_timing_temporal_check import REFERENCE, check_windows, frozen_models


RIDGE = 0.001


def fit_additive_rule(pilot, classes, priors, alphabet, fallback):
    apps, _, fine, _, _ = pilot
    keep = np.isin(apps, classes)
    labels = np.searchsorted(classes, apps[keep])
    bins = timing.TIMING_BINS
    counts = timing.hist(labels, fine[keep], len(classes), alphabet * bins)
    mass = counts * (priors / counts.sum(axis=1))[:, None]
    mass = mass.T.reshape(alphabet, bins, len(classes))
    observed = np.flatnonzero(mass.sum(axis=(1, 2)))
    mass = mass[observed]
    symbol_mass = mass.sum(axis=2, keepdims=True)
    num_coarse = len(observed)
    shape = (num_coarse + bins, len(classes))

    def loss_and_gradient(flat):
        coefficients = flat.reshape(shape)
        logits = coefficients[:num_coarse, None, :] + coefficients[None, num_coarse:, :]
        log_prob = logits - logsumexp(logits, axis=2, keepdims=True)
        loss = -(mass * log_prob).sum() + 0.5 * RIDGE * (flat @ flat)
        residual = np.exp(log_prob) * symbol_mass - mass
        gradient = np.concatenate((residual.sum(axis=1), residual.sum(axis=0)), axis=0)
        return loss, gradient.ravel() + RIDGE * flat

    fit = minimize(loss_and_gradient, np.zeros(np.prod(shape)), jac=True, method="L-BFGS-B",
                   options={"maxiter": 500, "ftol": 1e-11, "gtol": 1e-8})
    if not fit.success:
        raise RuntimeError(f"the additive multinomial fit failed: {fit.message}")
    coefficients = fit.x.reshape(shape)
    logits = coefficients[:num_coarse, None, :] + coefficients[None, num_coarse:, :]
    rule = fallback.reshape(alphabet, bins).copy()
    rule[observed] = logits.argmax(axis=2)
    return rule.ravel(), {"loss": float(fit.fun), "iterations": int(fit.nit),
                          "fitting_coarse_cells": num_coarse}


def check_original_result(baseline, archived):
    for width, row in baseline["results_by_block_width"].items():
        expected = archived["results_by_block_width"][width]
        if row["class_counts"] != expected["class_counts"]:
            raise RuntimeError(f"the {width} holdout counts disagree with the archived sweep")
        for method, result in row["certificate_comparison"].items():
            if not np.isclose(result["lower"], expected["certificate_comparison"][method]["lower"],
                              rtol=0, atol=1e-10):
                raise RuntimeError(f"the {width} {method} bound disagrees with the archived sweep")


def run(args):
    reference_bytes = REFERENCE.read_bytes()
    reference = json.loads(reference_bytes)
    initial = file_state(args.xs_h5)
    digest = h5_pilot.sha256(args.xs_h5)
    if digest != reference["h5_sha256"]:
        raise ValueError(f"the XS H5 does not match the registered sweep: got {digest}")
    encoder = timing.FixedPrefixEncoder(timing.K, 2)
    source = FlowSource(args.xs_h5, args.backend)
    try:
        tables = source.tables()
        split = chronological_windows(tables, end_margin_seconds=ROUNDING_SECONDS)
        check_windows(split, reference)
        windows = {"pilot": split["pilot"], "original": split["evaluation"], "temporal": split["certificate"]}
        periods, rows = h5_pilot.scan(source, tables, windows, encoder, args.chunk_rows, ROUNDING_SECONDS)
    finally:
        source.close()
    if file_state(args.xs_h5) != initial:
        raise RuntimeError("the XS H5 changed during hashing or scanning")
    if any(not data for data in periods.values()):
        raise ValueError("each registered window must contain usable flows")
    pilot = periods.pop("pilot")
    models = frozen_models(pilot, encoder.alphabet, reference)
    cohorts = {}
    for name, (classes, priors, frequency, counts) in models.items():
        additive, fit_info = fit_additive_rule(pilot, classes, priors, encoder.alphabet, frequency)
        root_prior = np.sqrt(counts)
        root_prior /= root_prior.sum()
        scenarios = {
            "frequency_equal": (frequency, priors),
            "additive_logistic_equal": (additive, priors),
            "frequency_sqrt_pilot_prior": (frequency, root_prior),
        }
        holdouts = {}
        for period, data in periods.items():
            _, _, _, first, last = data
            day = (first // DAY).astype(np.int64)
            within_day = last + ROUNDING_SECONDS <= (day + 1) * DAY
            holdouts[period] = {
                label: evaluate_frozen_cohort(data, day, within_day, classes, weights, rule, compare=True)
                for label, (rule, weights) in scenarios.items()
            }
        archived = reference["service_sweep"]["expanded_cohorts"]["all" if name == "44" else name]
        check_original_result(holdouts["original"]["frequency_equal"], archived)
        cohorts[name] = {
            "app_codes": classes.tolist(),
            "pilot_class_counts": counts.tolist(),
            "scenario_priors": {label: weights.tolist() for label, (_, weights) in scenarios.items()},
            "additive_fit": fit_info,
            "fine_rules": {"frequency": frequency.tolist(), "additive_logistic": additive.tolist()},
            "holdouts": holdouts,
        }
    return {
        "source": "CESNET-QUICEXT-25 XS",
        "h5_sha256": digest,
        "reference_sweep_sha256": hashlib.sha256(reference_bytes).hexdigest(),
        "rows_scanned": rows,
        "backend": source.backend,
        "windows_utc": {name: [utc(value) for value in window] for name, window in windows.items()},
        "alpha_per_fixed_bound": ALPHA,
        "block_independence_is_assumed": True,
        "additive_logistic_ridge": RIDGE,
        "cohorts": cohorts,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xs-h5", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists() or args.chunk_rows <= 0:
        parser.error("use a new output path and a positive chunk size")
    result = run(args)
    write_json(args.out, result)
    for name, cohort in result["cohorts"].items():
        for period, scenarios in cohort["holdouts"].items():
            for label, entry in scenarios.items():
                print(f"{name} classes | {period} | {label}")
                print_block_results(entry, compare=True)
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
