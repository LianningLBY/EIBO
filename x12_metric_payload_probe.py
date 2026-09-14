#!/usr/bin/env python3
"""Read-only measurement probe for X12 detector metric payload sizing."""

from __future__ import annotations

import csv
import io
import os
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import tables


H5_PATH = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5")
SCRIPT_PATH = Path("/root/eibo/x12_detector_validation.py")
CSV_PATH = Path("/root/eibo/artifacts/x12_detector_validation_per_pair.csv")
TRAIN_MONTHS = ("202406", "202407", "202408", "202409", "202410", "202411")
TEST_MONTHS = ("202501", "202502", "202503", "202504", "202505")
BUFFER_MONTH = "202412"
N_CLASSES = 53


def print_csv_measurement() -> None:
    with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = sum(1 for _ in reader)
    print(f"CSV_PATH={CSV_PATH}")
    print(f"CSV_SIZE_BYTES={CSV_PATH.stat().st_size}")
    print(f"CSV_DATA_ROWS={rows}")
    print(f"CSV_HEADER={header!r}")
    print(
        "CSV_HAS_PER_CLASS_VECTOR="
        f"{any('prob' in col.lower() or 'score_vector' in col.lower() for col in header)}"
    )


def print_script_writer() -> None:
    lines = SCRIPT_PATH.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith("def prepare_csv(")]
    append_starts = [i for i, line in enumerate(lines) if line.startswith("def append_pair_rows(")]
    end_markers = [i for i, line in enumerate(lines) if line.startswith("def stratified_holdout_indices(")]
    if not starts or not append_starts or not end_markers:
        print("SCRIPT_WRITER_BLOCK=NOT_FOUND")
        return
    start = starts[0]
    end = end_markers[0]
    print(f"SCRIPT_WRITER_LINES={start + 1}:{end}")
    for line_number, line in enumerate(lines[start:end], start=start + 1):
        print(f"SCRIPT_WRITER[{line_number}]={line}")


def month_from_node_name(name: str) -> str:
    return name[1:7] if name.startswith("D") else name[:6]


def print_h5_measurement() -> None:
    command = (
        "/root/miniconda3/bin/python3 /root/eibo/x12_metric_payload_probe.py "
        "--h5 /root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5 "
        "--label-field APP"
    )
    print(f"H5_MEASUREMENT_COMMAND={command}")
    with tables.open_file(str(H5_PATH), mode="r") as h5:
        nodes = sorted(list(h5.list_nodes("/flows")), key=lambda node: node._v_name)
        if not nodes:
            raise RuntimeError("no tables under /flows")
        print(f"H5_NODE_COUNT={len(nodes)}")
        print(f"H5_FIRST_NODE={nodes[0]._v_pathname}")
        print(f"H5_FIRST_NODE_COLNAMES={nodes[0].colnames!r}")

        month_rows: Counter[str] = Counter()
        month_label_counts: dict[str, Counter[int]] = defaultdict(Counter)
        for node in nodes:
            month = month_from_node_name(node._v_name)
            app = np.asarray(node.col("APP"), dtype=np.int64)
            month_rows[month] += int(node.nrows)
            month_label_counts[month].update(int(value) for value in app if int(value) >= 0)

        train_rows_raw = sum(month_rows[month] for month in TRAIN_MONTHS)
        test_rows_raw = sum(month_rows[month] for month in TEST_MONTHS)
        buffer_rows = month_rows[BUFFER_MONTH]
        train_labels = set(
            label
            for month in TRAIN_MONTHS
            for label in month_label_counts[month]
            if label >= 0
        )
        test_labels = set(
            label
            for month in TEST_MONTHS
            for label in month_label_counts[month]
            if label >= 0
        )
        common_labels = sorted(train_labels & test_labels)
        train_rows_common = sum(
            count
            for month in TRAIN_MONTHS
            for label, count in month_label_counts[month].items()
            if label in common_labels
        )
        test_rows_common = sum(
            count
            for month in TEST_MONTHS
            for label, count in month_label_counts[month].items()
            if label in common_labels
        )

        print(f"H5_MONTH_ROWS={dict(sorted(month_rows.items()))}")
        print(f"H5_TRAIN_MONTHS={TRAIN_MONTHS}")
        print(f"H5_TEST_MONTHS={TEST_MONTHS}")
        print(f"H5_BUFFER_MONTH={BUFFER_MONTH}")
        print(f"H5_TRAIN_ROWS_RAW={train_rows_raw}")
        print(f"H5_TEST_ROWS_RAW={test_rows_raw}")
        print(f"H5_BUFFER_ROWS={buffer_rows}")
        print(f"H5_TRAIN_APP_LABEL_COUNT={len(train_labels)}")
        print(f"H5_TEST_APP_LABEL_COUNT={len(test_labels)}")
        print(f"H5_COMMON_APP_LABEL_COUNT={len(common_labels)}")
        print(f"H5_COMMON_APP_LABELS={common_labels}")
        print(f"H5_TRAIN_ROWS_AFTER_COMMON_LABEL_FILTER={train_rows_common}")
        print(f"H5_TEST_ROWS_AFTER_COMMON_LABEL_FILTER={test_rows_common}")


