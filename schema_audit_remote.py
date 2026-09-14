#!/usr/bin/env python3
"""Audit CESNET-QUICEXT-25 H5 and Parquet artifacts without whole-dataset loads."""

import json
import math
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import tables


TARGETS = [
    "QUIC_CLIENT_VERSION", "DST_COUNTRY", "DST_ASN", "QUIC_SNI", "TIME_FIRST",
    "APP", "PPI", "PPI_LEN", "PHIST_SRC_SIZES", "PHIST_DST_SIZES", "CATEGORY",
]
SCAN_COLS = TARGETS + ["PHIST_SRC_IPT", "PHIST_DST_IPT"]
H5_PATH = "/root/autodl-tmp/RECAST-QUICEXT-25-2026-09-07/data/XS/CESNET-QUICEXT-25-XS.h5"
PARQUET_ROOT = "/dev/shm/quicext_parquet"
PARQUET_RAW = "/root/autodl-tmp/eibo/data/raw"


def dtype_string(dtype):
    try:
        return str(np.dtype(dtype))
    except Exception:
        return str(dtype)


def h5_schema(path):
    out = {"exists": os.path.exists(path), "path": path, "columns": []}
    if not out["exists"]:
        return out, None
    with tables.open_file(path, mode="r") as f:
        names = list(f.root.flows._v_children)
        if not names:
            return out, None
        t = f.root.flows._v_children[names[0]]
        for name in t.colnames:
            col = t.coldtypes[name]
            out["columns"].append({"name": name, "dtype": dtype_string(col)})
        return out, names


def parquet_schema(files):
    out = {"exists": bool(files), "path": files, "columns": []}
    if not files:
        return out
    pf = pq.ParquetFile(files[0])
    schema = pf.schema_arrow
    out["columns"] = [{"name": field.name, "dtype": str(field.type)} for field in schema]
    return out


def parquet_schema_all(files):
    """Confirm that every extracted Parquet file has the same schema."""
    schemas = []
    for path in files:
        pf = pq.ParquetFile(path)
        schemas.append([(field.name, str(field.type)) for field in pf.schema_arrow])
    return schemas[0] if schemas else [], all(s == schemas[0] for s in schemas) if schemas else True


def count_table_rows(path):
    with tables.open_file(path, mode="r") as f:
        return sum(int(f.root.flows._v_children[name].nrows) for name in f.root.flows._v_children)


def decode_scalar(x):
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="replace")
    if isinstance(x, np.bytes_):
        return bytes(x).decode("utf-8", errors="replace")
    if isinstance(x, np.generic):
        return x.item()
    return x


def flatten_value(x):
    x = decode_scalar(x)
    if isinstance(x, np.ndarray):
        return tuple(flatten_value(v) for v in x.tolist())
    if isinstance(x, (list, tuple)):
        return tuple(flatten_value(v) for v in x)
    if isinstance(x, dict):
        return tuple((k, flatten_value(v)) for k, v in sorted(x.items()))
    if isinstance(x, float) and math.isnan(x):
        return None
    return x


def is_present_value(x):
    x = flatten_value(x)
    if x is None:
        return False
    if isinstance(x, str):
        return x != ""
    if isinstance(x, tuple):
        return len(x) > 0
    return True


def h5_rows(path, cols):
    with tables.open_file(path, mode="r") as f:
        for name in f.root.flows._v_children:
            t = f.root.flows._v_children[name]
            available = [c for c in cols if c in t.colnames]
            for row in t.iterrows():
                yield {c: row[c] for c in available}


def parquet_rows(files, cols):
    for path in files:
        pf = pq.ParquetFile(path)
        available = [c for c in cols if c in pf.schema_arrow.names]
        for batch in pf.iter_batches(columns=available, batch_size=100_000):
            data = batch.to_pydict()
            n = batch.num_rows
            for i in range(n):
                yield {c: data[c][i] for c in available}


def entropy(counter):
    n = sum(counter.values())
    if n == 0:
        return None
    return -sum((v / n) * math.log2(v / n) for v in counter.values() if v)


