#!/root/miniconda3/bin/python3
"""Estimate deployment-site missing host mass for the X1 training split.

The Good-Turing/Good-Toulmin coverage estimate of mass not represented by
observed destination-host identifiers is f_1 / n, where f_1 is the number of
host identifiers observed exactly once among n flows.  This runner uses the
finest identifier available in the H5 (DST_IP), never service labels, and
keeps the identifier out of the declared (direction, size) channel.

Outputs are written to /root/eibo/artifacts/x13_missing_service_mass.json.
The interval is a clearly labeled nonparametric multinomial-bootstrap
percentile alternative to an Eriksson-type interval; the Chao1 unseen-species
diagnostic is reported separately and is not silently treated as a probability
mass confidence bound.  The with/without comparison isolates the additive
unknown-class term because this runner is not given a base X1/X12 bound.
"""

from __future__ import annotations

import collections
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import tables


PROJECT_ROOT = Path("/root/eibo")
H5_PATH = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5")
ARTIFACT_PATH = PROJECT_ROOT / "artifacts" / "x13_missing_service_mass.json"
RUNNER_PATH = PROJECT_ROOT / "x13_missing_service_mass.py"
TRAIN_MONTHS = ("202406", "202407", "202408", "202409", "202410", "202411")
HOST_FIELD = "DST_IP"
CHUNK_SIZE = 100_000
SUBSAMPLE_RATES = (1.0, 0.1, 0.01)
SUBSAMPLE_SEED = 42
BOOTSTRAP_SEED = 42013
BOOTSTRAP_REPLICATES = 1000
ALPHA = 0.05

REQUIRED_FIELDS = (HOST_FIELD, "QUIC_SNI", "TIME_FIRST", "APP")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def month_from_node(node: tables.Table) -> str:
    name = str(node._v_name)
    if not name.startswith("D") or len(name) < 7:
        raise RuntimeError(f"unexpected flow table name: {name}")
    return name[1:7]


def selected_nodes(h5: tables.File) -> list[tables.Table]:
    nodes = [
        node
        for node in h5.list_nodes("/flows")
        if month_from_node(node) in set(TRAIN_MONTHS)
    ]
    nodes.sort(key=lambda node: str(node._v_name))
    if not nodes:
        raise RuntimeError(f"no /flows tables found for training months {TRAIN_MONTHS}")
    return nodes


def normalized_identifier(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, np.bytes_):
        return bytes(value)
    return str(value).encode("utf-8", errors="replace")


def frequency_of_frequencies(counter: collections.Counter[bytes]) -> dict[int, int]:
    fof = collections.Counter(counter.values())
    return {int(k): int(v) for k, v in sorted(fof.items())}


def summary_from_counter(counter: collections.Counter[bytes], n_flows: int) -> dict[str, Any]:
    fof = frequency_of_frequencies(counter)
    f1 = int(fof.get(1, 0))
    f2 = int(fof.get(2, 0))
    missing_mass = float(f1 / n_flows) if n_flows else 0.0
    if f2:
        chao1_unseen = float((f1 * f1) / (2.0 * f2))
    else:
        chao1_unseen = float(f1 * (f1 - 1) / 2.0)
    return {
        "n_flows": int(n_flows),
        "n_unique": int(len(counter)),
        "f1": f1,
        "f2": f2,
        "missing_mass": missing_mass,
        "frequency_of_frequencies": {str(k): v for k, v in fof.items()},
        "chao1_unseen_species_lower_bound": chao1_unseen,
        "chao1_note": (
            "Chao1 estimates unseen species count, not probability mass; it is "
            "reported as a diagnostic and is not used as the interval endpoint."
        ),
    }


def bootstrap_interval(
    counter: collections.Counter[bytes],
    n_flows: int,
    alpha: float,
    replicates: int,
    seed: int,
) -> dict[str, Any]:
    if n_flows <= 0 or not counter:
        return {
            "lower": 0.0,
            "upper": 0.0,
            "method": "nonparametric_multinomial_bootstrap_percentile",
            "alpha": alpha,
            "replicates": 0,
            "seed": seed,
        }

    observed_counts = np.asarray(list(counter.values()), dtype=np.int64)
    probabilities = observed_counts.astype(np.float64) / float(n_flows)
    rng = np.random.default_rng(seed)
    estimates = np.empty(replicates, dtype=np.float64)
    for index in range(replicates):
        resampled_counts = rng.multinomial(n_flows, probabilities)
        singleton_count = int(np.count_nonzero(resampled_counts == 1))
        estimates[index] = singleton_count / float(n_flows)

    lower, upper = np.quantile(estimates, [alpha / 2.0, 1.0 - alpha / 2.0])
    return {
        "lower": float(lower),
        "upper": float(upper),
        "method": "nonparametric_multinomial_bootstrap_percentile",
        "alternative_to": "Eriksson-type prediction interval",
        "alpha": alpha,
        "replicates": int(replicates),
        "seed": seed,
        "bootstrap_estimate_mean": float(np.mean(estimates)),
        "bootstrap_estimate_std": float(np.std(estimates, ddof=1)),
    }


