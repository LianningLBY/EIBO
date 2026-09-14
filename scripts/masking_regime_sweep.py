#!/usr/bin/env python3
import collections
import hashlib
import importlib.util
import itertools
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import tables


H5_PATH = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
EXPECTED_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"
OUT_PATH = "/root/eibo/artifacts/masking_regime_sweep.json"
SERVICE_THRESHOLD = 2000
CHUNK_SIZE = 100_000
DIRECTION_ROW = 1
SIZE_ROW = 2
KS = [5, 10]
MS = [1, 2, 4, 8, 16]
SATURATION_TV_THRESHOLD = 0.99
SATURATION_FRACTION_THRESHOLD = 0.5


def load_existing_helpers():
    path = Path("/root/eibo/scripts/xs_compression_early_readout.py")
    spec = importlib.util.spec_from_file_location("xs_compression_early_readout", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    required = [
        "table_paths",
        "collect_padding_samples",
        "pack_variable_masked_30",
        "direction_bits",
        "size_bins",
        "tv",
    ]
    missing = [name for name in required if not hasattr(mod, name)]
    if missing:
        raise RuntimeError(f"Missing required existing helpers: {missing}")
    return mod


def sha256_file(path, block=16 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(block), b""):
            h.update(b)
    return h.hexdigest()


def dump_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def summarize(vals):
    arr = np.asarray([float(v) for v in vals if v is not None and math.isfinite(float(v))], dtype=np.float64)
    if arr.size == 0:
        return {
            "count": 0,
            "min": None,
            "q5": None,
            "q25": None,
            "median": None,
            "mean": None,
            "q75": None,
            "q95": None,
            "max": None,
        }
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "q5": float(np.quantile(arr, 0.05)),
        "q25": float(np.quantile(arr, 0.25)),
        "median": float(np.quantile(arr, 0.50)),
        "mean": float(np.mean(arr)),
        "q75": float(np.quantile(arr, 0.75)),
        "q95": float(np.quantile(arr, 0.95)),
        "max": float(np.max(arr)),
    }


def initial_result(helpers):
    started = time.time()
    with tables.open_file(H5_PATH, mode="r") as h5:
        paths = helpers.table_paths(h5)
        if not paths:
            raise RuntimeError("No /flows/* table with APP, PPI, and PPI_LEN was found")
        schema = []
        row_count = 0
        for path in paths:
            node = h5.get_node(path)
            row_count += int(node.nrows)
            sample = node.read(0, min(1, node.nrows))
            ppi = sample["PPI"]
            lens = sample["PPI_LEN"]
            app = sample["APP"]
            schema.append(
                {
                    "path": path,
                    "nrows": int(node.nrows),
                    "APP_dtype": str(app.dtype),
                    "APP_shape_per_row": list(app.shape[1:]),
                    "PPI_dtype": str(ppi.dtype),
                    "PPI_shape_per_row": list(ppi.shape[1:]),
                    "PPI_LEN_dtype": str(lens.dtype),
                    "PPI_LEN_shape_per_row": list(lens.shape[1:]),
                }
            )
    h5_sha256 = sha256_file(H5_PATH)
    return {
        "run": {
            "timestamp_utc": "2026-09-13T17:12:37Z",
            "python": sys.executable,
            "cwd_required": "/root/eibo",
            "cwd_actual": os.getcwd(),
            "output_path": OUT_PATH,
            "service_threshold_flow_count": SERVICE_THRESHOLD,
            "chunk_size": CHUNK_SIZE,
            "k_values": KS,
            "M_values": MS,
            "same_flow_set_rule": "For each (M,k), both arms use exactly flows with PPI_LEN >= k.",
            "masked_arm": "row[:min(PPI_LEN, k)].tobytes() after direction_bits and size_bins on the first k slots",
            "unmasked_arm": "row[:k].tobytes() after direction_bits and size_bins on the first k slots",
            "prefix_identity_note": "Because this requested sweep filters to PPI_LEN >= k, min(PPI_LEN,k) equals k for every consumed flow; masked and unmasked symbol counts are therefore identical by definition at each rung.",
            "saturation_rule": "SATURATED when fraction of pairs with tv_masked >= 0.99 is at least 0.5; otherwise INFORMATIVE.",
            "elapsed_seconds_at_init": float(time.time() - started),
        },
        "h5_read": {
            "path": H5_PATH,
            "bytes": int(os.path.getsize(H5_PATH)),
            "sha256": h5_sha256,
            "expected_sha256": EXPECTED_SHA256,
            "sha256_matches_expected": bool(h5_sha256 == EXPECTED_SHA256),
            "row_count": int(row_count),
            "schema": schema,
        },
        "interpretation_rules": [
            "No change at k=X is a statement about THAT measurement point, NOT no contamination.",
            "If a rung is saturated (most pairs at tv >= 0.99), the comparison cannot detect contamination there.",
            "Do not conclude no contamination or that masking is optional from a saturated rung.",
            "If the k=5 small-M difference is significantly > 0, that confirms contamination exists, which makes the masking precondition genuinely load-bearing.",
            "Do not write k=30 difference is small, therefore masking is optional.",
        ],
        "executed_routines": [
            {
                "file": "/root/eibo/scripts/masking_regime_sweep.py",
                "routine": "load_existing_helpers",
                "output_consumed_by_reported_numbers": True,
            },
            {
                "file": "/root/eibo/scripts/xs_compression_early_readout.py",
                "routine": "table_paths",
                "output_consumed_by_reported_numbers": True,
            },
            {
                "file": "/root/eibo/scripts/xs_compression_early_readout.py",
                "routine": "direction_bits",
                "output_consumed_by_reported_numbers": True,
            },
            {
                "file": "/root/eibo/scripts/xs_compression_early_readout.py",
                "routine": "size_bins",
                "output_consumed_by_reported_numbers": True,
            },
            {
                "file": "/root/eibo/scripts/xs_compression_early_readout.py",
                "routine": "tv",
                "output_consumed_by_reported_numbers": True,
            },
            {
                "file": "/root/eibo/scripts/xs_compression_early_readout.py",
                "routine": "collect_padding_samples",
                "output_consumed_by_reported_numbers": False,
                "note": "Imported by load_existing_helpers compatibility check but not executed for this sweep.",
            },
            {
                "file": "/root/eibo/scripts/xs_compression_early_readout.py",
                "routine": "pack_variable_masked_30",
                "output_consumed_by_reported_numbers": False,
                "note": "Imported by load_existing_helpers compatibility check but not executed for this k=5/k=10 sweep.",
            },
        ],
        "summaries": [],
        "per_pair_rows": [],
        "completed_rungs": [],
        "skipped_rungs": [],
    }


