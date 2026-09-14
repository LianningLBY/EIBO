#!/root/miniconda3/bin/python3
"""Feasibility probe and one-month XS readout for CESNET-QUIC22.

This file is intentionally isolated from the existing experiment runners. It
records the commands and outputs needed to establish obtainability, schema,
size, disk placement, and a fixed k=5/M=1 upper-side readout.
"""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import importlib.util
import inspect
import itertools
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import requests
import tables


PROJECT_ROOT = Path("/root/eibo")
sys.path.insert(0, str(PROJECT_ROOT / "src"))
DATA_ROOT = Path("/root/autodl-tmp/eibo/data/cesnet-quic22-explicit-v2")
ARTIFACT_PATH = PROJECT_ROOT / "artifacts/x11_feasibility.json"
H5_PATH = DATA_ROOT / "XS/CESNET-QUIC22-XS.h5"
SERVICE_MAP_PATH = DATA_ROOT / "XS/servicemap.csv"
H5_PART_PATH = DATA_ROOT / "XS/CESNET-QUIC22-XS.h5.part"
LOCK_PATH = DATA_ROOT / ".x11_feasibility_probe.lock"
PRIMARY_H5 = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5")
PYTHON = "/root/miniconda3/bin/python3"
PIP = "/root/miniconda3/bin/pip"
K = 5
M = 1
ALPHA_PER_LAW = 0.025
SERVICE_THRESHOLD = 2000
CHUNK_SIZE = 100_000
DOWNLOAD_CHUNK_BYTES = 256 * 1024 * 1024
TRAIN_DATES = [
    "20221031",
    "20221101",
    "20221102",
    "20221103",
    "20221104",
    "20221105",
    "20221106",
]
BUFFER_DATES = [
    "20221107",
    "20221108",
    "20221109",
    "20221110",
    "20221111",
    "20221112",
    "20221113",
]
TEST_DATES = [
    "20221114",
    "20221115",
    "20221116",
    "20221117",
    "20221118",
    "20221119",
    "20221120",
    "20221121",
    "20221122",
    "20221123",
    "20221124",
    "20221125",
    "20221126",
    "20221127",
]


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(16 * 1024 * 1024)
            if not block:
                return digest.hexdigest()
            digest.update(block)


def run_command(command: str, timeout: int = 120) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "return_code": result.returncode,
    }


def request_evidence(url: str, timeout: int = 60) -> dict[str, Any]:
    response = requests.get(url, timeout=timeout)
    return {
        "url": url,
        "status_code": response.status_code,
        "final_url": response.url,
        "headers": {
            key: value
            for key, value in response.headers.items()
            if key.lower()
            in {
                "content-length",
                "content-range",
                "content-type",
                "accept-ranges",
                "etag",
                "last-modified",
            }
        },
        "text": response.text,
    }


def stream_probe(url: str) -> dict[str, Any]:
    response = requests.get(url, stream=True, timeout=60)
    try:
        first_chunk = next(response.iter_content(1024), b"")
        return {
            "url": url,
            "status_code": response.status_code,
            "final_url": response.url,
            "headers": {
                key: value
                for key, value in response.headers.items()
                if key.lower()
                in {
                    "content-length",
                    "content-range",
                    "content-type",
                    "accept-ranges",
                    "etag",
                    "last-modified",
                }
            },
            "first_chunk_len": len(first_chunk),
        }
    finally:
        response.close()


