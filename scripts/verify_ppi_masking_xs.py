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
OUT_PATH = "/root/eibo/artifacts/masking_verification.json"
SERVICE_THRESHOLD = 2000
PADDING_SAMPLE_SIZE = 200_000
PADDING_SAMPLE_SEED = 20260913
CHUNK_SIZE = 100_000
DIRECTION_ROW = 1
SIZE_ROW = 2
M = 16


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


def summarize(vals):
    arr = np.asarray([float(v) for v in vals if v is not None and math.isfinite(float(v))], dtype=np.float64)
    if arr.size == 0:
        return {"count": 0}
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


def quantiles_from_len_counts(counter):
    total = sum(counter.values())
    if total == 0:
        return {}
    targets = [
        ("q1", 0.01),
        ("q5", 0.05),
        ("q25", 0.25),
        ("median", 0.50),
        ("q75", 0.75),
        ("q95", 0.95),
        ("q99", 0.99),
        ("q100", 1.00),
    ]
    out = {}
    seen = 0
    i = 0
    for value, count in sorted(counter.items()):
        seen += count
        while i < len(targets) and seen >= math.ceil(targets[i][1] * total):
            out[targets[i][0]] = int(value)
            i += 1
    return out


def counter_to_json(counter):
    return {str(int(k)): int(v) for k, v in sorted(counter.items(), key=lambda kv: int(kv[0]))}


def add_symbol_codes(counts, apps, ppi, lens, helpers):
    d = helpers.direction_bits(ppi[:, DIRECTION_ROW, :30])
    b = helpers.size_bins(ppi[:, SIZE_ROW, :30], M)
    symbols = (d * M + b).astype(np.uint8, copy=False)
    for app, row, ln in zip(apps, symbols, lens):
        service = str(int(app))
        kk = max(0, min(int(ln), 30))
        counts["masked"][service][row[:kk].tobytes()] += 1
        counts["unmasked"][service][row.tobytes()] += 1


def validate_schema(h5, paths):
    if not paths:
        raise RuntimeError("No /flows/* table with APP, PPI, PPI_LEN was found")
    schema = []
    for path in paths:
        node = h5.get_node(path)
        row = node.read(0, min(1, node.nrows))
        ppi = row["PPI"]
        lens = row["PPI_LEN"]
        schema.append(
            {
                "path": path,
                "nrows": int(node.nrows),
                "PPI_dtype": str(ppi.dtype),
                "PPI_shape_per_row": list(ppi.shape[1:]),
                "PPI_LEN_dtype": str(lens.dtype),
                "PPI_LEN_shape_per_row": list(lens.shape[1:]),
            }
        )
        if ppi.dtype != np.dtype("int32") or list(ppi.shape[1:]) != [3, 30] or lens.dtype != np.dtype("uint16"):
            raise RuntimeError("h5py schema mismatch: " + json.dumps(schema, sort_keys=True))
    return schema


