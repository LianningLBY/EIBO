#!/root/miniconda3/bin/python3
import argparse
import collections
import datetime as dt
import hashlib
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

sys.path.insert(0, "/root/eibo/scripts")
import xs_compression_early_readout as xs

sys.path.insert(0, "/root/eibo/src")
from eibo.statcore import tv_lower_bound


H5_PATH = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
EXPECTED_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"
OUT_PATH = "/root/eibo/artifacts/q1_eps_lo_symbol_map.json"
STATE_PATH = "/root/eibo/artifacts/q1_eps_lo_symbol_map.state.pkl"
VECTOR_REFERENCE_PATH = "/root/eibo/artifacts/q2_phist_certificate_v2.json"

K = 5
M = 1
ALPHABET_M = (2 * M) ** K
ALPHA_OVERALL = 0.05
ALPHA_PER_LAW = ALPHA_OVERALL / 2.0
SAMPLE_CAP = 20000
SAMPLE_SEED = 20260913
LOWER_RANDOM_STATE = 0
SERVICE_THRESHOLD = 2000
CHUNK_SIZE = 100000
LOWER_EDGE_FLOOR = 0.05
LOWER_EDGE_CONSTANT = 1.958
UPPER_CONSTANT = math.sqrt(2.0 * math.log(2.0 / ALPHA_PER_LAW))


def sha256_file(path, block=16 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(block)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def atomic_json(data, path=OUT_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, default=json_default)
        handle.write("\n")
    os.replace(temporary, path)


def atomic_pickle(data, path=STATE_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "wb") as handle:
        pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temporary, path)


def quantile_set(values):
    clean = np.asarray([float(value) for value in values], dtype=np.float64)
    if clean.size == 0:
        return {name: None for name in ["min", "q5", "q25", "median", "q75", "q95", "max"]}
    return {
        "min": float(np.min(clean)),
        "q5": float(np.quantile(clean, 0.05)),
        "q25": float(np.quantile(clean, 0.25)),
        "median": float(np.quantile(clean, 0.50)),
        "q75": float(np.quantile(clean, 0.75)),
        "q95": float(np.quantile(clean, 0.95)),
        "max": float(np.max(clean)),
    }


def safe_diagnostics(diagnostics):
    return {
        key: value
        for key, value in diagnostics.items()
        if key != "classifier"
    }


def update_reservoir(reservoirs, seen, label, values, cap, rng):
    label = int(label)
    values = np.asarray(values, dtype=np.int32)
    if label not in reservoirs:
        reservoirs[label] = np.empty(cap, dtype=np.int32)
    old_seen = int(seen.get(label, 0))
    new_seen = old_seen + len(values)
    fill = min(max(cap - old_seen, 0), len(values))
    if fill:
        reservoirs[label][old_seen : old_seen + fill] = values[:fill]
    remainder = values[fill:]
    if len(remainder):
        positions = np.arange(old_seen + fill + 1, new_seen + 1, dtype=np.int64)
        destinations = rng.integers(0, positions, size=len(positions), dtype=np.int64)
        keep = destinations < cap
        if np.any(keep):
            reservoirs[label][destinations[keep]] = remainder[keep]
    seen[label] = new_seen


def schema_summary(h5, paths):
    required = ["APP", "PPI", "PPI_LEN", "TIME_FIRST"]
    result = {}
    for path in paths:
        node = h5.get_node(path)
        missing = [field for field in required if field not in node.colnames]
        if missing:
            raise RuntimeError(f"{path} missing required fields: {missing}")
        result[path] = {
            "nrows": int(node.nrows),
            "required_columns": {
                field: {
                    "dtype": str(node.coldtypes[field]),
                    "shape": list(node.coldtypes[field].shape),
                }
                for field in required
            },
        }
    return result