def download_exact(
    url: str, target: Path, max_bytes_this_call: int = DOWNLOAD_CHUNK_BYTES
) -> dict[str, Any]:
    """Resume one object while never writing beyond its advertised length."""
    target.parent.mkdir(parents=True, exist_ok=True)
    probe = requests.get(
        url,
        headers={"Range": "bytes=0-"},
        stream=True,
        timeout=(30, 60),
    )
    probe.raise_for_status()
    content_range = probe.headers.get("Content-Range", "")
    total = int(content_range.rsplit("/", 1)[1])
    probe.close()

    existing = target.stat().st_size if target.exists() else 0
    if existing > total:
        raise RuntimeError(
            f"partial target exceeds advertised object length: {existing} > {total}"
        )
    if existing == total:
        return {
            "status": "already_complete",
            "url": url,
            "target": str(target),
            "bytes": existing,
            "advertised_bytes": total,
        }

    end = min(existing + max_bytes_this_call - 1, total - 1)
    response = requests.get(
        url,
        headers={"Range": f"bytes={existing}-{end}"},
        stream=True,
        timeout=(30, 60),
    )
    response.raise_for_status()
    response_range = response.headers.get("Content-Range", "")
    if not response_range.startswith(f"bytes {existing}-{end}/"):
        response.close()
        raise RuntimeError(
            f"unexpected range response: requested bytes={existing}-{end}, "
            f"received {response_range!r}"
        )

    remaining = end - existing + 1
    written = 0
    with target.open("ab") as handle:
        for block in response.iter_content(1024 * 1024):
            if not block:
                continue
            take = min(len(block), remaining - written)
            handle.write(block[:take])
            written += take
            if written == remaining:
                break
    response.close()
    observed = target.stat().st_size
    return {
        "status": "complete" if observed == total else "partial",
        "url": url,
        "target": str(target),
        "bytes_written_this_call": written,
        "bytes": observed,
        "advertised_bytes": total,
        "max_bytes_this_call": max_bytes_this_call,
    }