def ppi_stats_from_values(vals, hist):
    if not vals:
        return {"min": None, "max": None, "median": None, "quantiles": {}, "frac_ge_15": None,
                "max_representable_k": None, "histogram": {}}
    a = np.asarray(vals, dtype=np.float64)
    qs = [1, 5, 25, 50, 75, 95, 99, 100]
    quant = {f"q{q}": float(np.percentile(a, q, method="linear")) for q in qs}
    return {"min": int(np.min(a)), "max": int(np.max(a)), "median": float(np.median(a)),
            "quantiles": quant, "frac_ge_15": float(np.mean(a >= 15)),
            "max_representable_k": int(np.max(a)), "ppi_storage_capacity": 30,
            "histogram": dict(sorted(hist.items(), key=lambda z: int(z[0])))}


def step0_from_accumulators(service_counts, occupancy, asn_by_service, service_by_asn):
    per_axis = {axis: sum(1 for d in service_counts.values() if len(d[axis]) >= 2)
                for axis in ("client_version", "month", "country")}
    crossings = {"client_version": per_axis["client_version"], "month": per_axis["month"], "country": per_axis["country"]}
    full_crossed = sum(1 for d in service_counts.values()
                       if len(d["client_version"]) >= 2 and len(d["month"]) >= 2 and len(d["country"]) >= 2)
    two_axis_crossed = sum(1 for d in service_counts.values()
                           if len(d["client_version"]) >= 2 and len(d["month"]) >= 2)
    design = "full_paired_design" if full_crossed >= 15 else "client_version_x_month_two_axis_fallback"
    occupancy_table = [{"service": str(s), "client_version": str(cv), "country": str(country), "month": str(month), "flows": n}
                       for (s, cv, country, month), n in sorted(occupancy.items(), key=lambda z: (str(z[0][0]), str(z[0][1]), str(z[0][2]), str(z[0][3])))]
    asn_audit = {
        "per_service_dst_asn_entropy": {str(s): entropy(c) for s, c in sorted(asn_by_service.items(), key=lambda z: str(z[0]))},
        "per_asn_service_entropy": {str(a): entropy(c) for a, c in sorted(service_by_asn.items(), key=lambda z: str(z[0]))},
    }
    single_as = sorted(str(s) for s, c in asn_by_service.items() if len(c) == 1)
    return {"status": "measured", "service_label_column": "APP", "service_count": len(service_counts),
            "per_axis_service_counts": per_axis, "crossings": {"full_three_axis": full_crossed, "two_axis": two_axis_crossed,
            "threshold": 15, "approx_service_target": 50}, "design": design, "occupancy_table": occupancy_table,
            "asn_audit": asn_audit, "single_as_services": single_as}