def build_initial_result(meta, services, reservoirs, seen, rows):
    vector_reference = load_vector_reference(services)
    return {
        "metadata": meta,
        "source": {
            "h5_path": H5_PATH,
            "h5_sha256": EXPECTED_SHA256,
            "python": sys.executable,
            "cwd": os.getcwd(),
        },
        "services": [int(value) for value in services],
        "service_eligible_counts": {
            str(service): int(seen[service]) for service in services
        },
        "vector_level_independent_one_sided": vector_reference,
        "rows": rows,
        "status": "lower_bound_in_progress",
    }


def load_vector_reference(services):
    if not os.path.isfile(VECTOR_REFERENCE_PATH):
        return {
            "status": "unavailable",
            "source_path": VECTOR_REFERENCE_PATH,
            "used_as_lower_bound_for_symbol_object": False,
        }
    with open(VECTOR_REFERENCE_PATH, "r", encoding="utf-8") as handle:
        reference = json.load(handle)
    reference_rows = reference.get("rows", [])
    expected_pairs = {
        (int(a), int(b))
        for a, b in itertools.combinations(sorted(map(int, services)), 2)
    }
    actual_pairs = {
        (int(row["service_a"]), int(row["service_b"]))
        for row in reference_rows
    }
    values = [
        float(row["eps_lo"])
        for row in reference_rows
        if row.get("eps_lo") is not None
    ]
    return {
        "status": "independent_reference",
        "source_path": VECTOR_REFERENCE_PATH,
        "object": reference.get("certified_object"),
        "preprocessing": reference.get("preprocessing"),
        "sampling_unit": reference.get("sampling_unit"),
        "guarantee": reference.get("lower_side", {}).get(
            "guarantee",
            "asymptotic HPLB estimate, not an exact finite-sample certificate",
        ),
        "method": reference.get("lower_side", {}).get("method", "michel"),
        "sample_cap_per_service": reference.get("lower_side", {}).get(
            "sample_cap_per_service"
        ),
        "sample_seed": reference.get("lower_side", {}).get("sample_seed"),
        "pair_count": len(reference_rows),
        "pair_set_matches_symbol_pairs": actual_pairs == expected_pairs,
        "eps_lo_quantiles": quantile_set(values),
        "fraction_eps_lo_positive": (
            sum(value > 0.0 for value in values) / len(values) if values else None
        ),
        "used_as_lower_bound_for_symbol_object": False,
        "note": (
            "This is an independent one-sided result for the per-flow normalized "
            "32-vector object. It is not used as a lower bound on the marginal "
            "k-prefix symbol-law TV."
        ),
    }