def load_helper():
    helper_path = PROJECT_ROOT / "scripts/xs_compression_early_readout.py"
    spec = importlib.util.spec_from_file_location("x11_xs_helper", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load helper: {helper_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def package_evidence() -> dict[str, Any]:
    import cesnet_datazoo
    from cesnet_datazoo.config import Protocol
    from cesnet_datazoo.constants import (
        APP_COLUMN,
        CATEGORY_COLUMN,
        DIR_POS,
        IPT_POS,
        PPI_COLUMN,
        PPI_MAX_LEN,
        SIZE_POS,
        UDP_PPI_CHANNELS,
    )
    from cesnet_datazoo.datasets.cesnet_dataset import CesnetDataset
    from cesnet_datazoo.datasets.datasets import CESNET_QUIC22
    from cesnet_datazoo.datasets.metadata.dataset_metadata import load_metadata

    metadata = load_metadata("CESNET-QUIC22")
    return {
        "module_file": cesnet_datazoo.__file__,
        "dataset_class_docstring": inspect.getdoc(CESNET_QUIC22),
        "base_class_docstring": inspect.getdoc(CesnetDataset),
        "download_source": inspect.getsource(CesnetDataset._download),
        "download_exists_source": inspect.getsource(CesnetDataset._is_downloaded),
        "dataset_class_attributes": {
            "name": CESNET_QUIC22.name,
            "database_filename": CESNET_QUIC22.database_filename,
            "bucket_url": CESNET_QUIC22.bucket_url,
            "available_dates": CESNET_QUIC22.available_dates,
            "time_periods": CESNET_QUIC22.time_periods,
        },
        "metadata_repr": repr(metadata),
        "metadata_fields": {
            "protocol": str(metadata.protocol),
            "published_in": metadata.published_in,
            "collected_in": metadata.collected_in,
            "collection_duration": metadata.collection_duration,
            "available_samples": metadata.available_samples,
            "available_dataset_sizes": metadata.available_dataset_sizes,
            "collection_period": metadata.collection_period,
            "missing_dates_in_collection_period": metadata.missing_dates_in_collection_period,
            "application_count": metadata.application_count,
            "background_traffic_classes": metadata.background_traffic_classes,
            "ppi_features": metadata.ppi_features,
            "flowstats_features": metadata.flowstats_features,
            "other_fields": metadata.other_fields,
            "zenodo_url": metadata.zenodo_url,
        },
        "constants": {
            "APP_COLUMN": APP_COLUMN,
            "CATEGORY_COLUMN": CATEGORY_COLUMN,
            "PPI_COLUMN": PPI_COLUMN,
            "IPT_POS": IPT_POS,
            "DIR_POS": DIR_POS,
            "SIZE_POS": SIZE_POS,
            "PPI_MAX_LEN": PPI_MAX_LEN,
            "UDP_PPI_CHANNELS": UDP_PPI_CHANNELS,
            "Protocol.QUIC": str(Protocol.QUIC),
        },
    }


def zenodo_metadata(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    record = response.json()
    metadata = record.get("metadata", {})
    return {
        "command_url": url,
        "status_code": response.status_code,
        "title": metadata.get("title"),
        "access_right": metadata.get("access_right"),
        "license": metadata.get("license"),
        "files": [
            {
                "key": item.get("key"),
                "size": item.get("size"),
                "checksum": item.get("checksum"),
                "content_url": item.get("links", {}).get("self"),
            }
            for item in record.get("files", [])
        ],
    }


def raw_metadata_csv() -> str:
    path = Path(
        "/root/miniconda3/lib/python3.12/site-packages/"
        "cesnet_datazoo/datasets/metadata/metadata.csv"
    )
    for line in path.read_text(errors="replace").splitlines():
        if line.startswith("CESNET-QUIC22,"):
            return line
    return "CESNET-QUIC22 row absent"


def actual_schema() -> dict[str, Any]:
    required = ["APP", "CATEGORY", "PPI", "PPI_LEN", "TIME_FIRST", "TIME_LAST"]
    nodes = []
    with tables.open_file(str(H5_PATH), mode="r") as h5:
        if hasattr(h5.root, "flows"):
            nodes = list(h5.walk_nodes("/flows", classname="Table"))
        if not nodes:
            raise RuntimeError("no /flows table found in downloaded QUIC22 H5")
        all_columns = sorted({column for node in nodes for column in node.colnames})
        first = nodes[0]
        sample = first.read(0, min(3, first.nrows))
        fields = {}
        for field in required:
            if field in first.colnames:
                value = sample[field]
                fields[field] = {
                    "present": True,
                    "dtype": str(value.dtype),
                    "shape_read": list(value.shape),
                    "shape_per_row": list(value.shape[1:]),
                    "column_dtype": str(first.coldtypes[field]),
                }
            else:
                fields[field] = {"present": False}
        enum_values = {}
        for field in ("APP", "CATEGORY"):
            if field in first.colnames:
                try:
                    enum_values[field] = {
                        str(key): str(value)
                        for key, value in dict(first.get_enum(field)).items()
                    }
                except Exception as exc:
                    enum_values[field] = {
                        "error": f"{type(exc).__name__}: {exc}"
                    }
        return {
            "table_count": len(nodes),
            "table_paths": [node._v_pathname for node in nodes],
            "table_row_counts": {
                node._v_pathname: int(node.nrows) for node in nodes
            },
            "all_columns": all_columns,
            "first_table_path": first._v_pathname,
            "required_fields": fields,
            "enum_values": enum_values,
            "first_sample": {
                "PPI": sample["PPI"].tolist() if "PPI" in first.colnames else None,
                "PPI_LEN": sample["PPI_LEN"].tolist()
                if "PPI_LEN" in first.colnames
                else None,
                "APP": sample["APP"].tolist() if "APP" in first.colnames else None,
                "CATEGORY": sample["CATEGORY"].tolist()
                if "CATEGORY" in first.colnames
                else None,
            },
        }


def bytes_record(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    return {
        "path": str(path),
        "exists": True,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def protocol_readout(helper, schema: dict[str, Any]) -> dict[str, Any]:
    from eibo.statcore import tv_upper_bound

    start_time = time.time()
    test_paths = {f"/flows/D{date}" for date in TEST_DATES}
    train_paths = {f"/flows/D{date}" for date in TRAIN_DATES}
    buffer_paths = {f"/flows/D{date}" for date in BUFFER_DATES}
    all_paths = set(schema["table_paths"])
    missing_split_paths = {
        "train": sorted(train_paths - all_paths),
        "buffer": sorted(buffer_paths - all_paths),
        "test": sorted(test_paths - all_paths),
    }
    if any(missing_split_paths.values()):
        return {
            "status": "blocked",
            "error": f"required split table paths missing: {missing_split_paths}",
            "split": {
                "train_dates": TRAIN_DATES,
                "buffer_dates": BUFFER_DATES,
                "test_dates": TEST_DATES,
            },
        }

    counts = collections.Counter()
    eligible_counts = collections.Counter()
    counters: dict[int, collections.Counter[int]] = collections.defaultdict(
        collections.Counter
    )
    total_rows = 0
    eligible_rows = 0

    with tables.open_file(str(H5_PATH), mode="r") as h5:
        for path in sorted(test_paths):
            node = h5.get_node(path)
            for begin in range(0, node.nrows, CHUNK_SIZE):
                end = min(begin + CHUNK_SIZE, node.nrows)
                apps = np.asarray(node.read(begin, end, field="APP")).reshape(-1)
                lens = np.asarray(node.read(begin, end, field="PPI_LEN")).reshape(-1)
                counts.update(map(int, apps))
                total_rows += len(apps)
                eligible = lens >= K
                if not np.any(eligible):
                    continue
                ppi = np.asarray(node.read(begin, end, field="PPI"))[eligible]
                apps_e = apps[eligible]
                codes = np.asarray(
                    helper.pack_rung_prefix(ppi, K, M, 1, 2), dtype=np.int64
                )
                eligible_rows += len(codes)
                values, code_counts = np.unique(apps_e, return_counts=True)
                for label, amount in zip(values, code_counts):
                    eligible_counts[int(label)] += int(amount)
                order = np.argsort(apps_e, kind="mergesort")
                apps_sorted = apps_e[order]
                codes_sorted = codes[order]
                breaks = np.flatnonzero(apps_sorted[1:] != apps_sorted[:-1]) + 1
                starts = np.r_[0, breaks]
                ends = np.r_[breaks, len(apps_sorted)]
                for begin_group, end_group in zip(starts, ends):
                    label = int(apps_sorted[begin_group])
                    counters[label].update(
                        map(int, codes_sorted[begin_group:end_group])
                    )

    services = sorted(
        label
        for label in counts
        if counts[label] >= SERVICE_THRESHOLD
        and eligible_counts[label] >= SERVICE_THRESHOLD
    )
    rows = []
    for service_a, service_b in itertools.combinations(services, 2):
        tv_hat = helper.tv(counters[service_a], counters[service_b])
        if tv_hat is None:
            continue
        n_a = int(eligible_counts[service_a])
        n_b = int(eligible_counts[service_b])
        radius_a = 0.5 * math.sqrt(32.0 / n_a) + 0.5 * math.sqrt(
            2.0 * math.log(2.0 / ALPHA_PER_LAW) / n_a
        )
        radius_b = 0.5 * math.sqrt(32.0 / n_b) + 0.5 * math.sqrt(
            2.0 * math.log(2.0 / ALPHA_PER_LAW) / n_b
        )
        raw_eps_hi = float(tv_hat + radius_a + radius_b)
        rows.append(
            {
                "service_a": str(service_a),
                "service_b": str(service_b),
                "n_a": n_a,
                "n_b": n_b,
                "tv_hat": float(tv_hat),
                "eps_hi_raw": raw_eps_hi,
                "eps_hi": min(1.0, max(0.0, raw_eps_hi)),
                "eps_hi_lt_0_5": bool(raw_eps_hi < 0.5),
            }
        )

    reference_check = None
    if len(services) >= 2:
        service_a, service_b = services[:2]
        sample_a = np.repeat(
            np.arange(32, dtype=np.int16),
            [counters[service_a].get(i, 0) for i in range(32)],
        )
        sample_b = np.repeat(
            np.arange(32, dtype=np.int16),
            [counters[service_b].get(i, 0) for i in range(32)],
        )
        reference = tv_upper_bound(
            sample_a,
            sample_b,
            alphabet_size=32,
            alpha=ALPHA_PER_LAW,
        )
        direct = next(
            row
            for row in rows
            if row["service_a"] == str(service_a)
            and row["service_b"] == str(service_b)
        )
        reference_check = {
            "pair": [str(service_a), str(service_b)],
            "reference_function": "/root/eibo/src/eibo/statcore.py::tv_upper_bound",
            "reference_result": {
                "tv_hat": reference.tv_hat,
                "eps_hi": reference.eps_hi,
                "radius_1": reference.radius_1,
                "radius_2": reference.radius_2,
                "n1": reference.n1,
                "n2": reference.n2,
                "alpha": reference.alpha,
                "alphabet_size": reference.alphabet_size,
            },
            "batch_reduction_result": direct,
            "absolute_diffs": {
                "tv_hat": abs(reference.tv_hat - direct["tv_hat"]),
                "eps_hi": abs(reference.eps_hi - direct["eps_hi"]),
            },
        }

    eps_values = np.asarray([row["eps_hi"] for row in rows], dtype=float)
    tv_values = np.asarray([row["tv_hat"] for row in rows], dtype=float)
    return {
        "status": "completed",
        "object": "k=5 M=1 categorical direction-prefix law; size axis is collapsed at M=1; timing channel excluded",
        "statistics_source": {
            "symbol_packing": "/root/eibo/scripts/xs_compression_early_readout.py::pack_rung_prefix",
            "tv_hat": "/root/eibo/scripts/xs_compression_early_readout.py::tv",
            "upper_reference": "/root/eibo/src/eibo/statcore.py::tv_upper_bound",
            "reference_reconciliation": reference_check,
        },
        "parameters": {
            "k": K,
            "M": M,
            "alphabet_size": 32,
            "alpha_per_law": ALPHA_PER_LAW,
            "service_threshold": SERVICE_THRESHOLD,
            "tuning_performed": False,
        },
        "split": {
            "policy": "flow-disjoint AND time-disjoint; packet-level splitting prohibited",
            "train_dates": TRAIN_DATES,
            "buffer_dates": BUFFER_DATES,
            "test_dates": TEST_DATES,
            "statistics_use": "test dates only; train and buffer dates were excluded from the reported pair statistics",
            "buffer_month_available": False,
            "buffer_week_used": True,
            "table_paths_are_flow_units": True,
        },
        "test_period": {
            "table_count": len(test_paths),
            "total_rows": total_rows,
            "eligible_rows_ppi_len_ge_5": eligible_rows,
            "eligible_fraction": eligible_rows / total_rows if total_rows else None,
            "all_service_labels_in_test": len(counts),
            "retained_services": len(services),
            "pair_count": len(rows),
        },
        "per_pair_summary": {
            "tv_hat": {
                "min": float(np.min(tv_values)) if len(tv_values) else None,
                "median": float(np.median(tv_values)) if len(tv_values) else None,
                "max": float(np.max(tv_values)) if len(tv_values) else None,
            },
            "eps_hi": {
                "min": float(np.min(eps_values)) if len(eps_values) else None,
                "median": float(np.median(eps_values)) if len(eps_values) else None,
                "max": float(np.max(eps_values)) if len(eps_values) else None,
            },
            "upper_count_eps_hi_lt_0_5": int(
                np.count_nonzero(eps_values < 0.5)
            ),
            "upper_fraction_eps_hi_lt_0_5": float(
                np.mean(eps_values < 0.5)
            )
            if len(eps_values)
            else None,
            "rows": rows,
        },
        "elapsed_seconds": time.time() - start_time,
        "lower_side": {
            "status": "not_run",
            "reason": "This feasibility readout is upper-only and does not launch the classifier-based lower-bound pipeline.",
        },
    }


def _main() -> None:
    started = time.time()
    result: dict[str, Any] = {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "current_time_authoritative": "2026-09-14 06:39:31 UTC",
        "cwd": os.getcwd(),
        "runner_path": str(Path(__file__).resolve()),
        "scope": {
            "cpu_only": True,
            "gpu_requested": False,
            "full_pipeline_started": False,
            "existing_pipeline_modified": False,
            "paused_primary_transfer_touched": False,
        },
        "commands": {},
    }

    result["commands"]["detect_image"] = {
        "command": "detect_image(server=111, account=root)",
        "stdout": "",
        "stderr": "",
        "return_code": 1,
        "error": "SSH error: exit code 1",
        "note": "Known non-blocking host probe failure.",
    }
    result["commands"]["module_before"] = run_command(
        f'{PYTHON} -c "import cesnet_datazoo; print(cesnet_datazoo.__file__)"'
    )
    result["commands"]["pip_show_before"] = run_command(
        f"{PIP} show cesnet-datazoo"
    )
    result["commands"]["install_reverification"] = run_command(
        f"{PIP} install --force-reinstall --no-deps cesnet-datazoo",
        timeout=300,
    )
    result["commands"]["module_after"] = run_command(
        f'{PYTHON} -c "import cesnet_datazoo; print(cesnet_datazoo.__file__)"'
    )
    result["commands"]["pip_show_after"] = run_command(
        f"{PIP} show cesnet-datazoo"
    )

    result["commands"]["disk_before"] = run_command(
        "df -h /root/autodl-tmp"
    )
    result["commands"]["primary_location"] = run_command(
        "find /root/autodl-tmp/eibo -name CESNET-QUICEXT-25-XS.complete.h5"
    )
    result["primary_file"] = bytes_record(PRIMARY_H5)

    result["package"] = package_evidence()
    result["raw_metadata_csv"] = raw_metadata_csv()

    docs_url = "https://cesnet.github.io/cesnet-datazoo/"
    docs = request_evidence(docs_url)
    docs_lines = [
        line.strip()
        for line in docs["text"].splitlines()
        if any(
            key in line.lower()
            for key in ("public datasets", "dataset sizes", "25 million", "quic22")
        )
    ]
    result["official_docs"] = {
        "url": docs_url,
        "status_code": docs["status_code"],
        "quoted_matching_lines": docs_lines,
    }
    result["zenodo"] = zenodo_metadata(
        "https://zenodo.org/api/records/7963302"
    )

    download_url = (
        "https://liberouter.org/datazoo/download"
        "?bucket=cesnet-quic22&file=CESNET-QUIC22-XS.h5"
    )
    result["download_probe"] = stream_probe(download_url)
    result["download_target_before"] = bytes_record(H5_PATH)

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    download_started = time.time()
    explicit_url = (
        "https://liberouter.org/datazoo/download"
        "?bucket=cesnet-quic22&file=CESNET-QUIC22-XS.h5"
    )
    service_url = (
        "https://liberouter.org/datazoo/download"
        "?bucket=cesnet-quic22&file=servicemap.csv"
    )
    advertised_bytes = int(
        result["download_probe"]["headers"]["content-length"]
    )
    if H5_PATH.exists() and H5_PATH.stat().st_size == advertised_bytes:
        partial_result = {
            "status": "already_complete",
            "url": explicit_url,
            "target": str(H5_PATH),
            "bytes": H5_PATH.stat().st_size,
            "advertised_bytes": advertised_bytes,
        }
    else:
        if H5_PATH.exists() and not H5_PART_PATH.exists():
            os.replace(H5_PATH, H5_PART_PATH)
        partial_result = download_exact(explicit_url, H5_PART_PATH)
    result["download_api_call"] = {
        "python": "cesnet_datazoo package installed and inspected; explicit exact-length HTTP Range download used for the data object",
        "data_root": str(DATA_ROOT),
        "database_path": str(H5_PATH),
        "servicemap_path": str(SERVICE_MAP_PATH),
        "partial_download": partial_result,
        "elapsed_seconds": time.time() - download_started,
    }
    result["download_target_after"] = (
        bytes_record(H5_PATH)
        if partial_result["status"] == "already_complete"
        else bytes_record(H5_PART_PATH)
    )
    result["commands"]["disk_after_download"] = run_command(
        "df -h /root/autodl-tmp"
    )
    if partial_result["status"] not in {"complete", "already_complete"}:
        result["not_completed"] = [
            {
                "item": "one-month H5 download",
                "status": "partial",
                "literal_reason": (
                    f"bounded chunk limit {DOWNLOAD_CHUNK_BYTES} bytes per invocation; "
                    f"resume from {partial_result['bytes']} of "
                    f"{partial_result['advertised_bytes']} bytes"
                ),
            },
            {
                "item": "actual HDF5 schema audit",
                "status": "not_run",
                "literal_reason": "The H5 is not complete, so schema inspection was not attempted.",
            },
            {
                "item": "protocol readout",
                "status": "not_run",
                "literal_reason": "The H5 is not complete, so the protocol was not attempted.",
            },
        ]
        result["elapsed_seconds_total"] = time.time() - started
        ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(str(ARTIFACT_PATH) + ".tmp")
        temporary.write_text(
            json.dumps(result, indent=2, sort_keys=True, default=json_default)
            + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, ARTIFACT_PATH)
        print(json.dumps({
            "artifact": str(ARTIFACT_PATH),
            "artifact_bytes": ARTIFACT_PATH.stat().st_size,
            "artifact_sha256": sha256_file(ARTIFACT_PATH),
            "download_status": partial_result["status"],
            "download_bytes": partial_result["bytes"],
            "download_advertised_bytes": partial_result["advertised_bytes"],
            "runner": bytes_record(Path(__file__).resolve()),
        }, sort_keys=True))
        return

    os.replace(H5_PART_PATH, H5_PATH)
    service_response = requests.get(service_url, timeout=(30, 60))
    service_response.raise_for_status()
    SERVICE_MAP_PATH.write_bytes(service_response.content)
    result["download_api_call"]["service_map_content_length"] = len(
        service_response.content
    )
    result["download_api_call"]["elapsed_seconds"] = time.time() - download_started
    result["download_target_after"] = bytes_record(H5_PATH)
    result["servicemap_after"] = bytes_record(SERVICE_MAP_PATH)
    result["commands"]["disk_after_download"] = run_command(
        "df -h /root/autodl-tmp"
    )

    result["actual_schema"] = actual_schema()
    helper = load_helper()
    protocol = protocol_readout(helper, result["actual_schema"])
    result["protocol"] = protocol
    result["field_mapping"] = {
        "primary_PPI_direction_row_1": "QUIC22 PPI row 1 / DIR_POS=1; actual column PPI, per-packet sequence",
        "primary_PPI_size_row_2": "QUIC22 PPI row 2 / SIZE_POS=2; actual column PPI, per-packet sequence",
        "primary_PPI_LEN": "QUIC22 PPI_LEN; actual flowstats column PPI_LEN",
        "primary_APP": "QUIC22 APP; actual label column APP and APP enum",
        "primary_CATEGORY": "QUIC22 CATEGORY; actual label/category enum column CATEGORY",
        "primary_timing_row": "QUIC22 PPI row 0 / IPT_POS=0; present but excluded from protocol statistics",
    }
    result["not_completed"] = [
        {
            "item": "classifier-based lower side",
            "status": "not_run",
            "literal_reason": "This feasibility task ran the fixed upper-only readout; no lower-bound classifier pipeline was launched.",
        },
        {
            "item": "full multi-rung pipeline",
            "status": "not_run",
            "literal_reason": "The task explicitly prohibited launching a full pipeline.",
        }
    ]
    result["elapsed_seconds_total"] = time.time() - started

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(ARTIFACT_PATH) + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True, default=json_default) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, ARTIFACT_PATH)
    print(json.dumps({
        "artifact": str(ARTIFACT_PATH),
        "artifact_bytes": ARTIFACT_PATH.stat().st_size,
        "artifact_sha256": sha256_file(ARTIFACT_PATH),
        "h5": bytes_record(H5_PATH),
        "runner": bytes_record(Path(__file__).resolve()),
        "protocol_status": protocol.get("status"),
        "pair_count": protocol.get("test_period", {}).get("pair_count"),
    }, sort_keys=True))


if __name__ == "__main__":
    try:
        lock_fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit(f"probe lock exists: {LOCK_PATH}")
    try:
        os.write(lock_fd, str(os.getpid()).encode("ascii"))
        os.close(lock_fd)
        _main()
    finally:
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass
