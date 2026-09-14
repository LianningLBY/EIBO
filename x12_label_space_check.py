#!/usr/bin/env python3
"""Read-only label-space and detector agreement check for X12 outputs."""

import csv
import hashlib
import json
import os
from collections import defaultdict


JSON_PATH = "/root/eibo/artifacts/x12_detector_validation.json"
CSV_PATH = "/root/eibo/artifacts/x12_detector_validation_per_pair.csv"
OUTPUT_PATH = "/root/eibo/artifacts/x12_label_space_check.json"


def parse_value(value):
    value = value.strip()
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def parse_bool(value):
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def value_range(values):
    return {
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "distinct_count": len(set(values)),
    }


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as handle:
        validation = json.load(handle)

    schema = validation.get("schema", {})
    class_key = "service_labels_common_to_both_sides"
    if class_key in schema:
        labels = schema[class_key]
    else:
        candidates = [
            (key, value)
            for key, value in schema.items()
            if any(token in key.lower() for token in ("class", "label", "common"))
            and isinstance(value, list)
        ]
        if not candidates:
            raise KeyError("no class/label/common list found in JSON schema")
        class_key, labels = candidates[0]

    detector_names = ("lightgbm", "prototype", "ronetc")
    stats = {
        name: {
            "equal": 0,
            "different": 0,
            "total": 0,
            "accepted_true": 0,
            "pred_values": [],
        }
        for name in detector_names
    }
    true_values = []

    with open(CSV_PATH, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            true_value = parse_value(row["true_label"])
            true_values.append(true_value)
            for name in detector_names:
                item = stats[name]
                pred_value = parse_value(row[f"{name}_pred"])
                item["pred_values"].append(pred_value)
                item["total"] += 1
                if pred_value == true_value:
                    item["equal"] += 1
                else:
                    item["different"] += 1
                if parse_bool(row[f"{name}_accepted"]):
                    item["accepted_true"] += 1

    detector_json = validation.get("metrics", {}).get("lightgbm", {})
    accepted_rates = []

    def collect_accepted(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                if key == "accepted_rate":
                    accepted_rates.append(nested)
                collect_accepted(nested)
        elif isinstance(value, list):
            for nested in value:
                collect_accepted(nested)

    collect_accepted(detector_json)
    all_rows_accepted = bool(accepted_rates) and all(float(value) == 1.0 for value in accepted_rates)

    result = {
        "classes": {
            "key": class_key,
            "list": labels,
            "length": len(labels),
            "min": min(labels) if labels else None,
            "max": max(labels) if labels else None,
            "max_equals_length_minus_one": bool(labels) and max(labels) == len(labels) - 1,
        },
        "agreement": {
            "rows": len(true_values),
            "true_label_range": value_range(true_values),
            "detectors": {
                name: {
                    "equal": stats[name]["equal"],
                    "different": stats[name]["different"],
                    "total": stats[name]["total"],
                    "pred_range": value_range(stats[name]["pred_values"]),
                    "accepted_true": stats[name]["accepted_true"],
                }
                for name in detector_names
            },
        },
        "accept_flag": {
            "detector": "lightgbm",
            "json_key": "metrics.lightgbm.holdouts.*.per_service.*.accepted_rate",
            "all_rows_accepted": all_rows_accepted,
        },
        "commands": [
            "stat /root/eibo/artifacts/x12_detector_validation.json /root/eibo/artifacts/x12_detector_validation_per_pair.csv",
            "head -n 1 /root/eibo/artifacts/x12_detector_validation_per_pair.csv",
            "cd /root/eibo && /root/miniconda3/bin/python3 /root/eibo/x12_label_space_check.py",
        ],
    }

    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(encoded)

    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"OUTPUT_PATH={OUTPUT_PATH}")
    print(f"OUTPUT_SIZE={os.path.getsize(OUTPUT_PATH)}")
    print(f"OUTPUT_SHA256SUM={digest}")


if __name__ == "__main__":
    main()
