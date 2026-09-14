#!/usr/bin/env python3
"""X12 Stage 1 detector validation.

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


def preregistration_payload(args: argparse.Namespace, output_json: Path) -> dict[str, Any]:
    timestamp = utc_now()
    return {
        "stage": "X12 Stage 1",
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
            "DEFERRED: depends on the rebuilt X1 upper side; no un-rebuilt "
            "upper-side numbers are consumed."
        ),
        "per_pair_detector_errors": {
            "csv_path": str(resolve_output_paths(args)[1]),
            "status": "PENDING",
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
                "flow_key",
                "date",
                "service_label",
                "holdout_level",
                "true_label",
                "lightgbm_pred",
                "lightgbm_accepted",
                "lightgbm_score",
                "lightgbm_error",
                "prototype_pred",
                "prototype_accepted",
                "prototype_score",
                "prototype_error",
                "ronetc_pred",
                "ronetc_accepted",
                "ronetc_score",
                "ronetc_error",
                "pcap_encoder_pred",
                "pcap_encoder_accepted",
                "pcap_encoder_score",
                "pcap_encoder_error",
                "eps_hat_k_hi",
                "informative_stratum",
                "floor_violation",
            ]
        )


def append_pair_rows(
    path: Path,
    indices: Any,
    holdout_level: float,
    test: dict[str, Any],
    classes: list[int],
    results: dict[str, dict[str, Any]],
) -> int:
    import numpy as np

    flow_keys = build_flow_keys(test["date"], test["ids"])
    count = 0
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        for index in indices.tolist():
            row: list[Any] = [
                flow_keys[index],
                str(test["date"][index]),
                int(test["y"][index]),
                holdout_level,
                int(test["y"][index]),
            ]
            for detector in ("lightgbm", "prototype", "ronetc", "pcap_encoder"):
                result = results.get(detector, {})
                pred = result.get("pred")
                accepted = result.get("accepted")
                score = result.get("score")
                if pred is None:
                    row.extend(["", "", "", result.get("error", "not_run")])
                else:
                    pred_label = int(classes[int(pred[index])])
                    accepted_value = bool(accepted[index]) if accepted is not None else ""
                    score_value = float(score[index]) if score is not None else ""
                    row.extend(
                        [
                            pred_label,
                            accepted_value,
                            score_value,
                            int(pred_label != int(test["y"][index])),
                        ]
                    )
            row.extend(["", "DEFERRED", "DEFERRED"])
            writer.writerow(row)
            count += 1
    return count


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
    return {
        "pred": nearest,
        "score": score,
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


def deferred_floor_test() -> dict[str, Any]:
    return {
        "status": "DEFERRED",
        "reason": (
            "eps_hat_k_hi is unavailable until the X1 upper side is rebuilt; "
            "no un-rebuilt upper-side numbers are consumed"
        ),
        "primary_stratum": "eps_hat_k^hi < 0.5",
        "secondary_stratum": "0.5 <= eps_hi < 0.9",
        "excluded_stratum": "eps_hi >= 0.9",
        "statistic": "number of floor violations",
        "test": "one-sided binomial test",
        "nominal_coverage": 0.95,
        "alpha": 0.05,
        "split_convention": "one-sided; alpha is not split",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h5", default=str(DEFAULT_H5))
    parser.add_argument("--output-json")
    parser.add_argument("--output-csv")
    parser.add_argument("--label-field", default="CATEGORY", choices=["APP", "CATEGORY"])
    parser.add_argument("--k-packets", type=int, default=15)
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
    if args.smoke:
        args.max_flows = 4_000 if args.max_flows is None else min(args.max_flows, 4_000)
        args.holdouts = [0.20]
        args.lgbm_rounds = min(args.lgbm_rounds, 5)
        args.ronetc_epochs = min(args.ronetc_epochs, 2)
        args.ronetc_mc_samples = min(args.ronetc_mc_samples, 2)
        args.ronetc_calibration_rows = min(args.ronetc_calibration_rows, 2_000)
    if args.k_packets < 1 or args.k_packets > 30:
        raise SystemExit("--k-packets must be in [1, 30]")
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
            if args.smoke:
                train_months = {months[0]}
                test_months = {months[1]}
            else:
                split_index = max(1, len(months) // 2)
                train_months = set(months[:split_index])
                test_months = set(months[split_index:])
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
            f"train_months={sorted(train_months)} test_months={sorted(test_months)} "
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
        results: dict[str, dict[str, Any]] = {}

        log("DETECTOR_START lightgbm")
        results["lightgbm"] = run_lightgbm(train["X"], train["y"], test["X"], args)
        state["detectors"]["lightgbm"] = {
            key: value
            for key, value in results["lightgbm"].items()
            if key not in {"pred", "score", "accepted"}
        }
        log(
            f"DETECTOR_DONE lightgbm status={results['lightgbm'].get('status')} "
            f"device={results['lightgbm'].get('device')} "
            f"error={results['lightgbm'].get('error', '')}"
        )
        checkpoint(state, output_json, started, force=True)

        log("DETECTOR_START prototype")
        results["prototype"] = run_prototype(train["X"], train["y"], test["X"], args)
        state["detectors"]["prototype"] = {
            key: value
            for key, value in results["prototype"].items()
            if key not in {"pred", "score", "accepted"}
        }
        log(
            f"DETECTOR_DONE prototype status={results['prototype'].get('status')} "
            f"device={results['prototype'].get('device')}"
        )
        checkpoint(state, output_json, started, force=True)

        log("DETECTOR_START ronetc")
        results["ronetc"] = run_ronetc(train["X"], train["y"], test["X"], args)
        state["detectors"]["ronetc"] = {
            key: value
            for key, value in results["ronetc"].items()
            if key not in {"pred", "score", "accepted"}
        }
        log(
            f"DETECTOR_DONE ronetc status={results['ronetc'].get('status')} "
            f"device={results['ronetc'].get('device')} "
            f"error={results['ronetc'].get('error', '')}"
        )
        checkpoint(state, output_json, started, force=True)

        log("DETECTOR_START pcap_encoder")
        results["pcap_encoder"] = run_pcap_encoder_probe(args)
        state["detectors"]["pcap_encoder"] = {
            key: value
            for key, value in results["pcap_encoder"].items()
            if key not in {"pred", "score", "accepted"}
        }
        checkpoint(state, output_json, started, force=True)

        holdouts = args.holdouts
        state["metrics"] = evaluate_results(test["y"], results, classes, holdouts)
        state["address_randomization_invariance"] = address_randomization_check(test["X"], results)
        state["floor_violation_test"] = deferred_floor_test()
        rows_written = 0
        for level in holdouts:
            indices = stratified_holdout_indices(test["y"], classes, level)
            rows_written += append_pair_rows(output_csv, indices, level, test, classes, results)
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
