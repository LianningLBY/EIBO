#!/usr/bin/env python3
# X9_C adds a matched-cardinality, SNI-independent control arm to X9.
# Arm C crosses the existing k=5 packed prefix with per-flow random 10-byte
# identifiers, matching Arm B's fixed alphabet while breaking DST_IP dependence.
# Inputs: the XS H5 corpus, APP labels, PPI/PPI_LEN, and the DST_IP identifier.
# Outputs: /root/eibo/artifacts/x9_cardinality_control.json and a final JSON
# completion line containing artifact and runner hashes.
# Key dependencies: PyTables, NumPy, the repository packing helper
# scripts/xs_compression_early_readout.py::pack_rung_prefix, and
# src/eibo/statcore.py::tv_upper_bound. This experiment is CPU-only.

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import itertools
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import tables


PROJECT_ROOT = Path("/root/eibo")
H5_PATH = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5")
EXISTING_ARTIFACT_PATH = PROJECT_ROOT / "artifacts" / "x9_sni_channel_delta.json"
ARTIFACT_PATH = PROJECT_ROOT / "artifacts" / "x9_cardinality_control.json"
RUNNER_PATH = PROJECT_ROOT / "x9_cardinality_control.py"
HELPER_PATH = PROJECT_ROOT / "scripts" / "xs_compression_early_readout.py"
STATCORE_PATH = PROJECT_ROOT / "src" / "eibo" / "statcore.py"

K = 5
M = 1
SERVICE_THRESHOLD = 2000
ALPHA_PER_LAW = 0.025
CHUNK_SIZE = 100_000
HOST_FIELD = "DST_IP"
# Fixed, non-secret seed for exact reproducibility of the matched-cardinality
# negative control. It controls only Arm C's independent per-flow identifiers.
RANDOM_IDENTIFIER_SEED = 20260914
TRAIN_MONTHS = ("202406", "202407", "202408", "202409", "202410", "202411")
BUFFER_MONTH = "202412"
TEST_MONTHS = ("202501", "202502", "202503", "202504", "202505")
ALL_SPLIT_MONTHS = TRAIN_MONTHS + (BUFFER_MONTH,) + TEST_MONTHS

# DST_IP is stored as exactly ten bytes. This is a fixed storage-domain
# superset, chosen before reading realized values, so the inclusive-arm m is
# not data-dependent. The 32 prefix symbols are crossed with that domain.
HOST_STORAGE_BYTES = 10
PREFIX_ALPHABET_SIZE = 2**K
INCLUSIVE_ALPHABET_SIZE = PREFIX_ALPHABET_SIZE * (256**HOST_STORAGE_BYTES)
CONTROL_ALPHABET_SIZE = INCLUSIVE_ALPHABET_SIZE

OBJECT_DECLARATION = (
    "ARM A (SNI-EXCLUDED), ARM B (SNI-INCLUSIVE), and ARM C "
    "(MATCHED-CARDINALITY SNI-INDEPENDENT) are laws over the same flow rows, "
    "the same (direction,size) k=5 prefix observations, the same service-pair "
    "population, and the same train/test split. Arm C matches Arm B's fixed "
    "alphabet size while replacing DST_IP with an independent per-flow random "
    "10-byte identifier."
)