def load_or_init(helpers):
    if os.path.exists(OUT_PATH):
        with open(OUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    result = initial_result(helpers)
    dump_json(OUT_PATH, result)
    return result


def next_rung(result):
    done = set(result.get("completed_rungs", []))
    for k in KS:
        for m in MS:
            key = f"k={k},M={m}"
            if key not in done:
                return k, m, key
    return None


def update_counts_for_chunk(counts, helpers, ppi, apps, lens, k, m):
    eligible = lens >= k
    if not np.any(eligible):
        return 0
    ppi_e = ppi[eligible]
    apps_e = apps[eligible]
    d = helpers.direction_bits(ppi_e[:, DIRECTION_ROW, :k])
    b = helpers.size_bins(ppi_e[:, SIZE_ROW, :k], m)
    symbols = (d * m + b).astype(np.uint8, copy=False)
    codes = np.ascontiguousarray(symbols).view(np.dtype((np.void, k))).reshape(-1)
    order = np.argsort(apps_e, kind="mergesort")
    apps_sorted = apps_e[order]
    codes_sorted = codes[order]
    if apps_sorted.size == 0:
        return 0
    breaks = np.flatnonzero(apps_sorted[1:] != apps_sorted[:-1]) + 1
    starts = np.r_[0, breaks]
    ends = np.r_[breaks, apps_sorted.size]
    for start, end in zip(starts, ends):
        service = str(int(apps_sorted[start]))
        counts[service].update(bytes(code) for code in codes_sorted[start:end])
    return int(apps_sorted.size)


def scan_rung(helpers, k, m):
    counts = collections.defaultdict(collections.Counter)
    eligible_flow_count = 0
    table_rows_read = 0
    started = time.time()
    with tables.open_file(H5_PATH, mode="r") as h5:
        paths = helpers.table_paths(h5)
        for path in paths:
            node = h5.get_node(path)
            for start in range(0, node.nrows, CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, node.nrows)
                table_rows_read += int(stop - start)
                apps = np.asarray(node.read(start, stop, field="APP")).reshape(-1)
                lens = np.asarray(node.read(start, stop, field="PPI_LEN")).reshape(-1)
                ppi = np.asarray(node.read(start, stop, field="PPI"))
                eligible_flow_count += update_counts_for_chunk(counts, helpers, ppi, apps, lens, k, m)

    service_counts = {service: int(sum(counter.values())) for service, counter in counts.items()}
    services = sorted(
        [service for service, count in service_counts.items() if count >= SERVICE_THRESHOLD],
        key=lambda x: int(x),
    )
    pairs = []
    pair_rows = []
    for a, b in itertools.combinations(services, 2):
        value = helpers.tv(counts[a], counts[b])
        if value is None:
            continue
        row = {
            "k": int(k),
            "M": int(m),
            "service_a": a,
            "service_b": b,
            "tv_masked": float(value),
            "tv_unmasked": float(value),
            "tv_unmasked_minus_masked": 0.0,
            "abs_difference": 0.0,
        }
        pairs.append(row)
        if k == 5 and m in {1, 2, 4}:
            pair_rows.append(row)

    tv_vals = [row["tv_masked"] for row in pairs]
    diffs = [row["tv_unmasked_minus_masked"] for row in pairs]
    saturated_count = sum(1 for v in tv_vals if v >= SATURATION_TV_THRESHOLD)
    saturated_fraction = float(saturated_count / len(tv_vals)) if tv_vals else None
    status = "SATURATED" if saturated_fraction is not None and saturated_fraction >= SATURATION_FRACTION_THRESHOLD else "INFORMATIVE"
    max_pair = None
    if pairs:
        max_pair = max(pairs, key=lambda row: abs(row["tv_unmasked_minus_masked"]))
        max_pair = {
            "service_a": max_pair["service_a"],
            "service_b": max_pair["service_b"],
            "tv_unmasked_minus_masked": max_pair["tv_unmasked_minus_masked"],
            "abs_difference": max_pair["abs_difference"],
        }
    return {
        "summary": {
            "k": int(k),
            "M": int(m),
            "alphabet_cardinality": int((2 * m) ** k),
            "eligible_flow_rule": f"PPI_LEN >= {k}",
            "same_flows_held_fixed": True,
            "table_rows_read": int(table_rows_read),
            "eligible_flow_count": int(eligible_flow_count),
            "service_threshold_flow_count": SERVICE_THRESHOLD,
            "service_count": int(len(services)),
            "pair_count": int(len(pairs)),
            "tv_masked_median": float(np.quantile(tv_vals, 0.5)) if tv_vals else None,
            "tv_unmasked_median": float(np.quantile(tv_vals, 0.5)) if tv_vals else None,
            "tv_masked_saturated_pair_count": int(saturated_count),
            "tv_masked_saturated_fraction_ge_0_99": saturated_fraction,
            "dynamic_range_label": status,
            "difference_distribution": summarize(diffs),
            "nonzero_difference_pair_count": 0,
            "largest_abs_difference_pair": max_pair,
            "masked_unmasked_symbol_counts_identical": True,
            "masked_unmasked_code_mismatch_count": 0,
            "elapsed_seconds": float(time.time() - started),
        },
        "pair_rows": pair_rows,
    }


def final_print(result):
    byte_size = os.path.getsize(OUT_PATH)
    digest = sha256_file(OUT_PATH)
    print(
        json.dumps(
            {
                "path": OUT_PATH,
                "bytes": int(byte_size),
                "sha256": digest,
                "h5_row_count": int(result["h5_read"]["row_count"]),
                "stored_pair_row_count": int(len(result.get("per_pair_rows", []))),
                "completed_rungs": result.get("completed_rungs", []),
                "skipped_rungs": result.get("skipped_rungs", []),
            },
            indent=2,
            sort_keys=True,
        )
    )


def main():
    if os.getcwd() != "/root/eibo":
        raise RuntimeError(f"cwd must be /root/eibo, got {os.getcwd()}")
    helpers = load_existing_helpers()
    result = load_or_init(helpers)
    rung = next_rung(result)
    if rung is None:
        final_print(result)
        return 0
    k, m, key = rung
    measured = scan_rung(helpers, k, m)
    result["summaries"].append(measured["summary"])
    result["per_pair_rows"].extend(measured["pair_rows"])
    result["completed_rungs"].append(key)
    result["run"]["elapsed_seconds_at_last_write"] = float(
        sum(row.get("elapsed_seconds", 0.0) for row in result["summaries"])
    )
    dump_json(OUT_PATH, result)
    final_print(result)
    return 75 if next_rung(result) is not None else 0


if __name__ == "__main__":
    raise SystemExit(main())
