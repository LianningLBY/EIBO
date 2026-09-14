#!/root/miniconda3/bin/python3
import collections
import datetime as dt
import hashlib
import importlib.util
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
OUT_PATH = "/root/eibo/artifacts/step0_occupancy.json"
STATE_PATH = "/root/eibo/artifacts/step0_occupancy.state.json"
CHUNK_SIZE = 100_000
SERVICE_THRESHOLD = 2000


def load_table_paths_helper():
    path = Path("/root/eibo/scripts/xs_compression_early_readout.py")
    spec = importlib.util.spec_from_file_location("xs_compression_early_readout", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod.table_paths


def sha256_file(path, block=16 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block_bytes in iter(lambda: handle.read(block), b""):
            digest.update(block_bytes)
    return digest.hexdigest()


def jsonable_counter(counter):
    return {str(k): int(v) for k, v in sorted(counter.items(), key=lambda item: str(item[0]))}


def entropy(counter):
    total = sum(counter.values())
    if total == 0:
        return None
    return float(-sum((n / total) * math.log2(n / total) for n in counter.values() if n))


def decode_country(value):
    if isinstance(value, bytes):
        return value.decode("ascii", errors="replace")
    return str(value)


def month_from_unix_seconds(value):
    return dt.datetime.fromtimestamp(float(value), tz=dt.timezone.utc).strftime("%Y-%m")


def new_state(paths):
    return {
        "version": 1,
        "h5_path": H5_PATH,
        "expected_sha256": EXPECTED_SHA256,
        "table_paths": paths,
        "next_table_index": 0,
        "rows_processed": 0,
        "app_counts": {},
        "axis_values": {},
        "asn_by_service": {},
        "services_by_asn": {},
        "time_first_min": None,
        "time_first_max": None,
        "months": [],
    }


def load_or_initialize(paths):
    if not os.path.exists(STATE_PATH):
        return new_state(paths)
    with open(STATE_PATH, "r", encoding="utf-8") as handle:
        state = json.load(handle)
    if state.get("table_paths") != paths:
        raise RuntimeError("Checkpoint table list differs from current h5 table list")
    return state


def checkpoint(state):
    temp_path = STATE_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(state, handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, STATE_PATH)


def add_chunk(state, apps, versions, countries, times, asns):
    app_counts = state["app_counts"]
    axis_values = state["axis_values"]
    asn_by_service = state["asn_by_service"]
    services_by_asn = state["services_by_asn"]
    months = set(state["months"])

    for app_raw, version_raw, country_raw, time_raw, asn_raw in zip(
        apps, versions, countries, times, asns
    ):
        app = str(int(app_raw))
        version = str(int(version_raw))
        country = decode_country(country_raw)
        asn = str(int(asn_raw))
        month = month_from_unix_seconds(time_raw)

        app_counts[app] = app_counts.get(app, 0) + 1
        axes = axis_values.setdefault(app, {"QUIC_CLIENT_VERSION": [], "DST_COUNTRY": [], "months": []})
        for field, value in (
            ("QUIC_CLIENT_VERSION", version),
            ("DST_COUNTRY", country),
            ("months", month),
        ):
            if value not in axes[field]:
                axes[field].append(value)

        service_asns = asn_by_service.setdefault(app, {})
        service_asns[asn] = service_asns.get(asn, 0) + 1
        asn_services = services_by_asn.setdefault(asn, {})
        asn_services[app] = asn_services.get(app, 0) + 1

        numeric_time = float(time_raw)
        if state["time_first_min"] is None or numeric_time < state["time_first_min"]:
            state["time_first_min"] = numeric_time
        if state["time_first_max"] is None or numeric_time > state["time_first_max"]:
            state["time_first_max"] = numeric_time
        months.add(month)

    state["months"] = sorted(months)
    state["rows_processed"] += len(apps)


def summarize(state, thresholded):
    counts = {k: int(v) for k, v in state["app_counts"].items()}
    if thresholded:
        services = sorted(app for app, count in counts.items() if count >= SERVICE_THRESHOLD)
    else:
        services = sorted(counts)
    service_set = set(services)

    axis_cardinalities = {}
    for app in services:
        axes = state["axis_values"][app]
        axis_cardinalities[app] = {
            "QUIC_CLIENT_VERSION": len(set(axes["QUIC_CLIENT_VERSION"])),
            "DST_COUNTRY": len(set(axes["DST_COUNTRY"])),
            "months": len(set(axes["months"])),
        }

    two_axis = [
        app
        for app in services
        if axis_cardinalities[app]["QUIC_CLIENT_VERSION"] >= 2
        and axis_cardinalities[app]["months"] >= 2
    ]
    full_crossing = [
        app
        for app in two_axis
        if axis_cardinalities[app]["DST_COUNTRY"] >= 2
    ]

    per_service_asn_entropy = {
        app: entropy(state["asn_by_service"].get(app, {})) for app in services
    }
    per_asn_entropy = {}
    for asn, service_counts in state["services_by_asn"].items():
        selected_counts = {
            app: count for app, count in service_counts.items() if app in service_set
        }
        if selected_counts:
            per_asn_entropy[asn] = entropy(selected_counts)
    single_asn_services = [
        app
        for app in services
        if len(state["asn_by_service"].get(app, {})) == 1
    ]

    return {
        "services": services,
        "axis_cardinalities": axis_cardinalities,
        "gate": {
            "two_axis_count": len(two_axis),
            "two_axis_service_ids": two_axis,
            "full_crossing_count": len(full_crossing),
            "full_crossing_service_ids": full_crossing,
        },
        "single_as_service_count": len(single_asn_services),
        "single_as_service_ids": single_asn_services,
        "per_service_dst_asn_entropy_bits": per_service_asn_entropy,
        "per_asn_service_entropy_bits": per_asn_entropy,
    }


def main():
    started = time.time()
    table_paths = load_table_paths_helper()
    with tables.open_file(H5_PATH, mode="r") as h5:
        paths = table_paths(h5)
        if not paths:
            raise RuntimeError("No /flows/* tables found")
        first = h5.get_node(paths[0])
        required = ["APP", "QUIC_CLIENT_VERSION", "DST_COUNTRY", "TIME_FIRST", "DST_ASN"]
        missing = [field for field in required if field not in first.colnames]
        if missing:
            raise RuntimeError(f"Schema mismatch: missing={missing}; dtype={first.dtype}; shape={first.shape}")
        schema = {
            field: {"dtype": str(first.coldtypes[field]), "shape": list(first.coldtypes[field].shape)}
            for field in required
        }
        state = load_or_initialize(paths)
        for table_index in range(state["next_table_index"], len(paths)):
            node = h5.get_node(paths[table_index])
            for start in range(0, node.nrows, CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, node.nrows)
                arrays = {
                    field: node.read(start, stop, field=field)
                    for field in required
                }
                add_chunk(
                    state,
                    arrays["APP"],
                    arrays["QUIC_CLIENT_VERSION"],
                    arrays["DST_COUNTRY"],
                    arrays["TIME_FIRST"],
                    arrays["DST_ASN"],
                )
            state["next_table_index"] = table_index + 1
            checkpoint(state)

    digest = sha256_file(H5_PATH)
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"h5 sha256 mismatch: actual={digest} expected={EXPECTED_SHA256}")

    all_summary = summarize(state, thresholded=False)
    threshold_summary = summarize(state, thresholded=True)
    result = {
        "run": {
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "elapsed_seconds": time.time() - started,
            "python": sys.executable,
            "cwd": os.getcwd(),
            "chunk_size": CHUNK_SIZE,
            "subsampled": False,
            "sample_size": None,
            "service_threshold": SERVICE_THRESHOLD,
            "service_threshold_label": "SELF-DEFINED (CESNET's QUIC22 mapping has no publicly stated minimum-flow threshold)",
            "h5_read_only": True,
        },
        "h5_read": {
            "path": H5_PATH,
            "sha256": digest,
            "expected_sha256": EXPECTED_SHA256,
            "sha256_matches_expected": digest == EXPECTED_SHA256,
            "rows_processed": state["rows_processed"],
            "table_count": len(state["table_paths"]),
            "schema_from_artifact": schema,
        },
        "helpers_reused": {
            "table_paths": "/root/eibo/scripts/xs_compression_early_readout.py",
            "chunked_read_pattern": "/root/eibo/scripts/verify_ppi_masking_xs.py",
            "table_paths_output_consumed": True,
            "chunked_read_output_consumed": True,
        },
        "app_counts": {k: int(v) for k, v in sorted(state["app_counts"].items(), key=lambda item: (-item[1], int(item[0])))},
        "distinct_services_total": len(all_summary["services"]),
        "app_counts_at_2000_threshold": {
            app: int(state["app_counts"][app]) for app in threshold_summary["services"]
        },
        "services_at_2000_threshold": threshold_summary["services"],
        "all_services": all_summary,
        "threshold_2000": threshold_summary,
        "time_first_span": {
            "min_unix_seconds": state["time_first_min"],
            "max_unix_seconds": state["time_first_max"],
            "min_utc": dt.datetime.fromtimestamp(state["time_first_min"], tz=dt.timezone.utc).isoformat(),
            "max_utc": dt.datetime.fromtimestamp(state["time_first_max"], tz=dt.timezone.utc).isoformat(),
            "distinct_months": len(state["months"]),
            "months": state["months"],
        },
        "hedge": "This corpus is the XS 10M-flow BUDGET SUBSET of QUICEXT-25; its month coverage is UNKNOWN. Occupancy measured here characterises this subset and is NOT established to represent the full corpus.",
        "label_availability": "The h5 is the only format carrying APP labels -- the Parquet route has no service label at all, so this table can only be built on the h5.",
    }
    temp_path = OUT_PATH + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, OUT_PATH)
    print(OUT_PATH)
    print(os.path.getsize(OUT_PATH))
    print(sha256_file(OUT_PATH))
    print(json.dumps({
        "distinct_services_total": result["distinct_services_total"],
        "services_at_2000_threshold_count": len(result["services_at_2000_threshold"]),
        "two_axis_all": result["all_services"]["gate"],
        "two_axis_threshold": result["threshold_2000"]["gate"],
        "single_as_all": result["all_services"]["single_as_service_count"],
        "single_as_threshold": result["threshold_2000"]["single_as_service_count"],
        "time_first_span": result["time_first_span"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