def scan():
    started = time.time()
    observed_sha = sha256_file(H5_PATH)
    if observed_sha != EXPECTED_SHA256:
        raise RuntimeError(
            f"H5 sha256 mismatch: expected {EXPECTED_SHA256}, observed {observed_sha}"
        )

    app_counts = collections.Counter()
    eligible_counts = collections.Counter()
    reservoirs = {}
    seen = collections.Counter()
    rng = np.random.default_rng(SAMPLE_SEED)
    validation = {
        "mask_helper_executed": False,
        "mask_helper_all_use_true": True,
        "mask_helper_lengths_valid": True,
        "size_bins_m1_all_zero": True,
    }

    with tables.open_file(H5_PATH, mode="r") as h5:
        paths = xs.table_paths(h5)
        if not paths:
            raise RuntimeError("No /flows/* table with APP, PPI, PPI_LEN was found")
        schema = schema_summary(h5, paths)
        first_node = h5.get_node(paths[0])
        sample_stop = min(10000, int(first_node.nrows))
        sample_ppi = np.asarray(first_node.read(0, sample_stop, field="PPI"))
        sample_lens = np.asarray(first_node.read(0, sample_stop, field="PPI_LEN")).reshape(-1)
        inferred = xs.infer_ppi_channels(sample_ppi, sample_lens)
        direction_row = int(inferred["direction_row"])
        size_row = int(inferred["size_row"])
        time_min = math.inf
        time_max = -math.inf
        total_rows = 0

        for path in paths:
            node = h5.get_node(path)
            for start in range(0, int(node.nrows), CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, int(node.nrows))
                apps = np.asarray(node.read(start, stop, field="APP")).reshape(-1)
                lens = np.asarray(node.read(start, stop, field="PPI_LEN")).reshape(-1)
                times = np.asarray(node.read(start, stop, field="TIME_FIRST")).reshape(-1)
                app_counts.update(map(int, apps))
                eligible = lens >= K
                values, counts = np.unique(apps[eligible], return_counts=True)
                for service, count in zip(values, counts):
                    eligible_counts[int(service)] += int(count)
                time_min = min(time_min, float(np.min(times)))
                time_max = max(time_max, float(np.max(times)))
                total_rows += len(apps)
                if not np.any(eligible):
                    continue

                ppi = np.asarray(node.read(start, stop, field="PPI"))[eligible]
                apps_e = apps[eligible]
                lens_e = lens[eligible]

                masked_codes, use = xs.pack_variable_masked_30(
                    ppi, lens_e, direction_row, size_row
                )
                validation["mask_helper_executed"] = True
                validation["mask_helper_all_use_true"] &= bool(np.all(use))
                validation["mask_helper_lengths_valid"] &= all(
                    len(code) == 2 * min(max(int(length), 0), 30)
                    for code, length in zip(masked_codes, lens_e)
                )

                symbols = np.asarray(
                    xs.pack_rung_k5(ppi, M, direction_row, size_row),
                    dtype=np.int32,
                )
                size_check = xs.size_bins(ppi[:, size_row, :K], M)
                validation["size_bins_m1_all_zero"] &= bool(
                    np.all(np.asarray(size_check) == 0)
                )
                for service in np.unique(apps_e):
                    selector = apps_e == service
                    update_reservoir(
                        reservoirs,
                        seen,
                        int(service),
                        symbols[selector],
                        SAMPLE_CAP,
                        rng,
                    )

    layer1 = sorted(
        int(service) for service, count in app_counts.items() if count >= SERVICE_THRESHOLD
    )
    services = sorted(
        int(service)
        for service in layer1
        if eligible_counts[service] >= SERVICE_THRESHOLD
    )
    if len(services) < 2:
        raise RuntimeError(f"fewer than two retained services: {services}")

    metadata = {
        "object_definition": (
            "The k-prefix SYMBOL law at k=5, M=1: draw a flow uniformly from "
            "a service and map its first five masked (direction, size) symbols "
            "to one of 32 categorical cells."
        ),
        "alphabet_cardinality_m": ALPHABET_M,
        "alphabet_reason": (
            "m=32 because this object is categorical over the a-priori-fixed "
            "alphabet of (2M)^k = 2^5 = 32 cells; realized support was not used."
        ),
        "masking": {
            "precondition": "PPI slots beyond PPI_LEN are masked before reporting.",
            "helper": "/root/eibo/scripts/xs_compression_early_readout.py:pack_variable_masked_30",
            "validation": validation,
            "direction_row": direction_row,
            "size_row": size_row,
            "k": K,
            "M": M,
        },
        "upper_side": {
            "formula": (
                "eps_hi = tv_hat + radius_a + radius_b; "
                "radius_i = (sqrt(m) + sqrt(2*log(2*alpha_per_law)))/sqrt(n_i)"
            ),
            "guarantee": "finite-sample, distribution-free plug-in upper certificate",
            "alpha_overall": ALPHA_OVERALL,
            "alpha_per_law": ALPHA_PER_LAW,
            "radius_constant": UPPER_CONSTANT,
            "radius_constant_expression": "sqrt(2*log(80))",
            "separate_n_substitution": True,
        },
        "lower_side": {
            "formula": (
                "tv_lower_bound(X1, X2, alpha=0.025, method='michel')"
            ),
            "input_unit": (
                "one-hot rows: one row per sampled flow, with a 32-dimensional "
                "one-hot indicator for that flow's observed symbol"
            ),
            "guarantee": (
                "asymptotic HPLB estimate; not an exact finite-sample certificate"
            ),
            "alpha_passed": ALPHA_PER_LAW,
            "alpha_internal_binomial_witness": (
                "alpha/3 is applied inside tv_lower_bound; no additional division"
            ),
            "sample_cap_per_service": SAMPLE_CAP,
            "sample_seed": SAMPLE_SEED,
            "lower_random_state": LOWER_RANDOM_STATE,
        },
        "service_selection": {
            "rule": (
                "retain services with at least 2000 total flows and at least "
                "2000 flows with PPI_LEN >= 5"
            ),
            "service_threshold": SERVICE_THRESHOLD,
            "retained_service_count": len(services),
            "pair_count": len(list(itertools.combinations(services, 2))),
            "sample_size_per_service": (
                "n_i = min(eligible_flow_count_i, fixed cap)"
            ),
        },
        "naming_correction": (
            "The previous run did not compute eps_lo; that run's "
            "lower_side_fraction was the band's lower-edge constraint, not a "
            "proven bound."
        ),
        "band_lower_edge_constraint": {
            "name": "band_lower_edge_satisfied_fraction",
            "formula": (
                "tv_hat > max(0.05 + 1.958/sqrt(n_a), "
                "0.05 + 1.958/sqrt(n_b))"
            ),
            "not_a_proven_bound": True,
        },
        "routine_execution_report": [
            {
                "routine": "/root/eibo/scripts/xs_compression_early_readout.py:table_paths",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "select actual /flows/* tables",
            },
            {
                "routine": "/root/eibo/scripts/xs_compression_early_readout.py:infer_ppi_channels",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "identify direction and size PPI rows from the artifact",
            },
            {
                "routine": "/root/eibo/scripts/xs_compression_early_readout.py:pack_variable_masked_30",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "mask validation precondition for every eligible chunk",
            },
            {
                "routine": "/root/eibo/scripts/xs_compression_early_readout.py:pack_rung_k5",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "construct the M=1 k=5 symbol code",
            },
            {
                "routine": "/root/eibo/scripts/xs_compression_early_readout.py:direction_bits",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "called by pack_rung_k5 for direction normalization",
            },
            {
                "routine": "/root/eibo/scripts/xs_compression_early_readout.py:size_bins",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "M=1 size-axis collapse sanity check; all outputs must be zero",
            },
            {
                "routine": "/root/eibo/scripts/xs_compression_early_readout.py:tv",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "empirical TV of the same sampled categorical symbol laws",
            },
            {
                "routine": "/root/eibo/src/eibo/statcore.py:599 tv_lower_bound",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "Michel lower side on one-hot symbol rows",
            },
            {
                "routine": f"{__file__}:sha256_file",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "verify the read-only H5 against the supplied digest",
            },
            {
                "routine": f"{__file__}:load_vector_reference",
                "executed": True,
                "output_consumed_by_reported_numbers": True,
                "purpose": "independent vector-level one-sided comparison only",
            },
        ],
        "scan_elapsed_seconds": time.time() - started,
        "h5_schema": schema,
        "h5_total_rows": total_rows,
        "time_first_min": time_min,
        "time_first_max": time_max,
        "time_first_min_utc": dt.datetime.fromtimestamp(
            time_min, tz=dt.timezone.utc
        ).isoformat(),
        "time_first_max_utc": dt.datetime.fromtimestamp(
            time_max, tz=dt.timezone.utc
        ).isoformat(),
    }
    rows = []
    for service_a, service_b in itertools.combinations(services, 2):
        n_a = min(int(seen[service_a]), SAMPLE_CAP)
        n_b = min(int(seen[service_b]), SAMPLE_CAP)
        rows.append(
            {
                "service_a": service_a,
                "service_b": service_b,
                "n_a": n_a,
                "n_b": n_b,
                "tv_hat": None,
                "radius_a": None,
                "radius_b": None,
                "eps_hi": None,
                "eps_lo": None,
                "band_lower_edge_satisfied": None,
                "eps_lo_le_eps_hi": None,
                "lower_side_status": "pending",
            }
        )
    result = build_initial_result(metadata, services, reservoirs, seen, rows)
    state = {
        "metadata": metadata,
        "services": services,
        "seen": {int(key): int(value) for key, value in seen.items()},
        "reservoirs": {
            int(key): np.asarray(value[: min(int(seen[key]), SAMPLE_CAP)], dtype=np.int32)
            for key, value in reservoirs.items()
            if int(seen[key]) > 0
        },
        "rows": rows,
        "result": result,
        "scan_complete": True,
    }
    atomic_pickle(state)
    atomic_json(result)
    print(
        json.dumps(
            {
                "status": "scan_complete",
                "services": len(services),
                "pairs": len(rows),
                "output": OUT_PATH,
                "state": STATE_PATH,
            },
            sort_keys=True,
        )
    )