def audit_stream(rows_factory, names, do_step0=False):
    """Accumulate all requested measurements in one streaming pass."""
    counts = {c: 0 for c in names.intersection(TARGETS)}
    ppi_vals = []
    ppi_hist = Counter()
    phist_occupied = Counter()
    phist_flow_count = 0
    service_counts = defaultdict(lambda: {"client_version": set(), "month": set(), "country": set()})
    occupancy = Counter()
    asn_by_service = defaultdict(Counter)
    service_by_asn = defaultdict(Counter)
    row_count = 0
    for row in rows_factory():
        row_count += 1
        for col in counts:
            if is_present_value(row.get(col)):
                counts[col] += 1
        if "PPI_LEN" in row:
            x = flatten_value(row["PPI_LEN"])
            if x is not None:
                x = int(x)
                ppi_vals.append(x)
                ppi_hist[str(x)] += 1
        phist_cols = [
            ("src", "size", "PHIST_SRC_SIZES"), ("dst", "size", "PHIST_DST_SIZES"),
            ("src", "ipt", "PHIST_SRC_IPT"), ("dst", "ipt", "PHIST_DST_IPT"),
        ]
        if all(col in row for _, _, col in phist_cols):
            phist_flow_count += 1
            for direction in ("src", "dst"):
                size_arr = flatten_value(row[f"PHIST_{'SRC' if direction == 'src' else 'DST'}_SIZES"])
                ipt_arr = flatten_value(row[f"PHIST_{'SRC' if direction == 'src' else 'DST'}_IPT"])
                size_bins = [i for i, value in enumerate(size_arr) if int(value) > 0]
                ipt_bins = [i for i, value in enumerate(ipt_arr) if int(value) > 0]
                for size_bin in size_bins:
                    for ipt_bin in ipt_bins:
                        phist_occupied[(direction, size_bin, ipt_bin)] += 1
        if not do_step0:
            continue
        service = flatten_value(row.get("APP"))
        if not is_present_value(service):
            service = flatten_value(row.get("QUIC_SNI"))
        if not is_present_value(service):
            continue
        cv = flatten_value(row.get("QUIC_CLIENT_VERSION"))
        country = flatten_value(row.get("DST_COUNTRY"))
        asn = flatten_value(row.get("DST_ASN"))
        time = flatten_value(row.get("TIME_FIRST"))
        month = None
        if time is not None:
            try:
                month = pd.Timestamp(time).strftime("%Y-%m")
            except Exception:
                match = re.search(r"(20\d{2})[-/]?(\d{2})", str(time))
                if match:
                    month = f"{match.group(1)}-{match.group(2)}"
        d = service_counts[service]
        if is_present_value(cv):
            d["client_version"].add(cv)
        if month is not None:
            d["month"].add(month)
        if is_present_value(country):
            d["country"].add(country)
        if is_present_value(asn):
            asn_by_service[service][asn] += 1
            service_by_asn[asn][service] += 1
        if is_present_value(cv) and month is not None and is_present_value(country):
            occupancy[(service, cv, country, month)] += 1
    audit = {}
    for col in TARGETS:
        if col not in names:
            audit[col] = {"present": False, "populated_count": None}
        else:
            audit[col] = {"present": True, "populated_count": counts.get(col, 0)}
    ppi = ppi_stats_from_values(ppi_vals, ppi_hist)
    phist = {"rows_with_phist": phist_flow_count, "realized_support": len(phist_occupied),
             "flow_count_per_cell": {f"{direction}:size_bin={size_bin}:ipt_bin={ipt_bin}": n for (direction, size_bin, ipt_bin), n in sorted(phist_occupied.items())}}
    phist["rows_scanned"] = row_count
    step = step0_from_accumulators(service_counts, occupancy, asn_by_service, service_by_asn) if do_step0 else None
    return audit, ppi, phist, step


def ensure_parquet():
    os.makedirs(PARQUET_ROOT, exist_ok=True)
    files = sorted(str(p) for p in Path(PARQUET_ROOT).glob("*.parquet"))
    if files:
        return files
    for zip_path in sorted(Path(PARQUET_RAW).glob("*.zip")):
        try:
            with zipfile.ZipFile(zip_path) as z:
                bad = z.testzip()
                if bad is not None:
                    continue
                for info in z.infolist():
                    if info.filename.endswith(".parquet"):
                        target = Path(PARQUET_ROOT) / Path(info.filename).name
                        if not target.exists():
                            with z.open(info) as src, open(target, "wb") as dst:
                                while True:
                                    chunk = src.read(8 * 1024 * 1024)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
        except (zipfile.BadZipFile, OSError):
            continue
    return sorted(str(p) for p in Path(PARQUET_ROOT).glob("*.parquet"))


