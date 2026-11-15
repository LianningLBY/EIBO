#!/usr/bin/env python3
"""Run the timing gain experiment on a local CESNET-QUICEXT-25 XS H5."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from quic_timing_pilot import ALPHA, K, TIMING_BINS, TIMING_CUTS_MS, assess, fit_rules, gain_bound
from eibo.realdata import DAY, FlowSource, chronological_windows, utc, whole_interval_mask
from eibo.realexperiment import FixedPrefixEncoder, TimeUnitGeometry

BLOCK_HOURS = (1, 6, 24, 48)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(16 * 1024**2), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan(source, tables, windows, encoder, chunk_rows, rounding, *, raw_timing=False):
    """Read bounded chunks, optionally retaining the interval in place of the fine symbol."""
    parts = {period: [] for period in windows}
    rows_read = 0
    for index, table in enumerate(tables, 1):
        capacity = table["ppi_capacity"]
        if capacity < K:
            raise ValueError(f"PPI capacity too small in {table['path']}")
        for start in range(0, table["rows"], chunk_rows):
            records = source.read(table["path"], start, min(start + chunk_rows, table["rows"]))
            rows_read += len(records)
            first = np.asarray(records["TIME_FIRST"], dtype=float)
            last = np.asarray(records["TIME_LAST"], dtype=float)
            lengths = np.asarray(records["PPI_LEN"], dtype=float)
            apps = records["APP"]
            if apps.dtype.kind not in "iu" or any(a.shape != (len(records),) for a in (first, last, lengths, apps)):
                raise ValueError("expected scalar epoch seconds, prefix lengths and integer APP codes")
            valid = np.isfinite(first) & np.isfinite(last) & (last >= first)
            valid &= (lengths >= K) & (lengths <= capacity) & (lengths == np.floor(lengths))
            ppi = records["PPI"][:, :, :K]
            valid &= np.isin(ppi[:, 1], (-1, 1)).all(axis=1)
            sizes, timing = ppi[:, 2], ppi[:, 0, 1]
            valid &= (np.isfinite(sizes) & (sizes > 0) & (sizes == np.floor(sizes))).all(axis=1)
            valid &= np.isfinite(timing) & (timing >= 0)
            for period, window in windows.items():
                use = valid & whole_interval_mask(first, last, window, rounding)
                if use.any():
                    x = encoder.encode(ppi[use])
                    interval = timing[use]
                    if not raw_timing:
                        t = np.searchsorted(TIMING_CUTS_MS, interval, side="left")
                        interval = (x * TIMING_BINS + t).astype(np.int16)
                    parts[period].append((apps[use], x.astype(np.int16), interval, first[use], last[use]))
        if index % 30 == 0 or index == len(tables):
            print(f"Scanned {index}/{len(tables)} daily tables ({rows_read:,} rows)", flush=True)
    if rows_read != sum(table["rows"] for table in tables):
        raise RuntimeError("H5 scan did not read the expected row count")
    return {name: tuple(np.concatenate(column) for column in zip(*chunks)) for name, chunks in parts.items()}, rows_read


def rank_pilot_services(apps):
    """Rank eligible pilot APP codes by count, with code order breaking ties."""
    codes, counts = np.unique(apps, return_counts=True)
    order = np.argsort(-counts, kind="stable")
    return codes[order], counts[order]


def fit(pilot, alphabet, *, classes=None):
    apps, x, z, _, _ = pilot
    if classes is None:
        ranked, _ = rank_pilot_services(apps)
        if len(ranked) < 8:
            raise ValueError("the pilot window has fewer than eight usable APP codes")
        classes = ranked[:8]
    classes = np.sort(classes)
    priors = np.full(len(classes), 1 / len(classes))
    keep = np.isin(apps, classes)
    coarse, fused, ns = fit_rules(np.searchsorted(classes, apps[keep]), x[keep], z[keep], priors, alphabet)
    return classes, priors, coarse, fused, ns


def evaluate(data, window, rounding, classes, priors, alphabet, coarse, fused):
    apps, x, z, first, last = data
    keep = np.isin(apps, classes)
    labels = np.searchsorted(classes, apps[keep])
    present = np.bincount(labels, minlength=len(classes)) > 0
    if not present.all():
        raise ValueError(f"fixed pilot APP codes missing in evaluation: {classes[~present].tolist()}")
    selected_first = first[keep]
    hour = (selected_first // 3600).astype(np.int64)
    result = assess((labels, x[keep], z[keep], hour), priors, alphabet, coarse, fused)
    geometry = TimeUnitGeometry(window, len(classes), [h * 3600 for h in BLOCK_HOURS], rounding)
    # Other eligible APP codes can bridge boundaries even though they carry no score weight.
    geometry.add(first, last, selected_first, labels)
    gap = result["fused_minus_coarse_sample_optimum"]
    for info in geometry.diagnostics(priors, ALPHA):
        width = info["block_seconds"] // 3600
        budget = info["span_merged_squared_change_budget"]
        result["bounds"][f"span_merged_{width}h"] = {
            "blocks": info["span_merged_nonempty_units"], "effective_blocks": 1 / budget,
            "merged_boundary_edges": info["merged_boundary_edges"], **gain_bound(gap, budget),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--backend", choices=("auto", "tables", "h5py"), default="auto")
    parser.add_argument("--chunk-rows", type=int, default=20_000)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    if args.out.exists() or args.chunk_rows <= 0:
        parser.error("use a new output path and a positive chunk size")

    before = args.h5.stat()
    source_hash = sha256(args.h5) if args.expected_sha256 else None
    if source_hash and source_hash != args.expected_sha256.lower():
        raise ValueError(f"H5 SHA-256 mismatch: got {source_hash}")
    rounding = 3600
    encoder = FixedPrefixEncoder(K, 2)
    source = FlowSource(args.h5, args.backend)
    try:
        tables = source.tables()
        windows = chronological_windows(tables, gap_seconds=DAY, end_margin_seconds=rounding)
        periods, rows_read = scan(source, tables, windows, encoder, args.chunk_rows, rounding)
    finally:
        source.close()
    after = args.h5.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError("H5 changed during the scan")
    for name, data in periods.items():
        if not data:
            raise ValueError(f"no eligible rows in {name}; check the H5 dates and epoch seconds")
    classes, priors, coarse, fused, counts = fit(periods.pop("pilot"), encoder.alphabet)
    pooled_window = (windows["certificate"][0], windows["evaluation"][1])
    results = {name: evaluate(data, windows[name], rounding, classes, priors, encoder.alphabet, coarse, fused)
               for name, data in periods.items()}
    pooled = tuple(np.concatenate(column) for column in zip(periods["certificate"], periods["evaluation"]))
    results["all"] = evaluate(pooled, pooled_window, rounding, classes, priors, encoder.alphabet, coarse, fused)

    output = {"source": {"path": str(args.h5.resolve()), "bytes": before.st_size, "sha256": source_hash,
                         "backend": source.backend, "rows_read": rows_read, "daily_tables": len(tables)},
              "windows_utc": {name: [utc(start), utc(stop)] for name, (start, stop) in windows.items()},
              "k": K, "size_encoding": "EIBO log M=2", "timing": "second packet inter-arrival (ms)",
              "timing_cuts_inclusive_ms": TIMING_CUTS_MS, "rounding_seconds": rounding,
              "alpha_per_scenario": ALPHA, "classes_in_count_order": classes.tolist(),
              "priors": priors.tolist(), "fit_counts": counts.tolist(), "results": results,
              "interpretation": "Exploratory fixed APP cohort. Classes are the eight most frequent eligible pilot codes. Bounds condition on training and class counts per sampling unit, and assume independence across those units. Span merging links blocks touched by the same flow under the hourly timestamp envelope. Grouping and merging do not establish independence."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")
    for name, result in results.items():
        print(f"{name}: n={result['flows']:,}, ceilings {result['coarse_ceiling']:.2%} -> {result['fused_ceiling']:.2%}")
        print("  gain lower bounds: " + ", ".join(f"{key}={value['lower']:.2%}" for key, value in result["bounds"].items()))
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