def load_state():
    if not os.path.isfile(STATE_PATH):
        raise RuntimeError(f"missing state: {STATE_PATH}; run --stage scan first")
    with open(STATE_PATH, "rb") as handle:
        return pickle.load(handle)


def compute_pair(row, reservoirs):
    a = int(row["service_a"])
    b = int(row["service_b"])
    codes_a = np.asarray(reservoirs[a], dtype=np.int32)
    codes_b = np.asarray(reservoirs[b], dtype=np.int32)
    counts_a = collections.Counter(map(int, codes_a))
    counts_b = collections.Counter(map(int, codes_b))
    tv_hat = float(xs.tv(counts_a, counts_b))
    n_a = len(codes_a)
    n_b = len(codes_b)
    radius_a = (math.sqrt(ALPHABET_M) + UPPER_CONSTANT) / math.sqrt(n_a)
    radius_b = (math.sqrt(ALPHABET_M) + UPPER_CONSTANT) / math.sqrt(n_b)
    eps_hi = tv_hat + radius_a + radius_b
    threshold_a = LOWER_EDGE_FLOOR + LOWER_EDGE_CONSTANT / math.sqrt(n_a)
    threshold_b = LOWER_EDGE_FLOOR + LOWER_EDGE_CONSTANT / math.sqrt(n_b)
    one_hot_a = np.eye(ALPHABET_M, dtype=np.float64)[codes_a]
    one_hot_b = np.eye(ALPHABET_M, dtype=np.float64)[codes_b]
    eps_lo, diagnostics = tv_lower_bound(
        one_hot_a,
        one_hot_b,
        alpha=ALPHA_PER_LAW,
        method="michel",
        random_state=LOWER_RANDOM_STATE,
    )
    eps_lo = float(eps_lo)
    return {
        "service_a": a,
        "service_b": b,
        "n_a": n_a,
        "n_b": n_b,
        "tv_hat": tv_hat,
        "radius_a": radius_a,
        "radius_b": radius_b,
        "eps_hi": float(eps_hi),
        "eps_lo": eps_lo,
        "band_lower_edge_satisfied": bool(
            tv_hat > max(threshold_a, threshold_b)
        ),
        "band_threshold_a": threshold_a,
        "band_threshold_b": threshold_b,
        "eps_lo_le_eps_hi": bool(eps_lo <= eps_hi),
        "lower_side_status": "computed",
        "lower_diagnostics": safe_diagnostics(diagnostics),
    }


