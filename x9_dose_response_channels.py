#!/usr/bin/env python3
"""CPU-only X9 dose-response runner.

This copies the prior X9 channel comparison and adds a declared bucket ladder,
matched random-identifier controls, and a direct QUIC_SNI/DST_IP premise test.
Every concentration alphabet is fixed before data access: m=32*B for the
hash-bucket arms, m=32 for ARM A, and m=32*256**10 for the original extreme.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import itertools
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import tables


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


PROJECT_ROOT = Path("/root/eibo")
H5_PATH = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5")
ARTIFACT_PATH = PROJECT_ROOT / "artifacts" / "x9_dose_response_channels.json"
RUNNER_PATH = Path(__file__).resolve()
RUNNER_SHA256 = sha256_file(RUNNER_PATH)
HELPER_PATH = PROJECT_ROOT / "scripts" / "xs_compression_early_readout.py"
STATCORE_PATH = PROJECT_ROOT / "src" / "eibo" / "statcore.py"

K = 5
M = 1
SERVICE_THRESHOLD = 2000
ALPHA_PER_LAW = 0.025
CHUNK_SIZE = 100_000
HOST_FIELD = "DST_IP"
SNI_FIELD = "QUIC_SNI"
TRAIN_MONTHS = ("202406", "202407", "202408", "202409", "202410", "202411")
BUFFER_MONTH = "202412"
TEST_MONTHS = ("202501", "202502", "202503", "202504", "202505")
ALL_SPLIT_MONTHS = TRAIN_MONTHS + (BUFFER_MONTH,) + TEST_MONTHS

# This seed is part of the artifact contract. blake2b is used as a deterministic
# PRF so each flow gets one reproducible ten-byte identifier without depending on
# scan order or on an observed support estimate.
RANDOM_IDENTIFIER_SEED = 20260914
RANDOM_IDENTIFIER_DOMAIN = "x9-dose-response-per-flow-S10-v1"

# The ladder is declared before any corpus read. B is the public digest bucket
# count; m=32*B is therefore a protocol-level reachable-set cardinality.
BUCKET_LADDER = (2, 4, 16, 256, 65536, 256**10)
PREFIX_ALPHABET_SIZE = 2**K
EXTREME_ALPHABET_SIZE = PREFIX_ALPHABET_SIZE * (256**10)

PREDICTION = {
    "statement": (
        "At a sane declared m, the SNI-inclusive arm will probably stop clipping; "
        "the 'including the identifier destroys certification' reading should dissolve, "
        "leaving the true statement 'including the host identifier raises measured TV by about +0.39'."
    ),
    "sane_bucket_max": 65536,
    "near_plus_0_39_tolerance": 0.10,
}


def load_modules() -> tuple[Any, Any]:
    helper_spec = importlib.util.spec_from_file_location("x9_existing_helper", HELPER_PATH)
    if helper_spec is None or helper_spec.loader is None:
        raise RuntimeError(f"cannot load packing helper from {HELPER_PATH}")
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    if not hasattr(helper, "pack_rung_prefix"):
        raise RuntimeError("existing helper does not export pack_rung_prefix")
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from eibo.statcore import tv_upper_bound

    return helper, tv_upper_bound


def month_from_node(node: tables.Table) -> str:
    name = str(node._v_name)
    if not name.startswith("D") or len(name) < 7:
        raise RuntimeError(f"unexpected flow table name: {name}")
    return name[1:7]


def selected_nodes(h5: tables.File, months: Iterable[str]) -> list[tables.Table]:
    month_set = set(months)
    return sorted(
        [node for node in h5.list_nodes("/flows") if month_from_node(node) in month_set],
        key=lambda node: str(node._v_name),
    )


def assert_split_structure(h5: tables.File) -> dict[str, Any]:
    available = {month_from_node(node) for node in h5.list_nodes("/flows")}
    missing = sorted(set(ALL_SPLIT_MONTHS) - available)
    if missing:
        raise RuntimeError(f"required split months missing from H5: {missing}")
    bounds: dict[str, Any] = {}
    for label, months in (("train", TRAIN_MONTHS), ("test", TEST_MONTHS)):
        minimum = None
        maximum = None
        for node in selected_nodes(h5, months):
            values = np.asarray(node.read(field="TIME_FIRST"))
            if values.size:
                node_min = values.min().item()
                node_max = values.max().item()
                minimum = node_min if minimum is None or node_min < minimum else minimum
                maximum = node_max if maximum is None or node_max > maximum else maximum
        if minimum is None or maximum is None:
            raise RuntimeError(f"no TIME_FIRST values found for {label} split")
        bounds[f"{label}_min"] = int(minimum) if isinstance(minimum, (int, np.integer)) else str(minimum)
        bounds[f"{label}_max"] = int(maximum) if isinstance(maximum, (int, np.integer)) else str(maximum)
    if not (bounds["train_max"] < bounds["test_min"]):
        raise RuntimeError(f"strict time-disjoint guard failed: {bounds}")
    bounds["flow_disjoint"] = True
    bounds["time_disjoint"] = True
    return bounds


def count_eligible_services(h5: tables.File, months: Iterable[str]) -> collections.Counter[int]:
    counts: collections.Counter[int] = collections.Counter()
    for node in selected_nodes(h5, months):
        for start in range(0, int(node.nrows), CHUNK_SIZE):
            stop = min(start + CHUNK_SIZE, int(node.nrows))
            apps = np.asarray(node.read(start, stop, field="APP"), dtype=np.int64)
            lens = np.asarray(node.read(start, stop, field="PPI_LEN"), dtype=np.int64)
            counts.update(map(int, apps[lens >= K]))
    return counts


def identifier_bucket(value: bytes, buckets: int) -> int:
    digest = hashlib.blake2b(value, digest_size=16, person=b"EIBO-X9-BKT-v1").digest()
    return int.from_bytes(digest, "big") % buckets


def random_identifier(node_name: str, row_index: int) -> bytes:
    payload = f"{RANDOM_IDENTIFIER_DOMAIN}|{RANDOM_IDENTIFIER_SEED}|{node_name}|{row_index}".encode()
    return hashlib.blake2b(payload, digest_size=10, person=b"EIBO-X9-RID-v1").digest()


def premise_test(h5: tables.File) -> dict[str, Any]:
    """Audit the two H5 columns and count both mapping directions."""
    dst_to_sni: dict[bytes, bytes] = {}
    dst_conflicts: set[bytes] = set()
    sni_to_dst: dict[bytes, bytes] = {}
    sni_conflicts: set[bytes] = set()
    rows = 0
    for node in selected_nodes(h5, ALL_SPLIT_MONTHS):
        for start in range(0, int(node.nrows), CHUNK_SIZE):
            stop = min(start + CHUNK_SIZE, int(node.nrows))
            dst = node.read(start, stop, field=HOST_FIELD)
            sni = node.read(start, stop, field=SNI_FIELD)
            for dst_value, sni_value in zip(dst, sni):
                d = bytes(dst_value)
                s = bytes(sni_value)
                prior_s = dst_to_sni.setdefault(d, s)
                if prior_s != s:
                    dst_conflicts.add(d)
                prior_d = sni_to_dst.setdefault(s, d)
                if prior_d != d:
                    sni_conflicts.add(s)
            rows += stop - start
    return {
        "readable_as_columns": True,
        "identifier_location": "H5 /flows table column",
        "rows_checked": rows,
        "distinct_QUIC_SNI": len(sni_to_dst),
        "distinct_DST_IP": len(dst_to_sni),
        "DST_IP_values_mapping_to_more_than_one_QUIC_SNI": len(dst_conflicts),
        "QUIC_SNI_values_mapping_to_more_than_one_DST_IP": len(sni_conflicts),
        "derivation_holds": len(dst_conflicts) == 0,
        "derivation_direction": "DST_IP is a function of QUIC_SNI" if not dst_conflicts else "DST_IP is not a function of QUIC_SNI",
    }


def build_arm_counters(
    h5: tables.File,
    months: Iterable[str],
    services: list[int],
    helper: Any,
    bucket_count: int | None = None,
    include_original: bool = False,
) -> dict[str, dict[int, collections.Counter[Any]]]:
    """Build A plus one matched B/C point, or A plus the original extreme."""
    names = ["A"]
    if include_original:
        names.append("B_original_256^10")
    else:
        names.extend([f"B_{bucket_count}", f"C_{bucket_count}"])
    counters = {name: {service: collections.Counter() for service in services} for name in names}
    service_set = set(services)
    service_array = np.asarray(services, dtype=np.int64)
    for node in selected_nodes(h5, months):
        for start in range(0, int(node.nrows), CHUNK_SIZE):
            stop = min(start + CHUNK_SIZE, int(node.nrows))
            apps = np.asarray(node.read(start, stop, field="APP"), dtype=np.int64)
            lens = np.asarray(node.read(start, stop, field="PPI_LEN"), dtype=np.int64)
            use = np.isin(apps, service_array) & (lens >= K)
            if not np.any(use):
                continue
            ppi = np.asarray(node.read(start, stop, field="PPI"))[use]
            hosts = np.asarray(node.read(start, stop, field=HOST_FIELD))[use]
            apps_use = apps[use]
            row_indices = np.arange(start, stop, dtype=np.int64)[use]
            codes = np.asarray(helper.pack_rung_prefix(ppi, K, M, 1, 2), dtype=np.uint64)
            for service in np.unique(apps_use):
                service_i = int(service)
                if service_i not in service_set:
                    continue
                local = apps_use == service_i
                a_counter = counters["A"][service_i]
                a_counter.update(int(value) for value in codes[local])
                if include_original:
                    counters["B_original_256^10"][service_i].update(
                        (int(code), bytes(host)) for code, host in zip(codes[local], hosts[local])
                    )
                else:
                    b_counter = counters[f"B_{bucket_count}"][service_i]
                    c_counter = counters[f"C_{bucket_count}"][service_i]
                    for code, host, row_index in zip(codes[local], hosts[local], row_indices[local]):
                        b_bucket = identifier_bucket(bytes(host), int(bucket_count))
                        rid = random_identifier(str(node._v_name), int(row_index))
                        c_bucket = identifier_bucket(rid, int(bucket_count))
                        b_counter[(int(code), b_bucket)] += 1
                        c_counter[(int(code), c_bucket)] += 1
    return counters


def pair_result(counter_a: collections.Counter[Any], counter_b: collections.Counter[Any], m: int, tv_upper_bound: Any) -> dict[str, Any]:
    sample_a = list(counter_a.elements())
    sample_b = list(counter_b.elements())
    result = tv_upper_bound(sample_a, sample_b, alphabet_size=m, alpha=ALPHA_PER_LAW)
    support = len(set(sample_a) | set(sample_b))
    return {
        "n_a": int(result.n1),
        "n_b": int(result.n2),
        "tv_hat": float(result.tv_hat),
        "eps_hi": float(result.eps_hi),
        "radius_1": float(result.radius_1),
        "radius_2": float(result.radius_2),
        "radius_term_a": float(0.5 * math.sqrt(float(m) / result.n1)),
        "radius_term_b": float(0.5 * math.sqrt(float(m) / result.n2)),
        "realized_support_union_information_only": int(support),
        "declared_m_is_not_realized_support": True,
    }


def summarize(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "median": None}
    array = np.asarray(values, dtype=np.float64)
    return {"count": int(array.size), "mean": float(np.mean(array)), "median": float(np.median(array))}


def arm_summary(pair_rows: list[dict[str, Any]], arm: str, declared_m: int) -> dict[str, Any]:
    rows = [row[arm] for row in pair_rows]
    eps = [float(row["eps_hi"]) for row in rows]
    n_a = [float(row["n_a"]) for row in rows]
    n_b = [float(row["n_b"]) for row in rows]
    rad_a = [float(row["radius_term_a"]) for row in rows]
    rad_b = [float(row["radius_term_b"]) for row in rows]
    support = [float(row["realized_support_union_information_only"]) for row in rows]
    return {
        "declared_m": int(declared_m),
        "declared_m_is_a_priori_function_of_B_alone": True,
        "realized_support": {
            "label": "information only; not the bound's m",
            "max_pair_union": int(max(support)) if support else 0,
            "mean_pair_union": float(np.mean(support)) if support else None,
        },
        "n": {"law_1": summarize(n_a), "law_2": summarize(n_b)},
        "radius_term_0_5_sqrt_m_over_n": {"law_1": summarize(rad_a), "law_2": summarize(rad_b)},
        "clipped_fraction": float(np.mean(np.asarray(eps) == 1.0)) if eps else None,
        "clipped_count": int(sum(value == 1.0 for value in eps)),
        "observation_count": len(eps),
        "saturated": bool(eps) and all(value == 1.0 for value in eps),
        "mean_median_tv_hat": summarize([float(row["tv_hat"]) for row in rows]),
        "mean_median_eps_hi": summarize(eps),
    }


def run_point(
    h5: tables.File,
    split_name: str,
    months: tuple[str, ...],
    services: list[int],
    helper: Any,
    tv_upper_bound: Any,
    bucket_count: int | None = None,
    include_original: bool = False,
) -> dict[str, Any]:
    counters = build_arm_counters(h5, months, services, helper, bucket_count, include_original)
    specs = {"A": PREFIX_ALPHABET_SIZE}
    if include_original:
        specs["B_original_256^10"] = EXTREME_ALPHABET_SIZE
    else:
        specs[f"B_{bucket_count}"] = PREFIX_ALPHABET_SIZE * int(bucket_count)
        specs[f"C_{bucket_count}"] = PREFIX_ALPHABET_SIZE * int(bucket_count)
    arm_names = list(specs)
    rows = []
    for service_a, service_b in itertools.combinations(services, 2):
        row = {"service_a": service_a, "service_b": service_b}
        for arm in arm_names:
            row[arm] = pair_result(counters[arm][service_a], counters[arm][service_b], specs[arm], tv_upper_bound)
        rows.append(row)
    return {
        "split": split_name,
        "months_used": list(months),
        "pair_count": len(rows),
        "arms": {arm: arm_summary(rows, arm, specs[arm]) for arm in arm_names},
        "pairs": rows,
    }


def delta_summary(values: list[float], excluded_reason: str | None = None) -> dict[str, Any]:
    if excluded_reason is not None:
        return {"status": "excluded", "reason": excluded_reason, "count": 0, "mean": None, "median": None}
    if not values:
        return {"status": "no_rows", "count": 0, "mean": None, "median": None}
    return {"status": "informative", **summarize(values)}


def reference_radius_result(
    n_a: int,
    n_b: int,
    alphabet_size: int,
    tv_upper_bound: Any,
) -> Any:
    """Obtain repository radii for observed sample sizes without data samples."""
    return tv_upper_bound(
        itertools.repeat(0, int(n_a)),
        itertools.repeat(0, int(n_b)),
        alphabet_size=alphabet_size,
        alpha=ALPHA_PER_LAW,
    )


def largest_informative_bucket(
    n_a: int,
    n_b: int,
    tv_upper_bound: Any,
) -> int | None:
    """Find the largest integer B whose repository radius sum remains below one."""
    def is_informative(bucket_count: int) -> bool:
        reference = reference_radius_result(
            n_a,
            n_b,
            PREFIX_ALPHABET_SIZE * int(bucket_count),
            tv_upper_bound,
        )
        return float(reference.radius_1) + float(reference.radius_2) < 1.0

    upper = int(BUCKET_LADDER[-1])
    if not is_informative(1):
        return None
    if is_informative(upper):
        return upper
    lo, hi = 1, upper
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if is_informative(mid):
            lo = mid
        else:
            hi = mid - 1
    return lo


def build_arithmetic_labels(
    split_results: dict[str, dict[str, Any]],
    services: list[int],
    tv_upper_bound: Any,
) -> dict[str, Any]:
    reference_pair = {"service_a": int(services[0]), "service_b": int(services[1])}
    thresholds: dict[str, Any] = {}
    per_ladder_point: dict[str, Any] = {}
    forced_clip_rungs: dict[str, list[int]] = {}
    for split_name in ("train", "test"):
        reference_rows = split_results[split_name][f"B_{BUCKET_LADDER[0]}"]["pairs"]
        reference_row = next(
            row
            for row in reference_rows
            if row["service_a"] == reference_pair["service_a"]
            and row["service_b"] == reference_pair["service_b"]
        )
        n_a = int(reference_row[f"B_{BUCKET_LADDER[0]}"]["n_a"])
        n_b = int(reference_row[f"B_{BUCKET_LADDER[0]}"]["n_b"])
        threshold_b = largest_informative_bucket(n_a, n_b, tv_upper_bound)
        thresholds[split_name] = {
            "reference_pair": reference_pair,
            "observed_n": {"law_1": n_a, "law_2": n_b},
            "largest_B_with_radius_sum_below_1": threshold_b,
            "corresponding_m": None if threshold_b is None else PREFIX_ALPHABET_SIZE * threshold_b,
        }
        per_ladder_point[split_name] = {}
        forced_clip_rungs[split_name] = []
        for bucket_count in BUCKET_LADDER:
            point_name = f"B_{bucket_count}"
            rows = split_results[split_name][point_name]["pairs"]
            pair_labels = []
            for row in rows:
                arm = row[point_name]
                radius_sum = float(arm["radius_1"]) + float(arm["radius_2"])
                pair_labels.append(
                    {
                        "service_a": int(row["service_a"]),
                        "service_b": int(row["service_b"]),
                        "n": {"law_1": int(arm["n_a"]), "law_2": int(arm["n_b"])},
                        "radius_1": float(arm["radius_1"]),
                        "radius_2": float(arm["radius_2"]),
                        "radius_sum": radius_sum,
                        "arithmetically_forced_to_clip": radius_sum >= 1.0,
                    }
                )
            forced = bool(pair_labels) and all(item["arithmetically_forced_to_clip"] for item in pair_labels)
            per_ladder_point[split_name][point_name] = {
                "m": PREFIX_ALPHABET_SIZE * int(bucket_count),
                "observed_clipped_fraction": split_results[split_name][point_name]["arms"][point_name]["clipped_fraction"],
                "arithmetically_forced_to_clip": forced,
                "per_pair": pair_labels,
            }
            if forced:
                forced_clip_rungs[split_name].append(int(bucket_count))
    return {
        "per_ladder_point": per_ladder_point,
        "forced_clip_rungs": forced_clip_rungs,
        "informative_threshold": thresholds,
        "threshold_method": "integer bisection over B using eibo.statcore.tv_upper_bound result.radius_1 and result.radius_2; strict radius_sum < 1.0",
        "calibration_record": calibrate_previous_arm_a_test(tv_upper_bound),
        "pre_registered_sane_bucket_max": PREDICTION["sane_bucket_max"],
    }


def build_comparison_availability(
    split_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    points: dict[str, Any] = {}
    for bucket_count in BUCKET_LADDER:
        point_name = f"B_{bucket_count}"
        by_split: dict[str, Any] = {}
        for split_name in ("train", "test"):
            rows = split_results[split_name][point_name]["pairs"]
            pair_labels = []
            tv_values = []
            eps_values = []
            for row in rows:
                left = row[f"B_{bucket_count}"]
                right = row[f"C_{bucket_count}"]
                both_nonclipped = float(left["eps_hi"]) != 1.0 and float(right["eps_hi"]) != 1.0
                pair_labels.append(
                    {
                        "service_a": int(row["service_a"]),
                        "service_b": int(row["service_b"]),
                        "both_arms_nonclipped": both_nonclipped,
                    }
                )
                tv_values.append(float(left["tv_hat"]) - float(right["tv_hat"]))
                if both_nonclipped:
                    eps_values.append(float(left["eps_hi"]) - float(right["eps_hi"]))
            both_arms_nonclipped = bool(rows) and all(item["both_arms_nonclipped"] for item in pair_labels)
            tv_summary = summarize(tv_values)
            tv_summary["status"] = "informative_radius_free_measurement" if tv_values else "no_rows"
            by_split[split_name] = {
                "both_arms_nonclipped": both_arms_nonclipped,
                "per_pair": pair_labels,
                "delta_eps_hi": delta_summary(eps_values) if both_arms_nonclipped else "comparison_unavailable",
                "delta_tv_hat": tv_summary,
            }
        points[point_name] = {"by_split": by_split}
    return {
        "delta_tv_hat_validity": "delta_tv_hat is radius-free and valid at every rung, including clipped rungs",
        "delta_eps_hi_validity": "delta_eps_hi is quoted only when both_arms_nonclipped is true; otherwise it is comparison_unavailable",
        "points": points,
    }


def resolve_existing_path(candidates: Iterable[Path]) -> Path:
    candidate_list = list(candidates)
    for candidate in candidate_list:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"calibration input not found; tried: {[str(path) for path in candidate_list]}"
    )


def calibrate_previous_arm_a_test(tv_upper_bound: Any) -> dict[str, Any]:
    candidates = [
        PROJECT_ROOT / "artifacts" / "x9_sni_channel_delta.json",
        PROJECT_ROOT / "artifacts" / "X9" / "data" / "x9_sni_channel_delta.json",
    ]
    calibration_path = resolve_existing_path(candidates)
    with calibration_path.open(encoding="utf-8") as handle:
        previous = json.load(handle)
    calibration_pair = next(
        pair
        for pair in previous["per_pair"]
        if pair["service_a"] == 0 and pair["service_b"] == 1
    )
    recorded = calibration_pair["by_split"]["test"]["arm_a_sni_excluded"]
    reference = reference_radius_result(
        int(recorded["n_a"]),
        int(recorded["n_b"]),
        PREFIX_ALPHABET_SIZE,
        tv_upper_bound,
    )
    predicted_eps_hi = min(
        1.0,
        float(recorded["tv_hat"]) + float(reference.radius_1) + float(reference.radius_2),
    )
    absolute_difference = abs(predicted_eps_hi - float(recorded["eps_hi"]))
    if absolute_difference > 1e-6:
        raise RuntimeError(f"calibration absolute difference exceeds 1e-6: {absolute_difference}")
    return {
        "source": str(calibration_path),
        "candidates_tried": [str(path) for path in candidates],
        "service_pair": {"service_a": 0, "service_b": 1},
        "split": "test",
        "predicted_arm_a_eps_hi": predicted_eps_hi,
        "recorded_arm_a_eps_hi": float(recorded["eps_hi"]),
        "absolute_difference": absolute_difference,
    }


def build_deltas(split_results: dict[str, dict[str, Any]], services: list[int]) -> dict[str, Any]:
    """Compare matched arms while excluding every saturated eps delta."""
    points: dict[str, Any] = {}
    point_names = ["B_2", "B_4", "B_16", "B_256", "B_65536", "B_1208925819614629174706176", "B_original_256^10"]
    for point in point_names:
        if point == "B_original_256^10":
            matched = [("B_original_256^10", "A", "B_original_256^10_vs_A")]
        else:
            b = point.split("_", 1)[1]
            matched = [(f"B_{b}", "A", f"B_{b}_vs_A"), (f"C_{b}", "A", f"C_{b}_vs_A"), (f"B_{b}", f"C_{b}", f"B_{b}_vs_C_{b}")]
        for left, right, label in matched:
            tv_values = []
            eps_values = []
            excluded = 0
            for split_name in ("train", "test"):
                rows = split_results[split_name][point]["pairs"]
                for row in rows:
                    tv_values.append(float(row[left]["tv_hat"]) - float(row[right]["tv_hat"]))
                    if float(row[left]["eps_hi"]) == 1.0 or float(row[right]["eps_hi"]) == 1.0:
                        excluded += 1
                    else:
                        eps_values.append(float(row[left]["eps_hi"]) - float(row[right]["eps_hi"]))
            reason = None
            if excluded:
                reason = f"{excluded} pair-split rows had at least one saturated arm; delta_eps_hi is arithmetic residue and is not quotable"
            tv_summary = summarize(tv_values)
            tv_summary["status"] = "informative_radius_free_measurement" if tv_values else "no_rows"
            points[label] = {
                "delta_tv_hat": tv_summary,
                "delta_eps_hi": delta_summary(eps_values, reason),
            }
    return points


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def smoke() -> int:
    helper, tv_upper_bound = load_modules()
    print(f"SMOKE tv_upper_bound_imported={tv_upper_bound.__module__}.{tv_upper_bound.__name__}")
    print(f"SMOKE declared_m_values=A:{PREFIX_ALPHABET_SIZE} ladder:" + ",".join(str(PREFIX_ALPHABET_SIZE * b) for b in BUCKET_LADDER) + f" original:{EXTREME_ALPHABET_SIZE}")
    with tables.open_file(str(H5_PATH), mode="r") as h5:
        train_counts = count_eligible_services(h5, TRAIN_MONTHS)
        test_counts = count_eligible_services(h5, TEST_MONTHS)
        services = sorted(s for s in set(train_counts) & set(test_counts) if train_counts[s] >= SERVICE_THRESHOLD and test_counts[s] >= SERVICE_THRESHOLD)
        if len(services) < 2:
            raise RuntimeError(f"threshold left fewer than two common services: {len(services)}")
        one = services[:2]
        for bucket_count in (BUCKET_LADDER[0], BUCKET_LADDER[-1]):
            result = run_point(h5, "test", TEST_MONTHS, one, helper, tv_upper_bound, bucket_count=bucket_count)
            print(f"SMOKE point=B_{bucket_count} pair_computed={result['pair_count']} declared_m_B={PREFIX_ALPHABET_SIZE * bucket_count} declared_m_C={PREFIX_ALPHABET_SIZE * bucket_count} declared_m_A={PREFIX_ALPHABET_SIZE} a_priori=True")
        original = run_point(h5, "test", TEST_MONTHS, one, helper, tv_upper_bound, include_original=True)
        print(f"SMOKE point=B_original_256^10 pair_computed={original['pair_count']} declared_m={EXTREME_ALPHABET_SIZE} a_priori=True")
    print("SMOKE cpu_only=True CUDA_touched=False")
    print("SMOKE OK")
    return 0


def run() -> int:
    started = time.time()
    helper, tv_upper_bound = load_modules()
    if not H5_PATH.exists():
        raise RuntimeError(f"corpus does not exist: {H5_PATH}")
    with tables.open_file(str(H5_PATH), mode="r") as h5:
        split_bounds = assert_split_structure(h5)
        premise = premise_test(h5)
        train_counts = count_eligible_services(h5, TRAIN_MONTHS)
        test_counts = count_eligible_services(h5, TEST_MONTHS)
        services = sorted(s for s in set(train_counts) & set(test_counts) if train_counts[s] >= SERVICE_THRESHOLD and test_counts[s] >= SERVICE_THRESHOLD)
        if len(services) < 2:
            raise RuntimeError(f"threshold left fewer than two common services: {len(services)}")
        print(json.dumps({"stage": "threshold", "common_service_count": len(services), "service_threshold": SERVICE_THRESHOLD, "cpu_only": True}, sort_keys=True), flush=True)
        split_results: dict[str, dict[str, Any]] = {"train": {}, "test": {}}
        for split_name, months in (("train", TRAIN_MONTHS), ("test", TEST_MONTHS)):
            original = run_point(h5, split_name, months, services, helper, tv_upper_bound, include_original=True)
            split_results[split_name]["B_original_256^10"] = original
            for bucket_count in BUCKET_LADDER:
                point = run_point(h5, split_name, months, services, helper, tv_upper_bound, bucket_count=bucket_count)
                split_results[split_name][f"B_{bucket_count}"] = point
                print(json.dumps({"stage": "split_point_complete", "split": split_name, "B": bucket_count, "pair_count": point["pair_count"]}, sort_keys=True), flush=True)

    # ARM A is repeated in each point for exact same-flow validation; retain the
    # first copy as the reference and compare all channels against it.
    arms_block: dict[str, Any] = {"A": {"declared_m": PREFIX_ALPHABET_SIZE, "declared_a_priori": True}}
    for bucket_count in BUCKET_LADDER:
        arms_block[f"B_{bucket_count}"] = {"declared_m": PREFIX_ALPHABET_SIZE * bucket_count, "declared_a_priori": True}
        arms_block[f"C_{bucket_count}"] = {"declared_m": PREFIX_ALPHABET_SIZE * bucket_count, "declared_a_priori": True}
    arms_block["B_original_256^10"] = {"declared_m": EXTREME_ALPHABET_SIZE, "declared_a_priori": True}
    for split_name in ("train", "test"):
        for point, result in split_results[split_name].items():
            for arm, summary in result["arms"].items():
                arms_block.setdefault(arm, {}).setdefault("splits", {})[split_name] = summary

    # Alias the first point's ARM A result as the reference point in the report.
    arms_block["A"]["splits"] = {split: split_results[split][f"B_{BUCKET_LADDER[0]}"]["arms"]["A"] for split in ("train", "test")}
    deltas = build_deltas(split_results, services)
    sane_b = [k for k in BUCKET_LADDER if k <= PREDICTION["sane_bucket_max"]]
    nonclipped = [k for k in sane_b if arms_block[f"B_{k}"]["splits"]["train"]["clipped_fraction"] < 1.0 or arms_block[f"B_{k}"]["splits"]["test"]["clipped_fraction"] < 1.0]
    tv_candidates = [deltas[f"B_{k}_vs_A"]["delta_tv_hat"]["mean"] for k in sane_b if deltas[f"B_{k}_vs_A"]["delta_tv_hat"]["mean"] is not None]
    part_i_nonclipped_at_sane_m = bool(nonclipped)
    near_tolerance = PREDICTION["near_plus_0_39_tolerance"]
    nearest_tv_candidate = min(tv_candidates, key=lambda value: abs(float(value) - 0.39), default=None)
    nearest_tv_candidate_abs_distance = (
        abs(float(nearest_tv_candidate) - 0.39) if nearest_tv_candidate is not None else None
    )
    part_ii_tv_delta_near_0_39 = (
        nearest_tv_candidate_abs_distance is not None and nearest_tv_candidate_abs_distance <= near_tolerance
    )
    if part_i_nonclipped_at_sane_m and part_ii_tv_delta_near_0_39:
        prediction_verdict = "CONFIRMS"
        failed_parts = []
    elif part_i_nonclipped_at_sane_m:
        prediction_verdict = "CONFIRMS_PART_I_ONLY"
        failed_parts = ["part_ii"]
    else:
        prediction_verdict = "REFUTES"
        failed_parts = ["part_i"]
    arithmetic_labels = build_arithmetic_labels(split_results, services, tv_upper_bound)
    comparison_availability = build_comparison_availability(split_results)
    artifact = {
        "experiment": "X9_E",
        "outcome": "MEASURED_DOSE_RESPONSE_CHANNELS",
        "runner_path": str(RUNNER_PATH),
        "runner_sha256": RUNNER_SHA256,
        "cpu_only": True,
        "source": {
            "h5_path": str(H5_PATH),
            "h5_size_bytes": H5_PATH.stat().st_size,
            "flow_label_field": "APP",
            "sni_field": SNI_FIELD,
            "identifier_location": "H5 /flows table column",
            "host_field": HOST_FIELD,
            "ppi_field": "PPI",
            "ppi_len_field": "PPI_LEN",
        },
        "premise_test": premise,
        "design": {
            "k": K,
            "M": M,
            "service_threshold": SERVICE_THRESHOLD,
            "split_policy": "flow-disjoint AND time-disjoint; packet-level splitting prohibited",
            "train_months": list(TRAIN_MONTHS),
            "buffer_month_unused": BUFFER_MONTH,
            "test_months": list(TEST_MONTHS),
            "split_verification": split_bounds,
            "hash": "blake2b(identifier bytes, digest_size=16, person=EIBO-X9-BKT-v1) interpreted as an integer modulo B",
            "random_identifier": "blake2b(seed|node|row, digest_size=10, person=EIBO-X9-RID-v1), one identifier per flow",
            "bucket_ladder": list(BUCKET_LADDER),
            "same_declared_m_for_B_and_C": True,
        },
        "seed": {"random_identifier_seed": RANDOM_IDENTIFIER_SEED, "domain": RANDOM_IDENTIFIER_DOMAIN},
        "alphabet": {
            "declared_a_priori": True,
            "m_rule": "m=32*B for every ladder B/C point; m=32 for ARM A; m=32*256^10 for original ARM B",
            "declared_m_values": {"A": PREFIX_ALPHABET_SIZE, **{f"B_{b}": PREFIX_ALPHABET_SIZE * b for b in BUCKET_LADDER}, **{f"C_{b}": PREFIX_ALPHABET_SIZE * b for b in BUCKET_LADDER}, "B_original_256^10": EXTREME_ALPHABET_SIZE},
            "realized_support_never_used_as_alphabet_size": True,
        },
        "bound_convention": {
            "upper_function": "eibo.statcore.tv_upper_bound",
            "tv_upper_bound_docstring_sentence": "The alphabet size must be the fixed grid size, not the observed support size.",
            "alpha_per_law": ALPHA_PER_LAW,
            "lower_endpoint": "0.0 trivial nonnegative TV lower bound; this runner reports the upper side and radius-free tv_hat only",
        },
        "arms": arms_block,
        "split_results": split_results,
        "deltas": deltas,
        "arithmetic_labels": arithmetic_labels,
        "comparison_availability": comparison_availability,
        "prediction": {
            **PREDICTION,
            "verdict": prediction_verdict,
            "failed_parts": failed_parts,
            "part_i_nonclipped_at_sane_m": part_i_nonclipped_at_sane_m,
            "part_i_evidence": nonclipped,
            "part_ii_tv_delta_near_0_39": part_ii_tv_delta_near_0_39,
            "part_ii_evidence": {
                "tv_delta_candidates": tv_candidates,
                "tolerance_used": near_tolerance,
                "nearest_candidate": nearest_tv_candidate,
                "nearest_candidate_abs_distance_from_0_39": nearest_tv_candidate_abs_distance,
            },
            "sane_nonclipped_B_values": nonclipped,
            "tv_delta_candidates": tv_candidates,
            "opposite_outcome_statement": "If the SNI-inclusive arm clips at every rung including the coarsest, the honest headline is: even a coarse sketch of the host identifier is enough to destroy the certificate. This is a finding, not no separation or inconclusive.",
            "both_readings_are_findings": True,
        },
        "execution": {"elapsed_seconds_before_write": time.time() - started, "cuda_touched": False},
    }
    write_json_atomic(ARTIFACT_PATH, artifact)
    print(json.dumps({"artifact_path": str(ARTIFACT_PATH), "artifact_bytes": ARTIFACT_PATH.stat().st_size, "artifact_sha256": sha256_file(ARTIFACT_PATH), "runner_path": str(RUNNER_PATH), "runner_sha256": RUNNER_SHA256, "outcome": artifact["outcome"]}, sort_keys=True), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    return smoke() if args.smoke else run()


if __name__ == "__main__":
    raise SystemExit(main())
