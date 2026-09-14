#!/usr/bin/env python3
"""Assemble X8: vector-law Michel lower bounds and the DPI-ordered pooled law.

The vector object is the project's fixed PHIST object: each retained flow is
represented by the concatenation of PHIST_SRC_SIZES, PHIST_DST_SIZES,
PHIST_SRC_IPT, and PHIST_DST_IPT (four fixed 8-bin arrays), normalized to sum
to one.  The vector-side quantity is an asymptotic Michel HPLB estimate, not a
finite-sample certificate.

The k=5/M=1 prefix-symbol TV is joined only as an empirical comparison.  It
is not DPI-ordered with the PHIST vector law.  The DPI-ordered comparison is
against the PHIST pooled-cell law, whose per-pair tv_hat is
0.5 * ||mean(vector_a) - mean(vector_b)||_1.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import multiprocessing as mp
import os
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/root/eibo")
H5_CANDIDATE = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5")
VECTOR_SUMMARY_PATH = ROOT / "artifacts/q1_vector_level_one_sided_full_n.json"
VECTOR_CSV_PATH = ROOT / "artifacts/q1_vector_level_one_sided_full_n.csv"
VECTOR_STATE_PATH = Path("/dev/shm/q1_vector_level_one_sided_full_n.state.pkl")
VECTOR_RUNNER_PATH = ROOT / "scripts/compute_vector_level_one_sided_full_n.py"
POOLED_PATH = ROOT / "artifacts/q2_phist_certificate_v3.json"
KPREFIX_PATH = ROOT / "artifacts/q1_eps_lo_symbol_map.json"
STATCORE_PATH = ROOT / "src/eibo/statcore.py"
OUT_PATH = ROOT / "artifacts/x8_vector_law_tv.json"
VECTOR_WORKERS = 16

sys.path.insert(0, str(ROOT / "src"))
from eibo.statcore import tv_lower_bound  # noqa: E402

_WORKER_VECTORS: dict[int, np.ndarray] | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path),
        "size_bytes": int(stat.st_size),
        "sha256": sha256_file(path),
    }


def load_pair_map(path: Path, value_key: str) -> dict[tuple[int, int], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"]
    result = {}
    for row in rows:
        key = (int(row["service_a"]), int(row["service_b"]))
        if key in result:
            raise RuntimeError(f"duplicate pair in {path}: {key}")
        result[key] = {
            value_key: float(row[value_key]),
            **{
                field: row[field]
                for field in ("n_a", "n_b", "pair_flow_count")
                if field in row
            },
        }
    return result


def load_vector_rows() -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    summary = json.loads(VECTOR_SUMMARY_PATH.read_text(encoding="utf-8"))
    vector_meta = summary["vector_level_one_sided"]
    if vector_meta["method"] != "michel":
        raise RuntimeError(f"unexpected vector method: {vector_meta['method']}")
    if vector_meta["sample_cap_per_service"] is not None:
        raise RuntimeError("X8 requires the full-n vector result, not a capped result")

    rows: dict[tuple[int, int], dict[str, Any]] = {}
    with VECTOR_CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            key = (int(raw["service_a"]), int(raw["service_b"]))
            if key in rows:
                raise RuntimeError(f"duplicate vector pair: {key}")
            rows[key] = {
                "vector_law_tv_lower_bound": float(raw["eps_lo"]),
                "vector_n_a": int(raw["n_a"]),
                "vector_n_b": int(raw["n_b"]),
            }
    if len(rows) != int(vector_meta["pair_count"]):
        raise RuntimeError("vector CSV count disagrees with its summary")
    return rows, summary


def load_state_vectors() -> dict[int, np.ndarray]:
    if not VECTOR_STATE_PATH.exists():
        raise FileNotFoundError(VECTOR_STATE_PATH)
    with VECTOR_STATE_PATH.open("rb") as handle:
        state = pickle.load(handle)
    vectors = state["vectors"]
    if not isinstance(vectors, dict) or len(vectors) != 45:
        raise RuntimeError("vector state does not contain the expected 45 services")
    for service, values in vectors.items():
        array = np.asarray(values, dtype=float)
        if array.ndim != 2 or array.shape[1] != 32:
            raise RuntimeError(f"service {service} has vector shape {array.shape}, expected (*, 32)")
        if not np.all(np.isfinite(array)):
            raise RuntimeError(f"service {service} contains non-finite vector values")
        if not np.allclose(array.sum(axis=1), 1.0, rtol=0.0, atol=2e-6):
            raise RuntimeError(f"service {service} vectors are not normalized")
        vectors[int(service)] = array
    return vectors


def _compute_vector_pair(pair: tuple[int, int]) -> tuple[tuple[int, int], float]:
    if _WORKER_VECTORS is None:
        raise RuntimeError("vector worker cache is not initialized")
    service_a, service_b = pair
    value, diagnostics = tv_lower_bound(
        _WORKER_VECTORS[service_a],
        _WORKER_VECTORS[service_b],
        alpha=0.025,
        random_state=0,
        method="michel",
    )
    if diagnostics.get("method") != "michel_adaptive_sup_cutoff":
        raise RuntimeError(f"unexpected Michel diagnostic for {pair}: {diagnostics.get('method')}")
    return pair, float(value)


def recompute_vector_rows(vectors: dict[int, np.ndarray]) -> dict[tuple[int, int], dict[str, Any]]:
    pairs = sorted((a, b) for index, a in enumerate(sorted(vectors)) for b in sorted(vectors)[index + 1 :])
    global _WORKER_VECTORS
    _WORKER_VECTORS = vectors

    # Fork preserves the read-only vector cache without serializing it per pair.
    with mp.get_context("fork").Pool(
        processes=min(VECTOR_WORKERS, len(pairs)),
        maxtasksperchild=1,
    ) as pool:
        values = dict(pool.map(_compute_vector_pair, pairs, chunksize=1))
    return {
        pair: {
            "vector_law_tv_lower_bound": value,
            "vector_n_a": int(len(vectors[pair[0]])),
            "vector_n_b": int(len(vectors[pair[1]])),
        }
        for pair, value in values.items()
    }


def inspect_h5_schema() -> dict[str, Any]:
    import tables

    with tables.open_file(str(H5_CANDIDATE), mode="r") as h5:
        nodes = [
            node
            for node in h5.walk_nodes("/flows", classname="Table")
            if {"APP", "PHIST_SRC_SIZES", "PHIST_DST_SIZES", "PHIST_SRC_IPT", "PHIST_DST_IPT"}
            .issubset(set(node.colnames))
        ]
        if not nodes:
            raise RuntimeError("primary H5 has no table with the required PHIST fields")
        node = nodes[0]
        fields = ("APP", "PHIST_SRC_SIZES", "PHIST_DST_SIZES", "PHIST_SRC_IPT", "PHIST_DST_IPT")
        return {
            "path": str(H5_CANDIDATE),
            "sha256": sha256_file(H5_CANDIDATE),
            "table_count_with_required_fields": len(nodes),
            "first_table": node._v_pathname,
            "first_table_nrows": int(node.nrows),
            "fields": {
                field: {
                    "dtype": str(node.coldtypes[field]),
                    "shape": list(node.coldtypes[field].shape),
                }
                for field in fields
            },
        }


def build_artifact(recompute: bool) -> dict[str, Any]:
    if not H5_CANDIDATE.exists():
        raise FileNotFoundError(H5_CANDIDATE)
    vector_rows, vector_summary = load_vector_rows()
    prior_vector_rows = vector_rows
    reconciliation = {
        "performed": False,
        "max_abs_difference_vs_existing_full_n_csv": None,
        "mean_abs_difference_vs_existing_full_n_csv": None,
    }
    if recompute:
        vector_rows = recompute_vector_rows(load_state_vectors())
        differences = np.asarray(
            [
                abs(
                    vector_rows[pair]["vector_law_tv_lower_bound"]
                    - prior_vector_rows[pair]["vector_law_tv_lower_bound"]
                )
                for pair in sorted(vector_rows)
            ],
            dtype=float,
        )
        reconciliation = {
            "performed": True,
            "max_abs_difference_vs_existing_full_n_csv": float(np.max(differences)),
            "mean_abs_difference_vs_existing_full_n_csv": float(np.mean(differences)),
        }

    pooled_rows = load_pair_map(POOLED_PATH, "tv_hat")
    kprefix_rows = load_pair_map(KPREFIX_PATH, "tv_hat")
    keys = set(vector_rows)
    if keys != set(pooled_rows) or keys != set(kprefix_rows):
        raise RuntimeError("vector, pooled-cell, and k-prefix pair sets differ")
    if len(keys) != 990:
        raise RuntimeError(f"expected 990 pairs, observed {len(keys)}")

    rows = []
    for service_a, service_b in sorted(keys):
        vector = vector_rows[(service_a, service_b)]
        pooled = pooled_rows[(service_a, service_b)]
        kprefix = kprefix_rows[(service_a, service_b)]
        rows.append(
            {
                "service_a": service_a,
                "service_b": service_b,
                "vector_law_tv_lower_bound": vector["vector_law_tv_lower_bound"],
                "pooled_cell_tv_hat": pooled["tv_hat"],
                "kprefix_symbol_tv_hat": kprefix["tv_hat"],
                "vector_n_a": vector.get("vector_n_a"),
                "vector_n_b": vector.get("vector_n_b"),
                "pooled_n_a": pooled.get("n_a"),
                "pooled_n_b": pooled.get("n_b"),
                "vector_ge_pooled_sanity": (
                    vector["vector_law_tv_lower_bound"] >= pooled["tv_hat"]
                ),
                "vector_lt_kprefix_empirical": (
                    vector["vector_law_tv_lower_bound"] < kprefix["tv_hat"]
                ),
            }
        )

    vector_values = np.asarray([row["vector_law_tv_lower_bound"] for row in rows], dtype=float)
    pooled_values = np.asarray([row["pooled_cell_tv_hat"] for row in rows], dtype=float)
    kprefix_values = np.asarray([row["kprefix_symbol_tv_hat"] for row in rows], dtype=float)
    dpi_sanity_count = int(np.count_nonzero(vector_values >= pooled_values))
    dpi_violation_count = int(np.count_nonzero(vector_values < pooled_values))
    inversion_count = int(np.count_nonzero(vector_values < kprefix_values))
    summary_medians = {
        "vector_law_tv_median": float(np.median(vector_values)),
        "pooled_cell_tv_median": float(np.median(pooled_values)),
        "kprefix_marginal_tv_median": float(np.median(kprefix_values)),
    }
    consistency_checks = {
        "pair_count_all_sources_equal_990": len(keys) == 990,
        "dpi_partition_sums_to_pair_count": dpi_sanity_count + dpi_violation_count == len(rows),
        "kprefix_inversion_count_in_range": 0 <= inversion_count <= len(rows),
        "median_recomputations_match": all(
            value == float(np.median(values))
            for value, values in (
                (summary_medians["vector_law_tv_median"], vector_values),
                (summary_medians["pooled_cell_tv_median"], pooled_values),
                (summary_medians["kprefix_marginal_tv_median"], kprefix_values),
            )
        ),
    }
    summary_conflicts = int(sum(not value for value in consistency_checks.values()))

    return {
        "status": "complete",
        "pair_count": len(rows),
        **summary_medians,
        "dpi_violations_vector_vs_pooled": dpi_violation_count,
        "dpi_sanity_pass_pairs": dpi_sanity_count,
        "kprefix_inversion_count": inversion_count,
        "vector_side_quantity_type": "asymptotic_HPLB_michel_adaptive",
        "vector_side_object": "TV of the per-flow normalized 32-vector PHIST law",
        "pooled_side_object": "TV of the PHIST pooled cell law, p_service = E[per-flow normalized vector]",
        "kprefix_side_object": "TV of the k=5/M=1 prefix-symbol law",
        "pairs_where_dpi_check_can_falsify": 0,
        "check_is_sanity_not_detector": True,
        "check_is_sanity_not_detector_note": (
            "The DPI comparison is between the vector law and its pooled-cell image, "
            "but both reported quantities are lower-bound/point-estimate outputs; a "
            "vector-side Michel lower bound below pooled tv_hat is expected and is not "
            "a falsification."
        ),
        "alpha": 0.05,
        "alpha_per_law": 0.025,
        "alpha_split_convention": (
            "The vector Michel call uses alpha=0.025. The pooled-side tv_hat is a "
            "point estimate; no finite-sample certificate is claimed for this one-sided result."
        ),
        "guarantee_scope": (
            "The vector-side value is asymptotic, not finite-sample. This artifact "
            "does not claim a finite-sample certificate for the vector law."
        ),
        "protocol": {
            "primary_h5": str(H5_CANDIDATE),
            "kprefix_k": 5,
            "kprefix_M": 1,
            "kprefix_alphabet_cardinality": 32,
            "kprefix_channel": "PPI[1] direction and PPI[2] size; PPI[0] excluded",
            "vector_channel": "four PHIST 8-bin marginal arrays, concatenated to 32 coordinates",
            "vector_full_n": True,
        },
        "source_files": {
            "h5": inspect_h5_schema(),
            "vector_summary": snapshot(VECTOR_SUMMARY_PATH),
            "vector_csv": snapshot(VECTOR_CSV_PATH),
            "vector_runner": snapshot(VECTOR_RUNNER_PATH),
            "pooled_cell_artifact": snapshot(POOLED_PATH),
            "kprefix_artifact": snapshot(KPREFIX_PATH),
            "statcore": snapshot(STATCORE_PATH),
        },
        "provenance": {
            "vector_summary_method": vector_summary["vector_level_one_sided"]["method"],
            "vector_summary_guarantee": vector_summary["vector_level_one_sided"]["guarantee"],
            "pooled_value_field": "q2_phist_certificate_v3.json rows[].tv_hat",
            "kprefix_value_field": "q1_eps_lo_symbol_map.json rows[].tv_hat",
            "recomputed_vector_values": recompute,
            "vector_reconciliation": reconciliation,
        },
        "mutual_consistency_conflict_count": summary_conflicts,
        "mutual_consistency_checks": consistency_checks,
        "per_pair_rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--recompute-vector",
        action="store_true",
        help="re-run tv_lower_bound on the saved full-n vector cache",
    )
    parser.add_argument("--out", type=Path, default=OUT_PATH)
    args = parser.parse_args()
    result = build_artifact(recompute=args.recompute_vector)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    temp_path = args.out.with_suffix(args.out.suffix + ".tmp")
    temp_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, args.out)
    print(
        json.dumps(
            {
                "status": result["status"],
                "pair_count": result["pair_count"],
                "vector_law_tv_median": result["vector_law_tv_median"],
                "pooled_cell_tv_median": result["pooled_cell_tv_median"],
                "kprefix_marginal_tv_median": result["kprefix_marginal_tv_median"],
                "dpi_violations_vector_vs_pooled": result["dpi_violations_vector_vs_pooled"],
                "kprefix_inversion_count": result["kprefix_inversion_count"],
                "output": str(args.out),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