def sha256_file(path: Path) -> str:
    """Hash a file in bounded memory for the completion record."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_modules() -> tuple[Any, Any]:
    """Load the existing packer and TV reference without importing CUDA code."""
    helper_spec = importlib.util.spec_from_file_location("x9_existing_helper", HELPER_PATH)
    if helper_spec is None or helper_spec.loader is None:
        raise RuntimeError(f"cannot load packing helper from {HELPER_PATH}")
    helper = importlib.util.module_from_spec(helper_spec)
    helper_spec.loader.exec_module(helper)
    if not hasattr(helper, "pack_rung_prefix") or not hasattr(helper, "tv"):
        raise RuntimeError("existing helper does not export pack_rung_prefix and tv")

    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from eibo.statcore import tv_upper_bound

    return helper, tv_upper_bound


def month_from_node(node: tables.Table) -> str:
    """Return YYYYMM from a daily H5 table name such as D20240601."""
    name = str(node._v_name)
    if not name.startswith("D") or len(name) < 7:
        raise RuntimeError(f"unexpected flow table name: {name}")
    return name[1:7]


def selected_nodes(h5: tables.File, months: Iterable[str]) -> list[tables.Table]:
    """Return sorted /flows tables for an explicit month set."""
    month_set = set(months)
    nodes = [
        node
        for node in h5.list_nodes("/flows")
        if month_from_node(node) in month_set
    ]
    return sorted(nodes, key=lambda node: str(node._v_name))


def assert_split_structure(h5: tables.File) -> dict[str, Any]:
    """Verify the required month layout and strict raw-time separation."""
    available = {month_from_node(node) for node in h5.list_nodes("/flows")}
    missing = sorted(set(ALL_SPLIT_MONTHS) - available)
    if missing:
        raise RuntimeError(f"required split months missing from H5: {missing}")

    bounds: dict[str, Any] = {}
    for label, months in (("train", TRAIN_MONTHS), ("test", TEST_MONTHS)):
        minimum = None
        maximum = None
        for node in selected_nodes(h5, months):
            values = np.asarray(node.col("TIME_FIRST"))
            if values.size == 0:
                continue
            node_min = values.min().item()
            node_max = values.max().item()
            minimum = node_min if minimum is None or node_min < minimum else minimum
            maximum = node_max if maximum is None or node_max > maximum else maximum
        if minimum is None or maximum is None:
            raise RuntimeError(f"no TIME_FIRST values found for {label} split")
        bounds[f"{label}_min"] = int(minimum) if isinstance(minimum, (int, np.integer)) else str(minimum)
        bounds[f"{label}_max"] = int(maximum) if isinstance(maximum, (int, np.integer)) else str(maximum)

    if not (bounds["train_max"] < bounds["test_min"]):
        raise RuntimeError(
            f"strict time-disjoint guard failed: train_max={bounds['train_max']} "
            f"test_min={bounds['test_min']}"
        )
    bounds["flow_disjoint"] = True
    bounds["time_disjoint"] = True
    return bounds


def count_eligible_services(h5: tables.File, months: Iterable[str]) -> collections.Counter[int]:
    """Count APP rows with at least K stored PPI observations."""
    counts: collections.Counter[int] = collections.Counter()
    for node in selected_nodes(h5, months):
        for start in range(0, int(node.nrows), CHUNK_SIZE):
            stop = min(start + CHUNK_SIZE, int(node.nrows))
            apps = np.asarray(node.read(start, stop, field="APP"), dtype=np.int64)
            lens = np.asarray(node.read(start, stop, field="PPI_LEN"), dtype=np.int64)
            use = lens >= K
            if np.any(use):
                counts.update(map(int, apps[use]))
    return counts


def build_counters(
    h5: tables.File,
    months: Iterable[str],
    services: list[int],
    helper: Any,
) -> tuple[dict[int, collections.Counter[Any]], dict[int, collections.Counter[Any]]]:
    """Pack the same eligible rows into excluded and inclusive symbol laws."""
    arm_a = {service: collections.Counter() for service in services}
    arm_b = {service: collections.Counter() for service in services}
    service_set = set(services)
    for node in selected_nodes(h5, months):
        for start in range(0, int(node.nrows), CHUNK_SIZE):
            stop = min(start + CHUNK_SIZE, int(node.nrows))
            apps = np.asarray(node.read(start, stop, field="APP"), dtype=np.int64)
            lens = np.asarray(node.read(start, stop, field="PPI_LEN"), dtype=np.int64)
            use = np.isin(apps, np.asarray(services, dtype=np.int64)) & (lens >= K)
            if not np.any(use):
                continue
            ppi = np.asarray(node.read(start, stop, field="PPI"))[use]
            hosts = np.asarray(node.read(start, stop, field=HOST_FIELD))[use]
            apps_use = apps[use]
            codes = np.asarray(helper.pack_rung_prefix(ppi, K, M, 1, 2), dtype=np.uint64)
            for service in np.unique(apps_use):
                service_i = int(service)
                if service_i not in service_set:
                    continue
                local = apps_use == service_i
                arm_a[service_i].update(int(value) for value in codes[local])
                arm_b[service_i].update(
                    (int(code), bytes(host))
                    for code, host in zip(codes[local], hosts[local])
                )
    return arm_a, arm_b


def random_identifier_bytes(rng: np.random.Generator, count: int) -> list[bytes]:
    """Draw independent fixed-width byte identifiers for Arm C rows."""
    # DST_IP is a PyTables StringCol with dtype |S10, so Arm C uses exactly the
    # same 10-byte storage width while removing any dependence on host identity.
    draws = rng.integers(0, 256, size=(count, HOST_STORAGE_BYTES), dtype=np.uint8)
    return [bytes(row) for row in draws]


def build_control_counters(
    h5: tables.File,
    months: Iterable[str],
    services: list[int],
    helper: Any,
    rng: np.random.Generator,
) -> dict[int, collections.Counter[Any]]:
    """Pack eligible rows into Arm C using independent per-flow identifiers."""
    arm_c = {service: collections.Counter() for service in services}
    service_set = set(services)
    services_array = np.asarray(services, dtype=np.int64)
    for node in selected_nodes(h5, months):
        for start in range(0, int(node.nrows), CHUNK_SIZE):
            stop = min(start + CHUNK_SIZE, int(node.nrows))
            apps = np.asarray(node.read(start, stop, field="APP"), dtype=np.int64)
            lens = np.asarray(node.read(start, stop, field="PPI_LEN"), dtype=np.int64)
            use = np.isin(apps, services_array) & (lens >= K)
            if not np.any(use):
                continue
            ppi = np.asarray(node.read(start, stop, field="PPI"))[use]
            apps_use = apps[use]
            codes = np.asarray(helper.pack_rung_prefix(ppi, K, M, 1, 2), dtype=np.uint64)
            random_ids = random_identifier_bytes(rng, int(codes.size))
            for service in np.unique(apps_use):
                service_i = int(service)
                if service_i not in service_set:
                    continue
                local = apps_use == service_i
                arm_c[service_i].update(
                    (int(code), random_id)
                    for code, random_id in zip(codes[local], np.asarray(random_ids, dtype=object)[local])
                )
    return arm_c


def reference_radius(
    n: int,
    alphabet_size: float,
    tv_upper_bound: Any,
) -> Any:
    """Get the repository radius for one law, following the X1 cache pattern."""
    # X1's assembler uses repeat iterables to obtain the reference radius
    # without rebuilding large empirical samples. The observed TV is supplied
    # separately from the repository packing helper below.
    return tv_upper_bound(
        itertools.repeat(0, n),
        itertools.repeat(0, n),
        alphabet_size=alphabet_size,
        alpha=ALPHA_PER_LAW,
    )


def upper_row(
    counter_a: collections.Counter[Any],
    counter_b: collections.Counter[Any],
    radius_a: Any,
    radius_b: Any,
    helper: Any,
) -> dict[str, float | int]:
    """Assemble one upper bracket from repository TV and radius returns."""
    tv_hat = helper.tv(counter_a, counter_b)
    if tv_hat is None:
        raise RuntimeError("empty counter encountered while computing TV")
    eps_hi = min(1.0, float(tv_hat) + float(radius_a.radius_1) + float(radius_b.radius_1))
    return {
        "n_a": int(sum(counter_a.values())),
        "n_b": int(sum(counter_b.values())),
        "tv_hat": float(tv_hat),
        "eps_lo_trivial": 0.0,
        "eps_hi": float(eps_hi),
    }


def summarize(values: list[float]) -> dict[str, float | int]:
    """Return deterministic aggregate statistics for a list of deltas."""
    if not values:
        return {"count": 0}
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def reconcile_real_row(
    service_a: int,
    service_b: int,
    counters_a: dict[int, collections.Counter[Any]],
    counters_b: dict[int, collections.Counter[Any]],
    tv_upper_bound: Any,
    assembled_a: dict[str, float | int],
    assembled_b: dict[str, float | int],
) -> dict[str, Any]:
    """Compare one assembled result with direct repository calls on real symbols."""
    sample_a = list(counters_a[service_a].elements())
    sample_b = list(counters_a[service_b].elements())
    direct_a = tv_upper_bound(sample_a, sample_b, alphabet_size=PREFIX_ALPHABET_SIZE, alpha=ALPHA_PER_LAW)
    sample_a_inclusive = list(counters_b[service_a].elements())
    sample_b_inclusive = list(counters_b[service_b].elements())
    direct_b = tv_upper_bound(
        sample_a_inclusive,
        sample_b_inclusive,
        alphabet_size=INCLUSIVE_ALPHABET_SIZE,
        alpha=ALPHA_PER_LAW,
    )
    return {
        "pair": [service_a, service_b],
        "arm_a_direct_eps_hi": float(direct_a.eps_hi),
        "arm_a_assembled_eps_hi": float(assembled_a["eps_hi"]),
        "arm_a_abs_diff": abs(float(direct_a.eps_hi) - float(assembled_a["eps_hi"])),
        "arm_b_direct_eps_hi": float(direct_b.eps_hi),
        "arm_b_assembled_eps_hi": float(assembled_b["eps_hi"]),
        "arm_b_abs_diff": abs(float(direct_b.eps_hi) - float(assembled_b["eps_hi"])),
    }


def reconcile_control_real_row(
    service_a: int,
    service_b: int,
    counters_c: dict[int, collections.Counter[Any]],
    tv_upper_bound: Any,
    assembled_c: dict[str, float | int],
) -> dict[str, Any]:
    """Compare one Arm C assembled result with a direct repository call."""
    sample_a = list(counters_c[service_a].elements())
    sample_b = list(counters_c[service_b].elements())
    direct_c = tv_upper_bound(
        sample_a,
        sample_b,
        alphabet_size=CONTROL_ALPHABET_SIZE,
        alpha=ALPHA_PER_LAW,
    )
    return {
        "pair": [service_a, service_b],
        "arm_c_direct_eps_hi": float(direct_c.eps_hi),
        "arm_c_assembled_eps_hi": float(assembled_c["eps_hi"]),
        "arm_c_abs_diff": abs(float(direct_c.eps_hi) - float(assembled_c["eps_hi"])),
    }


def make_split_result(
    split_name: str,
    months: tuple[str, ...],
    services: list[int],
    h5: tables.File,
    helper: Any,
    tv_upper_bound: Any,
) -> tuple[dict[str, Any], dict[int, collections.Counter[Any]], dict[int, collections.Counter[Any]]]:
    """Build both channel arms and all same-population pair rows for one split."""
    counters_a, counters_b = build_counters(h5, months, services, helper)
    radius_a = {
        service: reference_radius(sum(counters_a[service].values()), PREFIX_ALPHABET_SIZE, tv_upper_bound)
        for service in services
    }
    radius_b = {
        service: reference_radius(sum(counters_b[service].values()), INCLUSIVE_ALPHABET_SIZE, tv_upper_bound)
        for service in services
    }

    rows: list[dict[str, Any]] = []
    for service_a, service_b in itertools.combinations(services, 2):
        result_a = upper_row(counters_a[service_a], counters_a[service_b], radius_a[service_a], radius_a[service_b], helper)
        result_b = upper_row(counters_b[service_a], counters_b[service_b], radius_b[service_a], radius_b[service_b], helper)
        rows.append(
            {
                "service_a": service_a,
                "service_b": service_b,
                "arm_a_sni_excluded": result_a,
                "arm_b_sni_inclusive": result_b,
                "delta_tv_hat_inclusive_minus_excluded": result_b["tv_hat"] - result_a["tv_hat"],
                "delta_eps_hi_inclusive_minus_excluded": result_b["eps_hi"] - result_a["eps_hi"],
            }
        )

    deltas_tv = [float(row["delta_tv_hat_inclusive_minus_excluded"]) for row in rows]
    deltas_hi = [float(row["delta_eps_hi_inclusive_minus_excluded"]) for row in rows]
    first = rows[0]
    reconciliation = reconcile_real_row(
        int(first["service_a"]),
        int(first["service_b"]),
        counters_a,
        counters_b,
        tv_upper_bound,
        first["arm_a_sni_excluded"],
        first["arm_b_sni_inclusive"],
    )
    result = {
        "split": split_name,
        "months_used": list(months),
        "service_count": len(services),
        "pair_count": len(rows),
        "pairs": rows,
        "aggregate_delta_tv_hat": summarize(deltas_tv),
        "aggregate_delta_eps_hi": summarize(deltas_hi),
        "reference_reconciliation_on_first_real_pair": reconciliation,
    }
    return result, counters_a, counters_b


def make_control_split_result(
    split_name: str,
    months: tuple[str, ...],
    services: list[int],
    h5: tables.File,
    helper: Any,
    tv_upper_bound: Any,
    rng: np.random.Generator,
) -> tuple[dict[str, Any], dict[int, collections.Counter[Any]]]:
    """Build Arm C and all same-population pair rows for one split."""
    counters_c = build_control_counters(h5, months, services, helper, rng)
    radius_c = {
        service: reference_radius(sum(counters_c[service].values()), CONTROL_ALPHABET_SIZE, tv_upper_bound)
        for service in services
    }

    rows: list[dict[str, Any]] = []
    for service_a, service_b in itertools.combinations(services, 2):
        result_c = upper_row(counters_c[service_a], counters_c[service_b], radius_c[service_a], radius_c[service_b], helper)
        rows.append(
            {
                "service_a": service_a,
                "service_b": service_b,
                "arm_c_matched_cardinality_sni_independent": result_c,
            }
        )

    first = rows[0]
    reconciliation = reconcile_control_real_row(
        int(first["service_a"]),
        int(first["service_b"]),
        counters_c,
        tv_upper_bound,
        first["arm_c_matched_cardinality_sni_independent"],
    )
    result = {
        "split": split_name,
        "months_used": list(months),
        "service_count": len(services),
        "pair_count": len(rows),
        "pairs": rows,
        "reference_reconciliation_on_first_real_pair": reconciliation,
    }
    return result, counters_c


def load_existing_artifact() -> dict[str, Any]:
    """Load the completed X9 artifact that supplies Arms A and B."""
    with EXISTING_ARTIFACT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def split_pair_index(split_result: dict[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    """Index split rows by service pair."""
    return {
        (int(row["service_a"]), int(row["service_b"])): row
        for row in split_result["pairs"]
    }


def arm_summary(rows: list[dict[str, float | int]]) -> dict[str, float | int]:
    """Summarize one arm over all split-level pair rows."""
    tv_values = np.asarray([float(row["tv_hat"]) for row in rows], dtype=np.float64)
    hi_values = np.asarray([float(row["eps_hi"]) for row in rows], dtype=np.float64)
    return {
        "pair_split_count": int(tv_values.size),
        "tv_hat_mean": float(np.mean(tv_values)),
        "tv_hat_median": float(np.median(tv_values)),
        "eps_hi_mean": float(np.mean(hi_values)),
        "eps_hi_median": float(np.median(hi_values)),
        "eps_hi_clipped_fraction": float(np.mean(hi_values >= 1.0)),
    }


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write the result through a temporary sibling and atomically replace it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def smoke() -> int:
    """Load the corpus, apply the threshold, and compute one pair in all arms."""
    helper, tv_upper_bound = load_modules()
    existing = load_existing_artifact()
    print(f"SMOKE tv_upper_bound_imported={tv_upper_bound.__module__}.{tv_upper_bound.__name__}")
    print("SMOKE packer_imported=x9_existing_helper.pack_rung_prefix")
    print(
        "SMOKE alphabet "
        f"arm_a={PREFIX_ALPHABET_SIZE} arm_b={INCLUSIVE_ALPHABET_SIZE} "
        f"arm_c={CONTROL_ALPHABET_SIZE} arm_c_equals_arm_b={CONTROL_ALPHABET_SIZE == INCLUSIVE_ALPHABET_SIZE}"
    )
    with tables.open_file(str(H5_PATH), mode="r") as h5:
        split_bounds = assert_split_structure(h5)
        train_counts = count_eligible_services(h5, TRAIN_MONTHS)
        test_counts = count_eligible_services(h5, TEST_MONTHS)
        services = sorted(
            service
            for service in set(train_counts) & set(test_counts)
            if train_counts[service] >= SERVICE_THRESHOLD and test_counts[service] >= SERVICE_THRESHOLD
        )
        if len(services) < 2:
            raise RuntimeError(f"threshold left fewer than two common services: {len(services)}")
        one = services[:2]
        counters_a, counters_b = build_counters(h5, TEST_MONTHS, one, helper)
        counters_c = build_control_counters(h5, TEST_MONTHS, one, helper, np.random.default_rng(RANDOM_IDENTIFIER_SEED))
        radius_a = [reference_radius(sum(counters_a[s].values()), PREFIX_ALPHABET_SIZE, tv_upper_bound) for s in one]
        radius_b = [reference_radius(sum(counters_b[s].values()), INCLUSIVE_ALPHABET_SIZE, tv_upper_bound) for s in one]
        radius_c = [reference_radius(sum(counters_c[s].values()), CONTROL_ALPHABET_SIZE, tv_upper_bound) for s in one]
        result_a = upper_row(counters_a[one[0]], counters_a[one[1]], radius_a[0], radius_a[1], helper)
        result_b = upper_row(counters_b[one[0]], counters_b[one[1]], radius_b[0], radius_b[1], helper)
        result_c = upper_row(counters_c[one[0]], counters_c[one[1]], radius_c[0], radius_c[1], helper)
    existing_rule = existing["aggregate"]["pair_aggregation_rule"]
    print(f"SMOKE split_flow_disjoint={split_bounds['flow_disjoint']} split_time_disjoint={split_bounds['time_disjoint']}")
    print(f"SMOKE common_services_after_threshold={len(services)} service_threshold={SERVICE_THRESHOLD}")
    print(f"SMOKE existing_pair_aggregation_rule={existing_rule}")
    print(
        "SMOKE pair_computed=1 "
        f"arm_a_tv_hat={result_a['tv_hat']:.12g} arm_a_eps_hi={result_a['eps_hi']:.12g} "
        f"arm_b_tv_hat={result_b['tv_hat']:.12g} arm_b_eps_hi={result_b['eps_hi']:.12g} "
        f"arm_c_tv_hat={result_c['tv_hat']:.12g} arm_c_eps_hi={result_c['eps_hi']:.12g} "
        "cpu_only=True"
    )
    print("SMOKE OK")
    return 0


def run() -> int:
    """Run Arm C and combine it with the completed X9 Arm A/B artifact."""
    started = time.time()
    helper, tv_upper_bound = load_modules()
    if not H5_PATH.exists():
        raise RuntimeError(f"corpus does not exist: {H5_PATH}")
    if not STATCORE_PATH.exists():
        raise RuntimeError(f"statcore does not exist: {STATCORE_PATH}")
    if not EXISTING_ARTIFACT_PATH.exists():
        raise RuntimeError(f"existing X9 artifact does not exist: {EXISTING_ARTIFACT_PATH}")
    existing = load_existing_artifact()
    pair_aggregation_rule = existing["aggregate"]["pair_aggregation_rule"]

    with tables.open_file(str(H5_PATH), mode="r") as h5:
        split_bounds = assert_split_structure(h5)
        train_counts = count_eligible_services(h5, TRAIN_MONTHS)
        test_counts = count_eligible_services(h5, TEST_MONTHS)
        services = sorted(
            service
            for service in set(train_counts) & set(test_counts)
            if train_counts[service] >= SERVICE_THRESHOLD and test_counts[service] >= SERVICE_THRESHOLD
        )
        if len(services) < 2:
            raise RuntimeError(f"threshold left fewer than two common services: {len(services)}")
        print(json.dumps({
            "stage": "threshold",
            "cpu_only": True,
            "train_service_count": len([s for s in train_counts if train_counts[s] >= SERVICE_THRESHOLD]),
            "test_service_count": len([s for s in test_counts if test_counts[s] >= SERVICE_THRESHOLD]),
            "common_service_count": len(services),
            "service_threshold": SERVICE_THRESHOLD,
            "split": split_bounds,
        }, sort_keys=True), flush=True)

        control_rng = np.random.default_rng(RANDOM_IDENTIFIER_SEED)
        train_result, _ = make_control_split_result("train", TRAIN_MONTHS, services, h5, helper, tv_upper_bound, control_rng)
        print(json.dumps({"stage": "split_complete", "split": "train", "pair_count": train_result["pair_count"]}, sort_keys=True), flush=True)
        test_result, _ = make_control_split_result("test", TEST_MONTHS, services, h5, helper, tv_upper_bound, control_rng)
        print(json.dumps({"stage": "split_complete", "split": "test", "pair_count": test_result["pair_count"]}, sort_keys=True), flush=True)

    existing_by_split = {
        split_result["split"]: split_pair_index(split_result)
        for split_result in existing["split_results"]
    }
    control_by_split = {
        train_result["split"]: split_pair_index(train_result),
        test_result["split"]: split_pair_index(test_result),
    }

    by_pair: dict[tuple[int, int], dict[str, Any]] = {}
    for split_name in ("train", "test"):
        for key, row in existing_by_split[split_name].items():
            if key not in control_by_split[split_name]:
                raise RuntimeError(f"control split missing existing pair {split_name} {key}")
            control_row = control_by_split[split_name][key]
            c_row = control_row["arm_c_matched_cardinality_sni_independent"]
            a_row = row["arm_a_sni_excluded"]
            b_row = row["arm_b_sni_inclusive"]
            merged = {
                **row,
                "arm_c_matched_cardinality_sni_independent": c_row,
                "delta_tv_hat_control_minus_excluded": c_row["tv_hat"] - a_row["tv_hat"],
                "delta_eps_hi_control_minus_excluded": c_row["eps_hi"] - a_row["eps_hi"],
                "attributed_sni_effect_tv_hat": (
                    (b_row["tv_hat"] - a_row["tv_hat"]) - (c_row["tv_hat"] - a_row["tv_hat"])
                ),
                "attributed_sni_effect_eps_hi": (
                    (b_row["eps_hi"] - a_row["eps_hi"]) - (c_row["eps_hi"] - a_row["eps_hi"])
                ),
            }
            key = (int(row["service_a"]), int(row["service_b"]))
            by_pair.setdefault(key, {"service_a": key[0], "service_b": key[1], "by_split": {}})
            by_pair[key]["by_split"][split_name] = merged

    pair_rows = []
    for key in sorted(by_pair):
        item = by_pair[key]
        train_row = item["by_split"]["train"]
        test_row = item["by_split"]["test"]
        pair_rows.append({
            **item,
            "delta_eps_hi_mean_across_time_splits": float(np.mean([
                train_row["delta_eps_hi_inclusive_minus_excluded"],
                test_row["delta_eps_hi_inclusive_minus_excluded"],
            ])),
            "delta_tv_hat_mean_across_time_splits": float(np.mean([
                train_row["delta_tv_hat_inclusive_minus_excluded"],
                test_row["delta_tv_hat_inclusive_minus_excluded"],
            ])),
            "delta_eps_hi_inclusive_minus_excluded_mean_across_time_splits": float(np.mean([
                train_row["delta_eps_hi_inclusive_minus_excluded"],
                test_row["delta_eps_hi_inclusive_minus_excluded"],
            ])),
            "delta_tv_hat_inclusive_minus_excluded_mean_across_time_splits": float(np.mean([
                train_row["delta_tv_hat_inclusive_minus_excluded"],
                test_row["delta_tv_hat_inclusive_minus_excluded"],
            ])),
            "delta_eps_hi_control_minus_excluded_mean_across_time_splits": float(np.mean([
                train_row["delta_eps_hi_control_minus_excluded"],
                test_row["delta_eps_hi_control_minus_excluded"],
            ])),
            "delta_tv_hat_control_minus_excluded_mean_across_time_splits": float(np.mean([
                train_row["delta_tv_hat_control_minus_excluded"],
                test_row["delta_tv_hat_control_minus_excluded"],
            ])),
            "attributed_sni_effect_eps_hi_mean_across_time_splits": float(np.mean([
                train_row["attributed_sni_effect_eps_hi"],
                test_row["attributed_sni_effect_eps_hi"],
            ])),
            "attributed_sni_effect_tv_hat_mean_across_time_splits": float(np.mean([
                train_row["attributed_sni_effect_tv_hat"],
                test_row["attributed_sni_effect_tv_hat"],
            ])),
        })

    pair_delta_hi_ab = [float(row["delta_eps_hi_inclusive_minus_excluded_mean_across_time_splits"]) for row in pair_rows]
    pair_delta_tv_ab = [float(row["delta_tv_hat_inclusive_minus_excluded_mean_across_time_splits"]) for row in pair_rows]
    pair_delta_hi_ac = [float(row["delta_eps_hi_control_minus_excluded_mean_across_time_splits"]) for row in pair_rows]
    pair_delta_tv_ac = [float(row["delta_tv_hat_control_minus_excluded_mean_across_time_splits"]) for row in pair_rows]
    pair_effect_hi = [float(row["attributed_sni_effect_eps_hi_mean_across_time_splits"]) for row in pair_rows]
    pair_effect_tv = [float(row["attributed_sni_effect_tv_hat_mean_across_time_splits"]) for row in pair_rows]

    all_split_rows = [row for split_name in ("train", "test") for row in by_pair.values() for row in [row["by_split"][split_name]]]
    arm_a_rows = [row["arm_a_sni_excluded"] for row in all_split_rows]
    arm_b_rows = [row["arm_b_sni_inclusive"] for row in all_split_rows]
    arm_c_rows = [row["arm_c_matched_cardinality_sni_independent"] for row in all_split_rows]
    runner_sha = sha256_file(RUNNER_PATH)

    artifact: dict[str, Any] = {
        "experiment": "X9_C",
        "outcome": "MEASURED_MATCHED_CARDINALITY_CONTROL",
        "cpu_only": True,
        "object_declaration": OBJECT_DECLARATION,
        "source": {
            "h5_path": str(H5_PATH),
            "h5_size_bytes": H5_PATH.stat().st_size,
            "existing_x9_artifact_path": str(EXISTING_ARTIFACT_PATH),
            "existing_x9_artifact_sha256": sha256_file(EXISTING_ARTIFACT_PATH),
            "flow_label_field": "APP",
            "sni_field": "QUIC_SNI",
            "sni_derived_destination_host_identifier_field": HOST_FIELD,
            "identifier_location": "H5 /flows table column; verified on /flows/D20240601",
            "ppi_field": "PPI",
            "ppi_per_row_shape": [3, 30],
            "ppi_row_convention": "row 0 timing excluded; row 1 direction; row 2 size",
        },
        "design": {
            "k": K,
            "M": M,
            "service_threshold": SERVICE_THRESHOLD,
            "split_policy": "flow-disjoint AND time-disjoint; packet-level splitting prohibited",
            "train_months": list(TRAIN_MONTHS),
            "buffer_month_unused": BUFFER_MONTH,
            "test_months": list(TEST_MONTHS),
            "split_verification": split_bounds,
            "same_flow_set_across_arms": True,
            "arm_a": "partition symbol is pack_rung_prefix(PPI, k=5, M=1, direction_row=1, size_row=2)",
            "arm_b": "partition symbol is (arm_a packed prefix, fixed-width DST_IP storage value)",
            "arm_c": "partition symbol is (arm_a packed prefix, independent per-flow random fixed-width 10-byte identifier)",
            "host_identifier_inclusion_rule": "DST_IP participates for every eligible flow in ARM B; it is absent from ARM A and replaced by independent random identifiers in ARM C",
            "random_identifier_seed": RANDOM_IDENTIFIER_SEED,
            "random_identifier_assignment": "per eligible flow, independent of service, host, pair, and split label",
        },
        "arms": {
            "arm_a_sni_excluded": {
                "fixed_alphabet_size": PREFIX_ALPHABET_SIZE,
                "summary": arm_summary(arm_a_rows),
            },
            "arm_b_sni_inclusive": {
                "fixed_alphabet_size": INCLUSIVE_ALPHABET_SIZE,
                "summary": arm_summary(arm_b_rows),
            },
            "arm_c_matched_cardinality_sni_independent": {
                "fixed_alphabet_size": CONTROL_ALPHABET_SIZE,
                "summary": arm_summary(arm_c_rows),
            },
        },
        "alphabet": {
            "arm_a_fixed_alphabet_size": PREFIX_ALPHABET_SIZE,
            "arm_b_fixed_alphabet_size": INCLUSIVE_ALPHABET_SIZE,
            "arm_c_fixed_alphabet_size": CONTROL_ALPHABET_SIZE,
            "arm_c_matches_arm_b_fixed_alphabet_size": CONTROL_ALPHABET_SIZE == INCLUSIVE_ALPHABET_SIZE,
            "host_storage_domain": f"all 256^{HOST_STORAGE_BYTES} fixed-width byte strings crossed with the fixed 32-symbol prefix",
            "realized_support_not_used_for_m": True,
        },
        "bound_convention": {
            "upper_function": "src/eibo/statcore.py::tv_upper_bound",
            "packing_function": "scripts/xs_compression_early_readout.py::pack_rung_prefix",
            "alpha_per_law": ALPHA_PER_LAW,
            "joint_confidence_statement": "Each arm's per-pair upper side uses alpha=0.025 for each of the two laws, giving the repository's 0.95 union-bound convention.",
            "lower_endpoint": "0.0 trivial nonnegative TV lower bound; no classifier-based lower side is computed by this runner",
            "statcore_sha256": sha256_file(STATCORE_PATH),
            "helper_sha256": sha256_file(HELPER_PATH),
        },
        "threshold_counts": {
            "train": {str(k): int(v) for k, v in sorted(train_counts.items()) if v >= SERVICE_THRESHOLD},
            "test": {str(k): int(v) for k, v in sorted(test_counts.items()) if v >= SERVICE_THRESHOLD},
            "common_service_ids": services,
            "common_service_count": len(services),
        },
        "split_results": [
            {
                "split": split_name,
                "months_used": list(TRAIN_MONTHS) if split_name == "train" else list(TEST_MONTHS),
                "service_count": len(services),
                "pair_count": len(existing_by_split[split_name]),
                "pairs": [by_pair[key]["by_split"][split_name] for key in sorted(by_pair)],
                "control_reference_reconciliation_on_first_real_pair": (
                    train_result if split_name == "train" else test_result
                )["reference_reconciliation_on_first_real_pair"],
            }
            for split_name in ("train", "test")
        ],
        "per_pair": pair_rows,
        "aggregate": {
            "pair_aggregation_rule": pair_aggregation_rule,
            "pair_count": len(pair_rows),
            "three_way_table": {
                "delta_tv_hat_arm_b_minus_arm_a": summarize(pair_delta_tv_ab),
                "delta_tv_hat_arm_c_minus_arm_a": summarize(pair_delta_tv_ac),
                "attributed_sni_effect_tv_hat": summarize(pair_effect_tv),
                "delta_eps_hi_arm_b_minus_arm_a": summarize(pair_delta_hi_ab),
                "delta_eps_hi_arm_c_minus_arm_a": summarize(pair_delta_hi_ac),
                "attributed_sni_effect_eps_hi": summarize(pair_effect_hi),
            },
        },
        "execution": {
            "elapsed_seconds_before_write": time.time() - started,
            "cuda_touched": False,
            "packet_level_split": False,
            "runner_sha256": runner_sha,
        },
    }
    write_json_atomic(ARTIFACT_PATH, artifact)
    artifact_sha = sha256_file(ARTIFACT_PATH)
    print(json.dumps({
        "artifact_path": str(ARTIFACT_PATH),
        "artifact_bytes": ARTIFACT_PATH.stat().st_size,
        "artifact_sha256": artifact_sha,
        "runner_path": str(RUNNER_PATH),
        "runner_sha256": runner_sha,
        "outcome": artifact["outcome"],
    }, sort_keys=True), flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    return smoke() if args.smoke else run()


if __name__ == "__main__":
    raise SystemExit(main())
