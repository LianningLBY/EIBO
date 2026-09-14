#!/usr/bin/env python3
"""Full-n vector-level one-sided Michel lower bound for the fixed pair set."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import multiprocessing as mp
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import tables

sys.path.insert(0, "/root/eibo/src")
from eibo.statcore import tv_lower_bound  # noqa: E402


H5_PATH = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
PAIR_PATH = "/root/eibo/artifacts/q1_eps_lo_symbol_map.json"
OUT_PATH = "/root/eibo/artifacts/q1_vector_level_one_sided_full_n.json"
CSV_PATH = "/root/eibo/artifacts/q1_vector_level_one_sided_full_n.csv"
STATE_PATH = "/dev/shm/q1_vector_level_one_sided_full_n.state.pkl"
ROWS_STATE_PATH = "/dev/shm/q1_vector_level_one_sided_full_n.rows.json"
MODULE_PATH = "/root/eibo/src/eibo/statcore.py"
PYTHON_PATH = "/root/miniconda3/bin/python3"
PHIST_FIELDS = (
    "PHIST_SRC_SIZES",
    "PHIST_DST_SIZES",
    "PHIST_SRC_IPT",
    "PHIST_DST_IPT",
)
CELL_COUNT = 32
BATCH_SIZE = 100_000
MAX_PAIRS_DEFAULT = 50
POOL_WORKERS = 16

_WORKER_VECTORS: dict[int, np.ndarray] | None = None


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(16 * 1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def file_snapshot(path: str) -> dict[str, object]:
    stat = os.stat(path)
    return {
        "path": path,
        "sha256": sha256_file(path),
        "mtime_ns": int(stat.st_mtime_ns),
        "size_bytes": int(stat.st_size),
    }


def load_pairs() -> tuple[list[dict[str, object]], list[int]]:
    with open(PAIR_PATH, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload["rows"]
    assert len(rows) == 990, len(rows)
    keys = sorted(rows[0].keys())
    assert "service_a" in rows[0] and "service_b" in rows[0]
    services = sorted(
        {
            int(row["service_a"])
            for row in rows
        }
        | {
            int(row["service_b"])
            for row in rows
        }
    )
    print(f"pair_row_count={len(rows)}")
    print(f"pair_row_keys={json.dumps(keys)}")
    print(f"pair_first={json.dumps(rows[0], sort_keys=True, default=str)}")
    print(f"pair_service_count={len(services)}")
    pair_rows = [
        {
            "service_a": int(row["service_a"]),
            "service_b": int(row["service_b"]),
        }
        for row in rows
    ]
    return pair_rows, services


def table_nodes(h5: tables.File) -> list[tables.Table]:
    nodes = [
        node
        for node in h5.walk_nodes("/flows", classname="Table")
        if "APP" in node.colnames
    ]
    if not nodes:
        raise RuntimeError("no /flows table with APP found")
    missing = [
        f"{node._v_pathname}:{field}"
        for node in nodes
        for field in PHIST_FIELDS
        if field not in node.colnames
    ]
    if missing:
        raise RuntimeError(f"required PHIST fields missing: {missing[:5]}")
    return nodes


def read_batch(node: tables.Table, start: int, stop: int) -> tuple[np.ndarray, np.ndarray]:
    app = np.asarray(node.read(start=start, stop=stop, field="APP"), dtype=np.int16)
    fields = [
        np.asarray(node.read(start=start, stop=stop, field=field), dtype=np.uint32)
        for field in PHIST_FIELDS
    ]
    values = np.concatenate(fields, axis=1)
    return app, values


def scan_vectors(rows: list[dict[str, object]], services: list[int]) -> dict[str, object]:
    service_set = set(services)
    counts = {service: 0 for service in services}
    zero_vector_rows = 0
    total_rows = 0
    source_tables: list[str] = []
    source_table_row_counts: dict[str, int] = {}
    schema: dict[str, dict[str, object]] = {}

    with tables.open_file(H5_PATH, mode="r") as h5:
        nodes = table_nodes(h5)
        for node in nodes:
            source_tables.append(node._v_pathname)
            source_table_row_counts[node._v_pathname] = int(node.nrows)
        schema = {
            field: {
                "dtype": str(nodes[0].coldtypes[field]),
                "shape": list(nodes[0].coldtypes[field].shape),
            }
            for field in ("APP", *PHIST_FIELDS)
        }
        print(f"source_table_count={len(nodes)}")
        print(f"source_table_first={source_tables[0]}")
        print(f"source_table_last={source_tables[-1]}")
        print(f"actual_schema={json.dumps(schema, sort_keys=True)}")

        for node_index, node in enumerate(nodes, start=1):
            for start in range(0, int(node.nrows), BATCH_SIZE):
                stop = min(start + BATCH_SIZE, int(node.nrows))
                app, values = read_batch(node, start, stop)
                selected = np.isin(app, services)
                if not np.any(selected):
                    total_rows += len(app)
                    continue
                selected_values = values[selected]
                selected_app = app[selected]
                totals = selected_values.sum(axis=1, dtype=np.uint64)
                zero_vector_rows += int(np.count_nonzero(totals == 0))
                valid = totals > 0
                for service in services:
                    counts[service] += int(np.count_nonzero(valid & (selected_app == service)))
                total_rows += len(app)
            if node_index == 1 or node_index % 10 == 0 or node_index == len(nodes):
                print(f"scan_count_pass_tables={node_index}/{len(nodes)} total_rows={total_rows}")

    print(f"scan_total_rows={total_rows}")
    print(f"scan_zero_vector_rows={zero_vector_rows}")
    print(f"scan_service_count_summary={json.dumps({str(k): v for k, v in counts.items()}, sort_keys=True)}")
    if any(count <= 0 for count in counts.values()):
        raise RuntimeError(f"pair service without eligible vectors: {counts}")

    vectors = {
        service: np.empty((count, CELL_COUNT), dtype=np.float32)
        for service, count in counts.items()
    }
    positions = {service: 0 for service in services}
    total_valid = 0
    with tables.open_file(H5_PATH, mode="r") as h5:
        nodes = table_nodes(h5)
        for node_index, node in enumerate(nodes, start=1):
            for start in range(0, int(node.nrows), BATCH_SIZE):
                stop = min(start + BATCH_SIZE, int(node.nrows))
                app, values = read_batch(node, start, stop)
                selected = np.isin(app, services)
                if not np.any(selected):
                    continue
                selected_values = values[selected]
                selected_app = app[selected]
                totals = selected_values.sum(axis=1, dtype=np.uint64)
                valid = totals > 0
                if not np.any(valid):
                    continue
                valid_values = selected_values[valid].astype(np.float64, copy=False)
                valid_values /= totals[valid].astype(np.float64)[:, None]
                valid_app = selected_app[valid]
                for service in services:
                    mask = valid_app == service
                    count = int(np.count_nonzero(mask))
                    if count:
                        start_pos = positions[service]
                        vectors[service][start_pos : start_pos + count] = valid_values[mask]
                        positions[service] += count
                total_valid += len(valid_values)
            if node_index == 1 or node_index % 10 == 0 or node_index == len(nodes):
                print(f"scan_vector_pass_tables={node_index}/{len(nodes)} total_valid={total_valid}")

    for service in services:
        assert positions[service] == counts[service], (service, positions[service], counts[service])
        assert np.all(np.isfinite(vectors[service]))
        assert np.allclose(vectors[service].sum(axis=1), 1.0, rtol=0.0, atol=2e-6)
    print(f"normalized_vector_row_count={total_valid}")

    state = {
        "rows": [dict(row) for row in rows],
        "services": services,
        "vectors": vectors,
        "counts": counts,
        "total_rows": total_rows,
        "total_valid": total_valid,
        "zero_vector_rows": zero_vector_rows,
        "source_tables": source_tables,
        "source_table_row_counts": source_table_row_counts,
        "schema": schema,
        "h5_snapshot": file_snapshot(H5_PATH),
        "pair_snapshot": file_snapshot(PAIR_PATH),
        "module_snapshot": file_snapshot(MODULE_PATH),
    }
    with open(STATE_PATH, "wb") as handle:
        pickle.dump(state, handle, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"state_path={STATE_PATH}")
    print(f"state_bytes={os.path.getsize(STATE_PATH)}")
    return state


def quantiles(values: list[float]) -> dict[str, float]:
    q = np.quantile(np.asarray(values, dtype=np.float64), [0, 0.05, 0.25, 0.5, 0.75, 0.95, 1])
    return {
        "min": float(q[0]),
        "q5": float(q[1]),
        "q25": float(q[2]),
        "median": float(q[3]),
        "q75": float(q[4]),
        "q95": float(q[5]),
        "max": float(q[6]),
    }


def write_outputs(state: dict[str, object]) -> None:
    rows = state["rows"]
    values = [float(row["eps_lo"]) for row in rows]
    q = quantiles(values)
    result = {
        "vector_level_one_sided": {
            "object_bounded": "TV(per-flow normalized 32-vector law)",
            "object_composition": "Concatenation of PHIST_SRC_SIZES, PHIST_DST_SIZES, PHIST_SRC_IPT, PHIST_DST_IPT; four separate marginal histograms, 32 coordinates total; NOT a joint 8x8x2 object.",
            "preprocessing": "Per flow: concatenate the four 8-bin marginal histograms into a 32-vector and normalize to sum 1; pool flows within each APP service by averaging the normalized vectors.",
            "method": "michel",
            "alpha": 0.025,
            "random_state": 0,
            "guarantee": "asymptotic HPLB estimate, not an exact finite-sample certificate",
            "eps_lo_quantiles": q,
            "eps_lo_mean": float(np.mean(values)),
            "eps_lo_min": float(np.min(values)),
            "eps_lo_max": float(np.max(values)),
            "pair_count": len(rows),
            "fraction_eps_lo_positive": float(np.mean(np.asarray(values) > 0.0)),
            "sample_cap_per_service": None,
            "cap_is_none": True,
            "sample_seed": 20260913,
            "sampling_unit": "flow",
        },
        "measured_full_n_pair_count": len(rows),
        "assumed_pair_count": 0,
        "non_interchangeability": "This is a ONE-SIDED result for the PER-FLOW 32-VECTOR object, not for the marginal k-prefix symbol law. By the data-processing inequality TV(vector law) >= TV(marginal symbol law), so this is a STRONGER claim -- but the two quantities are NOT interchangeable and this figure must NEVER be reported as a better bound on Q1's or Q2's object. One-hot encoding was adopted precisely to put both sides of the bracket on ONE object, and the vector structure it discards is reported here as a SEPARATE, independent result.",
        "relationship_to_marginal": "TV(vector) >= TV(marginal). The marginal result's eps_lo median is 0.534945 (pair set and object as declared in q1_eps_lo_symbol_map.json). This run's value is the vector-level counterpart. The correct reading is that the certified marginal bracket is a CONSERVATIVE view of the total distinguishability, not that the vector number supersedes it.",
        "prior_capped_reference": "An earlier capped reference (median 0.8585373202534684) existed inside q1_eps_lo_symbol_map.json under vector_level_independent_one_sided, computed with a 20,000-flow-per-service cap from q2_phist_certificate_v2.json. This run replaces it with a full-n measurement. Report THIS run's quantiles; cite the old value only as the capped predecessor.",
        "pairs_source": "q1_eps_lo_symbol_map.json rows",
    }
    if os.path.exists(OUT_PATH):
        previous_sha = sha256_file(OUT_PATH)
        if previous_sha != "650a58bf76e13ee292ec593d55f10c9d9dc5b616ad4732a8ddad745c5dfd5e83":
            raise RuntimeError(f"refusing to overwrite existing artifact: {OUT_PATH}")
        print(f"replacing_own_failed_artifact_sha256={previous_sha}")
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if os.path.exists(CSV_PATH):
        previous_csv_sha = sha256_file(CSV_PATH)
        if previous_csv_sha != "c638e67e6584c0b2403f9bb2c6dd651231cd31a2bc8a409c304c1f51c4c9a346":
            raise RuntimeError(f"refusing to overwrite existing artifact: {CSV_PATH}")
        print(f"replacing_own_failed_csv_sha256={previous_csv_sha}")
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["service_a", "service_b", "n_a", "n_b", "eps_lo"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "service_a": int(row["service_a"]),
                "service_b": int(row["service_b"]),
                "n_a": int(row["n_a"]),
                "n_b": int(row["n_b"]),
                "eps_lo": repr(float(row["eps_lo"])),
            })
    print(f"final_quantiles={json.dumps(q, sort_keys=True)}")
    print(f"final_mean={result['vector_level_one_sided']['eps_lo_mean']:.17g}")
    print(f"final_min={result['vector_level_one_sided']['eps_lo_min']:.17g}")
    print(f"final_max={result['vector_level_one_sided']['eps_lo_max']:.17g}")
    print(f"final_fraction_eps_lo_positive={result['vector_level_one_sided']['fraction_eps_lo_positive']:.17g}")
    print(f"measured_full_n_pair_count={len(rows)}")
    print("assumed_pair_count=0")
    print("cap_is_none=True")
    print(f"artifact_sha256={sha256_file(OUT_PATH)}")
    print(f"artifact_bytes={os.path.getsize(OUT_PATH)}")
    print(f"csv_sha256={sha256_file(CSV_PATH)}")
    print(f"csv_row_count={sum(1 for _ in open(CSV_PATH, encoding='utf-8')) - 1}")
    for path in (PAIR_PATH, MODULE_PATH, H5_PATH):
            print("read_file_snapshot=" + json.dumps(file_snapshot(path), sort_keys=True))


def compute_pair(task: tuple[int, int, int]) -> tuple[int, float, dict[str, object]]:
    index, service_a, service_b = task
    assert _WORKER_VECTORS is not None
    X_a = _WORKER_VECTORS[service_a]
    X_b = _WORKER_VECTORS[service_b]
    eps_lo, diagnostics = tv_lower_bound(
        X_a, X_b, alpha=0.025, random_state=0, method="michel"
    )
    return index, float(eps_lo), {
        key: value for key, value in diagnostics.items() if key != "classifier"
    }


def main() -> None:
    max_pairs = int(sys.argv[1]) if len(sys.argv) > 1 else MAX_PAIRS_DEFAULT
    rows, services = load_pairs()
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "rb") as handle:
            state = pickle.load(handle)
        assert len(state["rows"]) == 990
        if any(row.get("eps_lo") is not None for row in state["rows"]):
            print("discarding_state_with_preexisting_eps_lo=true")
            state = scan_vectors(rows, services)
        else:
            print(f"loaded_state_rows={len(state['rows'])}")
            if os.path.exists(ROWS_STATE_PATH):
                with open(ROWS_STATE_PATH, "r", encoding="utf-8") as handle:
                    saved_rows = json.load(handle)
                assert len(saved_rows) == 990
                state["rows"] = saved_rows
                print(f"loaded_row_checkpoint={ROWS_STATE_PATH}")
    else:
        print(f"exact_tv_lower_bound_call=tv_lower_bound(X_a, X_b, alpha=0.025, random_state=0, method='michel')")
        print(f"tv_lower_bound_module={tv_lower_bound.__module__}")
        print(f"tv_lower_bound_source={MODULE_PATH}")
        print(f"tv_lower_bound_module_sha256={sha256_file(MODULE_PATH)}")
        state = scan_vectors(rows, services)

    global _WORKER_VECTORS
    _WORKER_VECTORS = state["vectors"]
    pending = [
        (index, int(row["service_a"]), int(row["service_b"]))
        for index, row in enumerate(state["rows"])
        if row.get("eps_lo") is None
    ][:max_pairs]
    done = 0
    started = time.time()
    if pending:
        context = mp.get_context("fork")
        with context.Pool(processes=min(POOL_WORKERS, len(pending)), maxtasksperchild=1) as pool:
            for index, eps_lo, diagnostics in pool.imap_unordered(compute_pair, pending, chunksize=1):
                row = state["rows"][index]
                X_a = state["vectors"][int(row["service_a"])]
                X_b = state["vectors"][int(row["service_b"])]
                row["n_a"] = int(len(X_a))
                row["n_b"] = int(len(X_b))
                row["eps_lo"] = eps_lo
                row["diagnostics"] = diagnostics
                done += 1
                with open(ROWS_STATE_PATH, "w", encoding="utf-8") as handle:
                    json.dump(state["rows"], handle, sort_keys=True)
                print(f"progress_batch_pairs={done}")
    computed = sum(row.get("eps_lo") is not None for row in state["rows"])
    print(f"progress_total_pairs={len(state['rows'])} computed={computed} remaining={len(state['rows']) - computed}")
    print(f"batch_elapsed_seconds={time.time() - started:.6f}")
    if computed == len(state["rows"]):
        write_outputs(state)


if __name__ == "__main__":
    main()
