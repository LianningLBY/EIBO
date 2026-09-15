#!/usr/bin/env python3
"""Compute R1-W9 cluster-bootstrap confidence intervals."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
PRIMARY_PATH = PROJECT / "artifacts/_project/data/q1_lower_side_full_n.json"
QUIC_PATH = PROJECT / "artifacts/X11/data/x11_full_bracket.json"
PAIR_CI_PATH = PROJECT / "artifacts/_project/data/ci_cross_corpus.json"
OUTPUT_PATH = PROJECT / "artifacts/_project/data/ci_cross_corpus_75134b.json"

SEED = 20260915
REPLICATES = 2000
PERCENTILES = (2.5, 97.5)
THRESHOLDS = (("all", None), (">=13049", 13049), (">=20000", 20000),
              (">=40000", 40000), (">=80000", 80000))


def _service_key(value: object) -> str:
    return str(value)


def _degree_check(rows: list[dict], expected_services: int) -> tuple[list[str], dict]:
    service_labels = sorted(
        {
            _service_key(row["service_a"])
            for row in rows
        }
        | {
            _service_key(row["service_b"])
            for row in rows
        },
        key=lambda value: (len(value), value),
    )
    if len(service_labels) != expected_services:
        raise AssertionError(
            f"expected {expected_services} services, found {len(service_labels)}"
        )

    pair_keys = {
        tuple(sorted((_service_key(row["service_a"]), _service_key(row["service_b"]))))
        for row in rows
    }
    if any(a == b for a, b in pair_keys):
        raise AssertionError("self-pair found")
    if len(pair_keys) != len(rows):
        raise AssertionError("duplicate unordered service pair found")

    expected_pairs = expected_services * (expected_services - 1) // 2
    if len(rows) != expected_pairs:
        raise AssertionError(
            f"expected {expected_pairs} rows for complete graph, found {len(rows)}"
        )

    degrees = {service: 0 for service in service_labels}
    for left, right in pair_keys:
        degrees[left] += 1
        degrees[right] += 1
    degree_distribution: dict[str, int] = {}
    for degree in degrees.values():
        degree_distribution[str(degree)] = degree_distribution.get(str(degree), 0) + 1
    if degree_distribution != {str(expected_services - 1): expected_services}:
        raise AssertionError(f"not a complete graph: {degree_distribution}")
    return service_labels, degree_distribution


def _row_arrays(
    rows: list[dict],
    services: list[str],
    eps_hi_path: str,
) -> tuple[dict[tuple[str, str], int], np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pair_to_index: dict[tuple[str, str], int] = {}
    lower = np.empty(len(rows), dtype=bool)
    upper = np.empty(len(rows), dtype=bool)
    n_min = np.empty(len(rows), dtype=np.int64)
    service_a = np.empty(len(rows), dtype=object)
    service_b = np.empty(len(rows), dtype=object)

    for index, row in enumerate(rows):
        left = _service_key(row["service_a"])
        right = _service_key(row["service_b"])
        key = tuple(sorted((left, right)))
        if key in pair_to_index:
            raise AssertionError(f"duplicate row for pair {key}")
        pair_to_index[key] = index
        service_a[index] = left
        service_b[index] = right
        lower[index] = float(row["eps_lo"]) > 0.05
        if eps_hi_path == "primary":
            eps_hi = row["upper_recomputed"]["eps_hi"]
        else:
            eps_hi = row["eps_hi"]
        upper[index] = float(eps_hi) < 0.5
        n_min[index] = min(int(row["n_a"]), int(row["n_b"]))

    if set(services) != set(service_a) | set(service_b):
        raise AssertionError("service inventory does not match row endpoints")
    return pair_to_index, lower, upper, n_min, service_a, service_b


def _replicate_pair_indices(
    draw: np.ndarray,
    services: list[str],
    pair_to_index: dict[tuple[str, str], int],
) -> np.ndarray:
    unique = np.unique(draw)
    pairs = [
        pair_to_index[
            tuple(sorted((services[unique[left]], services[unique[right]])))
        ]
        for left in range(len(unique))
        for right in range(left + 1, len(unique))
    ]
    return np.asarray(pairs, dtype=np.int64)


def _cluster_replicates(
    services: list[str],
    pair_to_index: dict[tuple[str, str], int],
    lower: np.ndarray,
    upper: np.ndarray,
    n_min: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, dict[int | None, np.ndarray]]:
    lower_values = np.empty(REPLICATES, dtype=float)
    pair_counts = np.empty(REPLICATES, dtype=np.int64)
    upper_values = {
        threshold: np.empty(REPLICATES, dtype=float)
        for _, threshold in THRESHOLDS
    }
    service_indices = np.arange(len(services), dtype=np.int64)

    for replicate in range(REPLICATES):
        draw = rng.choice(service_indices, size=len(services), replace=True)
        indices = _replicate_pair_indices(draw, services, pair_to_index)
        if indices.size == 0:
            raise AssertionError("replicate produced no distinct service pairs")
        pair_counts[replicate] = indices.size
        lower_values[replicate] = lower[indices].mean()
        for _, threshold in THRESHOLDS:
            if threshold is None:
                mask = np.ones(indices.size, dtype=bool)
            else:
                mask = n_min[indices] >= threshold
            if not mask.any():
                raise AssertionError(
                    f"replicate {replicate} has no pairs at threshold {threshold}"
                )
            upper_values[threshold][replicate] = upper[indices][mask].mean()
    return lower_values, pair_counts, upper_values


def _ci(values: np.ndarray) -> tuple[float, float]:
    return tuple(float(value) for value in np.percentile(values, PERCENTILES))


def _ratio(cluster_width: float, pair_width: float) -> float:
    if pair_width <= 0:
        raise AssertionError(f"pair CI width must be positive, got {pair_width}")
    return float(cluster_width / pair_width)


def main() -> None:
    primary = json.loads(PRIMARY_PATH.read_text())
    quic = json.loads(QUIC_PATH.read_text())
    pair_result = json.loads(PAIR_CI_PATH.read_text())
    primary_rows = primary["rows"]
    quic_rows = quic["per_pair_rows"]

    if len(primary_rows) != 990 or len(quic_rows) != 3321:
        raise AssertionError(
            f"unexpected row counts: primary={len(primary_rows)}, quic22={len(quic_rows)}"
        )

    primary_services, primary_degree = _degree_check(primary_rows, 45)
    quic_services, quic_degree = _degree_check(quic_rows, 82)
    (
        primary_pairs,
        primary_lower,
        primary_upper,
        primary_n_min,
        _,
        _,
    ) = _row_arrays(primary_rows, primary_services, "primary")
    quic_pairs, quic_lower, quic_upper, quic_n_min, _, _ = _row_arrays(
        quic_rows, quic_services, "quic22"
    )

    if not np.array_equal(
        primary_lower,
        np.asarray([bool(row["eps_lo_gt_0_05"]) for row in primary_rows]),
    ):
        raise AssertionError("primary eps_lo_gt_0_05 disagrees with eps_lo > 0.05")
    if not np.array_equal(
        quic_lower,
        np.asarray([float(row["eps_lo"]) > 0.05 for row in quic_rows]),
    ):
        raise AssertionError("QUIC22 lower indicator mismatch")

    primary_pair_lower = pair_result["lower_side_ci"]["primary"]
    quic_pair_lower = pair_result["lower_side_ci"]["quic22"]
    pair_gap_by_threshold = {
        item["threshold"]: item for item in pair_result["stratum_matched_gap_ci"]
    }
    if set(pair_gap_by_threshold) != {label for label, _ in THRESHOLDS}:
        raise AssertionError("stored pair result has unexpected threshold labels")

    rng = np.random.default_rng(SEED)
    primary_lower_reps, primary_counts, primary_upper_reps = _cluster_replicates(
        primary_services, primary_pairs, primary_lower, primary_upper, primary_n_min, rng
    )
    quic_lower_reps, quic_counts, quic_upper_reps = _cluster_replicates(
        quic_services, quic_pairs, quic_lower, quic_upper, quic_n_min, rng
    )

    primary_lower_fraction = float(primary_lower.mean())
    quic_lower_fraction = float(quic_lower.mean())
    primary_lower_ci = _ci(primary_lower_reps)
    quic_lower_ci = _ci(quic_lower_reps)

    lower_widths = {}
    for name, pair_data, cluster_ci in (
        ("primary", primary_pair_lower, primary_lower_ci),
        ("quic22", quic_pair_lower, quic_lower_ci),
    ):
        pair_width = float(pair_data["ci_hi"] - pair_data["ci_lo"])
        cluster_width = float(cluster_ci[1] - cluster_ci[0])
        lower_widths[name] = {
            "pair_width": pair_width,
            "cluster_width": cluster_width,
            "ratio": _ratio(cluster_width, pair_width),
        }

    gap_results = []
    gap_cluster_widths = {}
    for label, threshold in THRESHOLDS:
        primary_values = primary_upper_reps[threshold]
        quic_values = quic_upper_reps[threshold]
        gap_reps = quic_values - primary_values
        if threshold is None:
            primary_mask = np.ones(len(primary_rows), dtype=bool)
            quic_mask = np.ones(len(quic_rows), dtype=bool)
        else:
            primary_mask = primary_n_min >= threshold
            quic_mask = quic_n_min >= threshold
        primary_point = float(primary_upper[primary_mask].mean())
        quic_point = float(quic_upper[quic_mask].mean())
        gap = quic_point - primary_point
        cluster_ci = _ci(gap_reps)
        stored = pair_gap_by_threshold[label]
        if not np.isclose(gap, stored["gap"], rtol=0.0, atol=1e-12):
            raise AssertionError(f"{label}: point gap disagrees with pair result")
        gap_results.append(
            {
                "threshold": label,
                "gap": gap,
                "ci_lo": cluster_ci[0],
                "ci_hi": cluster_ci[1],
                "spans_zero": bool(cluster_ci[0] <= 0.0 <= cluster_ci[1]),
            }
        )
        if label == "all":
            pair_width = float(stored["ci_hi"] - stored["ci_lo"])
            cluster_width = float(cluster_ci[1] - cluster_ci[0])
            gap_cluster_widths["gap_all"] = {
                "pair_width": pair_width,
                "cluster_width": cluster_width,
                "ratio": _ratio(cluster_width, pair_width),
            }

    runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result = {
        "method": "nonparametric cluster bootstrap over services, percentile CI",
        "confidence_level": 0.95,
        "alpha": 0.05,
        "percentile_levels": list(PERCENTILES),
        "alpha_split_convention": "two-sided percentile interval: 0.025 lower and 0.025 upper tail",
        "seed": SEED,
        "replicates": REPLICATES,
        "runner_sha256": runner_sha256,
        "degree_check": {
            "primary": {
                "n_services": len(primary_services),
                "n_pairs": len(primary_rows),
                "expected": "C(45,2)",
                "degree_distribution": primary_degree,
            },
            "quic22": {
                "n_services": len(quic_services),
                "n_pairs": len(quic_rows),
                "expected": "C(82,2)",
                "degree_distribution": quic_degree,
            },
        },
        "lower_side_ci_cluster": {
            "primary": {
                "fraction": primary_lower_fraction,
                "ci_lo": primary_lower_ci[0],
                "ci_hi": primary_lower_ci[1],
                "replicate_pair_count_median": float(np.median(primary_counts)),
            },
            "quic22": {
                "fraction": quic_lower_fraction,
                "ci_lo": quic_lower_ci[0],
                "ci_hi": quic_lower_ci[1],
                "replicate_pair_count_median": float(np.median(quic_counts)),
            },
        },
        "stratum_matched_gap_ci_cluster": gap_results,
        "pair_vs_cluster_comparison": {
            "lower_side": lower_widths,
            "gap_all": gap_cluster_widths["gap_all"],
            "note": "source of the pair-bootstrap values for comparison: ci_cross_corpus.json",
        },
        "dependency_note": (
            "Both pair sets are complete graphs on their service sets, so pairs "
            "sharing a service are correlated. The pair bootstrap is anti-conservative; "
            "the cluster bootstrap is the defensible interval."
        ),
    }
    OUTPUT_PATH.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