def main():
    start = time.time()
    helpers = load_existing_helpers()
    digest = sha256_file(H5_PATH)
    h5_bytes = os.path.getsize(H5_PATH)

    len_counts = collections.Counter()
    app_counts = collections.Counter()
    len_ge5_counts = collections.Counter()
    padding_hist = collections.Counter()
    padding_by_row = {"row0": collections.Counter(), "row1": collections.Counter(), "row2": collections.Counter()}
    sampled_tail_flows = 0
    sampled_tail_scalar_slots = 0

    with tables.open_file(H5_PATH, "r") as h5:
        paths = helpers.table_paths(h5)
        schema = validate_schema(h5, paths)
        node_offsets = []
        total_rows = 0
        for path in paths:
            node_offsets.append(total_rows)
            total_rows += int(h5.get_node(path).nrows)

        sample_size = min(PADDING_SAMPLE_SIZE, total_rows)
        rng = np.random.default_rng(PADDING_SAMPLE_SEED)
        sample_ids = np.sort(rng.choice(total_rows, size=sample_size, replace=False))
        sample_cursor = 0

        for node_index, path in enumerate(paths):
            node = h5.get_node(path)
            base = node_offsets[node_index]
            for start_row in range(0, node.nrows, CHUNK_SIZE):
                stop_row = min(node.nrows, start_row + CHUNK_SIZE)
                apps = node.read(start_row, stop_row, field="APP")
                lens = node.read(start_row, stop_row, field="PPI_LEN")
                app_counts.update(map(int, apps))
                len_counts.update(map(int, lens))
                vals, cnts = np.unique(apps[lens >= 5], return_counts=True)
                for v, c in zip(vals, cnts):
                    len_ge5_counts[int(v)] += int(c)

                g_start = base + start_row
                g_stop = base + stop_row
                while sample_cursor < sample_size and sample_ids[sample_cursor] < g_start:
                    sample_cursor += 1
                sample_end = sample_cursor
                while sample_end < sample_size and sample_ids[sample_end] < g_stop:
                    sample_end += 1
                if sample_end > sample_cursor:
                    local = sample_ids[sample_cursor:sample_end] - g_start
                    ppi_sample = node.read(start_row, stop_row, field="PPI")[local]
                    lens_sample = lens[local]
                    _, row_counters = helpers.collect_padding_samples(ppi_sample, lens_sample, limit=0)
                    for row_name, ctr in row_counters.items():
                        padding_by_row[row_name].update(ctr)
                        padding_hist.update(ctr)
                    for ln in lens_sample:
                        tail = max(0, 30 - int(ln))
                        if tail:
                            sampled_tail_flows += 1
                            sampled_tail_scalar_slots += 3 * tail
                    sample_cursor = sample_end

        threshold_services = [str(k) for k, v in app_counts.items() if v >= SERVICE_THRESHOLD]
        threshold_services.sort(key=lambda s: (-app_counts[int(s)], int(s)))
        usable_k5_services = [s for s in threshold_services if len_ge5_counts[int(s)] >= SERVICE_THRESHOLD]
        service_ints = np.asarray([int(s) for s in threshold_services], dtype=app_counts and np.asarray(list(app_counts.keys())).dtype or np.int64)
        counts = {"masked": collections.defaultdict(collections.Counter), "unmasked": collections.defaultdict(collections.Counter)}

        # Existing masked helper is exercised on real rows to verify the imported masking path is usable.
        helper_validation_codes = 0
        for node_index, path in enumerate(paths):
            node = h5.get_node(path)
            for start_row in range(0, node.nrows, CHUNK_SIZE):
                stop_row = min(node.nrows, start_row + CHUNK_SIZE)
                apps = node.read(start_row, stop_row, field="APP")
                selected = np.isin(apps, service_ints)
                if not np.any(selected):
                    continue
                lens = node.read(start_row, stop_row, field="PPI_LEN")[selected]
                ppi = node.read(start_row, stop_row, field="PPI")[selected]
                apps_s = apps[selected]
                if helper_validation_codes == 0:
                    existing_codes, existing_use = helpers.pack_variable_masked_30(
                        ppi[: min(128, len(ppi))],
                        lens[: min(128, len(lens))],
                        DIRECTION_ROW,
                        SIZE_ROW,
                    )
                    helper_validation_codes = len(existing_codes)
                    if int(np.sum(existing_use)) != helper_validation_codes:
                        raise RuntimeError("pack_variable_masked_30 validation returned an unexpected use mask")
                add_symbol_codes(counts, apps_s, ppi, lens, helpers)

    pairs = []
    for a, b in itertools.combinations(threshold_services, 2):
        mtv = helpers.tv(counts["masked"][a], counts["masked"][b])
        utv = helpers.tv(counts["unmasked"][a], counts["unmasked"][b])
        pairs.append(
            {
                "service_a": a,
                "service_b": b,
                "masked_tv": mtv,
                "unmasked_tv": utv,
                "unmasked_minus_masked": None if mtv is None or utv is None else utv - mtv,
                "abs_difference": None if mtv is None or utv is None else abs(utv - mtv),
            }
        )

    max_pair = max((p for p in pairs if p["abs_difference"] is not None), key=lambda p: p["abs_difference"], default=None)
    total_pairs = len(threshold_services) * (len(threshold_services) - 1) // 2
    usable_pairs = len(usable_k5_services) * (len(usable_k5_services) - 1) // 2
    total_len = sum(len_counts.values())
    q = quantiles_from_len_counts(len_counts)
    result = {
        "run": {
            "timestamp_utc": "2026-09-13T16:39:11Z",
            "elapsed_seconds": time.time() - start,
            "python": sys.executable,
            "cwd_required": "/root/eibo",
            "output_path": OUT_PATH,
            "real_h5_full_scan_rows": int(total_len),
            "subsampled_for_tv": False,
        },
        "h5_read": {
            "path": H5_PATH,
            "bytes": int(h5_bytes),
            "sha256": digest,
            "expected_sha256": EXPECTED_SHA256,
            "sha256_matches_expected": digest == EXPECTED_SHA256,
            "schema": schema,
        },
        "helpers_reused": {
            "source": "/root/eibo/scripts/xs_compression_early_readout.py",
            "collect_padding_samples": True,
            "pack_variable_masked_30": True,
            "pack_variable_masked_30_validation_code_count": int(helper_validation_codes),
            "direction_bits": True,
            "size_bins": True,
            "tv": True,
        },
        "padding_value_distribution": {
            "sampling_method": "uniform random sample without replacement over global h5 row indices",
            "random_seed": PADDING_SAMPLE_SEED,
            "sampled_flow_count": int(sample_size),
            "sampled_tail_flow_count": int(sampled_tail_flows),
            "sampled_tail_scalar_slot_count_all_channels": int(sampled_tail_scalar_slots),
            "histogram_all_tail_values_all_channels": counter_to_json(padding_hist),
            "histogram_by_ppi_row": {row: counter_to_json(ctr) for row, ctr in padding_by_row.items()},
        },
        "masked_vs_unmasked_k30_tv": {
            "definition": "M=16 direction-crossed size-bin symbols at k=30; masked code uses only slots < PPI_LEN and unmasked code uses all 30 slots including padding; timing row 0 excluded",
            "same_flows_held_fixed": True,
            "threshold_flow_count_per_service": SERVICE_THRESHOLD,
            "service_count": len(threshold_services),
            "pair_count": len(pairs),
            "masked_tv_summary": summarize([p["masked_tv"] for p in pairs]),
            "unmasked_tv_summary": summarize([p["unmasked_tv"] for p in pairs]),
            "unmasked_minus_masked_summary": summarize([p["unmasked_minus_masked"] for p in pairs]),
            "abs_difference_summary": summarize([p["abs_difference"] for p in pairs]),
            "max_abs_difference_pair": max_pair,
        },
        "ppi_len_distribution": {
            "row_count": int(total_len),
            "min": int(min(len_counts)),
            "max": int(max(len_counts)),
            **q,
            "fraction_ppi_len_ge_15": float(sum(c for v, c in len_counts.items() if v >= 15) / total_len),
            "histogram_exact_length_counts": counter_to_json(len_counts),
        },
        "k5_retention_after_masking": {
            "threshold_flow_count_per_service": SERVICE_THRESHOLD,
            "total_services_at_threshold": len(threshold_services),
            "usable_services_at_k5_after_masking": len(usable_k5_services),
            "services_dropping_below_threshold_at_k5": len(threshold_services) - len(usable_k5_services),
            "total_pairs": int(total_pairs),
            "usable_pairs": int(usable_pairs),
            "usable_pair_fraction": float(usable_pairs / total_pairs) if total_pairs else 0.0,
        },
    }
    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, OUT_PATH)
    print(json.dumps({
        "out": OUT_PATH,
        "bytes": os.path.getsize(OUT_PATH),
        "sha256": sha256_file(OUT_PATH),
        "h5_sha256": digest,
        "rows": int(total_len),
        "pair_count": len(pairs),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
