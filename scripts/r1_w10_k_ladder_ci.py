#!/usr/bin/env python3
"""Assemble higher-k count files and compute cluster-bootstrap k ladder CIs."""

from __future__ import annotations

import collections
import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

import numpy as np


PROJECT = Path("/root/eibo")
ARTIFACTS = PROJECT / "artifacts"
OUTPUT = ARTIFACTS / "_project" / "data" / "ci_k_ladder.json"

SEED = 20260915
REPLICATES = 2000
PERCENTILES = (2.5, 97.5)
RUNG_MS = (1, 2, 4, 8, 16)
INCREMENT_PAIRS = ((2, 4), (4, 8), (8, 16))
LIMITATION = (
    "These are uncertainty estimates on the MEDIAN-TV LADDER at higher k. "
    "The hidden rung rows carry `tv_masked` ONLY (no `eps_hi`), so they do "
    "NOT enable a containment join; combined with the empty informative "
    "stratum at k=15/30, this does NOT make a higher-k containment panel "
    "possible. It under-claims deliberately."
)


def read_json(path: Path) -> Any:
    with path.open() as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def service_key(value: Any) -> str:
    return str(value)


def pair_key(row: dict[str, Any]) -> tuple[str, str]:
    left = service_key(row["service_a"])
    right = service_key(row["service_b"])
    if left == right:
        raise AssertionError(f"self-pair found for service {left}")
    return tuple(sorted((left, right)))


def rows_from_canonical(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("pairs"), list):
        return payload["pairs"]
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    if isinstance(payload, list):
        return payload
    raise AssertionError(f"could not locate pair rows in {path}")


def rows_from_hidden(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("fresh_h5_pass"), list):
        return payload["fresh_h5_pass"]
    if isinstance(payload, dict) and payload.get("fresh_h5_pass") is True and isinstance(payload.get("rows"), list):
        return payload["rows"]
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    if isinstance(payload, list):
        return payload
    raise AssertionError(f"could not locate fresh_h5_pass rows in {path}")


