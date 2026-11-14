#!/usr/bin/env python3
"""Certify the incremental value of a gyroscope on the KU-HAR activity task."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import platform
import re
import zipfile

import numpy as np
import sklearn
from sklearn.tree import DecisionTreeClassifier

import quic_timing_pilot as timing
from quic_timing_cell_certificate import ALPHA, cell_certificate
from quic_timing_pilot_h5 import sha256


ARCHIVE_SHA256 = "9fe5d0052f2f1d6711afac42ee4badd968116afa8ba4b8ba591f4fdd771c2ec2"
SOURCE = "https://doi.org/10.17632/45f952y38r.5"
RECORDING = re.compile(r"(?P<subject>\d{4})_[A-Z]_[\d_]+\.csv")
RATE = 100
WINDOW_ROWS = 3 * RATE
MIN_LEAF_ROWS = 30
LEAVES = (8, 16)
FIT_SUBJECTS = 30
SPLIT_SEED = 20261114


def sensor_columns(recording, column):
    time = recording[:, column]
    axes = recording[:, column + 1:column + 4]
    # The archive zero-pads the shorter channel stream. Time zero may also
    # describe the original first reading, so omit that boundary sample.
    keep = time > 0
    time, axes = time[keep], axes[keep]
    return time, axes


def describe(windows):
    magnitude = np.linalg.norm(windows, axis=2)
    return np.column_stack((windows.mean(axis=1), windows.std(axis=1),
                            magnitude.mean(axis=1), magnitude.std(axis=1)))


def paired_features(recording):
    accel, gyro = sensor_columns(recording, 0), sensor_columns(recording, 4)
    if any(len(time) < 2 or np.any(np.diff(time) <= 0) for time, _ in (accel, gyro)):
        # A reset or duplicate timestamp makes the interpolation ambiguous.
        return None, 0
    start = int(np.ceil(RATE * max(accel[0][0], gyro[0][0])))
    end = int(np.floor(RATE * min(accel[0][-1], gyro[0][-1])))
    points = max(0, end - start + 1) // WINDOW_ROWS * WINDOW_ROWS
    grid = np.arange(start, start + points) / RATE
    valid = np.ones(points, dtype=bool)
    result = []
    for time, axes in (accel, gyro):
        right = np.clip(np.searchsorted(time, grid), 1, len(time) - 1)
        gap = time[right] - time[right - 1]
        at_sample = np.isclose(grid, time[right], atol=1e-9, rtol=0)
        valid &= (gap <= 1.5 / RATE) | at_sample
        interpolated = np.column_stack([np.interp(grid, time, axis) for axis in axes.T])
        result.append(interpolated.reshape(-1, WINDOW_ROWS, 3))
    complete = valid.reshape(-1, WINDOW_ROWS).all(axis=1)
    return tuple(describe(windows[complete]) for windows in result), points // WINDOW_ROWS


def read_archive(path):
    labels, subjects, accel, gyro = [], [], [], []
    activity_names = {}
    skipped_recordings = 0
    unusable_clocks = 0
    discarded_windows = 0
    with zipfile.ZipFile(path) as archive:
        members = sorted(entry for entry in archive.namelist() if entry.endswith(".csv"))
        if len(members) != 1945 or len(set(members)) != len(members):
            raise ValueError("expected 1,945 distinct recordings in the KU-HAR v5 archive")
        for index, entry in enumerate(members, 1):
            name = PurePosixPath(entry)
            match = RECORDING.fullmatch(name.name)
            code, activity = name.parent.name.split(".", maxsplit=1)
            if match is None or not code.isdecimal():
                raise ValueError(f"unexpected recording name {entry}")
            label, subject = int(code), int(match["subject"])
            activity_names[label] = activity
            with archive.open(entry) as file:
                recording = np.loadtxt(file, delimiter=",", ndmin=2)
            if recording.shape[1] != 8 or not np.all(np.isfinite(recording)):
                raise ValueError(f"expected eight finite columns in {entry}")
            features, candidates = paired_features(recording)
            if features is None:
                unusable_clocks += 1
                continue
            a, g = features
            discarded_windows += candidates - len(a)
            if len(a):
                accel.append(a)
                gyro.append(g)
                labels.extend([label] * len(a))
                subjects.extend([subject] * len(a))
            else:
                skipped_recordings += 1
            if index % 250 == 0 or index == len(members):
                print(f"Read {index}/{len(members)} recordings ({len(labels):,} aligned windows)", flush=True)
    if sorted(activity_names) != list(range(18)) or len(set(subjects)) <= FIT_SUBJECTS:
        raise ValueError("the retained archive does not support the declared class and subject split")
    summary = {"recordings": len(members), "recordings_with_unusable_clocks": unusable_clocks,
               "recordings_without_a_complete_window": skipped_recordings,
               "discarded_windows_with_gaps": discarded_windows}
    return np.asarray(labels), np.asarray(subjects), np.concatenate(accel), np.concatenate(gyro), activity_names, summary


def discretize(features, labels, fit, max_leaves, fit_weights):
    # Each representation uses its own sensor. Fit only on training subjects.
    tree = DecisionTreeClassifier(max_leaf_nodes=max_leaves, min_samples_leaf=MIN_LEAF_ROWS,
                                  random_state=SPLIT_SEED)
    tree.fit(features[fit], labels[fit], sample_weight=fit_weights)
    nodes = tree.apply(features)
    leaf_ids = np.unique(nodes[fit])
    if not np.all(np.isin(nodes, leaf_ids)):
        raise RuntimeError("encountered a leaf with no training records")
    return np.searchsorted(leaf_ids, nodes), len(leaf_ids)


def fit_and_evaluate(labels, subjects, accel, gyro, fit, priors, max_leaves):
    fit_counts = np.bincount(labels[fit], minlength=len(priors))
    test_counts = np.bincount(labels[~fit], minlength=len(priors))
    if min(fit_counts.min(), test_counts.min()) == 0:
        raise ValueError("the declared split must retain every class on both sides")
    fit_weights = (priors / fit_counts)[labels[fit]]
    test_weights = (priors / test_counts)[labels[~fit]]
    coarse, accel_bins = discretize(accel, labels, fit, max_leaves, fit_weights)
    added, gyro_bins = discretize(gyro, labels, fit, max_leaves, fit_weights)
    fine = coarse * gyro_bins + added
    coarse_rule, fine_rule, _ = timing.fit_rules(
        labels[fit], coarse[fit], fine[fit], priors, accel_bins, added_bins=gyro_bins
    )
    result = cell_certificate(labels[~fit], coarse[~fit], fine[~fit], subjects[~fit], priors, fine_rule,
                              compare=True, report_pooled_blocks=True, added_bins=gyro_bins)
    for name, rule, codes in (("accel", coarse_rule, coarse), ("fused", fine_rule, fine)):
        result[f"frozen_{name}_balanced_accuracy"] = timing.rule_accuracy(labels[~fit], codes[~fit], rule,
                                                                         test_weights)
    result["frozen_fused_minus_accel_balanced_accuracy"] = (
        result["frozen_fused_balanced_accuracy"] - result["frozen_accel_balanced_accuracy"]
    )
    return {"accel_bins": accel_bins, "gyro_bins": gyro_bins, "fit_class_counts": fit_counts.tolist(), **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="KU-HAR v5 trimmed interpolated ZIP")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("--out must be a new file")
    digest = sha256(args.archive)
    if digest != ARCHIVE_SHA256:
        parser.error("archive SHA-256 is different from the KU-HAR v5 manifest")

    labels, subjects, accel, gyro, activity_names, archive_summary = read_archive(args.archive)
    rng = np.random.default_rng(SPLIT_SEED)
    fit_subjects = rng.permutation(np.unique(subjects))[:FIT_SUBJECTS]
    fit = np.isin(subjects, fit_subjects)
    priors = np.full(len(activity_names), 1 / len(activity_names))
    comparisons = {str(leaves): fit_and_evaluate(labels, subjects, accel, gyro, fit, priors, leaves)
                   for leaves in LEAVES}
    output = {
        "source": SOURCE,
        "archive_sha256": digest,
        "archive_summary": archive_summary,
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "sklearn": sklearn.__version__},
        "activity_names": dict(sorted(activity_names.items())),
        "sample_rate_hz": RATE,
        "window_seconds": WINDOW_ROWS // RATE,
        "window_alignment": "Interpolate each sensor on a shared grid over its support. Keep complete "
                            "nonoverlapping windows with no interpolation over gaps longer than 15 ms.",
        "encoding": "Fit a separate class-weighted decision tree for each sensor using means and standard "
                    "deviations of three axes and vector magnitude. Use leaf IDs as symbols. "
                    "The fine symbol pairs the accelerometer leaf with the gyroscope leaf.",
        "min_fit_rows_per_leaf": MIN_LEAF_ROWS,
        "split_seed": SPLIT_SEED,
        "fit_subject_ids": sorted(fit_subjects.tolist()),
        "evaluation_subject_ids": sorted(np.unique(subjects[~fit]).tolist()),
        "eligible_windows_per_subject": dict(sorted(Counter(subjects.tolist()).items())),
        "evaluation_unit": "participant, assuming conditional independence across participants",
        "class_prior": "equal",
        "alpha_per_fixed_method_and_encoding": ALPHA,
        "primary_encoding_max_leaves_per_sensor": LEAVES[0],
        "primary_method": "pooled_product",
        "results_by_max_leaves_per_sensor": comparisons,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2, allow_nan=False)
        handle.write("\n")
    for leaves, row in comparisons.items():
        print(f"{leaves} leaves per sensor | {row['sampling_units']} evaluation subjects | "
              f"{row['flows']:,} aligned windows | sample gain {100 * row['sample_bayes_gain']:+.3f} pp | "
              f"frozen comparison {100 * row['frozen_fused_minus_accel_balanced_accuracy']:+.3f} pp")
        print("  " + " | ".join(f"{key} {100 * item['lower']:+.3f} pp"
                                for key, item in row["certificate_comparison"].items()))
    print(f"Results: {args.out}")


if __name__ == "__main__":
    main()