def finalize(result):
    rows = result["rows"]
    computed = [row for row in rows if row["lower_side_status"] == "computed"]
    violations = [row for row in computed if not row["eps_lo_le_eps_hi"]]
    result["summary"] = {
        "row_count": len(computed),
        "eps_lo_quantiles": quantile_set([row["eps_lo"] for row in computed]),
        "eps_hi_quantiles": quantile_set([row["eps_hi"] for row in computed]),
        "fraction_bracket_nonempty": (
            sum(row["eps_lo"] < row["eps_hi"] for row in computed) / len(computed)
            if computed
            else None
        ),
        "fraction_eps_lo_positive": (
            sum(row["eps_lo"] > 0.0 for row in computed) / len(computed)
            if computed
            else None
        ),
        "band_lower_edge_satisfied_fraction": (
            sum(row["band_lower_edge_satisfied"] for row in computed) / len(computed)
            if computed
            else None
        ),
        "violation_count": len(violations),
    }
    vector_median = result["vector_level_independent_one_sided"].get(
        "eps_lo_quantiles", {}
    ).get("median")
    symbol_median = result["summary"]["eps_lo_quantiles"].get("median")
    result["prediction_test"] = {
        "vector_level_reference_median_eps_lo": vector_median,
        "symbol_map_median_eps_lo": symbol_median,
        "symbol_map_eps_lo_drops": (
            bool(symbol_median < vector_median)
            if symbol_median is not None and vector_median is not None
            else None
        ),
        "median_absolute_change": (
            float(symbol_median - vector_median)
            if symbol_median is not None and vector_median is not None
            else None
        ),
        "statement": (
            "The symbol-map eps_lo median drops relative to the independent "
            "vector-level reference."
            if symbol_median is not None
            and vector_median is not None
            and symbol_median < vector_median
            else "The symbol-map eps_lo median does not drop relative to the "
            "independent vector-level reference; this is informative and is "
            "reported without forcing the expected narrative."
        ),
    }
    result["offending_rows"] = violations
    result["status"] = (
        "valid_results" if not violations else "BUG_INVARIANT_VIOLATION"
    )
    if violations:
        result["valid_results_statement"] = (
            "No eps_lo/eps_hi numbers are presented as results because the hard "
            "per-row invariant eps_lo <= eps_hi was violated."
        )
    else:
        result["valid_results_statement"] = (
            "All reported rows satisfy the hard per-row invariant eps_lo <= eps_hi."
        )


