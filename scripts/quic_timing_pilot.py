#!/usr/bin/env python3
"""Matched sample ceilings and conditional gain bounds on CESNET-QUIC22."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from eibo.realexperiment import FixedPrefixEncoder
from eibo.riskcert import empirical_known_risk, joint_radius_from_change_budget

ARCHIVE = "https://zenodo.org/api/records/10728760/files/cesnet-quic22.zip/content"
ARCHIVE_SIZE = 20_952_008_298
PREFIX_BYTES = 4 * 1024**2
K = 5
TIMING_CUTS_MS = (0, 1, 4, 16)
TIMING_BINS = len(TIMING_CUTS_MS) + 1
FIT_END = "20221106"
GAP_DATE = "20221107"
EVAL_MID = "20221118"
ALPHA = 0.05


def archive_members(tail_file):
    """Read the central directory from its byte range, without a 21 GB file."""
    tail = tail_file.read_bytes()
    with zipfile.ZipFile(io.BytesIO(tail)) as archive:
        offset_correction = ARCHIVE_SIZE - len(tail)
        days = {}
        for member in archive.infolist():
            match = re.search(r"/flows-(\d{8})\.csv\.gz$", member.filename)
            if match:
                days[match[1]] = member.header_offset + offset_correction
    if len(days) != 28:
        raise ValueError("expected 28 daily flow members in the official archive")
    return days


def prefix_rows(raw, date):
    signature, _, _, method, *_, name_len, extra_len = struct.unpack("<4s5H3I2H", raw[:30])
    name = raw[30:30 + name_len].decode("ascii")
    if signature != b"PK\x03\x04" or method != zipfile.ZIP_DEFLATED or not name.endswith(f"/flows-{date}.csv.gz"):
        raise ValueError(f"wrong ZIP member for {date}")
    nested_gzip = zlib.decompressobj(-15).decompress(raw[30 + name_len + extra_len:])
    text = zlib.decompressobj(31).decompress(nested_gzip)
    # The compressed prefix may stop in the middle of a CSV record.
    complete = text[:text.rfind(b"\n") + 1]
    return csv.DictReader(io.StringIO(complete.decode("utf-8")), strict=True)


def read_day(path, date, encoder, offsets):
    raw = path.read_bytes()
    if len(raw) != PREFIX_BYTES:
        raise ValueError(f"incorrect prefix length for {date}")
    rows, hours, apps = [], [], []
    min_start, max_end, n_read = None, None, 0
    for row in prefix_rows(raw, date):
        n_read += 1
        app = row["APP"]
        if not app or "background" in app.lower() or int(row["PPI_LEN"]) < K:
            continue
        start, end = (dt.datetime.fromisoformat(row[key]) for key in ("TIME_FIRST", "TIME_LAST"))
        start_hour, end_hour = (t.replace(minute=0, second=0, microsecond=0) for t in (start, end))
        # Use the same cohort at every block width, with no flow split by an hour boundary.
        if end < start or end_hour != start_hour:
            continue
        ppi = [axis[:K] for axis in json.loads(row["PPI"])]
        if len(ppi) != 3 or any(len(axis) != K for axis in ppi):
            raise ValueError(f"inconsistent PPI length on {date}")
        if ppi[0][1] < 0 or any(size <= 0 for size in ppi[2]):
            continue
        rows.append(ppi)
        hours.append((start_hour.date().toordinal() - dt.date(1970, 1, 1).toordinal()) * 24 + start_hour.hour)
        apps.append(app)
        min_start = start if min_start is None else min(start, min_start)
        max_end = end if max_end is None else max(end, max_end)
    if not rows:
        raise ValueError(f"no usable rows for {date}")
    values = np.asarray(rows)
    x = encoder.encode(values)
    t = np.searchsorted(TIMING_CUTS_MS, values[:, 0, 1], side="left")
    meta = {"date": date, "byte_range": [offsets[date], offsets[date] + PREFIX_BYTES - 1],
            "sha256": hashlib.sha256(raw).hexdigest(), "complete_rows": n_read,
            "usable_nonbackground_rows": len(rows), "earliest_start": min_start.isoformat(),
            "latest_end": max_end.isoformat(), "nonempty_hours": len(set(hours))}
    return (np.asarray(apps), x, x * TIMING_BINS + t, np.asarray(hours)), meta


def combine(days, classes):
    merged = [np.concatenate(part) for part in zip(*days)]
    keep = np.isin(merged[0], classes)
    return (np.searchsorted(classes, merged[0][keep]), *(field[keep] for field in merged[1:]))


def hist(labels, symbols, n_classes, alphabet):
    return np.bincount(labels * alphabet + symbols, minlength=n_classes * alphabet).reshape(n_classes, alphabet)


def fit_rules(y, x, z, priors, alphabet, *, added_bins=TIMING_BINS):
    coarse = hist(y, x, len(priors), alphabet)
    fused = hist(y, z, len(priors), alphabet * added_bins)
    ns = coarse.sum(axis=1)
    train_weights = (priors / ns)[:, None]
    coarse_rule = (train_weights * coarse).argmax(axis=0)
    fused_rule = (train_weights * fused).argmax(axis=0)
    unseen = np.flatnonzero(fused.sum(axis=0) == 0)
    fused_rule[unseen] = coarse_rule[unseen // added_bins]
    return coarse_rule, fused_rule, ns


def rule_accuracy(labels, symbols, prediction, sample_weights):
    return float(sample_weights[labels == prediction[symbols]].sum())


def gain_bound(gap, budget):
    """Lower confidence bound using the range of the paired score in each block.

    The frozen fused classifier minus the empirical coarse optimum is at most
    the paired difference against the population-optimal coarse classifier.
    Conditional on training and fixed class counts, that comparison has a
    block score in [-w_b, w_b]. Across independent blocks its mean is at most
    the Bayes gain in the corresponding class-weighted target mixture.
    """
    radius = float(joint_radius_from_change_budget([4 * budget], alpha=ALPHA)[0])
    return {"radius": radius, "unclipped_lower": gap - radius, "lower": max(0.0, gap - radius)}


def assess(data, priors, alphabet, coarse_rule, fused_rule):
    y, x, z, hour = data
    n_classes = len(priors)
    coarse = hist(y, x, n_classes, alphabet)
    fused = hist(y, z, n_classes, alphabet * TIMING_BINS)
    ns = coarse.sum(axis=1)
    if not np.all(ns > 0) or not np.array_equal(coarse, fused.reshape(n_classes, alphabet, TIMING_BINS).sum(axis=2)):
        raise ValueError("empty class or the fine counts do not project to the coarse counts")
    coarse_ceiling = 1 - empirical_known_risk(coarse, priors)
    fused_ceiling = 1 - empirical_known_risk(fused, priors)
    if fused_ceiling + 1e-12 < coarse_ceiling:
        raise RuntimeError("sample ceiling decreased under refinement")
    weights = (priors / ns)[y]
    a_coarse = rule_accuracy(y, x, coarse_rule, weights)
    a_fused = rule_accuracy(y, z, fused_rule, weights)
    gap = a_fused - coarse_ceiling
    bounds = {"iid_flow": {"blocks": len(y), **gain_bound(gap, float(weights @ weights))}}
    for width in (1, 6, 24, 48):
        _, index = np.unique(hour // width, return_inverse=True)
        mass = np.bincount(index, weights=weights)
        budget = float(mass @ mass)
        bounds[f"{width}h"] = {"blocks": len(mass), "effective_blocks": 1 / budget,
                               "max_block_mass": float(mass.max()), **gain_bound(gap, budget)}
    return {"flows": len(y), "class_counts": ns.tolist(), "coarse_ceiling": coarse_ceiling,
            "fused_ceiling": fused_ceiling, "sample_ceiling_gain": fused_ceiling - coarse_ceiling,
            "frozen_coarse_accuracy": a_coarse, "frozen_fused_accuracy": a_fused,
            "frozen_model_gain": a_fused - a_coarse, "fused_minus_coarse_sample_optimum": gap,
            "bounds": bounds}


def daily_sensitivity(dates, daily):
    """Circular moving-block bootstrap of equal-day conservative gaps."""
    gaps = np.array([daily[date]["fused_minus_coarse_sample_optimum"] for date in dates])
    n = len(gaps)
    rng = np.random.default_rng(20261111)
    replicates = 20_000
    lower = {}
    for width in (1, 2, 4):
        starts = rng.integers(0, n, size=(replicates, (n + width - 1) // width))
        indices = (starts[:, :, None] + np.arange(width)).reshape(replicates, -1)[:, :n] % n
        lower[str(width)] = float(np.quantile(gaps[indices].mean(axis=1), ALPHA))
    return {"equal_day_mean_gap": float(gaps.mean()), "min_daily_gap": float(gaps.min()),
            "max_daily_gap": float(gaps.max()), "positive_days": int((gaps > 0).sum()),
            "bootstrap_5th_percentile_by_block_days": lower, "bootstrap_replicates": replicates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("refusing to overwrite existing results")
    encoder = FixedPrefixEncoder(K, 2)
    offsets = archive_members(args.prefix_dir / "quic22-tail.bin")
    days, manifests = {}, {}
    for date in sorted(offsets):
        if date != GAP_DATE:
            days[date], manifests[date] = read_day(args.prefix_dir / f"{date}.prefix", date, encoder, offsets)
    fit = [date for date in days if date <= FIT_END]
    evaluation = [date for date in days if date > GAP_DATE]
    fit_end = max(manifests[date]["latest_end"] for date in fit)
    eval_start = min(manifests[date]["earliest_start"] for date in evaluation)
    if fit_end >= eval_start:
        raise ValueError("fitting and evaluation flow intervals overlap")
    apps, counts = np.unique(np.concatenate([days[date][0] for date in fit]), return_counts=True)
    classes = np.asarray(sorted(apps[np.argsort(-counts, kind="stable")[:8]]))
    if len(classes) != 8:
        raise ValueError("insufficient pilot classes")
    priors = np.full(len(classes), 1 / len(classes))
    y, x, z, _ = combine([days[date] for date in fit], classes)
    coarse_rule, fused_rule, fit_counts = fit_rules(y, x, z, priors, encoder.alphabet)
    periods = {"all": evaluation, "early": [d for d in evaluation if d < EVAL_MID],
               "late": [d for d in evaluation if d >= EVAL_MID]}
    results = {name: {"dates": dates, **assess(combine([days[d] for d in dates], classes), priors,
                                               encoder.alphabet, coarse_rule, fused_rule)}
               for name, dates in periods.items()}
    daily = {}
    for date in evaluation:
        measures = assess(combine([days[date]], classes), priors, encoder.alphabet, coarse_rule, fused_rule)
        daily[date] = {key: measures[key] for key in ("flows", "coarse_ceiling", "fused_ceiling",
                                                    "frozen_fused_accuracy", "fused_minus_coarse_sample_optimum")}
    sensitivity = {name: daily_sensitivity(dates, daily) for name, dates in periods.items()}
    result = {"archive": ARCHIVE, "archive_size": ARCHIVE_SIZE, "prefix_bytes": PREFIX_BYTES,
              "k": K, "size_encoding": "EIBO log M=2", "timing": "second packet inter-arrival (ms)",
              "timing_cuts_inclusive_ms": TIMING_CUTS_MS, "alpha_per_scenario": ALPHA,
              "classes_in_count_order": classes.tolist(), "priors": priors.tolist(),
              "fit_dates": fit, "fit_counts": fit_counts.tolist(), "gap_date": GAP_DATE,
              "latest_fit_end": fit_end, "earliest_evaluation_start": eval_start, "files": manifests,
              "results": results, "daily": daily, "daily_sensitivity": sensitivity,
              "daily_sensitivity_scope": "Equal-day mean of frozen fusion accuracy minus that day's sample coarse optimum. Circular moving-block percentiles are exploratory, require a roughly stationary short-range dependent daily series, and do not provide a finite-sample certificate.",
              "interpretation": "Exploratory file-prefix cohort. Conditional on training and fixed per-block class counts, bounds allow arbitrary dependence within independent blocks. Block independence is not established by timestamp grouping. No extrapolation to unseen classes or full-day traffic."}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write("\n")


if __name__ == "__main__":
    main()
