#!/usr/bin/env python3
"""Read-only probe for the three X3 synthetic-arm constructors and artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path("/root/eibo")
SCRIPT_PATHS = [
    ROOT / "x3_controls.py",
    ROOT / "x3_variant_b_support_conditioning.py",
    ROOT / "x3_control_occupancy_dose_response.py",
]
ARTIFACT_PATHS = [
    ROOT / "artifacts/x3_control_known_truth.json",
    ROOT / "artifacts/x3_variant_b_support_conditioning.json",
    ROOT / "artifacts/x3_control_occupancy_dose_response.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def show_lines(path: Path, start: int, end: int) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    print(f"CODE {path} lines {start}-{end}")
    for number in range(start, min(end, len(lines)) + 1):
        print(f"{number}: {lines[number - 1]}")


def walk(obj, path=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            current = path + (str(key),)
            yield current, value
            yield from walk(value, current)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            current = path + (str(index),)
            yield current, value
            yield from walk(value, current)


def print_exponent_nodes(path: Path) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"ARTIFACT {path}")
    print(f"ROOT_KEYS {json.dumps(list(data.keys()))}")
    exponent_count = 0
    setting_matches = []
    for key_path, value in walk(data):
        key = key_path[-1].lower()
        if "exponent" in key:
            exponent_count += 1
            print(f"EXPONENT_PATH {'/'.join(key_path)} VALUE {repr(value)}")
        if any(token in key for token in ("baseline", "unfiltered", "no_filter")):
            setting_matches.append(("/".join(key_path), value))
    print(f"EXPONENT_COUNT {exponent_count}")
    print(f"BASELINE_FIELD_MATCHES {json.dumps(setting_matches, sort_keys=True)}")

    # Print the complete small parent object for every exponent field.
    def parent_at(root, parts):
        node = root
        for part in parts[:-1]:
            node = node[int(part)] if isinstance(node, list) else node[part]
        return node

    for key_path, value in walk(data):
        if "exponent" in key_path[-1].lower():
            print(
                "EXPONENT_PARENT "
                + "/".join(key_path[:-1])
                + " "
                + json.dumps(parent_at(data, key_path), sort_keys=True, default=str)
            )


def main() -> None:
    print("PROBE_READ_ONLY True")
    print("ROOT", ROOT)
    for path in SCRIPT_PATHS + ARTIFACT_PATHS:
        print("FILE", path, "BYTES", path.stat().st_size, "SHA256", sha256(path))

    show_lines(SCRIPT_PATHS[0], 489, 590)
    show_lines(SCRIPT_PATHS[0], 601, 650)
    show_lines(SCRIPT_PATHS[1], 1, 75)
    show_lines(SCRIPT_PATHS[1], 139, 224)
    show_lines(SCRIPT_PATHS[1], 249, 269)
    show_lines(SCRIPT_PATHS[1], 360, 455)
    show_lines(SCRIPT_PATHS[2], 15, 36)
    show_lines(SCRIPT_PATHS[2], 89, 115)
    show_lines(SCRIPT_PATHS[2], 173, 208)
    show_lines(SCRIPT_PATHS[2], 290, 307)
    show_lines(SCRIPT_PATHS[2], 325, 357)

    for path in ARTIFACT_PATHS:
        print_exponent_nodes(path)


if __name__ == "__main__":
    main()
