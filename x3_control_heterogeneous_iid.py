#!/usr/bin/env python3
"""X3 control (a): heterogeneous per-flow i.i.d. direction rates.

The nested-model fit is imported from the existing X3 runner.  Only the
synthetic arm is run; no real-data comparison is recomputed.
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

from x3_variant_c_nested_lr import (
    PREFIX_LENGTHS,
    SEQUENCE_LENGTH,
    direction_bits_from_codes,
    fit_nested_models,
)


PROJECT = Path("/root/eibo")
CACHE_DIR = Path("/dev/shm/eibo_x3_chain_rule")
MERGED_PATH = CACHE_DIR / "merged.pkl"
ARTIFACT_PATH = PROJECT / "artifacts" / "x3_control_heterogeneous_iid.json"
RUNNER_PATH = PROJECT / "x3_control_heterogeneous_iid.py"
SEED = 20260914

# Operationalization of the supplied phrase "essentially all items" over the
# existing experiment's per-item, per-prefix scope.
ESSENTIALLY_ALL_FRACTION = 44 / 45


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def cache_inventory() -> dict:
    required = [CACHE_DIR / "ledger.json", MERGED_PATH, CACHE_DIR / "results.pkl"]
    parts = sorted(CACHE_DIR.glob("part_*.npz")) if CACHE_DIR.exists() else []
    files = [p for p in CACHE_DIR.iterdir() if p.is_file()] if CACHE_DIR.exists() else []
    return {
        "present": bool(all(p.is_file() for p in required) and len(parts) == 360),
        "cache_dir": str(CACHE_DIR),
        "required_files": {p.name: p.is_file() for p in required},
        "npz_part_count": len(parts),
        "file_count": len(files),
        "total_bytes": int(sum(p.stat().st_size for p in files)),
        "h5_rescan": False,
    }


def load_merged() -> tuple[dict, dict]:
    inventory = cache_inventory()
    if not inventory["present"]:
        raise RuntimeError(
            "cached state incomplete at /dev/shm/eibo_x3_chain_rule; refusing to rescan the H5"
        )
    with MERGED_PATH.open("rb") as handle:
        return pickle.load(handle), inventory


def empirical_rates(merged: dict) -> tuple[np.ndarray, dict]:
    rate_counts = np.zeros(SEQUENCE_LENGTH + 1, dtype=np.int64)
    per_service = {}
    all_rates = []
    for service in map(int, merged["services"]):
        entry = merged["by_service"][service]
        bits = direction_bits_from_codes(entry["codes"], entry["lens"])
        numerators = bits.sum(axis=1).astype(np.int64)
        rate_counts += np.bincount(numerators, minlength=SEQUENCE_LENGTH + 1)
        rates = numerators.astype(np.float64) / SEQUENCE_LENGTH
        all_rates.append(rates)
        per_service[str(service)] = {
            "n_flows": int(rates.size),
            "mean_rate": float(np.mean(rates)),
            "std_rate": float(np.std(rates)),
        }
    pooled = np.concatenate(all_rates) if all_rates else np.empty(0, dtype=np.float64)
    distribution = {
        "definition": "pooled empirical distribution of per-flow one-rates over cached flows with PPI_LEN >= 30",
        "sequence_length": SEQUENCE_LENGTH,
        "n_flows": int(pooled.size),
        "support": [float(i / SEQUENCE_LENGTH) for i in range(SEQUENCE_LENGTH + 1) if rate_counts[i]],
        "histogram_by_ones_in_30": {str(i): int(rate_counts[i]) for i in range(SEQUENCE_LENGTH + 1)},
        "mean_rate": float(np.mean(pooled)),
        "std_rate": float(np.std(pooled)),
        "quantiles": {str(q): float(np.quantile(pooled, q)) for q in (0.0, 0.25, 0.5, 0.75, 1.0)},
        "per_service": per_service,
    }
    return pooled, distribution


def summarize(rows: list[dict]) -> dict:
    deltas = np.asarray([r["delta_bic_iid_minus_markov"] for r in rows], dtype=float)
    winners = [r["winner"] for r in rows]
    return {
        "n_items": len(rows),
        "markov_favours": int(sum(w == "MARKOV" for w in winners)),
        "iid_favours": int(sum(w == "IID" for w in winners)),
        "ties": int(sum(w == "TIE" for w in winners)),
        "delta_bic_mean": float(np.mean(deltas)),
        "delta_bic_median": float(np.median(deltas)),
        "delta_bic_min": float(np.min(deltas)),
        "delta_bic_max": float(np.max(deltas)),
    }


def main() -> int:
    started = time.time()
    preregistration = {
        "arm": "Each cached service keeps its exact usable-flow count. Each flow independently draws one rate with replacement from the pooled empirical per-flow rate distribution, then emits 30 i.i.d. Bernoulli bits at that rate.",
        "within_flow_truth": "i.i.d.; no within-flow dependence is generated",
        "comparison": "same exact MLE/BIC fit imported from /root/eibo/x3_variant_c_nested_lr.py:fit_nested_models",
        "prefix_lengths": list(PREFIX_LENGTHS),
        "decision_rule_given_by_request": {
            "dead": "If this arm also returns Markov favoured for essentially all items, between-flow heterogeneity fully explains the real result and the corroboration is dead.",
            "survives": "If this arm returns IID favoured, the control has discriminating power and the corroboration survives.",
        },
        "operationalization": "essentially all = at least 44/45 of all per-item per-prefix comparisons in the existing k=2..30 scope; k=30 is also reported separately",
        "essentially_all_fraction": ESSENTIALLY_ALL_FRACTION,
    }

    merged, cache = load_merged()
    rates, distribution = empirical_rates(merged)
    rng = np.random.default_rng(SEED)
    services = [int(s) for s in merged["services"]]
    per_prefix = []
    final_rows = []

    for service in services:
        entry = merged["by_service"][service]
        n_flows = int(np.sum(np.asarray(entry["lens"]) >= SEQUENCE_LENGTH))
        flow_rates = rng.choice(rates, size=n_flows, replace=True)
        bits = (rng.random((n_flows, SEQUENCE_LENGTH)) < flow_rates[:, None]).astype(np.uint8)
        rows_k30 = []
        for prefix_length in PREFIX_LENGTHS:
            row = fit_nested_models(bits, prefix_length)
            row["item"] = str(service)
            if prefix_length == SEQUENCE_LENGTH:
                rows_k30.append(row)
            per_prefix.append(row)
        final_rows.extend(rows_k30)

    by_k = []
    for prefix_length in PREFIX_LENGTHS:
        rows = [r for r in per_prefix if r["prefix_length"] == prefix_length]
        summary = summarize(rows)
        summary["prefix_length"] = int(prefix_length)
        summary["items"] = rows
        by_k.append(summary)

    final_summary = summarize(final_rows)
    final_summary["prefix_length"] = SEQUENCE_LENGTH
    total_item_prefixes = int(sum(row["n_items"] for row in by_k))
    total_markov = int(sum(row["markov_favours"] for row in by_k))
    total_iid = int(sum(row["iid_favours"] for row in by_k))
    total_ties = int(sum(row["ties"] for row in by_k))
    markov_essentially_all = total_markov / total_item_prefixes >= ESSENTIALLY_ALL_FRACTION
    if markov_essentially_all:
        verdict = "DEAD"
        verdict_text = "dead: the heterogeneous-i.i.d. arm returns Markov favoured for essentially all item-prefix comparisons"
    elif total_iid / total_item_prefixes > 0.5:
        verdict = "SURVIVES"
        verdict_text = "survives: the heterogeneous-i.i.d. arm returns IID favoured for a majority of item-prefix comparisons"
    else:
        verdict = "NOT_DECISIVE_UNDER_OPERATIONALIZATION"
        verdict_text = "not decisive under the preregistered operationalization"

    payload = {
        "control": "a",
        "preregistration": preregistration,
        "seed": SEED,
        "empirical_rate_distribution": distribution,
        "arm": {
            "service_count": len(services),
            "flow_count_by_service": {
                str(s): int(np.sum(np.asarray(merged["by_service"][s]["lens"]) >= SEQUENCE_LENGTH))
                for s in services
            },
            "truth": "independent Bernoulli bits within every flow; per-flow rate heterogeneity only",
            "per_prefix_summary": by_k,
            "final_summary_at_k30": final_summary,
        },
        "decision": {
            "scope": "all item-prefix comparisons for k=2..30",
            "total_item_prefix_comparisons": total_item_prefixes,
            "total_markov_favours": total_markov,
            "total_iid_favours": total_iid,
            "total_ties": total_ties,
            "markov_fraction": float(total_markov / total_item_prefixes),
            "markov_essentially_all": bool(markov_essentially_all),
            "verdict": verdict,
            "plain_statement": verdict_text,
        },
        "execution": {
            "cache": cache,
            "cache_reused": True,
            "h5_rescan": False,
            "real_data_comparison_recomputed": False,
            "x12_touched": False,
            "elapsed_seconds": float(time.time() - started),
        },
    }
    atomic_write_json(ARTIFACT_PATH, payload)
    print(json.dumps({
        "artifact": str(ARTIFACT_PATH),
        "artifact_bytes": ARTIFACT_PATH.stat().st_size,
        "artifact_sha256": sha256_file(ARTIFACT_PATH),
        "k30": final_summary,
        "verdict": verdict,
        "runner": str(RUNNER_PATH),
        "runner_sha256": sha256_file(RUNNER_PATH),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