def bytes_and_gb(value: int) -> str:
    return f"{value} bytes ({value / 1_000_000_000:.9f} GB; {value / 2**30:.9f} GiB)"


def print_size_measurements(rows: int) -> None:
    raw_f32 = rows * N_CLASSES * 4
    raw_f16 = rows * N_CLASSES * 2
    top5_f32_scores = rows * 5 * 4
    top5_f16_scores = rows * 5 * 2
    top5_uint8_ids = rows * 5
    top5_f32_with_ids = top5_f32_scores + top5_uint8_ids
    top5_f16_with_ids = top5_f16_scores + top5_uint8_ids

    block_rows = 100_000
    rng = np.random.default_rng(20260914)
    logits = rng.normal(size=(block_rows, N_CLASSES)).astype(np.float32)
    logits -= logits.max(axis=1, keepdims=True)
    block_f32 = np.exp(logits)
    block_f32 /= block_f32.sum(axis=1, keepdims=True)
    block_f32 = block_f32.astype(np.float32)
    block_f16 = block_f32.astype(np.float16)

    compressed_f32_buffer = io.BytesIO()
    np.savez_compressed(compressed_f32_buffer, scores=block_f32)
    compressed_f32_bytes = compressed_f32_buffer.tell()
    block_f32_bytes = block_f32.nbytes
    ratio_f32 = compressed_f32_bytes / block_f32_bytes
    extrapolated_f32 = int(round(raw_f32 * ratio_f32))

    compressed_f16_buffer = io.BytesIO()
    np.savez_compressed(compressed_f16_buffer, scores=block_f16)
    compressed_f16_bytes = compressed_f16_buffer.tell()
    block_f16_bytes = block_f16.nbytes
    ratio_f16 = compressed_f16_bytes / block_f16_bytes
    extrapolated_f16 = int(round(raw_f16 * ratio_f16))

    print(f"SIZE_ROWS={rows}")
    print(f"SIZE_CLASSES={N_CLASSES}")
    print(f"A_FLOAT32_ARITHMETIC={rows} * {N_CLASSES} * 4")
    print(f"A_FLOAT32={bytes_and_gb(raw_f32)}")
    print(f"A_FLOAT16_ARITHMETIC={rows} * {N_CLASSES} * 2")
    print(f"A_FLOAT16={bytes_and_gb(raw_f16)}")
    print(
        "B_BLOCK="
        f"{block_rows}x{N_CLASSES}, "
        f"f32_raw={block_f32_bytes}, f32_npz_compressed={compressed_f32_bytes}, "
        f"f32_ratio={ratio_f32:.9f}"
    )
    print(f"B_FLOAT32_EXTRAPOLATED={bytes_and_gb(extrapolated_f32)}")
    print(
        "B_BLOCK_FLOAT16="
        f"{block_rows}x{N_CLASSES}, "
        f"f16_raw={block_f16_bytes}, f16_npz_compressed={compressed_f16_bytes}, "
        f"f16_ratio={ratio_f16:.9f}"
    )
    print(f"B_FLOAT16_EXTRAPOLATED={bytes_and_gb(extrapolated_f16)}")
    print(f"C_TOP5_FLOAT32_SCORE_ONLY_ARITHMETIC={rows} * 5 * 4")
    print(f"C_TOP5_FLOAT32_SCORE_ONLY={bytes_and_gb(top5_f32_scores)}")
    print(f"C_TOP5_FLOAT32_WITH_UINT8_CLASS_IDS={bytes_and_gb(top5_f32_with_ids)}")
    print(f"C_TOP5_FLOAT16_SCORE_ONLY_ARITHMETIC={rows} * 5 * 2")
    print(f"C_TOP5_FLOAT16_SCORE_ONLY={bytes_and_gb(top5_f16_scores)}")
    print(f"C_TOP5_FLOAT16_WITH_UINT8_CLASS_IDS={bytes_and_gb(top5_f16_with_ids)}")


def main() -> None:
    print_csv_measurement()
    print_script_writer()
    print_h5_measurement()
    # The final held-out count is the script-equivalent count after common-label filtering.
    with tables.open_file(str(H5_PATH), mode="r") as h5:
        nodes = sorted(list(h5.list_nodes("/flows")), key=lambda node: node._v_name)
        train_labels = set()
        test_labels = set()
        for node in nodes:
            month = month_from_node_name(node._v_name)
            if month in TRAIN_MONTHS:
                train_labels.update(int(value) for value in node.col("APP") if int(value) >= 0)
            elif month in TEST_MONTHS:
                test_labels.update(int(value) for value in node.col("APP") if int(value) >= 0)
        common = train_labels & test_labels
        test_rows = sum(
            sum(1 for value in node.col("APP") if int(value) in common)
            for node in nodes
            if month_from_node_name(node._v_name) in TEST_MONTHS
        )
    print_size_measurements(test_rows)
    print(f"DATASET_DISK_PATH={H5_PATH}")
    print(f"DATASET_DISK_SIZE_BYTES={H5_PATH.stat().st_size}")
    print(f"PROBE_PID={os.getpid()}")


if __name__ == "__main__":
    main()
