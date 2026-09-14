#!/usr/bin/env python3
import argparse
import collections
import hashlib
import itertools
import json
import math
import os
import pickle
import time
from pathlib import Path

import numpy as np
import tables


EXPECTED_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"
H5_CANDIDATES = [
    "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5",
    "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.h5",
]
SERVICE_THRESHOLD = 2000
MIN_SERVICES = 20
KS = [5, 10, 15, 30]
RUNGS = [1, 2, 4, 8, 16]
ASSUMED = {1: 0.02, 2: 0.10, 4: 0.35, 8: 0.70, 16: 1.00}
TN = {"n=2e5": 0.0550, "n=3.9e6": 0.0511}
LABEL = (
    "early readout on the XS subset -- NOT the formal determination; denominator k, "
    "coverage p, and sampling scheme are reported with every compression result; "
    "the formal determination uses full monthly archives with the pre-registered "
    "flow-disjoint AND time-disjoint split"
)
# Resolve next to the script, not to a fixed container-root path: the previous
# absolute "/root/eibo/artifacts/..." wrote outside the shared project tree, so
# the artifact was invisible to the project. Repo convention is parents[1].
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = str(_PROJECT_ROOT / "artifacts" / "xs_compression_early_readout.json")
DEFAULT_STATE = str(_PROJECT_ROOT / "artifacts" / "xs_compression_early_readout_state.pkl")


def table_paths(h5):
    if not hasattr(h5.root, "flows"):
        return []
    paths = []
    for node in h5.walk_nodes("/flows", classname="Table"):
        if {"APP", "PPI", "PPI_LEN"}.issubset(set(node.colnames)):
            paths.append(node._v_pathname)
    return paths


def pick_h5():
    for path in H5_CANDIDATES:
        if os.path.exists(path):
            return path
    raise SystemExit("No XS h5 candidate exists under /root/autodl-tmp/eibo/data")


def sha256_file(path, block=16 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def dump_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = path + ".tmp"

    def json_default(value):
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.ndarray):
            return value.tolist()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, default=json_default)
        f.write("\n")
    os.replace(tmp, path)


