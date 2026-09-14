#!/usr/bin/env python3
"""Q2 v3: both sides bound one declared PHIST lattice law."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import pickle
import sys
from pathlib import Path
from typing import Any

import numpy as np
import tables

sys.path.insert(0, "/root/eibo/src")
from eibo.statcore import tv_lower_bound  # noqa: E402


H5_PATH = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
OUT_PATH = "/root/eibo/artifacts/q2_phist_certificate_v3.json"
STATE_PATH = "/root/autodl-tmp/eibo/q2_phist_certificate_v3_state.pkl"
EXPECTED_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"
PHIST_FIELDS = (
    "PHIST_SRC_SIZES",
    "PHIST_DST_SIZES",
    "PHIST_SRC_IPT",
    "PHIST_DST_IPT",
)
CELL_COUNT = 32
EFFECTIVE_DIMENSION = CELL_COUNT - 1
ALPHA_OVERALL = 0.05
ALPHA_SIDE = ALPHA_OVERALL / 2.0
SERVICE_THRESHOLD = 2_000
BATCH_SIZE = 100_000
SAMPLE_CAP = 20_000
SAMPLE_SEED = 20260913
LATTICE_SEED = 20260914
LOWER_GRID_POINTS = 1001


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(16 * 1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def atomic_pickle_dump(value: Any, path: str) -> None:
    temporary = path + ".tmp"
    with open(temporary, "wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temporary, path)


def reservoir_update(
    reservoirs: dict[int, np.ndarray],
    seen: dict[int, int],
    label: int,
    values: np.ndarray,
    rng: np.random.Generator,
) -> None:
    """Uniformly retain at most SAMPLE_CAP normalized flows per service."""
    label = int(label)
    old_seen = int(seen.get(label, 0))
    chunk = np.asarray(values, dtype=np.float64)
    new_seen = old_seen + len(chunk)
    if label not in reservoirs:
        reservoirs[label] = np.empty((SAMPLE_CAP, CELL_COUNT), dtype=np.float64)
    reservoir = reservoirs[label]
    fill = min(max(SAMPLE_CAP - old_seen, 0), len(chunk))
    if fill:
        reservoir[old_seen:old_seen + fill] = chunk[:fill]
    remainder_start = fill
    if remainder_start < len(chunk):
        positions = np.arange(old_seen + remainder_start + 1, new_seen + 1, dtype=np.int64)
        destinations = rng.integers(0, positions, size=len(positions), dtype=np.int64)
        keep = destinations < SAMPLE_CAP
        if np.any(keep):
            reservoir[destinations[keep]] = chunk[remainder_start:][keep]
    seen[label] = new_seen


def sample_lattice_cells(
    normalized_flows: dict[int, np.ndarray],
    labels: list[int],
) -> dict[int, np.ndarray]:
    """Sample one categorical cell after sampling a retained flow uniformly."""
    rng = np.random.default_rng(LATTICE_SEED)
    sampled: dict[int, np.ndarray] = {}
    for label in labels:
        flows = normalized_flows[label]
        cumulative = np.cumsum(flows, axis=1)
        cumulative[:, -1] = 1.0
        uniforms = rng.random(len(flows))
        sampled[label] = np.sum(uniforms[:, None] > cumulative, axis=1).astype(np.int16)
    return sampled


def coordinate_radius(n: int) -> float:
    # 2 * EFFECTIVE_DIMENSION * exp(-2*n*r^2) <= ALPHA_SIDE.
    return math.sqrt(
        math.log(2.0 * EFFECTIVE_DIMENSION / ALPHA_SIDE) / (2.0 * float(n))
    )


def upper_bound(tv_hat: float, n_a: int, n_b: int) -> dict[str, float]:
    radius_a = EFFECTIVE_DIMENSION * coordinate_radius(n_a)
    radius_b = EFFECTIVE_DIMENSION * coordinate_radius(n_b)
    eps_hi = float(tv_hat + radius_a + radius_b)
    return {
        "radius_coordinate_a": coordinate_radius(n_a),
        "radius_coordinate_b": coordinate_radius(n_b),
        "radius_tv_a": radius_a,
        "radius_tv_b": radius_b,
        "eps_hi": eps_hi,
    }


def scan_h5() -> dict[str, Any]:
    if not os.path.isfile(H5_PATH):
        raise SystemExit(f"missing H5: {H5_PATH}")
    h5_sha256 = sha256_file(H5_PATH)
    print(f"h5_path={H5_PATH}")
    print(f"h5_sha256={h5_sha256}")
    if h5_sha256 != EXPECTED_SHA256:
        raise SystemExit(
            f"H5 checksum mismatch: expected {EXPECTED_SHA256}, got {h5_sha256}"
        )

    with tables.open_file(H5_PATH, mode="r") as h5:
        nodes = [
            node for node in h5.walk_nodes("/flows", classname="Table")
            if "APP" in node.colnames
        ]
        if not nodes:
            raise SystemExit("no /flows table with APP found")
        missing = [
            f"{node._v_pathname}:{field}"
            for node in nodes
            for field in PHIST_FIELDS
            if field not in node.colnames
        ]
        if missing:
            print("actual_schema_missing=" + json.dumps(missing))
            raise SystemExit("required PHIST fields missing; stopped")
        schema = {
            field: {
                "dtype": str(nodes[0].coldtypes[field]),
                "shape": list(nodes[0].coldtypes[field].shape),
            }
            for field in PHIST_FIELDS
        }
        print("phist_schema=" + json.dumps(schema, sort_keys=True))

        sums: dict[int, np.ndarray] = {}
        counts: dict[int, int] = {}
        reservoirs: dict[int, np.ndarray] = {}
        seen: dict[int, int] = {}
        rng = np.random.default_rng(SAMPLE_SEED)
        total_valid_rows = 0
        zero_vector_rows = 0
        node_row_counts: dict[str, int] = {}
        for node in nodes:
            node_row_counts[node._v_pathname] = int(node.nrows)
            for start in range(0, int(node.nrows), BATCH_SIZE):
                stop = min(start + BATCH_SIZE, int(node.nrows))
                fields = {
                    field: node.read(start=start, stop=stop, field=field)
                    for field in (*PHIST_FIELDS, "APP")
                }
                app = np.asarray(fields["APP"], dtype=np.int64)
                values = np.stack(
                    [np.asarray(fields[field], dtype=np.float64) for field in PHIST_FIELDS],
                    axis=1,
                ).reshape(len(app), CELL_COUNT)
                totals = values.sum(axis=1)
                zero_vector_rows += int(np.count_nonzero(totals <= 0))
                valid = totals > 0
                if not np.all(valid):
                    values = values[valid]
                    app = app[valid]
                    totals = totals[valid]
                if not len(app):
                    continue
                values /= totals[:, None]
                labels, inverse = np.unique(app, return_inverse=True)
                for index, label in enumerate(labels):
                    mask = inverse == index
                    label = int(label)
                    values_for_label = values[mask]
                    sums[label] = sums.get(label, np.zeros(CELL_COUNT)) + values_for_label.sum(axis=0)
                    counts[label] = counts.get(label, 0) + int(mask.sum())
                    reservoir_update(reservoirs, seen, label, values_for_label, rng)
                total_valid_rows += len(app)

        labels = sorted(counts)
        means = {label: sums[label] / counts[label] for label in labels}
        retained = [label for label in labels if counts[label] >= SERVICE_THRESHOLD]
        rows: list[dict[str, Any]] = []
        for service_a, service_b in itertools.combinations(retained, 2):
            n_a, n_b = counts[service_a], counts[service_b]
            tv_hat = 0.5 * float(np.abs(means[service_a] - means[service_b]).sum())
            upper = upper_bound(tv_hat, n_a, n_b)
            rows.append(
                {
                    "service_a": int(service_a),
                    "service_b": int(service_b),
                    "n_a": int(n_a),
                    "n_b": int(n_b),
                    "pair_flow_count": int(n_a + n_b),
                    "tv_hat": tv_hat,
                    **upper,
                    "eps_lo": None,
                    "eps_lo_raw": None,
                    "eps_lo_status": "pending",
                    "bracket_nonempty": None,
                    "violation": None,
                    "eps_hi_raw_gt_one": bool(upper["eps_hi"] > 1.0),
                    "eps_hi_below_half": bool(upper["eps_hi"] < 0.5),
                }
            )

        normalized_flows = {
            label: reservoirs[label][:min(counts[label], SAMPLE_CAP)]
            for label in labels
        }
        lattice_cells = sample_lattice_cells(normalized_flows, labels)
        result = {
            "experiment": "Q2_RECALCULATION_V3",
            "status": "in_progress",
            "results_valid": False,
            "invalidity_reason": "pending until all per-row invariants are checked",
            "generated_at_utc": "2026-09-13T18:14:00Z",
            "h5_path": H5_PATH,
            "h5_sha256": h5_sha256,
            "source_table_paths": [node._v_pathname for node in nodes],
            "source_table_row_counts": node_row_counts,
            "total_valid_rows": int(total_valid_rows),
            "zero_vector_rows": int(zero_vector_rows),
            "service_flow_counts": {str(label): int(counts[label]) for label in labels},
            "retained_service_count": len(retained),
            "pair_count": len(rows),
            "certified_object": {
                "definition": (
                    "Draw a flow uniformly at random from the service; then draw one cell "
                    "from that flow's normalized 32-cell PHIST distribution."
                ),
                "law_type": "categorical distribution over the 32 PHIST cells",
                "probability_parameter": "p_service = E[per-flow normalized 32-vector]",
                "tv_identity": "TV(p_a, p_b) = 0.5 * ||mean_a - mean_b||_1",
                "not_bound": "the continuous-support law of per-flow normalized vectors",
            },
            "alphabet": {
                "m": CELL_COUNT,
                "a_priori_fixed": True,
                "effective_mean_dimension": EFFECTIVE_DIMENSION,
                "unobserved_cells_retained": True,
                "cells": "four fixed 8-bin marginal arrays concatenated: 4 * 8 = 32",
            },
            "confidence": {
                "alpha_overall": ALPHA_OVERALL,
                "alpha_per_law": ALPHA_SIDE,
                "split_convention": (
                    "alpha/2 = 0.025 is allocated to each law for the upper side; "
                    "the lower side is called with alpha=0.025"
                ),
                "upper_side_guarantee": (
                    "finite-sample, distribution-free, simultaneous per-law coordinate "
                    "Hoeffding plus union bound"
                ),
                "lower_side_guarantee": (
                    "Michel et al. asymptotic high-probability lower bound; not an exact "
                    "finite-sample certificate"
                ),
            },
            "upper_side": {
                "bound": "finite-sample mean-vector concentration",
                "formula": (
                    "For law i, r_i = sqrt(log(2*31/0.025)/(2*n_i)); Hoeffding plus "
                    "a union bound over the 31 free coordinates gives TV(p_i,p_hat_i) "
                    "<= 31*r_i. Therefore eps_hi = tv_hat + 31*r_a + 31*r_b, where "
                    "tv_hat = 0.5*||p_hat_a-p_hat_b||_1."
                ),
                "alpha_side": ALPHA_SIDE,
                "eps_hi_is_raw": True,
                "clipping": "none; raw values above 1 are retained and flagged",
            },
            "lower_side": {
                "bound": "tv_lower_bound(method='michel')",
                "routine_path": "/root/eibo/src/eibo/statcore.py:599",
                "alpha_passed": ALPHA_SIDE,
                "input_unit": (
                    "one independently sampled cell per uniformly retained flow, passed "
                    "as a 32-column one-hot matrix; never the per-flow 32-vector matrix"
                ),
                "sample_cap_per_service": SAMPLE_CAP,
                "sample_seed_for_flow_reservoir": SAMPLE_SEED,
                "sample_seed_for_lattice_cell": LATTICE_SEED,
                "michel_grid_points": LOWER_GRID_POINTS,
                "guarantee": (
                    "asymptotic HPLB, not an exact finite-sample guarantee; it is not "
                    "labeled finite-sample certified"
                ),
            },
            "ks_type_bound": {
                "used": False,
                "caveat": "No KS-type classifier-score bound is used in this run.",
            },
            "rows": rows,
            "violating_row_count": None,
            "offending_rows": [],
            "routine_execution_report": [
                {
                    "routine": "/root/eibo/q2_phist_certificate_v3.py:sha256_file",
                    "executed": True,
                    "output_consumed_by_reported_numbers": True,
                    "purpose": "H5 checksum verification",
                },
                {
                    "routine": "/root/eibo/q2_phist_certificate_v3.py:scan_h5",
                    "executed": True,
                    "output_consumed_by_reported_numbers": True,
                    "purpose": "read-only schema, service counts, normalized flow means, and tv_hat",
                },
                {
                    "routine": "/root/eibo/q2_phist_certificate_v3.py:reservoir_update",
                    "executed": True,
                    "output_consumed_by_reported_numbers": True,
                    "purpose": "fixed-seed uniform per-service retained flow samples",
                },
                {
                    "routine": "/root/eibo/q2_phist_certificate_v3.py:sample_lattice_cells",
                    "executed": True,
                    "output_consumed_by_reported_numbers": True,
                    "purpose": "one categorical cell draw per retained flow for the lower side",
                },
                {
                    "routine": "/root/eibo/q2_phist_certificate_v3.py:upper_bound",
                    "executed": True,
                    "output_consumed_by_reported_numbers": True,
                    "purpose": "31-dimensional finite-sample upper bound",
                },
                {
                    "routine": "/root/eibo/src/eibo/statcore.py:599:tv_lower_bound",
                    "executed": False,
                    "output_consumed_by_reported_numbers": True,
                    "purpose": "Michel lower bound; marked true as each pair is processed",
                },
                {
                    "routine": "/root/eibo/q2_phist_certificate_v3.py:finish_result",
                    "executed": False,
                    "output_consumed_by_reported_numbers": True,
                    "purpose": "per-row invariant, quantiles, fraction, and top-pair report",
                },
            ],
        }
        return {
            "h5_sha256": h5_sha256,
            "schema": schema,
            "total_valid_rows": total_valid_rows,
            "zero_vector_rows": zero_vector_rows,
            "labels": labels,
            "retained": retained,
            "counts": counts,
            "lattice_cells": lattice_cells,
            "rows": rows,
            "result": result,
            "scan_complete": True,
        }


def quantiles(values: list[float]) -> dict[str, float]:
    q = np.quantile(np.asarray(values, dtype=float), [0, 0.05, 0.25, 0.5, 0.75, 0.95, 1])
    return {
        "min": float(q[0]),
        "q5": float(q[1]),
        "q25": float(q[2]),
        "median": float(q[3]),
        "q75": float(q[4]),
        "q95": float(q[5]),
        "max": float(q[6]),
    }


def finish_result(state: dict[str, Any]) -> dict[str, Any]:
    result = state["result"]
    rows = state["rows"]
    violations = [row for row in rows if bool(row.get("violation"))]
    eps_lo_values = [float(row["eps_lo"]) for row in rows]
    eps_hi_values = [float(row["eps_hi"]) for row in rows]
    nonempty = [bool(row["bracket_nonempty"]) for row in rows]
    top_pairs = sorted(
        rows,
        key=lambda row: (-int(row["pair_flow_count"]), int(row["service_a"]), int(row["service_b"])),
    )[:10]
    result["status"] = "complete"
    result["results_valid"] = not violations
    result["invalidity_reason"] = (
        None if not violations else "eps_lo > eps_hi occurred; values are diagnostics, not reported results"
    )
    result["violating_row_count"] = len(violations)
    result["offending_rows"] = [
        {
            "service_a": row["service_a"],
            "service_b": row["service_b"],
            "eps_lo": row["eps_lo"],
            "eps_hi": row["eps_hi"],
        }
        for row in violations
    ]
    result["aggregate"] = {
        "fraction_bracket_nonempty_same_pairs": float(np.mean(nonempty)),
        "fraction_eps_lo_positive": float(np.mean(np.asarray(eps_lo_values) > 0)),
        "fraction_eps_hi_below_half": float(np.mean(np.asarray(eps_hi_values) < 0.5)),
        "eps_lo_quantiles": quantiles(eps_lo_values),
        "eps_hi_quantiles": quantiles(eps_hi_values),
    }
    result["top_10_pairs_by_n_a_plus_n_b"] = [
        {
            "service_a": row["service_a"],
            "service_b": row["service_b"],
            "n_a": row["n_a"],
            "n_b": row["n_b"],
            "pair_flow_count": row["pair_flow_count"],
            "tv_hat": row["tv_hat"],
            "eps_lo": row["eps_lo"],
            "eps_hi": row["eps_hi"],
        }
        for row in top_pairs
    ]
    result["report_text"] = (
        f"Violation count: {len(violations)}. "
        f"eps_lo quantiles (min/q5/q25/median/q75/q95/max): "
        f"{quantiles(eps_lo_values)}. "
        f"eps_hi quantiles (min/q5/q25/median/q75/q95/max): "
        f"{quantiles(eps_hi_values)}. "
        f"Non-empty fraction on the same pairs: {float(np.mean(nonempty)):.12g}."
    )
    for item in result["routine_execution_report"]:
        if item["routine"].endswith(":tv_lower_bound"):
            item["executed"] = True
        if item["routine"].endswith(":finish_result"):
            item["executed"] = True
    return result


def write_result(result: dict[str, Any]) -> None:
    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT_PATH + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, default=json_default)
        handle.write("\n")
    os.replace(temporary, OUT_PATH)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pairs", type=int, default=10)
    args = parser.parse_args()
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "rb") as handle:
            state = pickle.load(handle)
        if state.get("h5_sha256") != EXPECTED_SHA256 or not state.get("scan_complete"):
            state = scan_h5()
    else:
        state = scan_h5()

    rows = state["rows"]
    cells = state["lattice_cells"]
    processed = 0
    for row in rows:
        if row["eps_lo_status"] == "computed":
            continue
        if processed >= args.max_pairs:
            break
        eye = np.eye(CELL_COUNT, dtype=float)
        X_a = eye[cells[int(row["service_a"])]]
        X_b = eye[cells[int(row["service_b"])]]
        eps_lo, diagnostics = tv_lower_bound(
            X_a,
            X_b,
            alpha=ALPHA_SIDE,
            method="michel",
            michel_grid_points=LOWER_GRID_POINTS,
        )
        row["eps_lo"] = float(eps_lo)
        row["eps_lo_raw"] = float(diagnostics["bound_before_clipping"])
        row["eps_lo_status"] = "computed"
        row["lower_n_a"] = int(len(X_a))
        row["lower_n_b"] = int(len(X_b))
        row["lower_diagnostics"] = {
            key: value for key, value in diagnostics.items() if key != "classifier"
        }
        row["violation"] = bool(row["eps_lo"] > row["eps_hi"])
        row["bracket_nonempty"] = bool(not row["violation"])
        processed += 1
        if processed % 5 == 0:
            atomic_pickle_dump(state, STATE_PATH)
            print(f"progress computed_lower_pairs={processed}")

    atomic_pickle_dump(state, STATE_PATH)
    done = sum(row["eps_lo_status"] == "computed" for row in rows)
    print(f"progress_total_pairs={len(rows)} computed={done} remaining={len(rows) - done}")
    if done != len(rows):
        return
    result = finish_result(state)
    write_result(result)
    artifact_sha256 = sha256_file(OUT_PATH)
    print(f"json_path={OUT_PATH}")
    print(f"json_bytes={os.path.getsize(OUT_PATH)}")
    print(f"json_sha256={artifact_sha256}")
    print(f"row_count={len(rows)}")
    print(f"violating_row_count={result['violating_row_count']}")
    print("aggregate=" + json.dumps(result["aggregate"], sort_keys=True))
    print("top10_pairs_by_n_a_plus_n_b")
    print("service_a\tservice_b\tn_a\tn_b\tpair_flow_count\ttv_hat\teps_lo\teps_hi")
    for row in result["top_10_pairs_by_n_a_plus_n_b"]:
        print(
            f"{row['service_a']}\t{row['service_b']}\t{row['n_a']}\t{row['n_b']}\t"
            f"{row['pair_flow_count']}\t{row['tv_hat']:.8f}\t{row['eps_lo']:.8f}\t{row['eps_hi']:.8f}"
        )


if __name__ == "__main__":
    main()