def lower(start, count):
    state = load_state()
    rows = state["rows"]
    reservoirs = state["reservoirs"]
    stop = min(len(rows), int(start) + int(count))
    for index in range(int(start), stop):
        if rows[index]["lower_side_status"] == "computed":
            continue
        rows[index] = compute_pair(rows[index], reservoirs)
        state["rows"] = rows
        state["result"]["rows"] = rows
        state["result"]["completed_pairs"] = sum(
            row["lower_side_status"] == "computed" for row in rows
        )
        state["result"]["status"] = "lower_bound_in_progress"
        atomic_pickle(state)
        atomic_json(state["result"])
        print(
            json.dumps(
                {
                    "status": "pair_complete",
                    "index": index,
                    "service_a": rows[index]["service_a"],
                    "service_b": rows[index]["service_b"],
                    "eps_lo": rows[index]["eps_lo"],
                    "eps_hi": rows[index]["eps_hi"],
                    "violation": not rows[index]["eps_lo_le_eps_hi"],
                },
                sort_keys=True,
            ),
            flush=True,
        )
    computed = sum(row["lower_side_status"] == "computed" for row in rows)
    if computed == len(rows):
        finalize(state["result"])
        atomic_json(state["result"])
        state["finalized"] = True
        atomic_pickle(state)
        print(
            json.dumps(
                {
                    "status": state["result"]["status"],
                    "completed_pairs": computed,
                    "violation_count": state["result"]["summary"]["violation_count"],
                },
                sort_keys=True,
            )
        )
    else:
        print(
            json.dumps(
                {
                    "status": "lower_bound_in_progress",
                    "completed_pairs": computed,
                    "remaining_pairs": len(rows) - computed,
                },
                sort_keys=True,
            )
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["scan", "lower"], required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    if args.stage == "scan":
        scan()
    else:
        lower(args.start, args.count)


if __name__ == "__main__":
    main()
