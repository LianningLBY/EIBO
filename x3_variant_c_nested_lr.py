#!/usr/bin/env python3
"""X3 variant C: nested IID versus first-order Markov model comparison.

This runner deliberately does not compute or fit the prior D_k growth-rate
quantity. It runs the synthetic discrimination control before loading the
cached real sequences, then writes one new artifact when the control passes.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import time
from pathlib import Path

import numpy as np


PROJECT = Path("/root/eibo")
CACHE_DIR = Path("/dev/shm/eibo_x3_chain_rule")
MERGED_PATH = CACHE_DIR / "merged.pkl"
LEDGER_PATH = CACHE_DIR / "ledger.json"
RESULTS_PATH = CACHE_DIR / "results.pkl"
ARTIFACT_PATH = PROJECT / "artifacts" / "x3_variant_c_nested_lr.json"

SEED = 20260914
SEQUENCE_LENGTH = 30
PREFIX_LENGTHS = tuple(range(2, SEQUENCE_LENGTH + 1))
CONTROL_ITEMS = 12
CONTROL_FLOWS_PER_ITEM = 5000


ROUTE_STATEMENT = (
    "This is a DIFFERENT route from the prior D_k growth-rate claim: it compares nested "
    "first-order Markov and i.i.d. models, and a positive result here does NOT restore, "
    "confirm, or rescue any prior SUBLINEAR verdict."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def cache_inventory() -> dict:
    required = [MERGED_PATH, LEDGER_PATH, RESULTS_PATH]
    part_paths = sorted(CACHE_DIR.glob("part_*.npz"))
    all_cache_files = sorted(path for path in CACHE_DIR.iterdir() if path.is_file()) if CACHE_DIR.exists() else []
    present = all(path.exists() for path in required) and len(part_paths) == 360
    return {
        "present": bool(present),
        "cache_dir": str(CACHE_DIR),
        "required_files": {path.name: path.exists() for path in required},
        "npz_part_count": len(part_paths),
        "file_count": len(all_cache_files),
        "total_bytes": int(sum(path.stat().st_size for path in all_cache_files)),
        "file_bytes": {path.name: int(path.stat().st_size) for path in required if path.exists()},
        "rescan_performed": False,
        "cost_estimate": {
            "basis": "cached merged.pkl only; no H5 read",
            "model_fits_after_control": "service_count * 29 prefix lengths, plus one final k=30 report per service",
            "expected_prefix_lengths": list(PREFIX_LENGTHS),
        },
    }


def log_term(count: int, total: int) -> float:
    if count == 0:
        return 0.0
    return float(count) * math.log(float(count) / float(total))


def fit_nested_models(bits: np.ndarray, prefix_length: int) -> dict:
    """Fit the declared nested pair by exact Bernoulli MLE and return BIC only."""
    prefix = np.asarray(bits[:, :prefix_length], dtype=np.uint8)
    n_sequences = int(prefix.shape[0])
    n_observations = int(prefix.size)
    if n_sequences <= 0 or n_observations <= 0:
        raise ValueError("empty sequence sample")

    iid_ones = int(prefix.sum())
    iid_zeros = n_observations - iid_ones
    iid_log_likelihood = log_term(iid_ones, n_observations) + log_term(iid_zeros, n_observations)

    initial_ones = int(prefix[:, 0].sum())
    initial_zeros = n_sequences - initial_ones
    previous = prefix[:, :-1]
    following = prefix[:, 1:]
    count_00 = int(np.sum((previous == 0) & (following == 0)))
    count_01 = int(np.sum((previous == 0) & (following == 1)))
    count_10 = int(np.sum((previous == 1) & (following == 0)))
    count_11 = int(np.sum((previous == 1) & (following == 1)))
    markov_log_likelihood = (
        log_term(initial_ones, n_sequences)
        + log_term(initial_zeros, n_sequences)
        + log_term(count_01, count_00 + count_01)
        + log_term(count_00, count_00 + count_01)
        + log_term(count_11, count_10 + count_11)
        + log_term(count_10, count_10 + count_11)
    )

    iid_parameters = 1
    markov_parameters = 3
    iid_bic = -2.0 * iid_log_likelihood + iid_parameters * math.log(n_observations)
    markov_bic = -2.0 * markov_log_likelihood + markov_parameters * math.log(n_observations)
    delta_bic = iid_bic - markov_bic
    if delta_bic > 0.0:
        winner = "MARKOV"
    elif delta_bic < 0.0:
        winner = "IID"
    else:
        winner = "TIE"
    return {
        "prefix_length": int(prefix_length),
        "n_sequences": n_sequences,
        "n_observations": n_observations,
        "bic_iid": float(iid_bic),
        "bic_markov": float(markov_bic),
        "delta_bic_iid_minus_markov": float(delta_bic),
        "winner": winner,
    }


def summarize_item_rows(rows: list[dict]) -> dict:
    deltas = np.asarray([row["delta_bic_iid_minus_markov"] for row in rows], dtype=float)
    winners = [row["winner"] for row in rows]
    return {
        "n_items": len(rows),
        "markov_favours": int(sum(winner == "MARKOV" for winner in winners)),
        "iid_favours": int(sum(winner == "IID" for winner in winners)),
        "ties": int(sum(winner == "TIE" for winner in winners)),
        "delta_bic_mean": float(np.mean(deltas)) if deltas.size else None,
        "delta_bic_median": float(np.median(deltas)) if deltas.size else None,
        "delta_bic_min": float(np.min(deltas)) if deltas.size else None,
        "delta_bic_max": float(np.max(deltas)) if deltas.size else None,
    }


def position_rows(items: list[tuple[str, np.ndarray]], prefix_length: int) -> list[dict]:
    rows = []
    for item_id, bits in items:
        fit = fit_nested_models(bits, prefix_length)
        fit["item"] = item_id
        rows.append(fit)
    return rows


def synthetic_iid_case(rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    probabilities = np.linspace(0.20, 0.80, CONTROL_ITEMS)
    return [
        (
            f"iid_{index:02d}",
            (rng.random((CONTROL_FLOWS_PER_ITEM, SEQUENCE_LENGTH)) < probability).astype(np.uint8),
        )
        for index, probability in enumerate(probabilities)
    ]


def stationary_probability_one(p01: float, p11: float) -> float:
    return p01 / (1.0 - p11 + p01)


def synthetic_dependent_case(rng: np.random.Generator) -> list[tuple[str, np.ndarray]]:
    transition_pairs = [(0.10, 0.90), (0.12, 0.88), (0.15, 0.85), (0.18, 0.82)] * 3
    items = []
    for index, (p01, p11) in enumerate(transition_pairs):
        bits = np.empty((CONTROL_FLOWS_PER_ITEM, SEQUENCE_LENGTH), dtype=np.uint8)
        initial_probability = stationary_probability_one(p01, p11)
        bits[:, 0] = (rng.random(CONTROL_FLOWS_PER_ITEM) < initial_probability).astype(np.uint8)
        for position in range(1, SEQUENCE_LENGTH):
            probability = np.where(bits[:, position - 1] == 1, p11, p01)
            bits[:, position] = (rng.random(CONTROL_FLOWS_PER_ITEM) < probability).astype(np.uint8)
        items.append((f"dependent_{index:02d}", bits))
    return items


def control_case_report(items: list[tuple[str, np.ndarray]], case_name: str) -> dict:
    final_rows = position_rows(items, SEQUENCE_LENGTH)
    position_reports = []
    for prefix_length in PREFIX_LENGTHS:
        rows = position_rows(items, prefix_length)
        summary = summarize_item_rows(rows)
        summary["prefix_length"] = int(prefix_length)
        summary["items"] = rows
        position_reports.append(summary)
    final_summary = summarize_item_rows(final_rows)
    return {
        "case": case_name,
        "truth": "i.i.d. Bernoulli sequences" if case_name == "iid_control" else "first-order dependent binary Markov sequences",
        "items": final_rows,
        "final_prefix_summary": final_summary,
        "per_position": position_reports,
    }


def control_is_usable(iid_report: dict, dependent_report: dict) -> bool:
    iid_summary = iid_report["final_prefix_summary"]
    dependent_summary = dependent_report["final_prefix_summary"]
    iid_majority_rejects_markov = iid_summary["markov_favours"] < iid_summary["n_items"] / 2.0
    dependent_majority_selects_markov = dependent_summary["markov_favours"] > dependent_summary["n_items"] / 2.0
    iid_median_nonpositive = iid_summary["delta_bic_median"] <= 0.0
    dependent_median_positive = dependent_summary["delta_bic_median"] > 0.0
    return bool(
        iid_majority_rejects_markov
        and dependent_majority_selects_markov
        and iid_median_nonpositive
        and dependent_median_positive
    )


def direction_bits_from_codes(codes: np.ndarray, lens: np.ndarray) -> np.ndarray:
    usable = np.asarray(lens) >= SEQUENCE_LENGTH
    selected = np.asarray(codes, dtype=np.uint32)[usable]
    bits = np.empty((selected.shape[0], SEQUENCE_LENGTH), dtype=np.uint8)
    for position in range(SEQUENCE_LENGTH):
        bits[:, position] = ((selected >> np.uint32(29 - position)) & np.uint32(1)).astype(np.uint8)
    return bits


def real_data_report(merged: dict) -> dict:
    services = [int(service) for service in merged["services"]]
    items = []
    for service in services:
        entry = merged["by_service"][service]
        bits = direction_bits_from_codes(entry["codes"], entry["lens"])
        items.append((str(service), bits))

    final_rows = position_rows(items, SEQUENCE_LENGTH)
    for row in final_rows:
        row["service"] = int(row.pop("item"))
    final_summary = summarize_item_rows(final_rows)
    per_position = []
    for prefix_length in PREFIX_LENGTHS:
        rows = position_rows(items, prefix_length)
        for row in rows:
            row["service"] = int(row.pop("item"))
        summary = summarize_item_rows(rows)
        summary["prefix_length"] = int(prefix_length)
        summary["items"] = rows
        per_position.append(summary)

    return {
        "observable": "first 30 PPI direction bits for every cached flow with PPI_LEN >= 30",
        "service_count": len(items),
        "final_prefix_length": SEQUENCE_LENGTH,
        "items_at_k30": final_rows,
        "final_summary_at_k30": final_summary,
        "per_position": per_position,
    }


def main() -> int:
    started = time.time()
    inventory = cache_inventory()
    if not inventory["present"]:
        payload = {
            "route_statement": ROUTE_STATEMENT,
            "models": models_spec(),
            "known_truth_control": {},
            "control_outcome": "NOT_USABLE",
            "if_not_usable": "The required cached state is absent or incomplete; real data was NOT touched.",
            "execution": {"cache": inventory, "real_data_touched": False},
        }
        atomic_write_json(ARTIFACT_PATH, payload)
        print(json.dumps({"control_outcome": "NOT_USABLE", "cache": inventory}, sort_keys=True))
        return 2

    control_rng = np.random.default_rng(SEED)
    iid_report = control_case_report(synthetic_iid_case(control_rng), "iid_control")
    dependent_report = control_case_report(synthetic_dependent_case(control_rng), "dependent_control")
    usable = control_is_usable(iid_report, dependent_report)
    control_payload = {
        "seed": SEED,
        "items_per_case": CONTROL_ITEMS,
        "flows_per_item": CONTROL_FLOWS_PER_ITEM,
        "sequence_length": SEQUENCE_LENGTH,
        "decision_rule": {
            "iid_case": "strict majority of items must not favour Markov and median Delta_BIC must be <= 0",
            "dependent_case": "strict majority of items must favour Markov and median Delta_BIC must be > 0",
            "control_outcome": "USABLE iff both case rules hold",
        },
        "iid_control": iid_report,
        "dependent_control": dependent_report,
    }
    print(json.dumps({
        "stage": "known_truth_control",
        "control_outcome": "USABLE" if usable else "NOT_USABLE",
        "iid_final_summary": iid_report["final_prefix_summary"],
        "dependent_final_summary": dependent_report["final_prefix_summary"],
    }, sort_keys=True))

    if not usable:
        payload = {
            "route_statement": ROUTE_STATEMENT,
            "models": models_spec(),
            "known_truth_control": control_payload,
            "control_outcome": "NOT_USABLE",
            "if_not_usable": "The nested-model comparison failed its own known-truth discrimination control; real data was NOT touched.",
            "execution": {
                "cache": inventory,
                "real_data_touched": False,
                "elapsed_seconds": float(time.time() - started),
            },
        }
        atomic_write_json(ARTIFACT_PATH, payload)
        return 3

    with MERGED_PATH.open("rb") as handle:
        merged = pickle.load(handle)
    inventory["cost_estimate"]["cached_service_count"] = int(len(merged["services"]))
    inventory["cost_estimate"]["expected_model_fit_count"] = int(len(merged["services"]) * len(PREFIX_LENGTHS))
    real_report = real_data_report(merged)
    print(json.dumps({
        "stage": "real_data_nested_comparison",
        "final_summary_at_k30": real_report["final_summary_at_k30"],
    }, sort_keys=True))

    payload = {
        "route_statement": ROUTE_STATEMENT,
        "models": models_spec(),
        "known_truth_control": control_payload,
        "control_outcome": "USABLE",
        "real_data_comparison": real_report,
        "if_not_usable": "Not applicable: the known-truth control was usable.",
        "execution": {
            "cache": inventory,
            "real_data_touched": True,
            "merged_keys": list(merged.keys()),
            "cached_service_count": len(merged["services"]),
            "elapsed_seconds": float(time.time() - started),
        },
    }
    atomic_write_json(ARTIFACT_PATH, payload)
    print(json.dumps({
        "stage": "complete",
        "artifact": str(ARTIFACT_PATH),
        "artifact_sha256": sha256_file(ARTIFACT_PATH),
        "artifact_bytes": ARTIFACT_PATH.stat().st_size,
    }, sort_keys=True))
    return 0


def models_spec() -> dict:
    return {
        "observable": "Binary direction sequence X_1,...,X_30 from the cached first 30 PPI direction bits; flows are selected by PPI_LEN >= 30.",
        "iid_model": "X_t are independent Bernoulli(p) for all t, with one fitted parameter p.",
        "first_order_markov_model": "X_1 ~ Bernoulli(pi), and X_t | X_{t-1}=r ~ Bernoulli(theta_r) for r in {0,1} and t>=2, with three fitted parameters (pi, theta_0, theta_1).",
        "nested_constraint": "IID is the Markov submodel pi = theta_0 = theta_1 = p.",
        "fit": "Exact maximum likelihood from initial-state and transition counts; no smoothing.",
        "criterion": "BIC = -2 log(L) + d log(N), where N is the number of observed direction bits at the tested prefix length and d is the model parameter count.",
        "comparison": "Delta_BIC = BIC_IID - BIC_Markov; Delta_BIC > 0 favours Markov, Delta_BIC < 0 favours IID, and zero is a tie.",
        "pre_registered_scope": "Per-service at k=30 and per-service at every prefix length k=2..30; no aggregate-only verdict.",
        "pre_registered_control_gate": "USABLE iff the synthetic IID case has a strict majority of items not favouring Markov with median Delta_BIC <= 0, and the synthetic dependent case has a strict majority favouring Markov with median Delta_BIC > 0.",
        "parameter_count_asymmetry": "Markov has two more free parameters than IID; the BIC penalty is included in every reported comparison and raw likelihood advantage is not reported as a result.",
    }


if __name__ == "__main__":
    raise SystemExit(main())
