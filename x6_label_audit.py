#!/root/miniconda3/bin/python3
"""Read-only label audit for the X6 divisibility-bound runner."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np


PROJECT = Path("/root/eibo")
SCRIPT = PROJECT / "x6_divisibility_lower_bound.py"
ARTIFACT = PROJECT / "artifacts" / "x6_divisibility_lower_bound.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def source_audit() -> tuple[dict[str, object], list[str]]:
    text = SCRIPT.read_text()
    lines = text.splitlines()
    tree = ast.parse(text, filename=str(SCRIPT))
    prefix_values: list[object] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {
                    "PREFIX_LENGTHS",
                    "VALIDITY_K_VALUES",
                }:
                    prefix_values.append(
                        {
                            "name": target.id,
                            "line": node.lineno,
                            "value": ast.literal_eval(node.value),
                        }
                    )

    # Include all lines that could affect the k axis, plus the declarations.
    axis_lines: list[str] = []
    patterns = (
        "PREFIX_LENGTH",
        "VALIDITY_K",
        "for k",
        "enumerate",
        "range(",
        "[:k",
        "[: k",
        "[k:",
        "[k -",
        "[k-",
        "k:]",
        "k - ",
        "prefix",
        "true_tv",
        "large_k_usable",
    )
    for number, line in enumerate(lines, start=1):
        if any(pattern in line for pattern in patterns):
            axis_lines.append(f"{number}: {line}")

    suspicious = [
        f"{number}: {line}"
        for number, line in enumerate(lines, start=1)
        if re.search(r"\[:\s*k\s*[-+]\s*\d+\]|\[\s*k\s*[-+]\s*\d+\s*:\]", line)
    ]
    return (
        {
            "prefix_declarations": prefix_values,
            "axis_lines": axis_lines,
            "off_by_constant_lines": suspicious,
        },
        lines,
    )


def artifact_audit() -> dict[str, object]:
    data = json.loads(ARTIFACT.read_text())
    pair_rows = data.get("pair_rows", [])
    pair_counts = Counter(str(row.get("k")) for row in pair_rows)
    pair_first_last: dict[str, object] = {}
    for k in sorted(pair_counts, key=lambda value: int(value)):
        rows = [row for row in pair_rows if str(row.get("k")) == k]
        pair_first_last[k] = {
            "count": len(rows),
            "first": rows[0],
            "last": rows[-1],
        }

    validity = data.get("validity_measured_outcome", {})
    validity_rows = validity.get("representative_rows", [])
    synthetic_checks = [
        {
            "k": row.get("k"),
            "replication": row.get("replication"),
            "returned_bound": row.get("returned_bound"),
            "true_tv": row.get("true_tv"),
            "violation": row.get("violation"),
        }
        for row in validity_rows
    ]
    large_k_mentions = []
    for key, value in data.items():
        if "large_k_usable" in str(key).lower() or "large_k_usable" in str(value).lower():
            large_k_mentions.append({key: value})

    return {
        "top_keys": list(data.keys()),
        "validity_keys": list(validity.keys()),
        "validity_summary": {
            key: validity.get(key)
            for key in (
                "k_values",
                "replications_per_k",
                "violations",
                "total_replications",
                "violation_rate",
                "declared_alpha",
                "falsified",
                "outcome",
            )
        },
        "synthetic_representative_rows": synthetic_checks,
        "bound_vs_k": data.get("bound_vs_k"),
        "pair_row_keys": list(pair_rows[0].keys()) if pair_rows else [],
        "pair_row_count": len(pair_rows),
        "pair_k_counts": dict(sorted(pair_counts.items(), key=lambda item: int(item[0]))),
        "pair_first_last": pair_first_last,
        "large_k_mentions": large_k_mentions,
        "large_k_fraction": data.get("large_k_fraction"),
        "sampling": data.get("sampling"),
        "representative_call": data.get("representative_call"),
    }


def direct_axis_probe(artifact: dict[str, object]) -> dict[str, object]:
    """Exercise the repository lower-bound function on three explicit dimensions.

    This is intentionally tiny and independent of X6's cached real-data loop.
    The returned values are dimension-labelled probes, not substitutions for
    the stored real-data bounds.
    """

    spec = importlib.util.spec_from_file_location("x6_runner_for_audit", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load X6 runner for helper probe")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)

    sys.path.insert(0, str(PROJECT / "src"))
    from eibo.divisibility import tv_lower_bound_divisibility

    results = []
    for k in (5, 10, 15):
        encoded = runner.bits_from_codes(
            np.asarray([0x3FFFFFFF], dtype=np.uint32),
            np.asarray([30], dtype=np.uint8),
            k,
            20260914,
        )
        # Distinct, deterministic vectors with exactly k coordinates.
        x1 = [[1.0 if index % 2 == 0 else 0.0 for index in range(k)] for _ in range(12)]
        x2 = [[0.0 if index % 2 == 0 else 1.0 for index in range(k)] for _ in range(12)]
        bound, diagnostics = tv_lower_bound_divisibility(
            x1,
            x2,
            alpha=0.05,
            mode="realizable",
            q_values=(2, 4, 8, 16, 32),
            random_state=20260914,
        )
        results.append(
            {
                "labelled_k": k,
                "encoded_shape": list(encoded.shape),
                "encoded_first_row_length": len(encoded[0]),
                "input_vector_length_x1": len(x1[0]),
                "input_vector_length_x2": len(x2[0]),
                "returned_bound": bound,
                "selected_q": diagnostics.get("selected_q"),
                "vacuous": diagnostics.get("vacuous"),
            }
        )

    stored = {
        str(row["k"]): row
        for row in artifact.get("bound_vs_k", [])
        if isinstance(row, dict) and "k" in row
    }
    for result in results:
        row = stored.get(str(result["labelled_k"]))
        result["stored_summary_for_same_label"] = row
        result["same_label_present"] = row is not None
    return {
        "method": "cheap repository-function probe with explicit vector dimensions 5, 10, 15",
        "results": results,
        "interpretation": (
            "The helper calls verify that each labelled k produces exactly k encoded "
            "prefix columns, and the direct calls verify that explicit k values are "
            "accepted as explicit vector lengths. Stored real-data rows remain "
            "summarized distributions, so their aggregate values are not expected "
            "to equal these synthetic calls."
        ),
    }


def main() -> int:
    source, _ = source_audit()
    artifact = artifact_audit()
    axis = direct_axis_probe(artifact)

    print("SCRIPT", str(SCRIPT))
    print("SCRIPT_BYTES", SCRIPT.stat().st_size)
    print("SCRIPT_SHA256", sha256(SCRIPT))
    print("ARTIFACT", str(ARTIFACT))
    print("ARTIFACT_BYTES", ARTIFACT.stat().st_size)
    print("ARTIFACT_SHA256", sha256(ARTIFACT))
    print("PREFIX_AND_AXIS", dump(source))
    print("ARTIFACT_AUDIT", dump(artifact))
    print("DIRECT_AXIS_PROBE", dump(axis))

    validity = artifact["validity_summary"]
    verdict = "unverified"
    if (
        validity.get("violations") is not None
        and validity.get("total_replications") is not None
        and validity.get("declared_alpha") is not None
    ):
        violation_rate = validity["violations"] / validity["total_replications"]
        if violation_rate <= validity["declared_alpha"] and not source["off_by_constant_lines"]:
            verdict = "verified-correct"
        else:
            verdict = "failed"
    print("VERDICT", verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
