#!/usr/bin/env python3
"""Finalize C016 after the sibling eps_lo artifact becomes available."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


ROOT = Path("/root/eibo")
ARTIFACTS = ROOT / "artifacts"
OUT = ARTIFACTS / "q1_independent_recompute.json"
COUNTS = ARTIFACTS / "q1_absolute_counts.json"
EPS = ARTIFACTS / "q1_eps_lo_symbol_map.json"
SCRIPT = "/root/eibo/scripts/q1_independent_finalize_invariant.py"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def q1_eps_hi(row: dict) -> float:
    constant = math.sqrt(2.0 * math.log(2.0 / 0.025))
    n_a = int(row["n_a"])
    n_b = int(row["n_b"])
    radius_a = (math.sqrt(2.0**5) + constant) / math.sqrt(n_a)
    radius_b = (math.sqrt(2.0**5) + constant) / math.sqrt(n_b)
    return float(row["tv_k5_masked"]) + radius_a + radius_b


def main() -> None:
    with OUT.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    with COUNTS.open(encoding="utf-8") as handle:
        count_rows = [row for row in json.load(handle)["pairs"] if int(row["M"]) == 1]
    with EPS.open(encoding="utf-8") as handle:
        eps_payload = json.load(handle)
    eps_rows = eps_payload["rows"]

    count_map = {(str(row["service_a"]), str(row["service_b"])): row for row in count_rows}
    eps_map = {(str(row["service_a"]), str(row["service_b"])): row for row in eps_rows}
    keys = sorted(set(count_map) | set(eps_map))
    unmatched_count_keys = sorted(set(count_map) - set(eps_map))
    unmatched_eps_keys = sorted(set(eps_map) - set(count_map))
    violations = []
    eps_hi_disagreements = []
    for key in keys:
        if key not in count_map or key not in eps_map:
            continue
        row = count_map[key]
        sibling = eps_map[key]
        eps_hi = q1_eps_hi(row)
        sibling_eps_hi = float(sibling["eps_hi"])
        if abs(eps_hi - sibling_eps_hi) > 1.0e-12:
            eps_hi_disagreements.append({
                "service_a": key[0],
                "service_b": key[1],
                "recomputed_eps_hi": eps_hi,
                "sibling_eps_hi": sibling_eps_hi,
                "absolute_difference": abs(eps_hi - sibling_eps_hi),
            })
        eps_lo = float(sibling["eps_lo"])
        if eps_lo > eps_hi:
            violations.append({
                "service_a": key[0],
                "service_b": key[1],
                "eps_lo": eps_lo,
                "eps_hi": eps_hi,
                "gap": eps_lo - eps_hi,
            })

    payload["hard_invariant_c016"] = {
        "evaluated": True,
        "violation_count": len(violations),
        "assertion": "eps_lo <= eps_hi per row",
        "source_artifact": str(EPS),
        "source_artifact_sha256": sha256_file(EPS),
        "missing_column": None,
        "reason": "Sibling artifact exists and carries per-pair eps_lo; joined on (service_a, service_b).",
        "joined_row_count": len(keys) - len(unmatched_count_keys) - len(unmatched_eps_keys),
        "count_table_row_count": len(count_map),
        "sibling_row_count": len(eps_map),
        "unmatched_count_table_keys": unmatched_count_keys,
        "unmatched_sibling_keys": unmatched_eps_keys,
        "eps_hi_disagreement_count_vs_sibling": len(eps_hi_disagreements),
        "eps_hi_disagreements": eps_hi_disagreements[:10],
        "offending_rows": violations[:20],
        "substitution_forbidden": "tv_k5_masked was not substituted for eps_lo",
    }
    payload["source_summary_metadata"]["sibling_eps_lo_path"] = str(EPS)
    payload["source_summary_metadata"]["sibling_eps_lo_sha256"] = sha256_file(EPS)
    payload["provenance"]["post_run_invariant_joiner"] = {
        "file": SCRIPT,
        "output_consumed_by_reported_numbers": True,
        "routines": ["q1_eps_hi", "join_on_service_pair", "eps_lo_le_eps_hi_assertion"],
    }

    from q1_independent_recompute import build_report_text

    payload["report_text"] = build_report_text(payload)
    with OUT.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({
        "path": str(OUT),
        "byte_size": OUT.stat().st_size,
        "sha256": sha256_file(OUT),
        "row_count": payload["row_count"],
        "c016_violation_count": len(violations),
        "c016_joined_row_count": payload["hard_invariant_c016"]["joined_row_count"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
