#!/root/miniconda3/bin/python3
import argparse
import collections
import itertools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import tables

sys.path.insert(0, "/root/eibo/scripts")
import xs_compression_early_readout as xs

H5_PATH = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
K_VALUES = (15, 30)
M_VALUES = (1, 2, 4, 8, 16)
CHUNK_SIZE = 100_000
SERVICE_THRESHOLD = 2_000


def load_services():
    rows = json.load(open("/root/eibo/artifacts/q1_absolute_counts.json", "r"))["pairs"]
    services = sorted({int(r["service_a"]) for r in rows} | {int(r["service_b"]) for r in rows})
    if len(services) != 45:
        raise RuntimeError(f"expected 45 services from k5 artifact, observed {len(services)}")
    return services


def run(k, m, out):
    if k not in K_VALUES or m not in M_VALUES:
        raise ValueError((k, m))
    services = load_services()
    counters = {s: collections.Counter() for s in services}
    eligible_counts = collections.Counter()
    service_ints = np.asarray(services, dtype=np.int16)
    paths = []
    started = time.time()
    rows_seen = 0
    with tables.open_file(H5_PATH, mode="r") as h5:
        paths = xs.table_paths(h5)
        for table_index, path in enumerate(paths, 1):
            node = h5.get_node(path)
            for start in range(0, int(node.nrows), CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, int(node.nrows))
                apps = np.asarray(node.read(start, stop, field="APP")).reshape(-1)
                lens = np.asarray(node.read(start, stop, field="PPI_LEN")).reshape(-1)
                use = np.isin(apps, service_ints) & (lens >= k)
                if not np.any(use):
                    continue
                ppi = np.asarray(node.read(start, stop, field="PPI"))[use]
                apps_use = apps[use]
                codes = xs.pack_rung_prefix(ppi, k, m, 1, 2)
                for service in np.unique(apps_use):
                    sel = apps_use == service
                    service_i = int(service)
                    eligible_counts[service_i] += int(np.sum(sel))
                    counters[service_i].update(int(codes[i]) for i in np.flatnonzero(sel))
                rows_seen += int(len(apps_use))
            if table_index % 50 == 0 or table_index == len(paths):
                print(json.dumps({
                    "k": k,
                    "M": m,
                    "table_index": table_index,
                    "table_count": len(paths),
                    "eligible_rows_seen": rows_seen,
                    "elapsed_seconds": time.time() - started,
                }, sort_keys=True), flush=True)

    usable = [s for s in services if eligible_counts[s] >= SERVICE_THRESHOLD]
    rows = []
    for pair_index, (a, b) in enumerate(itertools.combinations(usable, 2), 1):
        value = xs.tv(counters[a], counters[b])
        if value is None:
            raise RuntimeError(f"empty counter for {a},{b}")
        rows.append({
            "service_a": str(a),
            "service_b": str(b),
            "M": int(m),
            "n_a": int(eligible_counts[a]),
            "n_b": int(eligible_counts[b]),
            "tv_masked": float(value),
        })
        if pair_index % 50 == 0 or pair_index == len(rows):
            print(json.dumps({"k": k, "M": m, "pair_index": pair_index, "pair_count": len(usable) * (len(usable) - 1) // 2}, sort_keys=True), flush=True)
    result = {
        "k": int(k),
        "M": int(m),
        "pair_count": len(rows),
        "usable_services": len(usable),
        "eligible_counts": {str(s): int(eligible_counts[s]) for s in usable},
        "rows": rows,
        "source_h5": H5_PATH,
        "source_tables": len(paths),
        "fresh_h5_pass": True,
        "masking": "PPI[1] direction and PPI[2] size; PPI_LEN tail masked by restricting to PPI_LEN >= k; PPI[0] excluded",
    }
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(result, handle, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, out)
    print(json.dumps({"status": "complete", "k": k, "M": m, "pair_count": len(rows), "out": out}, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, required=True)
    parser.add_argument("--m", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    run(args.k, args.m, args.out)


if __name__ == "__main__":
    main()