def grouped_by_m(rows: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    out: dict[int, list[dict[str, Any]]] = {m: [] for m in RUNG_MS}
    for row in rows:
        m = int(row["M"])
        if m not in out:
            raise AssertionError(f"unexpected M={m}")
        out[m].append(row)
    return out


def degree_check(rows: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = {pair_key(row) for row in rows}
    services = sorted({s for pair in pairs for s in pair}, key=lambda item: (len(item), item))
    degrees = {service: 0 for service in services}
    for left, right in pairs:
        degrees[left] += 1
        degrees[right] += 1
    degree_distribution = collections.Counter(degrees.values())
    expected_complete_pairs = len(services) * (len(services) - 1) // 2
    return {
        "service_count": len(services),
        "pair_count": len(pairs),
        "expected_complete_pair_count": expected_complete_pairs,
        "degree_distribution": {str(k): int(v) for k, v in sorted(degree_distribution.items())},
        "is_complete_graph": len(pairs) == expected_complete_pairs
        and len(degree_distribution) == 1
        and (not services or next(iter(degree_distribution)) == len(services) - 1),
        "services": services,
    }


def validate_k10_first(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = grouped_by_m(rows)
    rows_per_m = {str(m): len(grouped[m]) for m in RUNG_MS}
    if rows_per_m != {str(m): 990 for m in RUNG_MS}:
        raise AssertionError(f"k=10 rows per M mismatch: {rows_per_m}")
    check = degree_check(rows)
    if check["service_count"] != 45 or check["degree_distribution"] != {"44": 45}:
        raise AssertionError(f"k=10 is not the expected complete graph: {check}")
    if not check["is_complete_graph"]:
        raise AssertionError(f"k=10 degree check failed: {check}")
    check["rows_per_M"] = rows_per_m
    return check


def assemble_canonical(k: int, value_key: str, expected_rows: int) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    for m in RUNG_MS:
        source = ARTIFACTS / f".x1_k{k}_m{m}.json"
        rows = rows_from_hidden(source)
        if len(rows) != expected_rows:
            raise AssertionError(f"{source} expected {expected_rows} rows, found {len(rows)}")
        for row in rows:
            if set(row) != {"M", "n_a", "n_b", "service_a", "service_b", "tv_masked"}:
                raise AssertionError(f"unexpected keys in {source}: {sorted(row)}")
            if int(row["M"]) != m:
                raise AssertionError(f"{source} contains row with M={row['M']}")
            merged.append(
                {
                    "M": int(row["M"]),
                    "n_a": int(row["n_a"]),
                    "n_b": int(row["n_b"]),
                    "service_a": row["service_a"],
                    "service_b": row["service_b"],
                    value_key: float(row["tv_masked"]),
                }
            )
        source_files.append({"path": str(source), "rows": len(rows), "sha256": sha256(source)})
    out_path = ARTIFACTS / f"q1_absolute_counts_k{k}.json"
    write_json(out_path, {"pairs": merged})
    return out_path, merged, {"source_files": source_files, "sha256": sha256(out_path)}


def graph_values(rows: list[dict[str, Any]], value_key: str) -> dict[tuple[str, str], float]:
    values: dict[tuple[str, str], float] = {}
    for row in rows:
        key = pair_key(row)
        if key in values:
            raise AssertionError(f"duplicate pair {key}")
        values[key] = float(row[value_key])
    return values


def replicate_indices(
    services: list[str], observed_pairs: set[tuple[str, str]], rng: np.random.Generator
) -> list[tuple[str, str]]:
    draw = rng.choice(np.arange(len(services)), size=len(services), replace=True)
    unique = np.unique(draw)
    out: list[tuple[str, str]] = []
    for i, left_index in enumerate(unique):
        for right_index in unique[i + 1 :]:
            pair = tuple(sorted((services[int(left_index)], services[int(right_index)])))
            if pair in observed_pairs:
                out.append(pair)
    if not out:
        raise AssertionError("replicate produced no observed service pairs")
    return out


def pair_count_summary(pair_counts: list[int]) -> dict[str, Any]:
    values = np.asarray(pair_counts, dtype=np.int64)
    hist = collections.Counter(int(value) for value in values)
    return {
        "min": int(values.min()),
        "q25": float(np.percentile(values, 25)),
        "median": float(np.percentile(values, 50)),
        "q75": float(np.percentile(values, 75)),
        "max": int(values.max()),
        "histogram": {str(k): int(v) for k, v in sorted(hist.items())},
    }


def bootstrap_median(
    services: list[str], values_by_pair: dict[tuple[str, str], float], rng: np.random.Generator
) -> tuple[dict[str, float], dict[str, Any]]:
    observed_pairs = set(values_by_pair)
    reps: list[float] = []
    counts: list[int] = []
    for _ in range(REPLICATES):
        pairs = replicate_indices(services, observed_pairs, rng)
        counts.append(len(pairs))
        reps.append(float(np.median([values_by_pair[pair] for pair in pairs])))
    lo, hi = np.percentile(np.asarray(reps, dtype=float), PERCENTILES)
    point = float(np.median(list(values_by_pair.values())))
    return {"median_tv": point, "ci_lo": float(lo), "ci_hi": float(hi)}, pair_count_summary(counts)


def bootstrap_increment(
    services: list[str], low: dict[tuple[str, str], float], high: dict[tuple[str, str], float], rng: np.random.Generator
) -> tuple[dict[str, Any], dict[str, Any]]:
    common_pairs = set(low) & set(high)
    if not common_pairs:
        raise AssertionError("no common pairs for paired increment")
    reps: list[float] = []
    counts: list[int] = []
    for _ in range(REPLICATES):
        pairs = replicate_indices(services, common_pairs, rng)
        counts.append(len(pairs))
        reps.append(
            float(np.median([high[pair] for pair in pairs]) - np.median([low[pair] for pair in pairs]))
        )
    lo, hi = np.percentile(np.asarray(reps, dtype=float), PERCENTILES)
    point = float(np.median([high[pair] for pair in common_pairs]) - np.median([low[pair] for pair in common_pairs]))
    return {
        "statistic": "median(tv_high)-median(tv_low) on common observed pairs",
        "common_pair_count": len(common_pairs),
        "increment": point,
        "ci_lo": float(lo),
        "ci_hi": float(hi),
    }, pair_count_summary(counts)


def per_k_analysis(k: int, rows: list[dict[str, Any]], value_key: str, rng: np.random.Generator) -> dict[str, Any]:
    grouped = grouped_by_m(rows)
    pair_sets = {m: {pair_key(row) for row in grouped[m]} for m in RUNG_MS}
    union_rows = [row for m in RUNG_MS for row in grouped[m]]
    check = degree_check(union_rows)
    per_m_degree = {str(m): degree_check(grouped[m]) for m in RUNG_MS}
    check["rows_per_M"] = {str(m): len(grouped[m]) for m in RUNG_MS}
    check["same_pair_set_for_all_M"] = all(pair_sets[m] == pair_sets[RUNG_MS[0]] for m in RUNG_MS)
    if check["is_complete_graph"]:
        check["adaptation"] = "complete graph; standard service-set cluster bootstrap"
    else:
        check["adaptation"] = "not a complete graph; bootstrap draws from the actual observed service set and uses observed induced pairs only"

    values_by_m = {m: graph_values(grouped[m], value_key) for m in RUNG_MS}
    services = check["services"]
    per_m_ci: dict[str, Any] = {}
    pair_counts: dict[str, Any] = {}
    for m in RUNG_MS:
        per_m_ci[str(m)], pair_counts[f"M{m}"] = bootstrap_median(services, values_by_m[m], rng)
        per_m_ci[str(m)]["n_pairs"] = len(values_by_m[m])

    increments: dict[str, Any] = {}
    for low_m, high_m in INCREMENT_PAIRS:
        label = f"M{high_m}-M{low_m}"
        increments[label], pair_counts[label] = bootstrap_increment(
            services, values_by_m[low_m], values_by_m[high_m], rng
        )

    return {
        "degree_check": check,
        "per_M_degree_check": {str(m): per_m_degree[str(m)] if False else per_m_degree[str(m)] for m in []},
        "per_M_median_tv_ci": per_m_ci,
        "paired_increments": increments,
        "replicate_pair_counts": pair_counts,
    }


def object_mentions_k10(obj: dict[str, Any]) -> bool:
    for key, value in obj.items():
        key_lower = str(key).lower()
        if key_lower == "k" and str(value) == "10":
            return True
        if isinstance(value, str) and re.search(r"\bk\s*=?\s*10\b|\bk10\b", value.lower()):
            return True
    return False


def collect_k10_medians_from_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = read_json(path)
    candidates: list[dict[str, Any]] = []

    def walk(node: Any, trail: str) -> None:
        if isinstance(node, dict):
            if object_mentions_k10(node):
                for key, value in node.items():
                    key_lower = str(key).lower()
                    if "median" in key_lower and ("tv" in key_lower or "masked" in key_lower):
                        try:
                            numeric = float(value)
                        except (TypeError, ValueError):
                            continue
                        candidates.append(
                            {
                                "source": str(path),
                                "path": trail,
                                "key": str(key),
                                "M": int(node["M"]) if "M" in node and str(node["M"]).isdigit() else None,
                                "printed_value": numeric,
                            }
                        )
            for key, value in node.items():
                walk(value, f"{trail}.{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{trail}[{index}]")

    walk(payload, "$")
    return candidates


def collect_registry_k10_medians(paths: list[Path]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    pattern = re.compile(r"(?is)(.{0,160}(?:\bk\s*[:=]?\s*10\b|\bk10\b).{0,240}median.{0,240})")
    number_pattern = re.compile(r"[-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+(?:[eE][-+]?\d+)")
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        for match in pattern.finditer(text):
            snippet = " ".join(match.group(1).split())
            numbers = [float(item) for item in number_pattern.findall(snippet)]
            plausible = [value for value in numbers if 0 <= value <= 1]
            if plausible:
                candidates.append(
                    {
                        "source": str(path),
                        "path": "text-window",
                        "M": None,
                        "printed_value": plausible[-1],
                        "snippet": snippet[:500],
                    }
                )
    return candidates


def paper_agreement(k10_analysis: dict[str, Any]) -> dict[str, Any]:
    headline_paths = [
        ARTIFACTS / "x1_headline_table.json",
        ARTIFACTS / "_project" / "data" / "x1_headline_table.json",
        PROJECT / "x1_headline_table.json",
    ]
    registry_paths = [
        PROJECT / "registry.yaml",
        ARTIFACTS / "registry.yaml",
        ARTIFACTS / "_project" / "registry.yaml",
    ]
    candidates: list[dict[str, Any]] = []
    for path in headline_paths:
        candidates.extend(collect_k10_medians_from_json(path))
    candidates.extend(collect_registry_k10_medians(registry_paths))

    if not candidates:
        return {
            "k10": "no k=10 median printed in checked x1_headline_table.json or registry files",
            "checked_files": [str(path) for path in headline_paths + registry_paths],
        }

    comparisons: list[dict[str, Any]] = []
    for candidate in candidates:
        m_value = candidate.get("M")
        comparison = dict(candidate)
        if m_value is not None and str(m_value) in k10_analysis["per_M_median_tv_ci"]:
            computed = k10_analysis["per_M_median_tv_ci"][str(m_value)]["median_tv"]
            comparison["computed_median_tv"] = computed
            comparison["abs_diff"] = abs(computed - float(candidate["printed_value"]))
            comparison["matches_at_1e-12"] = comparison["abs_diff"] <= 1e-12
        else:
            comparison["comparison"] = "candidate has no M field, so no rung-specific comparison was made"
        comparisons.append(comparison)
    return {"k10": "k=10 median candidate(s) found", "comparisons": comparisons}


def runner_metadata() -> dict[str, Any]:
    path = Path(__file__).resolve()
    return {"path": str(path), "sha256": sha256(path)}


def main() -> None:
    started = time.monotonic()

    k10_path = ARTIFACTS / "q1_absolute_counts_k10.json"
    k10_rows = rows_from_canonical(k10_path)
    k10_degree = validate_k10_first(k10_rows)

    k15_path, k15_rows, k15_assembly = assemble_canonical(15, "tv_k15_masked", 946)
    k30_path, k30_rows, k30_assembly = assemble_canonical(30, "tv_k30_masked", 820)

    rng = np.random.default_rng(SEED)
    per_k = {
        "10": per_k_analysis(10, k10_rows, "tv_k10_masked", rng),
        "15": per_k_analysis(15, k15_rows, "tv_k15_masked", rng),
        "30": per_k_analysis(30, k30_rows, "tv_k30_masked", rng),
    }
    per_k["10"]["degree_check"].update(k10_degree)

    result = {
        "method": "cluster bootstrap over services with percentile 95% confidence intervals",
        "construction": (
            "Each replicate draws N services with replacement, deduplicates to a set, "
            "and recomputes the statistic on distinct unordered observed pairs induced "
            "by that set; complete graphs use all induced non-self pairs."
        ),
        "seed": SEED,
        "replicates": REPLICATES,
        "percentiles": list(PERCENTILES),
        "per_k": per_k,
        "paper_agreement": None,
        "new_numbers": {
            "15": "no printed values -- these medians are NEW",
            "30": "no printed values -- these medians are NEW",
        },
        "assembled_canonical_files": {
            "15": {"path": str(k15_path), **k15_assembly},
            "30": {"path": str(k30_path), **k30_assembly},
        },
        "source_artifacts": {
            "10": {"path": str(k10_path), "sha256": sha256(k10_path)},
        },
        "limitation": LIMITATION,
        "runner": runner_metadata(),
        "cost_used": {"wall_clock_seconds": None},
    }
    result["paper_agreement"] = paper_agreement(per_k["10"])
    result["cost_used"]["wall_clock_seconds"] = float(time.monotonic() - started)
    write_json(OUTPUT, result)

    summary = {
        "output": str(OUTPUT),
        "output_sha256": sha256(OUTPUT),
        "canonical_files": {
            "k15": {"path": str(k15_path), "exists": k15_path.exists(), "sha256": sha256(k15_path)},
            "k30": {"path": str(k30_path), "exists": k30_path.exists(), "sha256": sha256(k30_path)},
        },
        "degree_checks": {k: per_k[k]["degree_check"] for k in ("10", "15", "30")},
        "paper_agreement": result["paper_agreement"],
        "wall_clock_seconds": result["cost_used"]["wall_clock_seconds"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
