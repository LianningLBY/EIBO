#!/usr/bin/env python3
"""Compare global-i.i.d., position-wise i.i.d., and first-order Markov BIC."""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
from pathlib import Path

import numpy as np

from x3_variant_c_nested_lr import (
    CACHE_DIR,
    PREFIX_LENGTHS,
    SEQUENCE_LENGTH,
    direction_bits_from_codes,
    fit_nested_models,
)


PROJECT = Path("/root/eibo")
MERGED_PATH = CACHE_DIR / "merged.pkl"
ARTIFACT_PATH = PROJECT / "artifacts" / "x3_positionwise_iid_null.json"
RUNNER_PATH = PROJECT / "x3_positionwise_null.py"

PREREGISTERED_LICENSING_CRITERION = (
    "The word 'first-order' is licensed iff the position-wise i.i.d. null loses to the "
    "first-order Markov model by BIC for a strict majority of services at k=30 and at "
    "every tested prefix length k=2..30; if the position-wise null wins or ties at any "
    "tested prefix length, the word 'first-order' is not licensed."
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
    return {
        "present": bool(all(path.is_file() for path in required) and len(parts) == 360),
        "cache_dir": str(CACHE_DIR),
        "required_files": {path.name: path.is_file() for path in required},
        "npz_part_count": len(parts),
        "file_count": len(files),
        "total_bytes": int(sum(path.stat().st_size for path in files)),
        "h5_rescan": False,
    }


def positionwise_iid_bic(bits: np.ndarray, prefix_length: int) -> float:
    """BIC for independent positions, using one MLE per position."""
    prefix = np.asarray(bits[:, :prefix_length], dtype=np.uint8)
    n_sequences = int(prefix.shape[0])
    n_observations = int(prefix.size)
    log_likelihood = 0.0
    for position in range(prefix_length):
        ones = int(prefix[:, position].sum())
        zeros = n_sequences - ones
        if ones:
            log_likelihood += ones * math.log(ones / n_sequences)
        if zeros:
            log_likelihood += zeros * math.log(zeros / n_sequences)
    return float(-2.0 * log_likelihood + prefix_length * math.log(n_observations))


def compare(bits: np.ndarray, prefix_length: int) -> dict:
    global_fit = fit_nested_models(bits, prefix_length)
    positionwise_bic = positionwise_iid_bic(bits, prefix_length)
    delta_positionwise_minus_markov = positionwise_bic - global_fit["bic_markov"]
    if delta_positionwise_minus_markov > 0.0:
        winner = "MARKOV"
    elif delta_positionwise_minus_markov < 0.0:
        winner = "POSITIONWISE_IID"
    else:
        winner = "TIE"
    return {
        "prefix_length": int(prefix_length),
        "n_sequences": global_fit["n_sequences"],
        "n_observations": global_fit["n_observations"],
        "bic_global_iid": global_fit["bic_iid"],
        "bic_positionwise_iid": float(positionwise_bic),
        "bic_first_order_markov": global_fit["bic_markov"],
        "delta_bic_global_iid_minus_markov": global_fit["delta_bic_iid_minus_markov"],
        "delta_bic_positionwise_iid_minus_markov": float(delta_positionwise_minus_markov),
        "winner_positionwise_vs_markov": winner,
        "global_iid_winner": global_fit["winner"],
    }


def summarize(rows: list[dict]) -> dict:
    deltas = np.asarray(
        [row["delta_bic_positionwise_iid_minus_markov"] for row in rows], dtype=float
    )
    winners = [row["winner_positionwise_vs_markov"] for row in rows]
    return {
        "n_services": len(rows),
        "markov_favours_over_positionwise_iid": int(sum(x == "MARKOV" for x in winners)),
        "positionwise_iid_favours": int(sum(x == "POSITIONWISE_IID" for x in winners)),
        "ties": int(sum(x == "TIE" for x in winners)),
        "delta_bic_positionwise_minus_markov_mean": float(np.mean(deltas)),
        "delta_bic_positionwise_minus_markov_median": float(np.median(deltas)),
        "delta_bic_positionwise_minus_markov_min": float(np.min(deltas)),
        "delta_bic_positionwise_minus_markov_max": float(np.max(deltas)),
    }


def main() -> int:
    inventory = cache_inventory()
    if not inventory["present"]:
        raise RuntimeError(
            "cached state incomplete at /dev/shm/eibo_x3_chain_rule; refusing to rescan the H5"
        )
    print(json.dumps({"stage": "preregistration", "criterion": PREREGISTERED_LICENSING_CRITERION}))
    with MERGED_PATH.open("rb") as handle:
        merged = pickle.load(handle)

    services = [int(service) for service in merged["services"]]
    rows_by_k = []
    for prefix_length in PREFIX_LENGTHS:
        rows = []
        for service in services:
            entry = merged["by_service"][service]
            bits = direction_bits_from_codes(entry["codes"], entry["lens"])
            row = compare(bits, prefix_length)
            row["service"] = service
            rows.append(row)
        rows_by_k.append({
            "prefix_length": int(prefix_length),
            "summary": summarize(rows),
            "items": rows,
        })

    final = rows_by_k[-1]
    all_k_markov_majority = all(
        item["summary"]["markov_favours_over_positionwise_iid"] > len(services) / 2
        and item["summary"]["positionwise_iid_favours"] == 0
        and item["summary"]["ties"] == 0
        for item in rows_by_k
    )
    first_order_licensed = bool(all_k_markov_majority)
    outcome = (
        "LICENSED: first-order Markov beats the position-wise i.i.d. null at every tested k."
        if first_order_licensed
        else "NOT LICENSED: the position-wise i.i.d. null wins or ties at one or more tested k."
    )
    payload = {
        "preregistration": {
            "criterion_verbatim": PREREGISTERED_LICENSING_CRITERION,
            "written_before_measurement": True,
        },
        "models": {
            "global_iid": "Imported exact fit_nested_models: one Bernoulli p over all positions.",
            "positionwise_iid": "Independent Bernoulli positions with one MLE and one BIC parameter per position.",
            "first_order_markov": "Imported exact fit_nested_models: initial Bernoulli plus two transition rates.",
            "bic_convention": "BIC = -2 log(L) + d log(N), with N equal to all bits in the tested prefix.",
        },
        "outcome": {
            "first_order_licensed": first_order_licensed,
            "plain_statement": outcome,
            "all_prefix_lengths_markov_strictly_beats_positionwise": all_k_markov_majority,
        },
        "comparison_at_k30": final,
        "comparison_by_prefix_length": rows_by_k,
        "execution": {
            "cache": inventory,
            "cache_reused": True,
            "h5_rescan": False,
            "x12_touched": False,
        },
    }
    atomic_write_json(ARTIFACT_PATH, payload)
    print(json.dumps({
        "artifact": str(ARTIFACT_PATH),
        "artifact_bytes": ARTIFACT_PATH.stat().st_size,
        "artifact_sha256": sha256_file(ARTIFACT_PATH),
        "k30_summary": final["summary"],
        "first_order_licensed": first_order_licensed,
        "runner": str(RUNNER_PATH),
        "runner_sha256": sha256_file(RUNNER_PATH),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