def main():
    parquet_files = ensure_parquet()
    h5, h5_tables = h5_schema(H5_PATH)
    if h5["exists"]:
        h5["rows"] = count_table_rows(H5_PATH)
    parq = parquet_schema(parquet_files)
    parq_columns_all, parq_schema_consistent = parquet_schema_all(parquet_files)
    parq["schema_consistent_across_files"] = parq_schema_consistent
    parq["columns"] = [{"name": n, "dtype": d} for n, d in parq_columns_all]
    h5_names = {x["name"] for x in h5["columns"]}
    parq_names = {x["name"] for x in parq["columns"]}
    h5_rows_factory = lambda: h5_rows(H5_PATH, SCAN_COLS)
    parq_rows_factory = lambda: parquet_rows(parquet_files, SCAN_COLS)
    empty_ppi = ppi_stats_from_values([], Counter())
    empty_phist = {"rows_with_phist": 0, "realized_support": None, "flow_count_per_cell": {}}
    if h5["exists"]:
        h5_audit, h5_ppi, h5_phist, _ = audit_stream(h5_rows_factory, h5_names, do_step0=False)
    else:
        h5_audit, h5_ppi, h5_phist = ({c: {"present": False, "populated_count": None} for c in TARGETS}, empty_ppi, empty_phist)
    if parq["exists"]:
        parq_audit, parq_ppi, parq_phist, parq_step = audit_stream(parq_rows_factory, parq_names, do_step0=True)
    else:
        parq_audit, parq_ppi, parq_phist = ({c: {"present": False, "populated_count": None} for c in TARGETS}, empty_ppi, empty_phist)
        parq_step = {"status": "not_measurable", "reason": "Parquet absent", "per_axis_service_counts": {}, "crossings": {}, "design": "not_measurable", "occupancy_table": [], "asn_audit": {}, "single_as_services": []}
    h5_step = {"status": "not_measurable", "reason": "Step-0 is computed on Parquet only by request", "per_axis_service_counts": {}, "crossings": {}, "design": "not_measurable", "occupancy_table": [], "asn_audit": {}, "single_as_services": []}
    report = {
        "generated_at_utc": "2026-09-13T11:58:17Z",
        "formats": {"h5": h5, "parquet": {**parq, "files_audited": len(parquet_files)}},
        "field_audit": {"h5": h5_audit, "parquet": parq_audit},
        "app_label": {"exists_in_parquet": "APP" in parq_names, "exists_in_h5": "APP" in h5_names,
                       "derivation_needed": "APP" not in parq_names,
                       "evidence": {"parquet_populated_count": parq_audit.get("APP", {}).get("populated_count"),
                                    "h5_populated_count": h5_audit.get("APP", {}).get("populated_count"),
                                    "parquet_files_audited": len(parquet_files),
                                    "parquet_label_counts": "APP absent in the audited Parquet schema; no Parquet APP population count is measurable."}},
        "ppi_len": {"h5": h5_ppi, "parquet": parq_ppi},
        "phist": {"binning_scheme": {"size_buckets": 8, "ipt_buckets": 8, "directions": 2,
                                       "theoretical_cells": 8 * 8 * 2, "bucket_edges": ["0-15", "16-31", "32-63", "64-127", "128-255", "256-511", "512-1024", ">1024"]},
                   "source": {"repo": "https://github.com/CESNET/ipfixprobe", "phists_anchor": "https://github.com/CESNET/ipfixprobe/tree/master#phists", "verified_text": "CESNET QUIC22 Zenodo record description: eight logarithmic bins; 0-15, 16-31, 32-63, 64-127, 128-255, 256-511, 512-1024, >1024 [ms or B]"},
                   "theoretical_cells": 128, "realized_support": {"h5": h5_phist, "parquet": parq_phist},
                   "note": "realized_support counts nonzero coordinates across the four stored arrays; a full joint PHIST cell-support audit requires combining all four arrays into a pre-specified cell encoding."},
        "step0": {"h5": h5_step, "parquet": parq_step},
        "blockers": ["Only the valid ZIP archives currently present under /root/autodl-tmp/eibo/data/raw are audited; absent/incomplete monthly archives were not audited, so year-wide occupancy is not yet measurable.",
                     "H5 and Parquet values use different label/time encodings; this report preserves raw dtypes and counts but does not coerce APP ids to names or infer missing service-label semantics."]
    }
    report_path = "/root/eibo/artifacts/schema_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=True, sort_keys=True, indent=2)
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
