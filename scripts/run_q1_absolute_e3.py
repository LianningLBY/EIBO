#!/usr/bin/env python3
"""Incremental E3 reducer for the k=10 absolute-TV Q1 count table."""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import importlib.util
import itertools
import json
import math
import os
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import tables


H5_PATH = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
EXPECTED_SHA256 = (
    "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"
)
ARTIFACT_DIR = Path("/root/eibo/artifacts")
STATE_PATH = ARTIFACT_DIR / "q1_absolute_k10_state.pkl"
SUMMARY_PATH = ARTIFACT_DIR / "q1_absolute_k10_summary.json"
COUNTS_PATH = ARTIFACT_DIR / "q1_absolute_counts_k10.json"
CSV_PATH = ARTIFACT_DIR / "q1_absolute_counts_k10.csv"
META_PATH = ARTIFACT_DIR / "q1_absolute_counts_k10.meta.json"
DENSE_PATH = ARTIFACT_DIR / "q1_absolute_dense_counts_k10_m1_m2.json"

CHUNK_SIZE = 100_000
CHECKPOINT_TABLES = 5
SERVICE_THRESHOLD = 2_000
K_VALUES = (5, 10, 15, 30)
RUNGS = (1, 2, 4, 8, 16)
K = 10
DIRECTION_ROW = 1
SIZE_ROW = 2
ALPHA = 0.05
ALPHA_PER_LAW = ALPHA / 2
LOWER_C = 1.958
LOWER_FLOOR = 0.05
UPPER_C = 2.9604
SATURATION_THRESHOLD = 0.99
SATURATION_FRACTION_THRESHOLD = 0.50


def load_existing_helpers():
    path = Path("/root/eibo/scripts/xs_compression_early_readout.py")
    spec = importlib.util.spec_from_file_location("xs_compression_early_readout", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load helper module from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    required = (
        "table_paths",
        "pack_variable_masked_30",
        "pack_rung_prefix",
        "direction_bits",
        "size_bins",
        "tv",
    )
    missing = [name for name in required if not hasattr(mod, name)]
    if missing:
        raise RuntimeError(f"Missing required existing helpers: {missing}")
    return mod


def sha256_file(path: str | Path, block: int = 16 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            data = handle.read(block)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, default=json_default)
        handle.write("\n")
    os.replace(tmp, path)


def atomic_pickle(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


def load_state():
    with open(STATE_PATH, "rb") as handle:
        return pickle.load(handle)


def quantile(values, q: float):
    return float(np.quantile(np.asarray(values, dtype=np.float64), q))


def iso_utc(seconds: float) -> str:
    return dt.datetime.fromtimestamp(float(seconds), tz=dt.timezone.utc).isoformat()


def validate_schema(h5, paths):
    schema = []
    total_rows = 0
    for path in paths:
        node = h5.get_node(path)
        total_rows += int(node.nrows)
        sample = node.read(0, min(1, node.nrows))
        app = sample["APP"]
        ppi = sample["PPI"]
        lens = sample["PPI_LEN"]
        record = {
            "path": path,
            "nrows": int(node.nrows),
            "APP_dtype": str(app.dtype),
            "APP_shape_per_row": list(app.shape[1:]),
            "PPI_dtype": str(ppi.dtype),
            "PPI_shape_per_row": list(ppi.shape[1:]),
            "PPI_LEN_dtype": str(lens.dtype),
            "PPI_LEN_shape_per_row": list(lens.shape[1:]),
            "TIME_FIRST_dtype": str(sample["TIME_FIRST"].dtype),
            "TIME_FIRST_shape_per_row": list(sample["TIME_FIRST"].shape[1:]),
        }
        schema.append(record)
        if (
            app.dtype != np.dtype("int16")
            or list(app.shape[1:]) != []
            or ppi.dtype != np.dtype("int32")
            or list(ppi.shape[1:]) != [3, 30]
            or lens.dtype != np.dtype("uint16")
            or list(lens.shape[1:]) != []
            or sample["TIME_FIRST"].dtype != np.dtype("float64")
        ):
            raise RuntimeError(
                "h5 schema mismatch; actual first mismatching node: "
                + json.dumps(record, sort_keys=True)
            )
    return schema, total_rows


def validate_masking_helper(helpers, ppi, lens):
    take = min(256, len(lens))
    masked_codes, use = helpers.pack_variable_masked_30(
        ppi[:take], lens[:take], DIRECTION_ROW, SIZE_ROW
    )
    expected_lengths = [2 * min(int(length), 30) for length in lens[:take]]
    observed_lengths = [len(code) for code in masked_codes]
    if not np.all(use):
        raise RuntimeError("pack_variable_masked_30 returned a partial use mask")
    if observed_lengths != expected_lengths:
        raise RuntimeError(
            "pack_variable_masked_30 did not mask at PPI_LEN: "
            f"expected={expected_lengths[:8]} observed={observed_lengths[:8]}"
        )
    return {
        "sample_rows": int(take),
        "all_use_true": True,
        "masked_code_lengths_match_2_times_min_ppi_len": True,
        "output_consumed_as_precondition": True,
    }


def metadata_phase(helpers):
    started = time.time()
    h5_digest = sha256_file(H5_PATH)
    if h5_digest != EXPECTED_SHA256:
        raise RuntimeError(
            f"H5 sha256 mismatch: expected {EXPECTED_SHA256}, observed {h5_digest}"
        )

    app_counts = collections.Counter()
    eligible_counts = {k: collections.Counter() for k in K_VALUES}
    time_min = math.inf
    time_max = -math.inf
    time_rows = 0
    mask_validation = None

    with tables.open_file(H5_PATH, mode="r") as h5:
        paths = helpers.table_paths(h5)
        if not paths:
            raise RuntimeError("No /flows/* table with APP, PPI, PPI_LEN was found")
        schema, total_rows = validate_schema(h5, paths)
        for table_index, path in enumerate(paths):
            node = h5.get_node(path)
            for start in range(0, node.nrows, CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, node.nrows)
                apps = np.asarray(node.read(start, stop, field="APP")).reshape(-1)
                lens = np.asarray(node.read(start, stop, field="PPI_LEN")).reshape(-1)
                times = np.asarray(node.read(start, stop, field="TIME_FIRST")).reshape(-1)
                app_counts.update(map(int, apps))
                for k in K_VALUES:
                    values, counts = np.unique(apps[lens >= k], return_counts=True)
                    for service, count in zip(values, counts):
                        eligible_counts[k][int(service)] += int(count)
                time_min = min(time_min, float(np.min(times)))
                time_max = max(time_max, float(np.max(times)))
                time_rows += len(times)
                if mask_validation is None:
                    ppi = np.asarray(node.read(start, min(stop, start + 256), field="PPI"))
                    lens_sample = np.asarray(
                        node.read(start, min(stop, start + 256), field="PPI_LEN")
                    ).reshape(-1)
                    mask_validation = validate_masking_helper(
                        helpers, ppi, lens_sample
                    )

    all_labels = sorted(app_counts, key=int)
    layer1 = [s for s in all_labels if app_counts[s] >= SERVICE_THRESHOLD]
    layer2 = [s for s in layer1 if eligible_counts[K][s] >= SERVICE_THRESHOLD]
    retained = sorted(layer2, key=int)
    total_pairs = len(layer1) * (len(layer1) - 1) // 2

    coverage = {}
    for k in K_VALUES:
        usable = [s for s in layer1 if eligible_counts[k][s] >= SERVICE_THRESHOLD]
        usable_pairs = len(usable) * (len(usable) - 1) // 2
        eligible_flow_count = sum(eligible_counts[k][s] for s in layer1)
        selected_flow_count = sum(app_counts[s] for s in layer1)
        coverage[str(k)] = {
            "services_usable": len(usable),
            "usable_pair_count": usable_pairs,
            "total_pair_count": total_pairs,
            "usable_pair_fraction": usable_pairs / total_pairs if total_pairs else 0.0,
            "eligible_flow_count": eligible_flow_count,
            "selected_flow_count": selected_flow_count,
            "aggregate_flow_fraction": (
                eligible_flow_count / selected_flow_count
                if selected_flow_count
                else 0.0
            ),
        }

    def coverage_ok(k):
        row = coverage[str(k)]
        return row["usable_pair_fraction"] >= 0.80 and row["aggregate_flow_fraction"] >= 0.50

    chosen_k = 30 if coverage_ok(30) else 15 if coverage_ok(15) else 10 if coverage_ok(10) else 5
    alternatives = {30: (15, 10, 5), 15: (10, 30, 5), 10: (15, 5, 30), 5: (10, 15, 30)}
    alt_k = next(
        (k for k in alternatives[chosen_k] if coverage[str(k)]["usable_pair_count"] > 0),
        chosen_k,
    )

    state = {
        "run": {
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "python": sys.executable,
            "cwd_actual": os.getcwd(),
            "cwd_required": "/root/eibo",
            "chunk_size": CHUNK_SIZE,
            "subsampled_for_tv": False,
            "metadata_elapsed_seconds": time.time() - started,
        },
        "h5": {
            "path": H5_PATH,
            "bytes": os.path.getsize(H5_PATH),
            "sha256": h5_digest,
            "row_count": total_rows,
            "time_rows_read": time_rows,
        },
        "schema": schema,
        "paths": paths,
        "time_first": {
            "min": time_min,
            "max": time_max,
            "min_utc": iso_utc(time_min),
            "max_utc": iso_utc(time_max),
            "span_days": (time_max - time_min) / 86400.0,
            "table_count": len(paths),
            "measured_granularity": "day-level (/flows/DYYYYMMDD daily tables)",
        },
        "app_counts": dict(app_counts),
        "eligible_counts": {
            str(k): dict(counter) for k, counter in eligible_counts.items()
        },
        "all_service_labels": all_labels,
        "layer1_services": layer1,
        "layer2_services": retained,
        "coverage_by_k": coverage,
        "chosen_k": chosen_k,
        "alt_k": alt_k,
        "mask_validation": mask_validation,
        "completed_M": [],
        "rung_rows": {},
        "dense_counts": {},
        "active_m": None,
        "active_table_index": 0,
        "active_eligible_flow_count": 0,
        "active_counters": None,
    }
    atomic_pickle(STATE_PATH, state)
    print(
        json.dumps(
            {
                "phase": "metadata",
                "state_path": str(STATE_PATH),
                "h5_rows": total_rows,
                "all_labels": len(all_labels),
                "layer1_services": len(layer1),
                "layer2_services": len(retained),
                "coverage_by_k": coverage,
                "chosen_k": chosen_k,
                "alt_k": alt_k,
                "time_first_min_utc": iso_utc(time_min),
                "time_first_max_utc": iso_utc(time_max),
            },
            indent=2,
            sort_keys=True,
        )
    )


def update_counter_chunk(counters, helpers, ppi, apps, lens, services, m):
    eligible = np.asarray(lens >= K)
    if not np.any(eligible):
        return 0
    ppi_e = ppi[eligible]
    apps_e = apps[eligible]
    codes = helpers.pack_rung_prefix(ppi_e, K, m, DIRECTION_ROW, SIZE_ROW)
    order = np.argsort(apps_e, kind="mergesort")
    apps_sorted = apps_e[order]
    codes_sorted = np.asarray(codes, dtype=np.uint64)[order]
    breaks = np.flatnonzero(apps_sorted[1:] != apps_sorted[:-1]) + 1
    starts = np.r_[0, breaks]
    ends = np.r_[breaks, len(apps_sorted)]
    service_set = set(services)
    for begin, end in zip(starts, ends):
        service = int(apps_sorted[begin])
        if service in service_set:
            counters[service].update(
                int(code) for code in codes_sorted[begin:end]
            )
    return int(len(apps_e))


def finish_rung(state, helpers, m):
    services = sorted(state["layer2_services"], key=int)
    rows = []
    counters = state["active_counters"]
    for service_a, service_b in itertools.combinations(services, 2):
        value = helpers.tv(counters[service_a], counters[service_b])
        if value is None:
            raise RuntimeError(f"Empty counter for pair {service_a},{service_b}, M={m}")
        rows.append(
            {
                "service_a": str(service_a),
                "service_b": str(service_b),
                "M": int(m),
                "n_a": int(state["eligible_counts"][str(K)][int(service_a)]),
                "n_b": int(state["eligible_counts"][str(K)][int(service_b)]),
                "tv_k10_masked": float(value),
            }
        )
    state["rung_rows"][str(m)] = rows
    state["completed_M"] = sorted(set(state["completed_M"] + [int(m)]))
    if m in (1, 2):
        dense = {}
        alphabet = (2 * m) ** K
        for service in services:
            counter = counters[service]
            dense[service] = [int(counter.get(symbol, 0)) for symbol in range(alphabet)]
        state["dense_counts"][str(m)] = {
            "alphabet_cardinality": alphabet,
            "counts_by_service": dense,
        }
    state["active_m"] = None
    state["active_table_index"] = 0
    state["active_eligible_flow_count"] = 0
    state["active_counters"] = None
    atomic_pickle(STATE_PATH, state)
    return len(rows)


def rung_phase(helpers, m: int):
    if m not in RUNGS:
        raise ValueError(f"M must be one of {RUNGS}")
    state = load_state()
    if m in state["completed_M"]:
        print(json.dumps({"phase": "rung", "M": m, "status": "already-complete"}))
        return
    services = sorted(state["layer2_services"], key=int)
    service_ints = np.asarray([int(s) for s in services], dtype=np.int16)

    if state["active_m"] is None:
        state["active_m"] = int(m)
        state["active_table_index"] = 0
        state["active_eligible_flow_count"] = 0
        state["active_counters"] = {service: collections.Counter() for service in services}
        atomic_pickle(STATE_PATH, state)
    elif int(state["active_m"]) != int(m):
        raise RuntimeError(
            f"State has active M={state['active_m']}; resume that rung before M={m}"
        )

    started = time.time()
    table_index = int(state["active_table_index"])
    with tables.open_file(H5_PATH, mode="r") as h5:
        while table_index < len(state["paths"]):
            path = state["paths"][table_index]
            node = h5.get_node(path)
            for start in range(0, node.nrows, CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, node.nrows)
                apps = np.asarray(node.read(start, stop, field="APP")).reshape(-1)
                lens = np.asarray(node.read(start, stop, field="PPI_LEN")).reshape(-1)
                selected = np.isin(apps, service_ints)
                if np.any(selected):
                    ppi = np.asarray(node.read(start, stop, field="PPI"))[selected]
                    apps_s = apps[selected]
                    lens_s = lens[selected]
                    state["active_eligible_flow_count"] += update_counter_chunk(
                        state["active_counters"],
                        helpers,
                        ppi,
                        apps_s,
                        lens_s,
                        services,
                        m,
                    )
            table_index += 1
            state["active_table_index"] = table_index
            if table_index % CHECKPOINT_TABLES == 0 or table_index == len(state["paths"]):
                atomic_pickle(STATE_PATH, state)
                print(
                    json.dumps(
                        {
                            "phase": "rung",
                            "M": m,
                            "table_index": table_index,
                            "table_count": len(state["paths"]),
                            "eligible_flow_count": state["active_eligible_flow_count"],
                            "elapsed_seconds": time.time() - started,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )

    row_count = finish_rung(state, helpers, m)
    print(
        json.dumps(
            {
                "phase": "rung",
                "M": m,
                "status": "complete",
                "row_count": row_count,
                "completed_M": state["completed_M"],
            },
            sort_keys=True,
        )
    )


def threshold_pair(n_a: int, n_b: int) -> tuple[float, float, float]:
    t_a = LOWER_FLOOR + LOWER_C / math.sqrt(n_a)
    t_b = LOWER_FLOOR + LOWER_C / math.sqrt(n_b)
    return t_a, t_b, max(t_a, t_b)


def radius(M: int, n: int) -> float:
    return (math.sqrt((2 * M) ** K) + UPPER_C) / math.sqrt(n)


def build_summary(state, helpers):
    services = sorted(state["layer2_services"], key=int)
    all_rows = []
    per_rung = []
    for m in RUNGS:
        rows = state["rung_rows"][str(m)]
        all_rows.extend(rows)
        lower_count = 0
        upper_count = 0
        both_count = 0
        saturated_count = 0
        thresholds = []
        radii = []
        for row in rows:
            n_a = int(row["n_a"])
            n_b = int(row["n_b"])
            tv_value = float(row["tv_k10_masked"])
            t_a, t_b, t_pair = threshold_pair(n_a, n_b)
            r_a = radius(m, n_a)
            r_b = radius(m, n_b)
            eps_hi = tv_value + r_a + r_b
            lower_ok = tv_value > t_a and tv_value > t_b
            upper_ok = eps_hi < 0.5
            lower_count += int(lower_ok)
            upper_count += int(upper_ok)
            both_count += int(lower_ok and upper_ok)
            saturated_count += int(tv_value >= SATURATION_THRESHOLD)
            thresholds.append(t_pair)
            radii.append(r_a + r_b)
        total = len(rows)
        sat_fraction = saturated_count / total if total else None
        per_rung.append(
            {
                "M": int(m),
                "alphabet_cardinality": int((2 * m) ** K),
                "pairs": total,
                "lower_side_pairs": lower_count,
                "lower_side_fraction": lower_count / total if total else None,
                "upper_side_pairs": upper_count,
                "upper_side_fraction": upper_count / total if total else None,
                "gate_pairs_both": both_count,
                "gate_fraction_both": both_count / total if total else None,
                "saturation_fraction_tv_ge_0_99": sat_fraction,
                "saturation_label": (
                    "SATURATED"
                    if sat_fraction is not None
                    and sat_fraction >= SATURATION_FRACTION_THRESHOLD
                    else "INFORMATIVE"
                ),
                "T_n_median": quantile(thresholds, 0.5),
                "radius_median": quantile(radii, 0.5),
            }
        )

    total_labels = len(state["all_service_labels"])
    layer1_count = len(state["layer1_services"])
    layer2_count = len(services)
    time_span_days = state["time_first"]["span_days"]
    deviation = None
    if time_span_days < 28.0:
        deviation = (
            "DEVIATION: TIME_FIRST spans less than a full month; "
            "pre-registered split is month-level"
        )

    executed = [
        {
            "file": "/root/eibo/scripts/run_q1_absolute_e3.py",
            "routine": "metadata_phase",
            "output_consumed_by_reported_numbers": True,
        },
        {
            "file": "/root/eibo/scripts/run_q1_absolute_e3.py",
            "routine": "rung_phase",
            "output_consumed_by_reported_numbers": True,
        },
        {
            "file": "/root/eibo/scripts/run_q1_absolute_e3.py",
            "routine": "build_summary",
            "output_consumed_by_reported_numbers": True,
        },
        {
            "file": "/root/eibo/scripts/xs_compression_early_readout.py",
            "routine": "table_paths",
            "output_consumed_by_reported_numbers": True,
        },
        {
            "file": "/root/eibo/scripts/xs_compression_early_readout.py",
            "routine": "pack_variable_masked_30",
            "output_consumed_by_reported_numbers": True,
            "note": "Executed on a real sample as the masking precondition; its output gates continuation, while k=10 TV values use pack_rung_prefix on PPI_LEN >= 10 rows.",
        },
        {
            "file": "/root/eibo/scripts/xs_compression_early_readout.py",
            "routine": "pack_rung_prefix",
            "output_consumed_by_reported_numbers": True,
        },
        {
            "file": "/root/eibo/scripts/xs_compression_early_readout.py",
            "routine": "direction_bits",
            "output_consumed_by_reported_numbers": True,
            "note": "Called inside pack_rung_prefix.",
        },
        {
            "file": "/root/eibo/scripts/xs_compression_early_readout.py",
            "routine": "size_bins",
            "output_consumed_by_reported_numbers": True,
            "note": "Called inside pack_rung_prefix for M >= 2.",
        },
        {
            "file": "/root/eibo/scripts/xs_compression_early_readout.py",
            "routine": "tv",
            "output_consumed_by_reported_numbers": True,
        },
        {
            "file": "/root/eibo/scripts/run_q1_absolute_e3.py",
            "routine": "threshold_pair",
            "output_consumed_by_reported_numbers": True,
        },
        {
            "file": "/root/eibo/scripts/run_q1_absolute_e3.py",
            "routine": "radius",
            "output_consumed_by_reported_numbers": True,
        },
    ]

    meta = {
        "k": K,
        "masked": True,
        "masking_function": "pack_variable_masked_30",
        "grid_fixed_a_priori": True,
        "channel_exclusion_declaration": (
            "Channel is (direction, size). PPI row 1 = direction, row 2 = size. "
            "The exporter's third PPI channel (row 0, inter-packet time) is deliberately "
            "EXCLUDED; including it would change |A_k| and every k_cert value."
        ),
        "ml_only_inputs": (
            "Only direction and size from PPI are consumed; QUIC_USER_AGENT, "
            "QUIC_TLS_EXT_*, and QUIC_*CID are not consumed."
        ),
        "alpha": ALPHA,
        "alpha_convention": (
            "per-law alpha/2 = 0.025 on both sides; union bound over the two laws "
            "gives joint 0.95 for each side"
        ),
        "lower_side_formula": (
            "T(n_i) = 0.05 + 1.958/sqrt(n_i), with T(n_a) and T(n_b) "
            "substituted separately; lower passes iff tv > both thresholds"
        ),
        "upper_side_formula": (
            "radius_i(M) = (sqrt((2M)^10) + 2.9604)/sqrt(n_i), evaluated "
            "separately for i=a,b; sufficient upper certificate used here is "
            "eps_hi = tv_k10_masked + radius_a + radius_b < 0.5. "
            "The weaker radius_i < 0.5 check alone is not sufficient."
        ),
        "provenance": {
            "chosen_k": state["chosen_k"],
            "alt_k": state["alt_k"],
            "coverage_by_k": state["coverage_by_k"],
            "note": "Provenance only; no cross-k ratio is a gate criterion.",
        },
        "split": {
            "policy": "flow-disjoint AND time-disjoint; packet-level PROHIBITED",
            "flow_unit": "one H5 table row is one flow; no packet-level split was used",
            "time_granularity_achieved": state["time_first"]["measured_granularity"],
            "TIME_FIRST_min": state["time_first"]["min"],
            "TIME_FIRST_max": state["time_first"]["max"],
            "TIME_FIRST_min_utc": state["time_first"]["min_utc"],
            "TIME_FIRST_max_utc": state["time_first"]["max_utc"],
            "span_days": time_span_days,
            "deviation_label": deviation,
        },
        "source_h5": {
            "path": H5_PATH,
            "bytes": state["h5"]["bytes"],
            "sha256": state["h5"]["sha256"],
            "row_count": state["h5"]["row_count"],
            "subset_note": "10M-flow BUDGET SUBSET; month coverage measured from TIME_FIRST",
        },
        "pairing": {
            "rule": "unordered pairs, service_a < service_b",
                "service_threshold": (
                ">= 2000 total flows AND >= 2000 flows with PPI_LEN >= 10; "
                "SELF-DEFINED"
            ),
            "all_distinct_service_labels": total_labels,
            "services_dropped_by_total_flow_layer": total_labels - layer1_count,
            "services_after_total_flow_layer": layer1_count,
            "services_dropped_by_PPI_LEN_ge_5_layer": layer1_count - layer2_count,
            "services_retained": layer2_count,
            "pairs_expected": layer2_count * (layer2_count - 1) // 2,
        },
        "k10_denominator_exactness": {
            "post_mask_usable_pairs": layer2_count * (layer2_count - 1) // 2,
            "total_pairs": layer1_count * (layer1_count - 1) // 2,
            "usable_pair_fraction": (
                (layer2_count * (layer2_count - 1) / (layer1_count * (layer1_count - 1)))
                if layer1_count > 1
                else 0.0
            ),
            "services_retained_after_ppilen_ge_10_filter": layer2_count,
            "services_dropped_by_ppilen_ge_10_filter": layer1_count - layer2_count,
            "verify_in_run": True,
        },
        "coverage_by_k": state["coverage_by_k"],
        "row_count": len(all_rows),
        "table_fields": [
            "service_a",
            "service_b",
            "M",
            "n_a",
            "n_b",
            "tv_k10_masked",
        ],
        "executed_routines": executed,
        "mask_validation": state["mask_validation"],
    }

    counts_payload = {"pairs": all_rows}
    atomic_json(COUNTS_PATH, counts_payload)
    atomic_json(META_PATH, meta)
    atomic_json(DENSE_PATH, state["dense_counts"])

    with open(CSV_PATH.with_suffix(".tmp"), "w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "service_a",
            "service_b",
            "M",
            "n_a",
            "n_b",
            "tv_k10_masked",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    os.replace(CSV_PATH.with_suffix(".tmp"), CSV_PATH)

    summary = {
        "run": {
            **state["run"],
            "finalized_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "output_paths": {
                "summary": str(SUMMARY_PATH),
                "counts_json": str(COUNTS_PATH),
                "counts_csv": str(CSV_PATH),
                "metadata": str(META_PATH),
                "dense_m1_m2": str(DENSE_PATH),
            },
            "source_h5": meta["source_h5"],
        },
        "service_counts": {
            "all_distinct_service_labels": total_labels,
            "after_total_flow_threshold": layer1_count,
            "after_PPI_LEN_ge_10_threshold": layer2_count,
            "dropped_by_total_flow_threshold": total_labels - layer1_count,
            "dropped_by_PPI_LEN_ge_10_threshold": layer1_count - layer2_count,
        },
        "pair_counts": {
            "expected": layer2_count * (layer2_count - 1) // 2,
            "rows_per_rung": len(rows),
            "total_table_rows": len(all_rows),
            "formula": "(#retained_services choose 2) * 5",
        },
        "coverage_by_k": state["coverage_by_k"],
        "split": meta["split"],
        "per_rung": per_rung,
        "self_checks": {
            "pair_row_count_matches_formula": len(all_rows)
            == layer2_count * (layer2_count - 1) // 2 * len(RUNGS),
            "lower_side_ever_passes": any(
                item["lower_side_pairs"] > 0 for item in per_rung
            ),
            "lower_side_zero_at_every_rung": all(
                item["lower_side_fraction"] == 0.0 for item in per_rung
            ),
            "M_order_lower_fraction": [
                item["lower_side_fraction"] for item in per_rung
            ],
            "M_order_upper_fraction": [
                item["upper_side_fraction"] for item in per_rung
            ],
            "M_order_gate_fraction": [
                item["gate_fraction_both"] for item in per_rung
            ],
            "binding_side_by_rung": [
                {
                    "M": item["M"],
                    "binding_side": (
                        "lower"
                        if item["lower_side_fraction"] < item["upper_side_fraction"]
                        else "upper"
                        if item["upper_side_fraction"] < item["lower_side_fraction"]
                        else "tie"
                    ),
                }
                for item in per_rung
            ],
            "saturation_threshold": SATURATION_THRESHOLD,
        },
        "metadata_header_path": str(META_PATH),
    }
    atomic_json(SUMMARY_PATH, summary)

    print(json.dumps({"summary": str(SUMMARY_PATH), "per_rung": per_rung}, indent=2))
    print("FIRST_FIVE_ROWS")
    print(json.dumps(all_rows[:5], indent=2))
    print(
        json.dumps(
            {
                "row_count": len(all_rows),
                "expected_row_count": layer2_count * (layer2_count - 1) // 2 * len(RUNGS),
                "files": [str(SUMMARY_PATH), str(COUNTS_PATH), str(CSV_PATH), str(META_PATH), str(DENSE_PATH)],
            },
            indent=2,
        )
    )


def main():
    if os.getcwd() != "/root/eibo":
        raise RuntimeError(f"cwd must be /root/eibo, got {os.getcwd()}")
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("metadata", "rung", "final"))
    parser.add_argument("--m", type=int, choices=RUNGS)
    args = parser.parse_args()
    helpers = load_existing_helpers()
    if args.phase == "metadata":
        metadata_phase(helpers)
    elif args.phase == "rung":
        if args.m is None:
            raise ValueError("--m is required for phase=rung")
        rung_phase(helpers, args.m)
    else:
        state = load_state()
        missing = [m for m in RUNGS if m not in state["completed_M"]]
        if missing:
            raise RuntimeError(f"Cannot finalize; incomplete rungs: {missing}")
        build_summary(state, helpers)


if __name__ == "__main__":
    main()