def main() -> None:
    started = time.time()
    if not H5_PATH.is_file():
        raise FileNotFoundError(H5_PATH)

    rng = np.random.default_rng(SUBSAMPLE_SEED)
    counters = {rate: collections.Counter() for rate in SUBSAMPLE_RATES}
    n_flows = {rate: 0 for rate in SUBSAMPLE_RATES}
    schema: dict[str, str] = {}
    table_names: list[str] = []
    total_training_rows = 0

    with tables.open_file(H5_PATH, mode="r") as h5:
        nodes = selected_nodes(h5)
        first = nodes[0]
        missing = [field for field in REQUIRED_FIELDS if field not in first.colnames]
        if missing:
            raise RuntimeError(f"H5 schema missing required fields: {missing}")
        schema = {field: str(first.coldtypes[field]) for field in REQUIRED_FIELDS}
        table_names = [str(node._v_pathname) for node in nodes]

        for node in nodes:
            for start in range(0, int(node.nrows), CHUNK_SIZE):
                stop = min(start + CHUNK_SIZE, int(node.nrows))
                hosts = np.asarray(node.read(start, stop, field=HOST_FIELD))
                total_training_rows += int(hosts.size)
                uniforms = rng.random(hosts.size)
                for rate in SUBSAMPLE_RATES:
                    if rate == 1.0:
                        mask = np.ones(hosts.size, dtype=bool)
                    else:
                        mask = uniforms < rate
                    selected = hosts[mask]
                    n_flows[rate] += int(selected.size)
                    counters[rate].update(normalized_identifier(value) for value in selected)

    full = summary_from_counter(counters[1.0], n_flows[1.0])
    interval = bootstrap_interval(
        counters[1.0],
        n_flows[1.0],
        ALPHA,
        BOOTSTRAP_REPLICATES,
        BOOTSTRAP_SEED,
    )

    sensitivity = []
    for rate in SUBSAMPLE_RATES:
        item = summary_from_counter(counters[rate], n_flows[rate])
        sensitivity.append(
            {
                "subsample_rate": rate,
                "n_flows": item["n_flows"],
                "n_unique": item["n_unique"],
                "f1": item["f1"],
                "missing_mass": item["missing_mass"],
                "f2": item["f2"],
            }
        )

    # The task supplies no external base open-set bound.  This pair therefore
    # reports the isolated additive unknown-class term, making the comparison
    # explicit rather than fabricating a bound from an unrelated artifact.
    missing_mass = full["missing_mass"]
    bound_comparison = {
        "without_missing_mass": 0.0,
        "with_missing_mass": float(missing_mass),
        "difference": float(missing_mass),
        "interpretation": "isolated additive unknown-class term; base X1/X12 bound not supplied",
    }

    artifact = {
        "experiment": "X13",
        "estimator": "good_turing",
        "estimator_family": "Good-Toulmin coverage / Good-Turing missing mass",
        "identifier_field": HOST_FIELD,
        "identifier_granularity": "flow-level frequency-of-frequencies over anonymized destination-host identifiers",
        "input_h5": str(H5_PATH),
        "input_h5_sha256": sha256_file(H5_PATH),
        "train_months": list(TRAIN_MONTHS),
        "table_paths": table_names,
        "schema_verified_from_h5": schema,
        "n_total_flows": full["n_flows"],
        "n_training_rows_scanned": total_training_rows,
        "n_unique_identifiers": full["n_unique"],
        "f1": full["f1"],
        "f2": full["f2"],
        "frequency_of_frequencies": full["frequency_of_frequencies"],
        "missing_mass_estimate": missing_mass,
        "coverage_estimate": float(1.0 - missing_mass),
        "confidence_interval": interval,
        "chao1_unseen_species_lower_bound": full["chao1_unseen_species_lower_bound"],
        "chao1_note": full["chao1_note"],
        "sensitivity_analysis": sensitivity,
        "sampling": {
            "rates": list(SUBSAMPLE_RATES),
            "nested_uniform_mask": True,
            "seed": SUBSAMPLE_SEED,
            "note": "1:100 is the mandatory 0.01 subsample; all rates are over the X1 training split.",
        },
        "bound_comparison": bound_comparison,
        "scope": "deployment-site missing service mass, NOT a universal unknown prior",
        "identifiers_used_only_for_aggregate_bookkeeping": True,
        "identifier_enters_declared_channel": False,
        "guarantee_status": {
            "missing_mass_estimate": "point estimate",
            "confidence_interval": "bootstrap uncertainty interval, not a finite-sample distribution-free certificate",
            "chao1": "unseen-species count diagnostic, not a probability-mass confidence bound",
        },
        "runtime": {
            "python": "/root/miniconda3/bin/python3",
            "runner": str(RUNNER_PATH),
            "runner_sha256": sha256_file(RUNNER_PATH),
            "elapsed_seconds": float(time.time() - started),
        },
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = ARTIFACT_PATH.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, ARTIFACT_PATH)
    artifact["artifact_sha256"] = sha256_file(ARTIFACT_PATH)
    artifact["artifact_size_bytes"] = ARTIFACT_PATH.stat().st_size
    print(json.dumps({
        "artifact": str(ARTIFACT_PATH),
        "artifact_sha256": artifact["artifact_sha256"],
        "artifact_size_bytes": artifact["artifact_size_bytes"],
        "n_total_flows": artifact["n_total_flows"],
        "n_unique_identifiers": artifact["n_unique_identifiers"],
        "missing_mass_estimate": artifact["missing_mass_estimate"],
        "confidence_interval": artifact["confidence_interval"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
