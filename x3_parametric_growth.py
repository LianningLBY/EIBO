#!/usr/bin/env python3
"""Fit low-order Markov models and evaluate chain-rule divergence internally."""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
from pathlib import Path

import numpy as np

from x3_controls import fit_growth
from x3_variant_c_nested_lr import CACHE_DIR, SEQUENCE_LENGTH, direction_bits_from_codes


PROJECT = Path("/root/eibo")
MERGED_PATH = CACHE_DIR / "merged.pkl"
ARTIFACT_PATH = PROJECT / "artifacts" / "x3_parametric_growth.json"
RUNNER_PATH = PROJECT / "x3_parametric_growth.py"
SEED = 20260914
ORDERS = (0, 1, 2)
CONTROL_N = 20_000

PREREGISTERED_CONTROL_CRITERION = (
    "The fitted-model route passes its own known-truth control iff a second-order "
    "synthetic source selects order 2 by BIC, the fitted D_k curve has relative RMSE "
    "at most 5% against the exact D_k curve for k=5..30, and both fitted and exact "
    "curves receive the same LINEAR verdict from the repository fit_growth reference. "
    "If this control fails, stop before loading real cached service sequences."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def cache_inventory() -> dict:
    required = [CACHE_DIR / "ledger.json", MERGED_PATH, CACHE_DIR / "results.pkl"]
    parts = sorted(CACHE_DIR.glob("part_*.npz"))
    files = [path for path in CACHE_DIR.iterdir() if path.is_file()]
    services = None
    flows = None
    with MERGED_PATH.open("rb") as handle:
        merged = pickle.load(handle)
    services = len(merged["services"])
    flows = int(sum(np.sum(np.asarray(merged["by_service"][int(s)]["lens"]) >= 30) for s in merged["services"]))
    return {
        "present": bool(all(path.is_file() for path in required) and len(parts) == 360),
        "cache_dir": str(CACHE_DIR),
        "required_files": {path.name: path.is_file() for path in required},
        "npz_part_count": len(parts),
        "file_count": len(files),
        "total_bytes": int(sum(path.stat().st_size for path in files)),
        "cached_service_count": services,
        "cached_usable_flow_count": flows,
        "h5_rescan": False,
    }


def entropy(probabilities: np.ndarray) -> float:
    values = np.asarray(probabilities, dtype=float)
    values = values[values > 0.0]
    return float(-np.sum(values * np.log(values)))


def context_index(bits: np.ndarray) -> int:
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def fit_markov(bits: np.ndarray, order: int) -> dict:
    bits = np.asarray(bits, dtype=np.uint8)
    n_sequences, length = bits.shape
    if order == 0:
        p = float(bits.mean())
        log_likelihood = 0.0
        ones = int(bits.sum())
        zeros = int(bits.size - ones)
        if ones:
            log_likelihood += ones * math.log(ones / bits.size)
        if zeros:
            log_likelihood += zeros * math.log(zeros / bits.size)
        return {"order": 0, "initial": np.asarray([1.0]), "transition": None, "log_likelihood": log_likelihood, "parameters": 1, "p": p}
    initial_size = 1 << order
    weights = (1 << np.arange(order - 1, -1, -1, dtype=np.uint8)).astype(np.uint8)
    initial_codes = (bits[:, :order] * weights).sum(axis=1).astype(np.int64)
    initial_counts = np.bincount(initial_codes, minlength=initial_size).astype(np.int64)
    transition_counts = np.zeros((initial_size, 2), dtype=np.int64)
    for position in range(order, length):
        contexts = (bits[:, position - order:position] * weights).sum(axis=1).astype(np.int64)
        joint_codes = contexts * 2 + bits[:, position].astype(np.int64)
        counts = np.bincount(joint_codes, minlength=initial_size * 2)
        transition_counts += counts.reshape(initial_size, 2)
    initial = initial_counts / initial_counts.sum()
    transition = np.zeros_like(transition_counts, dtype=float)
    for context in range(initial_size):
        total = int(transition_counts[context].sum())
        if total:
            transition[context] = transition_counts[context] / total
    log_likelihood = entropy(initial) * -n_sequences
    for context in range(initial_size):
        total = int(transition_counts[context].sum())
        if total:
            log_likelihood += -total * entropy(transition[context])
    parameters = initial_size - 1 + initial_size
    return {
        "order": order,
        "initial": initial,
        "transition": transition,
        "log_likelihood": float(log_likelihood),
        "parameters": parameters,
    }


def bic(model: dict, n_observations: int) -> float:
    return float(-2.0 * model["log_likelihood"] + model["parameters"] * math.log(n_observations))


def marginal_and_entropy_curve(model: dict, max_length: int) -> list[dict]:
    order = int(model["order"])
    if order == 0:
        p = float(model["p"])
        h = -(p * math.log(p) if p else 0.0) - ((1 - p) * math.log(1 - p) if p < 1 else 0.0)
        return [{"k": k, "D_k": 0.0} for k in range(1, max_length + 1)]

    state = np.asarray(model["initial"], dtype=float)
    transition = np.asarray(model["transition"], dtype=float)
    marginals = []
    for position in range(order):
        q = sum(state[context] for context in range(len(state)) if ((context >> (order - 1 - position)) & 1))
        marginals.append(float(q))
    joint_entropy = entropy(state)
    curves = []
    for k in range(1, max_length + 1):
        if k > order:
            joint_entropy += float(np.dot(state, np.asarray([entropy(row) for row in transition])))
            next_state = np.zeros_like(state)
            for context, mass in enumerate(state):
                for bit in (0, 1):
                    next_context = ((context << 1) & (len(state) - 1)) | bit
                    next_state[next_context] += mass * transition[context, bit]
            state = next_state
            marginals.append(float(sum(state[context] for context in range(len(state)) if context & 1)))
        cross_entropy = 0.0
        for q in marginals[:k]:
            cross_entropy += -(q * math.log(q) if q else 0.0) - ((1 - q) * math.log(1 - q) if q < 1 else 0.0)
        curves.append({"k": k, "D_k": float(cross_entropy - joint_entropy)})
    return curves


def select_model(bits: np.ndarray) -> tuple[dict, list[dict]]:
    fits = []
    for order in ORDERS:
        model = fit_markov(bits, order)
        fits.append({"order": order, "bic": bic(model, bits.size)})
    selected_order = min(fits, key=lambda row: row["bic"])["order"]
    return fit_markov(bits, selected_order), fits


def curve_rows(curve: list[dict]) -> list[dict]:
    return [{"k": int(row["k"]), "D_k_median": float(row["D_k"])} for row in curve if row["k"] >= 5]


def generate_second_order_control(rng: np.random.Generator) -> tuple[np.ndarray, dict]:
    transition = np.asarray([[0.08, 0.92], [0.72, 0.28], [0.22, 0.78], [0.90, 0.10]], dtype=float)
    bits = np.empty((CONTROL_N, SEQUENCE_LENGTH), dtype=np.uint8)
    bits[:, :2] = (rng.random((CONTROL_N, 2)) < 0.5).astype(np.uint8)
    for position in range(2, SEQUENCE_LENGTH):
        contexts = bits[:, position - 2] * 2 + bits[:, position - 1]
        bits[:, position] = (rng.random(CONTROL_N) < transition[contexts, 1]).astype(np.uint8)
    true_model = {
        "order": 2,
        "initial": np.asarray([0.25, 0.25, 0.25, 0.25]),
        "transition": transition,
    }
    return bits, true_model


def control_report() -> dict:
    rng = np.random.default_rng(SEED)
    bits, true_model = generate_second_order_control(rng)
    fitted, bic_rows = select_model(bits)
    exact_curve = marginal_and_entropy_curve(true_model, SEQUENCE_LENGTH)
    fitted_curve = marginal_and_entropy_curve(fitted, SEQUENCE_LENGTH)
    exact_rows = curve_rows(exact_curve)
    fitted_rows = curve_rows(fitted_curve)
    exact_fit = fit_growth(exact_rows)
    fitted_fit = fit_growth(fitted_rows)
    truth = np.asarray([row["D_k_median"] for row in exact_rows])
    estimate = np.asarray([row["D_k_median"] for row in fitted_rows])
    relative_rmse = float(np.sqrt(np.mean((estimate - truth) ** 2)) / np.mean(truth))
    passed = bool(
        fitted["order"] == 2
        and relative_rmse <= 0.05
        and exact_fit["verdict"] == "LINEAR"
        and fitted_fit["verdict"] == exact_fit["verdict"]
    )
    return {
        "criterion_verbatim": PREREGISTERED_CONTROL_CRITERION,
        "source": "synthetic second-order binary Markov chain with known transition table",
        "n_sequences": CONTROL_N,
        "sequence_length": SEQUENCE_LENGTH,
        "known_transition_probability_one_by_context_00_01_10_11": [0.08, 0.72, 0.22, 0.90],
        "bic_candidates": bic_rows,
        "selected_order": int(fitted["order"]),
        "relative_rmse_k5_to_k30": relative_rmse,
        "exact_growth_fit": exact_fit,
        "fitted_growth_fit": fitted_fit,
        "exact_curve": exact_rows,
        "fitted_curve": fitted_rows,
        "passed": passed,
    }


def real_report(merged: dict) -> dict:
    service_rows = []
    curves = []
    for service in map(int, merged["services"]):
        entry = merged["by_service"][service]
        bits = direction_bits_from_codes(entry["codes"], entry["lens"])
        model, candidates = select_model(bits)
        curve = marginal_and_entropy_curve(model, SEQUENCE_LENGTH)
        rows = curve_rows(curve)
        growth = fit_growth(rows)
        service_rows.append({"service": service, "selected_order": int(model["order"]), "bic_candidates": candidates, "growth_fit": growth})
        curves.append(np.asarray([row["D_k_median"] for row in rows], dtype=float))
    matrix = np.vstack(curves)
    median_curve = [{"k": k, "D_k_median": float(np.median(matrix[:, index]))} for index, k in enumerate(range(5, SEQUENCE_LENGTH + 1))]
    return {
        "service_count": len(service_rows),
        "selected_order_counts": {str(order): int(sum(row["selected_order"] == order for row in service_rows)) for order in ORDERS},
        "median_curve": median_curve,
        "median_growth_fit": fit_growth(median_curve),
        "per_service": service_rows,
    }


def main() -> int:
    inventory = cache_inventory()
    if not inventory["present"]:
        raise RuntimeError("cached state incomplete at /dev/shm/eibo_x3_chain_rule; refusing to rescan the H5")
    print(json.dumps({
        "stage": "cost_estimate",
        "cache": inventory,
        "estimated_work": "one synthetic control with 3 candidate fits, then at most 45 services x 3 candidate fits and 26 D_k points per selected model",
        "cpu_only": True,
    }, sort_keys=True))
    control = control_report()
    print(json.dumps({"stage": "known_truth_control", "passed": control["passed"], "selected_order": control["selected_order"], "relative_rmse_k5_to_k30": control["relative_rmse_k5_to_k30"], "exact_verdict": control["exact_growth_fit"]["verdict"], "fitted_verdict": control["fitted_growth_fit"]["verdict"]}, sort_keys=True))
    payload = {
        "preregistration": {"control_criterion_verbatim": PREREGISTERED_CONTROL_CRITERION, "written_before_measurement": True},
        "method": {
            "route": "Fit order 0, 1, and 2 Markov models by BIC; compute D_k exactly under the selected fitted model against its own position-wise marginal product.",
            "occupancy_bypass": "All conditional probabilities come from fitted low-order contexts; no empirical k-prefix occupancy table is used.",
            "growth_reference": "/root/eibo/x3_controls.py:fit_growth",
        },
        "cost_basis": inventory,
        "known_truth_control": control,
        "execution": {"cache_reused": True, "h5_rescan": False, "real_data_touched": False, "x12_touched": False},
    }
    if not control["passed"]:
        payload["outcome"] = "STOPPED_CONTROL_FAILED"
        payload["plain_statement"] = "The fitted-model route was not run on real data because its preregistered known-truth control failed."
    else:
        real = real_report(pickle.load(MERGED_PATH.open("rb")))
        payload["real_data"] = real
        payload["execution"]["real_data_touched"] = True
        verdict = real["median_growth_fit"]["verdict"]
        payload["outcome"] = verdict
        payload["plain_statement"] = (
            "The question is adjudicable by the fitted-model route; the plug-in estimator limitation must be narrowed to the plug-in estimator only."
            if verdict == "LINEAR"
            else "The fitted-model route did not return LINEAR; the existing cannot-adjudicate wording may stand."
        )
    atomic_write_json(ARTIFACT_PATH, payload)
    print(json.dumps({"artifact": str(ARTIFACT_PATH), "artifact_bytes": ARTIFACT_PATH.stat().st_size, "artifact_sha256": sha256_file(ARTIFACT_PATH), "runner": str(RUNNER_PATH), "runner_sha256": sha256_file(RUNNER_PATH), "outcome": payload["outcome"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
