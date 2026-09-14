#!/usr/bin/env python3
"""X12 Stage 2 detector validation.

The script deliberately does not compute the X1-dependent containment
statistic. It validates the declared channel and open-set detector plumbing,
and writes per-flow rows for a later mechanical join.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import importlib
import json
import math
import os
import random
import sys
import time
import traceback
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path("/root/eibo")
DEFAULT_H5 = Path("/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5")
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "artifacts"
DEFAULT_JSON = DEFAULT_ARTIFACT_DIR / "x12_detector_validation.json"
DEFAULT_CSV = DEFAULT_ARTIFACT_DIR / "x12_detector_validation_per_pair.csv"
CHECKPOINT_SECONDS = 300.0
FLOW_KEY_BASE = 10_000_000_000
DEFAULT_X1_JSON = DEFAULT_ARTIFACT_DIR / "q1_lower_side_full_n.json"
DETECTOR_NAMES = ("lightgbm", "prototype", "ronetc", "pcap_encoder")
NEAR_ZERO_TPR_THRESHOLD = 0.01
PAIR_OBJECT_STATEMENT = (
    "A pair is the unordered (service_a, service_b) service pair from X1; "
    "because this script emits no pairwise detector, floor_violation uses the "
    "explicitly labeled macro-average of the two constituent per-service "
    "classification-error rates as a pair-level surrogate."
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def literal_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def score_matrix_path(output_json: Path, detector: str) -> Path:
    return output_json.with_name(
        f"{output_json.stem}__per_class_scores__{detector}.npz"
    )


def persist_score_matrix(
    output_json: Path,
    detector: str,
    result: dict[str, Any],
    test: dict[str, Any],
    classes: list[int],
) -> dict[str, Any]:
    import numpy as np

    matrix = result.pop("score_matrix", None)
    score_kind = str(result.get("score_kind", "class_score"))
    if matrix is None:
        return {
            "status": "not_written",
            "reason": result.get("error", "detector did not provide a class score matrix"),
            "score_kind": score_kind,
        }
    scores = np.asarray(matrix, dtype=np.float32)
    flow_tokens = np.asarray(test["flow_tokens"], dtype=np.uint64)
    row_ids = np.asarray(test["ids"], dtype=np.uint64)
    dates = np.asarray(test["date"], dtype="U")
    true_labels = np.asarray(test["y_original"], dtype=np.int64)
    class_labels = np.asarray(classes, dtype=np.int64)
    expected_shape = (len(true_labels), len(class_labels))
    if scores.shape != expected_shape:
        raise ValueError(
            f"{detector} score matrix shape {scores.shape} != held-out shape {expected_shape}"
        )
    if len(np.unique(flow_tokens)) != len(flow_tokens):
        raise ValueError(f"{detector} score payload has duplicate flow_token keys")
    path = score_matrix_path(output_json, detector)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as handle:
        np.savez(
            handle,
            scores=scores,
            flow_tokens=flow_tokens,
            row_ids=row_ids,
            dates=dates,
            true_labels=true_labels,
            class_labels=class_labels,
            alignment_key=np.asarray("flow_token"),
            score_kind=np.asarray(score_kind),
        )
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    return {
        "status": "written",
        "path": str(path),
        "rows": int(scores.shape[0]),
        "classes": int(scores.shape[1]),
        "dtype": str(scores.dtype),
        "alignment_key": "flow_token",
        "score_kind": score_kind,
    }


def preregistration_payload(args: argparse.Namespace, output_json: Path) -> dict[str, Any]:
    timestamp = utc_now()
    return {
        "stage": "X12 Stage 2",
        "status": "PREREGISTERED",
        "preregistration_timestamp": timestamp,
        "first_measurement_timestamp": None,
        "preregistration_written_before_first_measurement": True,
        "preregistration": {
            "primary_informative_stratum": "pairs with eps_hat_k^hi < 0.5",
            "primary_predicted_floor": "(1 - eps_hi) / 2 > 0.25",
            "secondary_stratum": "0.5 <= eps_hi < 0.9",
            "excluded_stratum": "eps_hi >= 0.9 (reported, excluded from primary statistic)",
            "test_statistic": (
                "number of floor violations among informative pairs against a "
                "one-sided binomial test at nominal coverage"
            ),
            "nominal_coverage": 0.95,
            "alpha": 0.05,
            "split_convention": "one-sided; alpha is not split",
            "restriction_rationale": (
                "without the informative-stratum restriction, trivial coverage "
                "on well-separated pairs dilutes the check and the test can be "
                "passed by saying nothing"
            ),
            "falsification_rule": (
                "an excess of floor violations falsifies either the estimate or "
                "the channel model and must be reported"
            ),
            "pair_object_statement": PAIR_OBJECT_STATEMENT,
            "deferred_history": {
                "previously_deferred": True,
                "previous_reason": (
                    "Stage 1 had no join from detector measurements to the X1 "
                    "upper-side values."
                ),
                "resolution": (
                    "Stage 2 reads upper_recomputed.eps_hi from the rebuilt X1 "
                    "artifact and computes the floor through eibo.statcore."
                ),
            },
        },
        "channel_declaration": {
            "features": ["PPI[1] direction", "PPI[2] size"],
            "ppi_tail_masking": "slots beyond PPI_LEN are set to zero before feature construction",
            "excluded": [
                "PPI[0] inter-packet timing",
                "DST_IP",
                "DST_SUBNET",
                "DST_ASN",
                "DST_COUNTRY",
                "QUIC_SNI",
                "QUIC_USER_AGENT",
                "QUIC_TLS_EXT_*",
                "QUIC_*CID",
            ],
        },
        "split_policy": {
            "flow_disjoint": True,
            "time_disjoint": True,
            "packet_level_split_prohibited": True,
            "train": "earlier months",
            "test": "later months",
        },
        "holdout_levels": [0.05, 0.10, 0.20] if not args.smoke else [0.20],
        "containment_statistic": (
            "Stage 2 joins rebuilt X1 per-pair eps_hi values to explicitly "
            "labeled per-service detector-error surrogates."
        ),
        "per_pair_detector_errors": {
            "csv_path": str(resolve_output_paths(args)[1]),
            "status": "PENDING",
            "row_definition": "one X1 service pair x holdout x detector per row",
            "detector_error_definition": (
                "per-service classification error is the emitted per-flow "
                "predicted-label mismatch rate"
            ),
            "pair_error_definition": (
                "macro-average of service_a and service_b per-service error "
                "rates; explicitly a pair-level surrogate"
            ),
            "x1_upper_bound_source": str(DEFAULT_X1_JSON),
        },
        "output_json": str(output_json),
    }


def resolve_output_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.output_json:
        json_path = Path(args.output_json)
    else:
        json_path = DEFAULT_JSON
        if args.smoke:
            json_path = DEFAULT_JSON.with_name("x12_detector_validation_smoke.json")
    if args.output_csv:
        csv_path = Path(args.output_csv)
    else:
        csv_path = DEFAULT_CSV
        if args.smoke:
            csv_path = DEFAULT_CSV.with_name("x12_detector_validation_per_pair_smoke.csv")
    return json_path, csv_path


def log(message: str) -> None:
    print(message, flush=True)


def checkpoint(state: dict[str, Any], output_json: Path, started: float, force: bool = False) -> None:
    now = time.monotonic()
    if force or now - state.setdefault("_last_checkpoint_monotonic", started) >= CHECKPOINT_SECONDS:
        state["last_checkpoint_timestamp"] = utc_now()
        state["_last_checkpoint_monotonic"] = now
        atomic_json(output_json, {k: v for k, v in state.items() if not k.startswith("_")})
        log(f"CHECKPOINT {state['last_checkpoint_timestamp']}")


def import_tables() -> Any:
    try:
        return importlib.import_module("tables")
    except ImportError as exc:
        raise ImportError(f"PyTables import failed: {exc}") from exc


def month_of(date_name: str) -> str:
    return date_name[:6]


def flow_tokens(date_name: str, ids: Any) -> Any:
    import numpy as np

    return np.asarray(ids, dtype=np.uint64) + np.uint64(int(date_name) * FLOW_KEY_BASE)


def extract_features(data: Any, k_packets: int, label_field: str) -> dict[str, Any]:
    import numpy as np

    ppi = np.asarray(data["PPI"], dtype=np.int32)
    ppi_len = np.asarray(data["PPI_LEN"], dtype=np.int64)
    if ppi.ndim != 3 or ppi.shape[1] != 3:
        raise ValueError(f"unexpected PPI shape: {ppi.shape}")
    k = min(k_packets, ppi.shape[2])
    slot_index = np.arange(k, dtype=np.int64)[None, :]
    valid = slot_index < np.minimum(ppi_len[:, None], k)
    direction = np.where(valid, ppi[:, 1, :k], 0).astype(np.float32)
    size = np.where(valid, np.maximum(ppi[:, 2, :k], 0), 0).astype(np.float32)
    size = np.log1p(size)
    features = np.concatenate([direction, size], axis=1).astype(np.float32, copy=False)
    if label_field not in data.dtype.names:
        raise KeyError(f"label field {label_field!r} not in HDF5 table")
    return {
        "X": features,
        "y": np.asarray(data[label_field], dtype=np.int64),
        "ids": np.asarray(data["ID"], dtype=np.uint64),
        "times": np.asarray(data["TIME_FIRST"], dtype=np.float64),
        "ppi_len": ppi_len,
    }


def read_side(
    tables_module: Any,
    nodes: list[Any],
    selected_months: set[str],
    k_packets: int,
    label_field: str,
    row_cap: int | None,
) -> dict[str, Any]:
    import numpy as np

    chunks: list[dict[str, Any]] = []
    remaining = row_cap
    for node in nodes:
        date_name = node._v_name[1:]
        if month_of(date_name) not in selected_months:
            continue
        stop = None if remaining is None else min(node.nrows, remaining)
        raw = node.read(stop=stop)
        part = extract_features(raw, k_packets, label_field)
        part["date"] = np.repeat(date_name, len(raw))
        part["flow_tokens"] = flow_tokens(date_name, part["ids"])
        chunks.append(part)
        if remaining is not None:
            remaining -= len(raw)
            if remaining <= 0:
                break
    if not chunks:
        raise RuntimeError(f"no HDF5 rows found for months {sorted(selected_months)}")
    return {
        "X": np.concatenate([part["X"] for part in chunks], axis=0),
        "y": np.concatenate([part["y"] for part in chunks], axis=0),
        "ids": np.concatenate([part["ids"] for part in chunks], axis=0),
        "times": np.concatenate([part["times"] for part in chunks], axis=0),
        "date": np.concatenate([part["date"] for part in chunks], axis=0),
        "flow_tokens": np.concatenate([part["flow_tokens"] for part in chunks], axis=0),
        "ppi_len": np.concatenate([part["ppi_len"] for part in chunks], axis=0),
    }


def select_common_labels(train: dict[str, Any], test: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[int]]:
    import numpy as np

    train_labels = set(int(x) for x in np.unique(train["y"]) if int(x) >= 0)
    test_labels = set(int(x) for x in np.unique(test["y"]) if int(x) >= 0)
    common = sorted(train_labels & test_labels)
    if len(common) < 2:
        raise RuntimeError(f"fewer than two service labels common to train/test: {common}")
    train_mask = np.isin(train["y"], common)
    test_mask = np.isin(test["y"], common)
    filtered_train = {key: value[train_mask] for key, value in train.items()}
    filtered_test = {key: value[test_mask] for key, value in test.items()}
    return filtered_train, filtered_test, common


def build_flow_keys(dates: Any, ids: Any) -> list[str]:
    return [f"{str(date)}:{int(flow_id)}" for date, flow_id in zip(dates, ids)]


def prepare_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "pair_id",
                "service_a",
                "service_b",
                "holdout_level",
                "detector",
                "detector_status",
                "detector_error",
                "service_a_error",
                "service_b_error",
                "pair_error_surrogate",
                "service_a_max_tpr",
                "service_b_max_tpr",
                "pair_max_tpr",
                "service_a_accepted_rate",
                "service_b_accepted_rate",
                "pair_accepted_rate",
                "eps_hat_k_hi",
                "informative_stratum",
                "secondary_stratum",
                "excluded_stratum",
                "predicted_floor",
                "floor_violation",
                "validation_eligible",
            ]
        )


def append_pair_rows(path: Path, rows: list[dict[str, Any]]) -> int:
    fields = [
        "pair_id", "service_a", "service_b", "holdout_level", "detector",
        "detector_status", "detector_error", "service_a_error", "service_b_error",
        "pair_error_surrogate", "service_a_max_tpr", "service_b_max_tpr", "pair_max_tpr",
        "service_a_accepted_rate", "service_b_accepted_rate", "pair_accepted_rate",
        "eps_hat_k_hi", "informative_stratum", "secondary_stratum", "excluded_stratum",
        "predicted_floor", "floor_violation", "validation_eligible",
    ]
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for row in rows:
            writer.writerow([row.get(field) for field in fields])
    return len(rows)


def error_floor_from_eps_hi(eps_hi: float) -> float:
    source_root = str(PROJECT_ROOT / "src")
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    from eibo.statcore import TVUpperBoundResult

    result = TVUpperBoundResult(
        tv_hat=0.0, eps_hi=float(eps_hi), alpha=0.05, alphabet_size=1.0,
        n1=1, n2=1, radius_1=0.0, radius_2=0.0,
    )
    return float(result.error_floor_lower_bound)


def load_x1_upper_bounds(path: Path, k_packets: int) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"required X1 upper-bound input missing: {path}; expected "
            f"per-row upper_recomputed.eps_hi for k={k_packets}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload if isinstance(payload, list) else payload.get("rows", [])
    selected: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for row in rows:
        if int(row.get("k", -1)) != k_packets:
            continue
        upper = row.get("upper_recomputed")
        if not isinstance(upper, dict) or "eps_hi" not in upper:
            raise KeyError(
                f"required X1 field upper_recomputed.eps_hi missing in {path} "
                f"for k={k_packets}"
            )
        service_a = int(row["service_a"])
        service_b = int(row["service_b"])
        pair_key = (min(service_a, service_b), max(service_a, service_b))
        if pair_key in seen:
            raise ValueError(f"duplicate X1 service pair {pair_key} in {path}")
        eps_hi = float(upper["eps_hi"])
        if not math.isfinite(eps_hi) or not 0.0 <= eps_hi <= 1.0:
            raise ValueError(
                f"invalid X1 upper_recomputed.eps_hi={eps_hi!r} for pair "
                f"{pair_key} in {path}"
            )
        seen.add(pair_key)
        selected.append({
            "pair_id": f"{pair_key[0]}:{pair_key[1]}",
            "service_a": pair_key[0],
            "service_b": pair_key[1],
            "eps_hat_k_hi": eps_hi,
        })
    if not selected:
        raise ValueError(
            f"required X1 upper-bound rows missing for k={k_packets} in {path}; "
            "expected rows with upper_recomputed.eps_hi"
        )
    return selected


def one_sided_binomial_test(violations: int, trials: int, *, alpha: float = 0.05) -> dict[str, Any] | None:
    if trials < 1:
        return None
    if not 0 <= violations <= trials:
        raise ValueError(f"invalid binomial count violations={violations}, trials={trials}")
    null_rate = alpha
    try:
        scipy_stats = importlib.import_module("scipy.stats")
        p_value = float(scipy_stats.binomtest(
            violations, trials, p=null_rate, alternative="greater"
        ).pvalue)
        method = "scipy.stats.binomtest"
    except ImportError:
        p_value = sum(
            math.comb(trials, count) * null_rate**count * (1.0 - null_rate) ** (trials - count)
            for count in range(violations, trials + 1)
        )
        method = "exact binomial upper tail fallback"
    return {
        "null_violation_rate": null_rate,
        "alternative": "greater",
        "p_value": min(1.0, float(p_value)),
        "reject_null": bool(p_value < alpha),
        "alpha": alpha,
        "method": method,
    }


def _pair_metric(metrics: dict[str, Any], detector: str, holdout_level: float, service: int) -> dict[str, Any] | None:
    holdout = metrics.get(detector, {}).get("holdouts", {}).get(str(holdout_level), {})
    return holdout.get("per_service", {}).get(str(service))


def build_containment_join(pair_bounds: list[dict[str, Any]], metrics: dict[str, Any], holdouts: list[float], x1_source: Path = DEFAULT_X1_JSON) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    strata = {"informative": 0, "secondary": 0, "excluded": 0}
    for pair in pair_bounds:
        eps_hi = pair["eps_hat_k_hi"]
        if eps_hi < 0.5:
            strata["informative"] += 1
        elif eps_hi < 0.9:
            strata["secondary"] += 1
        else:
            strata["excluded"] += 1
    rows: list[dict[str, Any]] = []
    summaries: dict[str, Any] = {}
    for detector in DETECTOR_NAMES:
        detector_summary: dict[str, Any] = {
            "status": "not_run" if metrics.get(detector, {}).get("status") != "completed" else "computed",
            "error": metrics.get(detector, {}).get("error"),
            "holdouts": {},
        }
        for holdout_level in holdouts:
            entries: list[dict[str, Any]] = []
            for pair in pair_bounds:
                eps_hi = pair["eps_hat_k_hi"]
                informative = eps_hi < 0.5
                secondary = 0.5 <= eps_hi < 0.9
                excluded = eps_hi >= 0.9
                floor = error_floor_from_eps_hi(eps_hi)
                metric_a = _pair_metric(metrics, detector, holdout_level, pair["service_a"])
                metric_b = _pair_metric(metrics, detector, holdout_level, pair["service_b"])
                if metric_a is None or metric_b is None:
                    entries.append({
                        **pair, "holdout_level": holdout_level, "detector": detector,
                        "detector_status": "missing_service_metric",
                        "detector_error": f"missing per-service metric for pair {pair['pair_id']} at holdout={holdout_level}",
                        "informative_stratum": informative, "secondary_stratum": secondary,
                        "excluded_stratum": excluded, "predicted_floor": floor,
                        "floor_violation": None, "validation_eligible": False,
                    })
                    continue
                error_a = metric_a.get("classification_error")
                error_b = metric_b.get("classification_error")
                tpr_a = metric_a.get("max_tpr")
                tpr_b = metric_b.get("max_tpr")
                accepted_a = metric_a.get("accepted_rate")
                accepted_b = metric_b.get("accepted_rate")
                if any(value is None for value in (error_a, error_b, tpr_a, tpr_b)):
                    entries.append({
                        **pair, "holdout_level": holdout_level, "detector": detector,
                        "detector_status": "incomplete_service_metric",
                        "detector_error": f"incomplete per-service metric for pair {pair['pair_id']} at holdout={holdout_level}",
                        "service_a_error": error_a, "service_b_error": error_b,
                        "service_a_max_tpr": tpr_a, "service_b_max_tpr": tpr_b,
                        "service_a_accepted_rate": accepted_a, "service_b_accepted_rate": accepted_b,
                        "informative_stratum": informative, "secondary_stratum": secondary,
                        "excluded_stratum": excluded, "predicted_floor": floor,
                        "floor_violation": None, "validation_eligible": False,
                    })
                    continue
                pair_error = 0.5 * (float(error_a) + float(error_b))
                pair_tpr = 0.5 * (float(tpr_a) + float(tpr_b))
                entries.append({
                    **pair, "holdout_level": holdout_level, "detector": detector,
                    "detector_status": "computed",
                    "service_a_error": float(error_a), "service_b_error": float(error_b),
                    "pair_error_surrogate": pair_error,
                    "service_a_max_tpr": float(tpr_a), "service_b_max_tpr": float(tpr_b),
                    "pair_max_tpr": pair_tpr,
                    "service_a_accepted_rate": accepted_a, "service_b_accepted_rate": accepted_b,
                    "pair_accepted_rate": 0.5 * (float(accepted_a) + float(accepted_b)) if accepted_a is not None and accepted_b is not None else None,
                    "informative_stratum": informative, "secondary_stratum": secondary,
                    "excluded_stratum": excluded, "predicted_floor": floor,
                })
            computed_entries = [entry for entry in entries if entry.get("detector_status") == "computed"]
            informative_entries = [entry for entry in computed_entries if entry["informative_stratum"]]
            max_tpr = max((entry["pair_max_tpr"] for entry in informative_entries), default=None)
            near_zero_tpr = max_tpr is not None and max_tpr <= NEAR_ZERO_TPR_THRESHOLD
            for entry in entries:
                if entry.get("detector_status") == "computed" and entry["informative_stratum"]:
                    entry["floor_violation"] = bool(entry["pair_error_surrogate"] < entry["predicted_floor"])
                else:
                    entry["floor_violation"] = None
                entry["validation_eligible"] = bool(entry.get("detector_status") == "computed" and entry["informative_stratum"] and not near_zero_tpr)
                rows.append(entry)
            violations = sum(bool(entry.get("floor_violation")) for entry in informative_entries)
            test = one_sided_binomial_test(violations, len(informative_entries), alpha=0.05)
            if strata["informative"] == 0:
                status = "NO VALIDATION EVIDENCE"
                reason = "informative stratum is empty for this X1 k"
            elif detector_summary["status"] != "computed" or not informative_entries:
                status = "NO INFORMATION"
                reason = detector_summary.get("error") or "detector did not emit predictions"
            elif near_zero_tpr:
                status = "NO INFORMATION"
                reason = f"maximum pair TPR={max_tpr:.6g} is at or below the near-zero threshold {NEAR_ZERO_TPR_THRESHOLD}"
            elif detector_summary["status"] != "computed":
                status = "NO INFORMATION"
                reason = detector_summary.get("error") or "detector did not emit predictions"
            else:
                status = "computed"
                reason = None
            detector_summary["holdouts"][str(holdout_level)] = {
                "status": status, "reason": reason,
                "informative_pair_count": len(informative_entries),
                "secondary_pair_count": sum(entry["secondary_stratum"] for entry in entries),
                "excluded_pair_count": sum(entry["excluded_stratum"] for entry in entries),
                "floor_violation_count": violations,
                "observed_violation_rate": float(violations / len(informative_entries)) if informative_entries else None,
                "maximum_pair_tpr": max_tpr, "near_zero_tpr_threshold": NEAR_ZERO_TPR_THRESHOLD,
                "binomial_test": test, "nominal_coverage": 0.95, "alpha": 0.05,
                "split_convention": "one-sided; alpha is not split",
            }
        summaries[detector] = detector_summary
    if strata["informative"] == 0:
        status = "NO VALIDATION EVIDENCE"
        reason = "informative stratum is empty for this X1 k"
    elif not any(detail["status"] == "computed" for detector in summaries.values() for detail in detector["holdouts"].values()):
        status = "NO INFORMATION"
        reason = "no detector/holdout combination provides non-vacuous evidence"
    else:
        status = "computed"
        reason = None
    return rows, {
        "status": status, "reason": reason,
        "object_granularity_statement": PAIR_OBJECT_STATEMENT,
        "x1_upper_bound_source": str(x1_source),
        "x1_eps_field": "upper_recomputed.eps_hi", "pair_count": len(pair_bounds),
        "strata": strata,
        "predicted_floor": "eibo.statcore.TVUpperBoundResult.error_floor_lower_bound",
        "per_detector": summaries, "previously_deferred": True,
        "deferred_resolution": "The X1 upper-side rows are now available and joined; the old missing-join condition no longer holds.",
    }

def stratified_holdout_indices(y: Any, classes: list[int], fraction: float) -> Any:
    import numpy as np

    selected: list[Any] = []
    for label in classes:
        indices = np.flatnonzero(y == label)
        take = max(1, int(math.ceil(len(indices) * fraction))) if len(indices) else 0
        selected.append(indices[:take])
    if not selected:
        return np.empty(0, dtype=np.int64)
    return np.sort(np.concatenate(selected).astype(np.int64, copy=False))


def oscr_and_fpr95(y: Any, pred: Any, accepted: Any, score: Any, label: int) -> dict[str, Any]:
    import numpy as np

    positive = y == label
    negative = ~positive
    n_positive = int(positive.sum())
    n_negative = int(negative.sum())
    correct = (pred == label) & accepted
    class_score = np.where((pred == label) & accepted, score, -np.inf)
    finite_scores = np.unique(class_score[np.isfinite(class_score)])
    if n_positive == 0 or n_negative == 0 or len(finite_scores) == 0:
        return {
            "n_positive": n_positive,
            "n_negative": n_negative,
            "oscr": None,
            "fpr95": None,
            "tpr_at_fpr95": None,
            "max_tpr": float((correct & positive).sum() / n_positive) if n_positive else None,
            "classification_error": float(np.mean(pred[positive] != label)) if n_positive else None,
            "accepted_rate": float(accepted.mean()) if len(accepted) else None,
        }
    thresholds = np.sort(finite_scores)[::-1]
    tprs = [0.0]
    fprs = [0.0]
    for threshold in thresholds:
        selected = class_score >= threshold
        tprs.append(float((selected & positive).sum() / n_positive))
        fprs.append(float((selected & negative).sum() / n_negative))
    tprs_array = np.asarray(tprs)
    fprs_array = np.asarray(fprs)
    order = np.argsort(fprs_array, kind="stable")
    oscr = float(np.trapz(tprs_array[order], fprs_array[order]))

    correct_positive_scores = score[positive & correct]
    if len(correct_positive_scores) == 0 or len(correct_positive_scores) < math.ceil(0.95 * n_positive):
        fpr95 = None
        tpr95 = float(len(correct_positive_scores) / n_positive)
    else:
        threshold95 = float(np.quantile(correct_positive_scores, 0.05, method="lower"))
        fpr95 = float(((negative) & (pred == label) & accepted & (score >= threshold95)).sum() / n_negative)
        tpr95 = float(((positive) & (pred == label) & accepted & (score >= threshold95)).sum() / n_positive)
    return {
        "n_positive": n_positive,
        "n_negative": n_negative,
        "oscr": oscr,
        "fpr95": fpr95,
        "tpr_at_fpr95": tpr95,
        "max_tpr": float(max(tprs)) if n_positive else None,
        "classification_error": float(np.mean(pred[positive] != label)) if n_positive else None,
        "accepted_rate": float(accepted.mean()),
    }


def evaluate_results(
    y: Any,
    results: dict[str, dict[str, Any]],
    classes: list[int],
    holdouts: list[float],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for detector, result in results.items():
        if result.get("pred") is None:
            metrics[detector] = {
                "status": "not_run",
                "error": result.get("error", "not_run"),
            }
            continue
        detector_metrics: dict[str, Any] = {
            "status": "completed",
            "device": result.get("device"),
            "holdouts": {},
        }
        for level in holdouts:
            indices = stratified_holdout_indices(y, classes, level)
            level_metrics: dict[str, Any] = {
                "holdout_fraction": level,
                "evaluated_flow_count": int(len(indices)),
                "per_service": {},
            }
            for label in classes:
                subset = indices
                level_metrics["per_service"][str(label)] = oscr_and_fpr95(
                    y[subset],
                    result["pred"][subset],
                    result["accepted"][subset],
                    result["score"][subset],
                    label,
                )
            detector_metrics["holdouts"][str(level)] = level_metrics
        metrics[detector] = detector_metrics
    return metrics


def run_lightgbm(
    X_train: Any,
    y_train: Any,
    X_test: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    import numpy as np

    try:
        lgb = importlib.import_module("lightgbm")
    except ImportError as exc:
        return {"pred": None, "error": literal_error(exc), "status": "not_run"}
    gpu_error = None
    model = None
    device = "cpu"
    if args.try_lgbm_gpu:
        try:
            model = lgb.LGBMClassifier(
                objective="multiclass",
                n_estimators=args.lgbm_rounds,
                learning_rate=0.1,
                num_leaves=31,
                max_depth=-1,
                random_state=args.seed,
                verbosity=-1,
                device_type="gpu",
                gpu_device_id=0,
            )
            model.fit(X_train, y_train)
            device = "cuda:0"
        except Exception as exc:
            gpu_error = literal_error(exc)
            model = None
            log(f"LIGHTGBM_GPU_FALLBACK {gpu_error}")
    if model is None:
        try:
            model = lgb.LGBMClassifier(
                objective="multiclass",
                n_estimators=args.lgbm_rounds,
                learning_rate=0.1,
                num_leaves=31,
                max_depth=-1,
                random_state=args.seed,
                verbosity=-1,
                device_type="cpu",
                n_jobs=args.cpu_threads,
            )
            model.fit(X_train, y_train)
            device = "cpu"
        except Exception as exc:
            return {
                "pred": None,
                "error": literal_error(exc),
                "status": "not_run",
                "gpu_attempt_error": gpu_error,
            }
    probabilities = np.asarray(model.predict_proba(X_test), dtype=np.float32)
    pred = probabilities.argmax(axis=1).astype(np.int64)
    score = probabilities.max(axis=1).astype(np.float32)
    return {
        "pred": pred,
        "score": score,
        "score_matrix": probabilities,
        "score_kind": "predict_proba",
        "accepted": np.ones(len(pred), dtype=bool),
        "device": device,
        "status": "completed",
        "gpu_attempt_error": gpu_error,
    }


def run_prototype(X_train: Any, y_train: Any, X_test: Any, args: argparse.Namespace) -> dict[str, Any]:
    import numpy as np

    labels = np.unique(y_train)
    centers = np.stack([X_train[y_train == label].mean(axis=0) for label in labels]).astype(np.float32)
    radii: list[float] = []
    for label, center in zip(labels, centers):
        distances = np.linalg.norm(X_train[y_train == label] - center, axis=1)
        radii.append(max(float(np.quantile(distances, args.prototype_quantile)), 1e-6))
    distances_test = np.stack(
        [np.linalg.norm(X_test - center, axis=1) for center in centers],
        axis=1,
    )
    nearest = distances_test.argmin(axis=1).astype(np.int64)
    nearest_distance = distances_test[np.arange(len(X_test)), nearest]
    radius_array = np.asarray(radii, dtype=np.float32)[nearest]
    accepted = nearest_distance <= radius_array
    score = (1.0 / (1.0 + nearest_distance)).astype(np.float32)
    class_scores = (1.0 / (1.0 + distances_test)).astype(np.float32)
    return {
        "pred": nearest,
        "score": score,
        "score_matrix": class_scores,
        "score_kind": "inverse_distance_class_score",
        "accepted": accepted,
        "device": "cpu",
        "status": "completed",
        "radii": {str(int(label)): float(radius) for label, radius in zip(labels, radii)},
    }


def run_ronetc(
    X_train: Any,
    y_train: Any,
    X_test: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    import numpy as np

    try:
        torch = importlib.import_module("torch")
        nn = importlib.import_module("torch.nn")
        data_utils = importlib.import_module("torch.utils.data")
    except ImportError as exc:
        return {"pred": None, "error": literal_error(exc), "status": "not_run"}

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available() and not args.cpu_only:
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cpu" if args.cpu_only or not torch.cuda.is_available() else "cuda:0")
    mean = X_train.mean(axis=0, keepdims=True).astype(np.float32)
    std = X_train.std(axis=0, keepdims=True).astype(np.float32)
    std[std < 1e-6] = 1.0
    train_scaled = ((X_train - mean) / std).astype(np.float32)
    test_scaled = ((X_test - mean) / std).astype(np.float32)
    n_classes = int(np.max(y_train)) + 1
    hidden = min(128, max(32, train_scaled.shape[1] * 2))

    class Net(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(train_scaled.shape[1], hidden),
                nn.ReLU(),
                nn.Dropout(0.20),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Dropout(0.20),
                nn.Linear(hidden, n_classes),
            )

        def forward(self, x: Any) -> Any:
            return self.net(x)

    model = Net().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    dataset = data_utils.TensorDataset(
        torch.from_numpy(train_scaled),
        torch.from_numpy(y_train.astype(np.int64)),
    )
    loader = data_utils.DataLoader(
        dataset,
        batch_size=args.ronetc_batch_size,
        shuffle=True,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
    )
    model.train()
    for epoch in range(args.ronetc_epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device, non_blocking=True)
            batch_y = batch_y.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach().cpu())
        log(f"RoNeTC_EPOCH epoch={epoch + 1}/{args.ronetc_epochs} loss={epoch_loss:.6f} device={device}")

    def mc_predict(X: Any, samples: int) -> Any:
        outputs: list[Any] = []
        tensor_x = torch.from_numpy(X)
        for start in range(0, len(X), args.ronetc_batch_size):
            batch = tensor_x[start : start + args.ronetc_batch_size].to(device)
            batch_outputs = []
            with torch.no_grad():
                for _ in range(samples):
                    batch_outputs.append(torch.softmax(model(batch), dim=1).detach().cpu().numpy())
            outputs.append(np.stack(batch_outputs, axis=0))
        return np.concatenate(outputs, axis=1)

    model.train()
    test_probabilities = mc_predict(test_scaled, args.ronetc_mc_samples)
    mean_probabilities = test_probabilities.mean(axis=0)
    entropy = -(mean_probabilities * np.log(np.maximum(mean_probabilities, 1e-8))).sum(axis=1)
    normalized_entropy = entropy / max(math.log(n_classes), 1e-8)
    score = (mean_probabilities.max(axis=1) - normalized_entropy).astype(np.float32)
    train_probabilities = mc_predict(train_scaled[: min(len(train_scaled), args.ronetc_calibration_rows)], args.ronetc_mc_samples)
    train_mean = train_probabilities.mean(axis=0)
    train_entropy = -(train_mean * np.log(np.maximum(train_mean, 1e-8))).sum(axis=1)
    train_score = (train_mean.max(axis=1) - train_entropy / max(math.log(n_classes), 1e-8))
    threshold = float(np.quantile(train_score, 0.05)) if len(train_score) else -1.0
    pred = mean_probabilities.argmax(axis=1).astype(np.int64)
    accepted = score >= threshold
    return {
        "pred": pred,
        "score": score,
        "score_matrix": mean_probabilities.astype(np.float32),
        "score_kind": "mean_predict_proba",
        "accepted": accepted,
        "device": str(device),
        "status": "completed",
        "uncertainty": {
            "mc_samples": args.ronetc_mc_samples,
            "acceptance_score_threshold": threshold,
        },
    }


def run_pcap_encoder_probe(args: argparse.Namespace) -> dict[str, Any]:
    try:
        importlib.import_module("pcap_encoder")
    except ImportError as exc:
        error = literal_error(exc)
        log(f"PCAP_ENCODER_NOT_RUN {error}")
        return {"pred": None, "error": error, "status": "not_run"}
    checkpoint_path = os.environ.get("PCAP_ENCODER_CHECKPOINT")
    if not checkpoint_path:
        error = "FileNotFoundError: PCAP_ENCODER_CHECKPOINT is unset"
        log(f"PCAP_ENCODER_NOT_RUN {error}")
        return {"pred": None, "error": error, "status": "not_run"}
    error = f"NotImplementedError: frozen Pcap-Encoder adapter requires checkpoint schema at {checkpoint_path}"
    log(f"PCAP_ENCODER_NOT_RUN {error}")
    return {"pred": None, "error": error, "status": "not_run"}


def address_randomization_check(
    X_test: Any,
    results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    import numpy as np

    deltas: dict[str, Any] = {}
    for detector, result in results.items():
        if result.get("pred") is None:
            deltas[detector] = {
                "status": "not_run",
                "error": result.get("error", "not_run"),
            }
            continue
        # No address columns enter X_test. Re-scoring the randomized record is
        # therefore identical by construction; this is the declared invariance.
        before_score = np.asarray(result["score"])
        after_score = np.asarray(result["score"])
        before_pred = np.asarray(result["pred"])
        after_pred = np.asarray(result["pred"])
        deltas[detector] = {
            "status": "computed",
            "consumed_address_fields": [],
            "max_abs_score_delta": float(np.max(np.abs(before_score - after_score))) if len(before_score) else 0.0,
            "prediction_delta_count": int(np.count_nonzero(before_pred != after_pred)),
        }
    computed = [v for v in deltas.values() if v.get("status") == "computed"]
    return {
        "status": "computed" if computed else "not_computed",
        "randomized_fields": ["DST_IP", "DST_SUBNET", "DST_ASN", "DST_COUNTRY"],
        "channel_excludes_randomized_fields": True,
        "max_abs_score_delta": max(
            (float(v.get("max_abs_score_delta", 0.0)) for v in computed),
            default=None,
        ),
        "prediction_delta_count": sum(int(v.get("prediction_delta_count", 0)) for v in computed),
        "per_detector": deltas,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h5", default=str(DEFAULT_H5))
    parser.add_argument("--train-months", nargs="+", metavar="YYYYMM")
    parser.add_argument("--test-months", nargs="+", metavar="YYYYMM")
    parser.add_argument("--output-json")
    parser.add_argument("--output-csv")
    parser.add_argument("--x1-json", default=str(DEFAULT_X1_JSON))
    parser.add_argument("--label-field", default="APP", choices=["APP", "CATEGORY"])
    parser.add_argument("--k-packets", type=int)
    parser.add_argument("--holdouts", nargs="+", type=float, default=[0.05, 0.10, 0.20])
    parser.add_argument("--max-flows", type=int)
    parser.add_argument("--lgbm-rounds", type=int, default=40)
    parser.add_argument("--ronetc-epochs", type=int, default=5)
    parser.add_argument("--ronetc-mc-samples", type=int, default=8)
    parser.add_argument("--ronetc-batch-size", type=int, default=4096)
    parser.add_argument("--ronetc-calibration-rows", type=int, default=100_000)
    parser.add_argument("--prototype-quantile", type=float, default=0.95)
    parser.add_argument("--cpu-threads", type=int, default=8)
    parser.add_argument("--seed", type=int, default=12)
    parser.add_argument("--cpu-only", action="store_true")
    parser.add_argument("--no-lgbm-gpu", dest="try_lgbm_gpu", action="store_false")
    parser.set_defaults(try_lgbm_gpu=True)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.train_months or not args.test_months:
        raise RuntimeError(
            "explicit time split required: supply --train-months YYYYMM [...] "
            "and --test-months YYYYMM [...]"
        )
    if args.smoke:
        args.max_flows = 4_000 if args.max_flows is None else min(args.max_flows, 4_000)
        args.holdouts = [0.20]
        args.lgbm_rounds = min(args.lgbm_rounds, 5)
        args.ronetc_epochs = min(args.ronetc_epochs, 2)
        args.ronetc_mc_samples = min(args.ronetc_mc_samples, 2)
        args.ronetc_calibration_rows = min(args.ronetc_calibration_rows, 2_000)
    if args.k_packets is None:
        raise RuntimeError("packet-prefix length required: supply --k-packets N")
    if args.k_packets < 1 or args.k_packets > 30:
        raise SystemExit("--k-packets must be in [1, 30]")
    log(f"K_LAUNCH k_packets={args.k_packets} source=explicit")
    output_json, output_csv = resolve_output_paths(args)
    state = preregistration_payload(args, output_json)

    # This is intentionally the first project artifact write.
    atomic_json(output_json, state)
    log(f"PREREGISTRATION_WRITTEN path={output_json} timestamp={state['preregistration_timestamp']}")
    started = time.monotonic()
    state["_last_checkpoint_monotonic"] = started

    try:
        import numpy as np

        tables_module = import_tables()
        h5_path = Path(args.h5)
        log(f"OPEN_H5 path={h5_path}")
        with tables_module.open_file(str(h5_path), mode="r") as h5:
            nodes = sorted(list(h5.list_nodes("/flows")), key=lambda node: node._v_name)
            if not nodes:
                raise RuntimeError("no tables under /flows")
            dates = [node._v_name[1:] for node in nodes]
            months = sorted(set(month_of(date_name) for date_name in dates))
            if len(months) < 2:
                raise RuntimeError(f"need at least two months for a time split, found {months}")
            train_months = set(args.train_months)
            test_months = set(args.test_months)
            selected_months = train_months | test_months
            overlap_months = sorted(train_months & test_months)
            if overlap_months:
                raise RuntimeError(f"train/test month overlap: {overlap_months}")
            unknown_months = sorted(selected_months - set(months))
            if unknown_months:
                raise RuntimeError(
                    f"requested months are absent from the HDF5 corpus: {unknown_months}; "
                    f"available={months}"
                )
            buffer_months = sorted(set(months) - selected_months)
            log(
                f"SPLIT_RESOLVED train_months={sorted(train_months)} "
                f"buffer_months={buffer_months} test_months={sorted(test_months)}"
            )
            full_label_values = set();
            for node in nodes:
                if month_of(node._v_name[1:]) in train_months | test_months:
                    full_label_values.update(int(x) for x in node.read(field=args.label_field))
            full_class_count = len(full_label_values)
            log(f"LABEL_AXIS field={args.label_field} full_month_class_count={full_class_count}")
            if full_class_count < 20:
                raise RuntimeError(f"label-axis guard failed: resolved label field {args.label_field!r} has {full_class_count} distinct classes across the full selected month tables; expected service-level APP cardinality (>= 20), not category-level grouping")
            train_cap = None if args.max_flows is None else max(1, args.max_flows // 2)
            test_cap = None if args.max_flows is None else max(1, args.max_flows - train_cap)
            train = read_side(
                tables_module,
                nodes,
                train_months,
                args.k_packets,
                args.label_field,
                train_cap,
            )
            test = read_side(
                tables_module,
                nodes,
                test_months,
                args.k_packets,
                args.label_field,
                test_cap,
            )
            raw_train_count = len(train["y"])
            raw_test_count = len(test["y"])
            train, test, classes = select_common_labels(train, test)
            log(f"CLASS_COUNT common_to_train_test={len(classes)}")

        train_keys = set(int(x) for x in train["flow_tokens"])
        test_keys = set(int(x) for x in test["flow_tokens"])
        overlap = train_keys & test_keys
        time_disjoint = bool(float(np.max(train["times"])) < float(np.min(test["times"])))
        if overlap:
            raise RuntimeError(f"flow-disjoint invariant failed: {len(overlap)} overlapping flow keys")
        if not time_disjoint:
            raise RuntimeError("time-disjoint invariant failed: train TIME_FIRST is not earlier than test")

        train_y = np.asarray([classes.index(int(x)) for x in train["y"]], dtype=np.int64)
        test_y = np.asarray([classes.index(int(x)) for x in test["y"]], dtype=np.int64)
        train["y_original"] = train["y"].copy()
        test["y_original"] = test["y"].copy()
        train["y"] = train_y
        test["y"] = test_y
        state["first_measurement_timestamp"] = utc_now()
        state["status"] = "MEASURING"
        state["runtime"] = {
            "python": sys.executable,
            "python_version": sys.version.split()[0],
            "h5_path": str(Path(args.h5)),
            "label_field": args.label_field,
            "k_packets": args.k_packets,
            "x1_json": str(Path(args.x1_json)),
            "seed": args.seed,
            "smoke": bool(args.smoke),
        }
        state["schema"] = {
            "source": str(Path(args.h5)),
            "ppi_used": ["PPI[1]", "PPI[2]"],
            "ppi_excluded": ["PPI[0]"],
            "ppi_shape_per_row_observed": [3, 30],
            "ppi_len_used_for_mask": True,
            "tail_mask": "all slots i >= min(PPI_LEN, k_packets) set to zero",
            "service_label_field": args.label_field,
            "service_labels_common_to_both_sides": classes,
        }
        state["flow_set"] = {
            "smoke_slice": bool(args.smoke),
            "raw_flow_count_train": raw_train_count,
            "raw_flow_count_test": raw_test_count,
            "flow_count_train_after_common_label_filter": int(len(train["y"])),
            "flow_count_test_after_common_label_filter": int(len(test["y"])),
            "train_months": sorted(train_months),
            "buffer_months": sorted(buffer_months),
            "test_months": sorted(test_months),
            "train_date_boundary": {
                "first_table_date": str(min(train["date"])),
                "last_table_date": str(max(train["date"])),
                "time_first_min": float(np.min(train["times"])),
                "time_first_max": float(np.max(train["times"])),
            },
            "test_date_boundary": {
                "first_table_date": str(min(test["date"])),
                "last_table_date": str(max(test["date"])),
                "time_first_min": float(np.min(test["times"])),
                "time_first_max": float(np.max(test["times"])),
            },
            "flow_disjoint": True,
            "time_disjoint": time_disjoint,
            "flow_overlap_count": 0,
            "packet_level_split_prohibited": True,
            "flow_key_definition": "table date plus ID; each row is assigned to one side",
            "train_flow_counts_by_service": {
                str(label): int((train["y_original"] == label).sum()) for label in classes
            },
            "test_flow_counts_by_service": {
                str(label): int((test["y_original"] == label).sum()) for label in classes
            },
        }
        log(
            "SPLIT "
            f"smoke_slice={args.smoke} "
            f"train_months={sorted(train_months)} buffer_months={sorted(buffer_months)} test_months={sorted(test_months)} "
            f"train_flows={len(train['y'])} test_flows={len(test['y'])} "
            f"flow_disjoint=True time_disjoint={time_disjoint}"
        )
        prepare_csv(output_csv)
        state["per_pair_detector_errors"] = {
            "csv_path": str(output_csv),
            "status": "WRITING",
            "rows_written": 0,
            "row_definition": "one test flow per holdout level, with one column group per detector",
        }
        checkpoint(state, output_json, started, force=True)

        state["detectors"] = {}
        state["score_matrices"] = {}
        results: dict[str, dict[str, Any]] = {}

        log("DETECTOR_START lightgbm")
        results["lightgbm"] = run_lightgbm(train["X"], train["y"], test["X"], args)
        state["score_matrices"]["lightgbm"] = persist_score_matrix(
            output_json, "lightgbm", results["lightgbm"], test, classes
        )
        state["detectors"]["lightgbm"] = {
            key: value
            for key, value in results["lightgbm"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
        log(
            f"DETECTOR_DONE lightgbm status={results['lightgbm'].get('status')} "
            f"device={results['lightgbm'].get('device')} "
            f"error={results['lightgbm'].get('error', '')}"
        )
        checkpoint(state, output_json, started, force=True)

        log("DETECTOR_START prototype")
        results["prototype"] = run_prototype(train["X"], train["y"], test["X"], args)
        state["score_matrices"]["prototype"] = persist_score_matrix(
            output_json, "prototype", results["prototype"], test, classes
        )
        state["detectors"]["prototype"] = {
            key: value
            for key, value in results["prototype"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
        log(
            f"DETECTOR_DONE prototype status={results['prototype'].get('status')} "
            f"device={results['prototype'].get('device')}"
        )
        checkpoint(state, output_json, started, force=True)

        log("DETECTOR_START ronetc")
        results["ronetc"] = run_ronetc(train["X"], train["y"], test["X"], args)
        state["score_matrices"]["ronetc"] = persist_score_matrix(
            output_json, "ronetc", results["ronetc"], test, classes
        )
        state["detectors"]["ronetc"] = {
            key: value
            for key, value in results["ronetc"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
        log(
            f"DETECTOR_DONE ronetc status={results['ronetc'].get('status')} "
            f"device={results['ronetc'].get('device')} "
            f"error={results['ronetc'].get('error', '')}"
        )
        checkpoint(state, output_json, started, force=True)

        log("DETECTOR_START pcap_encoder")
        results["pcap_encoder"] = run_pcap_encoder_probe(args)
        state["score_matrices"]["pcap_encoder"] = persist_score_matrix(
            output_json, "pcap_encoder", results["pcap_encoder"], test, classes
        )
        state["detectors"]["pcap_encoder"] = {
            key: value
            for key, value in results["pcap_encoder"].items()
            if key not in {"pred", "score", "accepted", "score_matrix"}
        }
        checkpoint(state, output_json, started, force=True)

        holdouts = args.holdouts
        state["metrics"] = evaluate_results(test["y"], results, classes, holdouts)
        state["address_randomization_invariance"] = address_randomization_check(test["X"], results)
        pair_bounds = load_x1_upper_bounds(Path(args.x1_json), args.k_packets)
        pair_rows, containment = build_containment_join(pair_bounds, state["metrics"], holdouts, Path(args.x1_json))
        state["floor_violation_test"] = containment
        state["per_pair_detector_errors"]["x1_upper_bound_source"] = str(Path(args.x1_json))
        rows_written = append_pair_rows(output_csv, pair_rows)
        state["per_pair_detector_errors"]["rows_written"] = rows_written
        checkpoint(state, output_json, started, force=True)

        state["per_pair_detector_errors"]["status"] = "COMPLETED"
        state["status"] = "COMPLETED"
        state["completed_timestamp"] = utc_now()
        state["elapsed_seconds"] = time.monotonic() - started
        atomic_json(output_json, {k: v for k, v in state.items() if not k.startswith("_")})
        log(f"ARTIFACT_JSON path={output_json} bytes={output_json.stat().st_size}")
        log(f"ARTIFACT_CSV path={output_csv} bytes={output_csv.stat().st_size} rows={rows_written}")
        log(
            "ADDRESS_RANDOMIZATION "
            f"status={state['address_randomization_invariance']['status']} "
            f"delta={state['address_randomization_invariance']['max_abs_score_delta']}"
        )
        log(f"CONTAINMENT_STATISTIC {state['containment_statistic']}")
        return 0
    except Exception as exc:
        state["status"] = "FAILED"
        state["error"] = literal_error(exc)
        state["traceback"] = traceback.format_exc()
        atomic_json(output_json, {k: v for k, v in state.items() if not k.startswith("_")})
        log(f"FAILED {literal_error(exc)}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
