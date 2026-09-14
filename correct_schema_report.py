#!/usr/bin/env python3
import json
import os
from pathlib import Path
from collections import Counter

import numpy as np
import pyarrow.parquet as pq
import tables

REPORT = "/root/eibo/artifacts/schema_report.json"
H5 = "/root/autodl-tmp/RECAST-QUICEXT-25-2026-09-07/data/XS/CESNET-QUICEXT-25-XS.h5"
PARQUET_ROOT = Path("/dev/shm/quicext_parquet")


def add_marginal_cells(counter, values, field):
    """Count occupied coordinates in one of the four emitted 8-bin arrays."""
    values = np.asarray(values)
    for bucket in range(8):
        n = int(np.count_nonzero(values[:, bucket] > 0))
        if n:
            counter[f"{field}:bin={bucket}"] += n


def h5_phist():
    c = Counter()
    rows = 0
    with tables.open_file(H5) as f:
        for name in f.root.flows._v_children:
            table = f.root.flows._v_children[name]
            rows += int(table.nrows)
            for start in range(0, table.nrows, 250_000):
                stop = min(start + 250_000, table.nrows)
                for field in ("PHIST_SRC_SIZES", "PHIST_SRC_IPT", "PHIST_DST_SIZES", "PHIST_DST_IPT"):
                    add_marginal_cells(c, table.read(start, stop, field=field), field)
    return {"rows_scanned": rows, "rows_with_phist": rows, "realized_support": len(c), "flow_count_per_cell": dict(sorted(c.items()))}


def parquet_phist(files):
    c = Counter()
    rows = 0
    for path in files:
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(columns=["PHIST_SRC_SIZES", "PHIST_DST_SIZES", "PHIST_SRC_IPT", "PHIST_DST_IPT"], batch_size=100_000):
            data = batch.to_pydict()
            for field in ("PHIST_SRC_SIZES", "PHIST_SRC_IPT", "PHIST_DST_SIZES", "PHIST_DST_IPT"):
                add_marginal_cells(c, np.asarray(data[field], dtype=np.int64), field)
            rows += batch.num_rows
    return {"rows_scanned": rows, "rows_with_phist": rows, "realized_support": len(c), "flow_count_per_cell": dict(sorted(c.items()))}


def main():
    with open(REPORT, encoding="utf-8") as f:
        report = json.load(f)
    files = sorted(str(p) for p in PARQUET_ROOT.glob("*.parquet"))
    report["app_label"] = {
        "exists_in_parquet": False,
        "exists_in_h5": True,
        "derivation_needed": True,
        "evidence": {
            "parquet_populated_count": None,
            "h5_populated_count": report["field_audit"]["h5"]["APP"]["populated_count"],
            "parquet_files_audited": len(files),
            "parquet_label_counts": "APP absent in the audited Parquet schema; no Parquet APP population count is measurable.",
        },
    }
    h5 = h5_phist()
    parq = parquet_phist(files) if files else {"rows_scanned": 0, "rows_with_phist": 0, "realized_support": None, "flow_count_per_cell": {}}
    report["phist"]["realized_support"] = {"h5": h5, "parquet": parq}
    report["phist"]["binning_scheme"] = {
        "size_buckets": 8,
        "ipt_buckets": 8,
        "directions": 2,
        "emitted_arrays": 4,
        "theoretical_cells": 4 * 8,
        "bucket_edges": ["0-15", "16-31", "32-63", "64-127", "128-255", "256-511", "512-1024", ">1024"],
    }
    report["phist"]["theoretical_cells"] = 4 * 8
    report["phist"]["note"] = "The exporter emits four separate marginal histograms (source/destination packet sizes and IPT), each with 8 fixed bins. Realized support counts nonzero field-bin coordinates; it is not a joint size-by-IPT cross-product."
    report["step0"] = {
        "h5": {
            "status": "not_measurable",
            "reason": "Step-0 is defined on Parquet only by request.",
            "service_label_column": None,
            "per_axis_service_counts": {},
            "crossings": {},
            "design": "not_measurable",
            "occupancy_table": [],
            "asn_audit": {},
            "single_as_services": [],
        },
        "parquet": {
            "status": "not_measurable",
            "reason": "Parquet has no APP column and no validated SNI-to-service mapping was supplied. Raw QUIC_SNI values are hostnames, not service labels, so service crossings, occupancy, and ASN confounding cannot be validly computed from these files alone.",
            "service_label_column": None,
            "per_axis_service_counts": {},
            "crossings": {},
            "design": "not_measurable",
            "occupancy_table": [],
            "asn_audit": {},
            "single_as_services": [],
        },
    }
    report["blockers"] = [
        "Only the valid ZIP archives currently present under /root/autodl-tmp/eibo/data/raw are audited; absent/incomplete monthly archives were not audited, so year-wide occupancy is not yet measurable.",
        "APP is absent from the audited Parquet schema, while H5 contains APP; service labels therefore require a Parquet-side derivation or a separately supplied mapping.",
        "The previous Parquet Step-0 pass used raw QUIC_SNI hostnames as service keys; that proxy result is discarded because it is not a validated service-label mapping. Step-0 is therefore not measurable on Parquet yet.",
    ]
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=True, sort_keys=True, indent=2)
    print(json.dumps({"report": REPORT, "app_label": report["app_label"], "phist": report["phist"], "blockers": report["blockers"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