def load_state(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


def save_state(path, state):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(state, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


def quantiles_from_counts(counter):
    total = sum(counter.values())
    if total == 0:
        return {str(q): None for q in [1, 5, 25, 50, 75, 95, 99, 100]}
    out = {}
    qs = [(q, q / 100.0 * (total - 1)) for q in [1, 5, 25, 50, 75, 95, 99, 100]]
    seen = 0
    qi = 0
    for value, count in sorted(counter.items()):
        next_seen = seen + count
        while qi < len(qs) and qs[qi][1] < next_seen:
            out[str(qs[qi][0])] = float(value)
            qi += 1
        seen = next_seen
    return out


def summarize(vals):
    clean = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    if not clean:
        return {"count": 0}
    arr = np.asarray(clean, dtype=np.float64)
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "q25": float(np.quantile(arr, 0.25)),
        "median": float(np.quantile(arr, 0.50)),
        "q75": float(np.quantile(arr, 0.75)),
        "max": float(np.max(arr)),
    }


def size_edges_definition():
    return {
        "M=1": "direction only; no size bins",
        "M=2": ["<=1200", ">1200"],
        "M=4": ["<=600", "601-1200", "1201-1350", ">1350"],
        "M=8": [
            "<=300", "301-600", "601-900", "901-1200", "1201-1275",
            "1276-1350", "1351-1425", ">1425",
        ],
        "M=16": [
            "<=150", "151-300", "301-450", "451-600", "601-750", "751-900",
            "901-1050", "1051-1200", "1201-1238", "1239-1275", "1276-1313",
            "1314-1350", "1351-1388", "1389-1425", "1426-1463", ">1463",
        ],
        "rule": (
            "fixed a-priori binary refinements preserving the RFC 9000 section 14.1 "
            "1200-byte split; M is the number of size bins, with direction crossed in "
            "for M>=2; M=1 is direction only"
        ),
    }


def size_bins(size, m):
    s = np.abs(size).astype(np.int64)
    if m == 1:
        return np.zeros_like(s, dtype=np.int64)
    half = m // 2
    out = np.empty_like(s, dtype=np.int64)
    low = s <= 1200
    out[low] = np.minimum(half - 1, ((np.maximum(s[low], 1) - 1) * half) // 1200)
    high_s = np.minimum(s[~low], 1500)
    out[~low] = half + np.minimum(half - 1, ((high_s - 1201) * half) // 300)
    return out


def direction_bits(direction):
    d = direction.astype(np.int64)
    u = set(map(int, np.unique(d[: min(d.size, 20000)])))
    if u.issubset({0, 1}):
        return d
    if u.issubset({1, 2}):
        return d - 1
    return (d > 0).astype(np.int64)


def infer_ppi_channels(ppi, lens):
    stats = []
    take = min(len(lens), 10000)
    ppi = ppi[:take]
    lens = lens[:take]
    for r in range(ppi.shape[1]):
        parts = []
        for i, ln in enumerate(lens):
            ln = int(max(0, min(int(ln), ppi.shape[2])))
            if ln:
                parts.append(ppi[i, r, :ln])
        v = np.concatenate(parts).astype(np.int64) if parts else np.asarray([], dtype=np.int64)
        if v.size == 0:
            stats.append({"row": r, "empty": True})
            continue
        abs_v = np.abs(v)
        unique_sample = sorted(map(int, np.unique(v[: min(v.size, 50000)])))[:40]
        direction_like = float(np.mean(np.isin(v, [-1, 0, 1, 2])))
        size_like = float(np.mean((abs_v >= 1) & (abs_v <= 10000)))
        time_like = float(np.mean(v >= 0)) * float(np.mean(abs_v <= 10_000_000))
        stats.append(
            {
                "row": r,
                "min": int(v.min()),
                "max": int(v.max()),
                "p50": float(np.quantile(v, 0.50)),
                "p95": float(np.quantile(v, 0.95)),
                "unique_sample": unique_sample,
                "direction_like_fraction": direction_like,
                "size_like_fraction": size_like,
                "nonnegative_time_like_fraction": time_like,
            }
        )
    direction_row = max(stats, key=lambda s: s.get("direction_like_fraction", -1))["row"]
    remaining = [s for s in stats if s["row"] != direction_row]
    size_row = max(remaining, key=lambda s: s.get("size_like_fraction", -1))["row"]
    time_row = next((s["row"] for s in stats if s["row"] not in {direction_row, size_row}), None)
    direction_ok = stats[direction_row].get("direction_like_fraction", 0.0) > 0.98
    size_ok = stats[size_row].get("size_like_fraction", 0.0) > 0.80
    return {
        "row_stats_from_artifact": stats,
        "direction_row": int(direction_row),
        "size_row": int(size_row),
        "time_row": None if time_row is None else int(time_row),
        "usable_for_direction_size": bool(direction_ok and size_ok),
        "what_the_3_means": (
            "PPI leading dimension is three measured packet channels. Project dataset notes state "
            "first-30-packet sequences contain packet size, direction, and inter-packet time; "
            "artifact statistics identify row %d as direction, row %d as size, and row %s as the "
            "remaining timing-like channel. Only direction and size are used for this readout."
            % (direction_row, size_row, str(time_row))
        ),
    }


def collect_padding_samples(ppi, lens, limit=12):
    samples = []
    per_row_tail_values = {"row0": collections.Counter(), "row1": collections.Counter(), "row2": collections.Counter()}
    for i, ln in enumerate(lens):
        ln = int(ln)
        if 0 <= ln < ppi.shape[2]:
            tail = ppi[i, :, ln:]
            for r in range(ppi.shape[1]):
                per_row_tail_values[f"row{r}"].update(map(int, tail[r].ravel()))
            if len(samples) < limit:
                samples.append(
                    {
                        "observed_ppi_len": ln,
                        "raw_tail_slots_all_channels": tail[:, : min(8, tail.shape[1])].astype(int).tolist(),
                    }
                )
    return samples, per_row_tail_values


def pack_exact(ppi, k, direction_row, size_row, fixed_all_30=False, lens=None):
    if fixed_all_30:
        use = np.ones(ppi.shape[0], dtype=bool)
        kk = 30
    else:
        use = lens >= k
        kk = k
    if not np.any(use):
        return [], use
    d = direction_bits(ppi[use, direction_row, :kk])
    s = np.abs(ppi[use, size_row, :kk].astype(np.int64))
    return [tuple(np.stack([d[i], s[i]], axis=1).ravel().astype(int).tolist()) for i in range(d.shape[0])], use


def pack_variable_masked_30(ppi, lens, direction_row, size_row):
    codes = []
    use = np.ones(ppi.shape[0], dtype=bool)
    for i, ln in enumerate(lens):
        kk = max(0, min(int(ln), 30))
        d = direction_bits(ppi[i : i + 1, direction_row, :kk])[0] if kk else np.asarray([], dtype=np.int64)
        s = np.abs(ppi[i, size_row, :kk].astype(np.int64)) if kk else np.asarray([], dtype=np.int64)
        codes.append(tuple(np.stack([d, s], axis=1).ravel().astype(int).tolist()) if kk else tuple())
    return codes, use


def pack_rung_k5(ppi, m, direction_row, size_row):
    d = direction_bits(ppi[:, direction_row, :5])
    if m == 1:
        sym = d
        base = 2
    else:
        b = size_bins(ppi[:, size_row, :5], m)
        sym = d * m + b
        base = 2 * m
    codes = []
    for row in sym:
        code = 0
        for x in row:
            code = code * base + int(x)
        codes.append(code)
    return codes


def pack_rung_prefix(ppi, k, m, direction_row, size_row):
    d = direction_bits(ppi[:, direction_row, :k])
    if m == 1:
        sym = d
        base = 2
    else:
        b = size_bins(ppi[:, size_row, :k], m)
        sym = d * m + b
        base = 2 * m
    codes = []
    for row in sym:
        code = 0
        for x in row:
            code = code * base + int(x)
        codes.append(code)
    return codes


def pack_variable_rung_30(ppi, lens, m, direction_row, size_row):
    codes = []
    for i, ln in enumerate(lens):
        kk = max(0, min(int(ln), 30))
        if kk == 0:
            codes.append((0, 0))
        else:
            codes.append((kk, pack_rung_prefix(ppi[i : i + 1], kk, m, direction_row, size_row)[0]))
    return codes


def tv(c1, c2):
    n1 = sum(c1.values())
    n2 = sum(c2.values())
    if n1 == 0 or n2 == 0:
        return None
    keys = set(c1)
    keys.update(c2)
    return 0.5 * sum(abs(c1.get(k, 0) / n1 - c2.get(k, 0) / n2) for k in keys)


def add_codes(counter, prefix, apps, codes, row_ids):
    for app, code, rid in zip(apps, codes, row_ids):
        app_key = str(int(app))
        split = "split0" if int(rid) % 2 == 0 else "split1"
        counter[(*prefix, "all", app_key)][code] += 1
        counter[(*prefix, split, app_key)][code] += 1


def choose_denominators(coverage):
    def ok(k):
        row = coverage[str(k)]
        return row["usable_pair_fraction"] >= 0.80 and row["aggregate_flow_fraction"] >= 0.50

    chosen = 30 if ok(30) else 15 if ok(15) else 10 if ok(10) else 5
    for alt in {30: [15, 10, 5], 15: [10, 30, 5], 10: [15, 5, 30], 5: [10, 15, 30]}[chosen]:
        if coverage[str(alt)]["usable_pair_count"] > 0:
            return chosen, alt
    return chosen, chosen


def build_meta(args, start_time):
    h5_path = pick_h5()
    result = {
        "h5_used": {"path": h5_path, "bytes": os.path.getsize(h5_path), "sha256": EXPECTED_SHA256},
        "early_readout_label": LABEL,
        "blockers": [],
        "incremental_status": {"phase": "metadata", "complete": False},
    }
    app_counts = collections.Counter()
    len_counts = collections.Counter()
    len_ge = {k: collections.Counter() for k in KS}
    padding_samples = []
    padding_counters = {"row0": collections.Counter(), "row1": collections.Counter(), "row2": collections.Counter()}
    channel = None
    with tables.open_file(h5_path, "r") as h5:
        paths = table_paths(h5)
        if not paths:
            result["blockers"].append("No /flows/* table with APP, PPI, PPI_LEN was found")
            result["gate"] = {"gate_passed": False}
            dump_json(args.out, result)
            return {"phase": "done", "result": result}
        for node_index, path in enumerate(paths):
            node = h5.get_node(path)
            for start in range(0, node.nrows, args.chunk_size):
                stop = min(node.nrows, start + args.chunk_size)
                apps = node.read(start, stop, field="APP")
                lens = node.read(start, stop, field="PPI_LEN")
                app_counts.update(map(int, apps))
                len_counts.update(map(int, lens))
                for k in KS:
                    vals, cnts = np.unique(apps[lens >= k], return_counts=True)
                    for v, c in zip(vals, cnts):
                        len_ge[k][int(v)] += int(c)
                if channel is None or len(padding_samples) < 12:
                    ppi = node.read(start, stop, field="PPI")
                    if channel is None:
                        channel = infer_ppi_channels(ppi, lens)
                        channel["ppi_array_shape"] = list(ppi.shape[1:])
                        channel["ppi_len_dtype"] = str(lens.dtype)
                    samples, counters = collect_padding_samples(ppi, lens, limit=12 - len(padding_samples))
                    padding_samples.extend(samples)
                    for krow, ctr in counters.items():
                        padding_counters[krow].update(ctr)
                if time.time() - start_time > args.max_seconds:
                    partial = dict(result)
                    partial["incremental_status"] = {
                        "phase": "metadata",
                        "complete": False,
                        "node_index": node_index,
                        "row_start_next_if_restarted": stop,
                        "note": "metadata phase is restarted from the beginning if interrupted; no TV counters are affected",
                    }
                    dump_json(args.out, partial)
                    raise SystemExit(75)

    services = [str(k) for k, v in app_counts.items() if v >= SERVICE_THRESHOLD]
    services.sort(key=lambda s: (-app_counts[int(s)], int(s)))
    selected_flow_count = sum(app_counts[int(s)] for s in services)
    total_pairs = len(services) * (len(services) - 1) // 2
    coverage = {}
    for k in KS:
        usable_services = [s for s in services if len_ge[k][int(s)] >= SERVICE_THRESHOLD]
        usable_pairs = len(usable_services) * (len(usable_services) - 1) // 2
        eligible = sum(len_ge[k][int(s)] for s in services)
        coverage[str(k)] = {
            "usable_pair_count": int(usable_pairs),
            "total_pair_count_from_threshold_services": int(total_pairs),
            "usable_pair_fraction": float(usable_pairs / total_pairs) if total_pairs else 0.0,
            "eligible_flow_count": int(eligible),
            "selected_flow_count": int(selected_flow_count),
            "aggregate_flow_fraction": float(eligible / selected_flow_count) if selected_flow_count else 0.0,
            "services_with_at_least_threshold_eligible_flows": len(usable_services),
        }
    chosen_k, alt_k = choose_denominators(coverage)
    ppi_present = bool(channel and channel.get("ppi_array_shape") == [3, 30])
    ppi_usable = bool(ppi_present and channel.get("usable_for_direction_size"))
    padding_summary = {k: dict(v.most_common(10)) for k, v in padding_counters.items()}
    size_row = channel.get("size_row") if channel else None
    size_tail_common = padding_counters.get(f"row{size_row}", collections.Counter()).most_common(5) if size_row is not None else []
    padding_value_observed = "all sampled post-PPI_LEN tail slots are zero" if all(
        set(counter.keys()).issubset({0}) for counter in padding_counters.values() if counter
    ) else "non-zero or mixed sampled post-PPI_LEN tail values observed"
    padding_is_legal = bool(size_tail_common and any(1 <= int(v) <= 10000 for v, _ in size_tail_common))
    blockers = []
    if not ppi_usable:
        blockers.append("PPI/PPI_LEN present but not usable as direction-size prefix after channel audit")
    if len(services) < MIN_SERVICES:
        blockers.append(f"Only {len(services)} services clear threshold {SERVICE_THRESHOLD}; require >= {MIN_SERVICES}")

    gate = {
        "ppi_present_and_usable": ppi_usable,
        "ppi_channel_audit": channel,
        "app_flow_counts_descending": [{"service": str(k), "flows": int(v)} for k, v in app_counts.most_common()],
        "service_threshold": SERVICE_THRESHOLD,
        "threshold_reason": (
            f"{SERVICE_THRESHOLD} flows per service gives >=1000 flows in each deterministic parity half "
            "for the internal flow-disjoint stability check while retaining enough XS services."
        ),
        "services_clearing_threshold": {"count": len(services), "minimum_required": MIN_SERVICES, "services": services},
        "sampling_does_not_bias_internal_ratio": {
            "primary_estimator_sampling_scheme": "no stochastic down-sampling; all denominator-eligible XS flows are used",
            "verification": "flow-disjoint parity split diagnostics are computed in the measurement phase",
            "failure_modes_named": [
                "stochastic subsampling could alter numerator/denominator ratios if service tails differ",
                "requiring len>=denominator_k changes the subpopulation and is reported as coverage bias, not sampling bias",
                "XS subset may not represent full monthly archives; unresolved until formal run",
            ],
        },
        "gate_passed_before_measurement": bool(ppi_usable and len(services) >= MIN_SERVICES),
    }
    result.update(
        {
            "blockers": blockers,
            "step0_masking": {
                "padding_value_observed": padding_value_observed,
                "sample_tail_slots": padding_samples,
                "padding_tail_value_counts_sample": padding_summary,
                "ppi_array_shape": channel.get("ppi_array_shape") if channel else None,
                "what_the_3_means": channel.get("what_the_3_means") if channel else None,
                "masked_vs_unmasked_k30_tv": None,
                "contamination_evidence": "pending measurement phase",
                "padding_is_legal_size_class": padding_is_legal,
                "padding_legal_size_class_note": (
                    "raw sampled size-channel padding is a legal positive size" if padding_is_legal else
                    "raw sampled size-channel padding is not a legal positive packet-size value; however naive binning of zero would map it to the lowest size bin"
                ),
            },
            "gate": gate,
            "ppi_len_distribution": {
                "quantiles": quantiles_from_counts(len_counts),
                "histogram_exact_length_counts": {str(k): int(v) for k, v in sorted(len_counts.items())},
            },
            "coverage_by_k": coverage,
            "denominator_choice": {
                "k_used": chosen_k,
                "coverage_p_usable_pair_fraction": coverage[str(chosen_k)]["usable_pair_fraction"],
                "coverage_p_aggregate_flow_fraction": coverage[str(chosen_k)]["aggregate_flow_fraction"],
                "stability_denominator_k": alt_k,
                "selection_rule": (
                    "Use k=30 only if usable-pair coverage >=0.80 and aggregate-flow coverage >=0.50; "
                    "otherwise step down to k=15, then k=10, then k=5. Ratios are computed at two denominator k values."
                ),
                "denominator_symbol_law": "M=16 direction x fixed size-bin prefix at denominator k, masked by PPI_LEN and restricted to len>=k",
            },
            "rung_edges_definition": size_edges_definition(),
            "incremental_status": {"phase": "metadata", "complete": True},
        }
    )
    dump_json(args.out, result)
    return {
        "phase": "measure" if not blockers else "done",
        "result": result,
        "paths": paths,
        "node_offsets": None,
        "services": services,
        "chosen_k": chosen_k,
        "alt_k": alt_k,
        "direction_row": channel.get("direction_row") if channel else None,
        "size_row": channel.get("size_row") if channel else None,
        "cursor": {"node_index": 0, "row_start": 0},
        "counts_den": collections.defaultdict(collections.Counter),
        "counts_num": collections.defaultdict(collections.Counter),
        "counts_masked30": collections.defaultdict(collections.Counter),
        "counts_unmasked30": collections.defaultdict(collections.Counter),
    }


def ensure_offsets(state, h5):
    if state.get("node_offsets") is not None:
        return
    offsets = []
    total = 0
    for path in state["paths"]:
        offsets.append(total)
        total += h5.get_node(path).nrows
    state["node_offsets"] = offsets


def measurement_step(args, state, start_time):
    service_ints = np.asarray([int(s) for s in state["services"]], dtype=np.int64)
    denom_ks = sorted(set([state["chosen_k"], state["alt_k"]]))
    with tables.open_file(state["result"]["h5_used"]["path"], "r") as h5:
        ensure_offsets(state, h5)
        ni = state["cursor"]["node_index"]
        row_start = state["cursor"]["row_start"]
        while ni < len(state["paths"]):
            node = h5.get_node(state["paths"][ni])
            while row_start < node.nrows:
                stop = min(node.nrows, row_start + args.chunk_size)
                apps = node.read(row_start, stop, field="APP")
                service_mask = np.isin(apps, service_ints)
                if np.any(service_mask):
                    lens = node.read(row_start, stop, field="PPI_LEN")[service_mask]
                    ppi = node.read(row_start, stop, field="PPI")[service_mask]
                    apps_e = apps[service_mask]
                    row_ids = np.arange(state["node_offsets"][ni] + row_start, state["node_offsets"][ni] + stop)[service_mask]

                    compare_mask = np.isin(apps_e, service_ints[: min(20, len(service_ints))])
                    if np.any(compare_mask):
                        masked_codes = pack_variable_rung_30(ppi[compare_mask], lens[compare_mask], 16, state["direction_row"], state["size_row"])
                        unmasked_codes = pack_rung_prefix(ppi[compare_mask], 30, 16, state["direction_row"], state["size_row"])
                        add_codes(state["counts_masked30"], ("masked_variable_k30_M16",), apps_e[compare_mask], masked_codes, row_ids[compare_mask])
                        add_codes(state["counts_unmasked30"], ("unmasked_fixed_k30_M16",), apps_e[compare_mask], unmasked_codes, row_ids[compare_mask])

                    for dk in denom_ks:
                        use = lens >= dk
                        if not np.any(use):
                            continue
                        den_codes = pack_rung_prefix(ppi[use], dk, 16, state["direction_row"], state["size_row"])
                        add_codes(state["counts_den"], (dk,), apps_e[use], den_codes, row_ids[use])
                        for m in RUNGS:
                            num_codes = pack_rung_k5(ppi[use], m, state["direction_row"], state["size_row"])
                            add_codes(state["counts_num"], (dk, m), apps_e[use], num_codes, row_ids[use])
                row_start = stop
                state["cursor"] = {"node_index": ni, "row_start": row_start}
                state["result"]["incremental_status"] = {
                    "phase": "measure",
                    "complete": False,
                    "node_index": ni,
                    "row_start_next": row_start,
                    "node_rows": int(node.nrows),
                }
                if time.time() - start_time > args.max_seconds:
                    save_state(args.state, state)
                    dump_json(args.out, state["result"])
                    raise SystemExit(75)
            ni += 1
            row_start = 0
            state["cursor"] = {"node_index": ni, "row_start": 0}
    state["phase"] = "finalize"
    state["result"]["incremental_status"] = {"phase": "measure", "complete": True}
    save_state(args.state, state)
    dump_json(args.out, state["result"])


def pair_rows(services, counts_num, counts_den, denom_k, split="all"):
    rows = []
    for a, b in itertools.combinations(services, 2):
        den_tv = tv(counts_den[(denom_k, split, a)], counts_den[(denom_k, split, b)])
        row = {"service_a": a, "service_b": b, "denominator_k": denom_k, "denominator_tv_hat": den_tv}
        for m in RUNGS:
            num_tv = tv(counts_num[(denom_k, m, split, a)], counts_num[(denom_k, m, split, b)])
            row[f"M={m}_tv_hat_k5"] = num_tv
            row[f"M={m}_compression_ratio"] = None if den_tv in (None, 0) or num_tv is None else num_tv / den_tv
        rows.append(row)
    return rows


def finalize(args, state):
    result = state["result"]
    chosen_k = state["chosen_k"]
    alt_k = state["alt_k"]
    services_chosen = [
        s for s in state["services"]
        if result["coverage_by_k"][str(chosen_k)]["services_with_at_least_threshold_eligible_flows"] >= MIN_SERVICES
    ]
    services_chosen = [
        s for s in state["services"]
        if sum(state["counts_den"][(chosen_k, "all", s)].values()) >= SERVICE_THRESHOLD
    ]
    services_alt = [s for s in state["services"] if sum(state["counts_den"][(alt_k, "all", s)].values()) >= SERVICE_THRESHOLD]
    rows = pair_rows(services_chosen, state["counts_num"], state["counts_den"], chosen_k, "all")
    rows_alt = pair_rows(services_alt, state["counts_num"], state["counts_den"], alt_k, "all")
    split0 = pair_rows(services_chosen, state["counts_num"], state["counts_den"], chosen_k, "split0")
    split1 = pair_rows(services_chosen, state["counts_num"], state["counts_den"], chosen_k, "split1")
    mask_pairs = []
    for a, b in itertools.combinations(services_chosen[: min(len(services_chosen), 20)], 2):
        mtv = tv(state["counts_masked30"][("masked_variable_k30_M16", "all", a)], state["counts_masked30"][("masked_variable_k30_M16", "all", b)])
        utv = tv(state["counts_unmasked30"][("unmasked_fixed_k30_M16", "all", a)], state["counts_unmasked30"][("unmasked_fixed_k30_M16", "all", b)])
        mask_pairs.append({"service_a": a, "service_b": b, "masked_variable_len_k30_tv": mtv, "unmasked_fixed_30_tv": utv, "unmasked_minus_masked": None if mtv is None or utv is None else utv - mtv})
    mask_diffs = [abs(r["unmasked_minus_masked"]) for r in mask_pairs if r["unmasked_minus_masked"] is not None]
    result["step0_masking"]["masked_vs_unmasked_k30_tv"] = {
        "pair_count": len(mask_pairs),
        "summary_abs_difference": summarize(mask_diffs),
        "pairs": mask_pairs[:100],
        "comparison_definition": "masked variable-length M=16 law uses only first min(PPI_LEN,30) slots for top-20 services; unmasked fixed M=16 law reads all 30 slots including padding",
    }
    result["step0_masking"]["contamination_evidence"] = (
        "material masked-vs-unmasked k=30 differences observed" if summarize(mask_diffs).get("median", 0.0) > 0.01
        else "masked-vs-unmasked k=30 differences small in this XS readout"
    )
    ratio_dist = {}
    empirical = {
        "denominator_prefix_tv_at_chosen_k_M16": summarize([r["denominator_tv_hat"] for r in rows]),
        "denominator_prefix_tv_at_stability_k_M16": summarize([r["denominator_tv_hat"] for r in rows_alt]),
        "rung_tv_hat_k5_same_denominator_eligible_flows": {},
    }
    measured_vs_assumed = {}
    comp_vs_tn = {}
    split_diag = {}
    stable = True
    for m in RUNGS:
        ratio_dist[f"M={m}"] = {
            f"denominator_k={chosen_k}": summarize([r[f"M={m}_compression_ratio"] for r in rows]),
            f"denominator_k={alt_k}": summarize([r[f"M={m}_compression_ratio"] for r in rows_alt]),
        }
        empirical["rung_tv_hat_k5_same_denominator_eligible_flows"][f"M={m}"] = summarize([r[f"M={m}_tv_hat_k5"] for r in rows])
        med = ratio_dist[f"M={m}"][f"denominator_k={chosen_k}"].get("median")
        measured_vs_assumed[f"M={m}"] = {
            "measured_median_ratio": med,
            "assumed_factor": ASSUMED[m],
            "verdict": None if med is None else ("HIGHER" if med > ASSUMED[m] else "LOWER"),
            "denominator": f"prefix TV at k={chosen_k}, usable-pair coverage p={result['coverage_by_k'][str(chosen_k)]['usable_pair_fraction']:.6f}, aggregate-flow coverage p={result['coverage_by_k'][str(chosen_k)]['aggregate_flow_fraction']:.6f}",
            "label": LABEL,
        }
        comp_vs_tn[f"M={m}"] = {}
        ratios = [r[f"M={m}_compression_ratio"] for r in rows if r[f"M={m}_compression_ratio"] is not None]
        for name, threshold in TN.items():
            comp_vs_tn[f"M={m}"][name] = {
                "T(n)": threshold,
                "median_comp": med,
                "statement": None if med is None else f"comp(M={m}) {'ABOVE' if med > threshold else 'BELOW'} T({name}) by median XS ratio",
                "pairs_above_Tn": int(sum(1 for x in ratios if x > threshold)),
                "pairs_total": int(len(ratios)),
            }
        s0 = summarize([r[f"M={m}_compression_ratio"] for r in split0])
        s1 = summarize([r[f"M={m}_compression_ratio"] for r in split1])
        delta = None if "median" not in s0 or "median" not in s1 else abs(s0["median"] - s1["median"])
        if delta is not None and delta > max(0.05, 0.25 * max(abs(s0["median"]), abs(s1["median"]), 1e-12)):
            stable = False
        split_diag[f"M={m}"] = {"split0_median": s0.get("median"), "split1_median": s1.get("median"), "absolute_delta": delta}
    stability_two_k = {}
    for m in RUNGS:
        a = ratio_dist[f"M={m}"][f"denominator_k={chosen_k}"].get("median")
        b = ratio_dist[f"M={m}"][f"denominator_k={alt_k}"].get("median")
        stability_two_k[f"M={m}"] = {f"median_ratio_at_k={chosen_k}": a, f"median_ratio_at_k={alt_k}": b, "absolute_delta": None if a is None or b is None else abs(a - b)}
    result["gate"]["sampling_does_not_bias_internal_ratio"].update(
        {
            "flow_disjoint_parity_split_median_ratio_delta_by_rung": split_diag,
            "internal_stability_passed": stable,
            "gate_interpretation": "primary estimate uses no stochastic sampling; split-half instability is reported as residual internal-risk evidence",
        }
    )
    result["gate"]["gate_passed"] = bool(result["gate"].get("gate_passed_before_measurement") and stable)
    if not stable:
        result["blockers"].append("Flow-disjoint split-half compression-ratio stability check failed")
    result["denominator_choice"]["stability_across_two_k_values"] = stability_two_k
    result["pairs_analyzed"] = {
        "service_threshold": SERVICE_THRESHOLD,
        "minimum_services_required": MIN_SERVICES,
        "denominator_k": chosen_k,
        "services": services_chosen,
        "pair_count": len(rows),
        "stability_denominator_k": alt_k,
        "stability_services": services_alt,
        "stability_pair_count": len(rows_alt),
        "sampling_scheme": "all denominator-eligible XS flows; parity split only for flow-disjoint internal check",
    }
    result["per_pair_table"] = rows
    result["ratio_distribution_by_rung"] = ratio_dist
    result["measured_vs_assumed"] = measured_vs_assumed
    result["comp_vs_Tn"] = comp_vs_tn
    result["empirical_tv_hat"] = empirical
    result["known_limitations"] = [
        "Every number is an early readout on the XS subset -- NOT the formal determination.",
        "The formal determination must use full monthly archives with pre-registered flow-disjoint AND time-disjoint split.",
        "Integer APP labels are reported as stored in the h5; no external service-name map was used in this measurement.",
        "The k-prefix denominator uses the declared top rung M=16 rather than raw exact byte sizes; ratios are therefore relative to the M=16 prefix law.",
        "PHIST is not analyzed here; no k or coverage annotation should be attached to PHIST figures.",
    ]
    result["incremental_status"] = {"phase": "finalize", "complete": True}
    dump_json(args.out, result)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--state", default=DEFAULT_STATE)
    ap.add_argument("--chunk-size", type=int, default=50000)
    ap.add_argument("--max-seconds", type=float, default=180.0)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--verify-hash", action="store_true")
    args = ap.parse_args()
    start_time = time.time()
    if args.fresh and os.path.exists(args.state):
        os.remove(args.state)
    state = load_state(args.state)
    if state is None:
        state = build_meta(args, start_time)
        save_state(args.state, state)
    if args.verify_hash:
        digest = sha256_file(state["result"]["h5_used"]["path"])
        state["result"]["h5_used"]["sha256"] = digest
        if digest != EXPECTED_SHA256:
            state["result"].setdefault("blockers", []).append("h5 sha256 did not match expected verified hash")
        dump_json(args.out, state["result"])
    if state["phase"] == "done":
        print(json.dumps({"status": "GATE_FAILED", "out": args.out, "blockers": state["result"].get("blockers", [])}, indent=2))
        return 2
    if state["phase"] == "measure":
        measurement_step(args, state, start_time)
    if state["phase"] == "finalize":
        result = finalize(args, state)
        save_state(args.state, {"phase": "done", "result": result})
        print(json.dumps({
            "status": "OK" if result["gate"].get("gate_passed") else "GATE_FAILED",
            "out": args.out,
            "h5_used": result["h5_used"],
            "step0_masking": result["step0_masking"],
            "gate": result["gate"],
            "ppi_len_distribution": result["ppi_len_distribution"],
            "coverage_by_k": result["coverage_by_k"],
            "denominator_choice": result["denominator_choice"],
            "ratio_distribution_by_rung": result.get("ratio_distribution_by_rung"),
            "measured_vs_assumed": result.get("measured_vs_assumed"),
            "comp_vs_Tn": result.get("comp_vs_Tn"),
        }, indent=2, sort_keys=True))
        return 0 if result["gate"].get("gate_passed") else 2
    print(json.dumps({"status": "IN_PROGRESS", "out": args.out, "phase": state["phase"], "cursor": state.get("cursor")}, indent=2))
    return 75


if __name__ == "__main__":
    raise SystemExit(main())
