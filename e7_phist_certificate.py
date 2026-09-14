#!/usr/bin/env python3
"""E7: fixed-alphabet PHIST two-sided certificate readout."""

import hashlib
import itertools
import json
import math
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import tables

sys.path.insert(0, "/root/eibo/src")
from eibo.statcore import tv_lower_bound


H5_PATH = "/root/autodl-tmp/eibo/data/CESNET-QUICEXT-25-XS.complete.h5"
OUT_PATH = "/root/eibo/artifacts/q2_phist_certificate_v2.json"
PREVIOUS_OUT_PATH = "/root/eibo/artifacts/q2_phist_certificate.json"
STATE_PATH = "/root/autodl-tmp/eibo/q2_phist_certificate_v2_state.pkl"
EXPECTED_SHA256 = "6b323c4c53b7c9d0ec9011f895b3c5ba6b35247576e41ef19fe84ab8632810ab"
PHIST_FIELDS = (
    "PHIST_SRC_SIZES",
    "PHIST_DST_SIZES",
    "PHIST_SRC_IPT",
    "PHIST_DST_IPT",
)
M = 32
ALPHA = 0.05
ALPHA_LAW = ALPHA / 2.0
BATCH_SIZE = 100_000
SERVICE_THRESHOLD = 2_000
SAMPLE_CAP = 20_000
SAMPLE_SEED = 20260913
PAIR_CHUNK = 10


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(16 * 1024 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def _atomic_pickle_dump(value, path):
    temporary = path + ".tmp"
    with open(temporary, "wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(temporary, path)


def _reservoir_update(reservoirs, seen, label, values, cap, rng):
    """Uniformly retain at most cap rows for one service in stream order."""
    label = int(label)
    chunk = np.asarray(values, dtype=np.float64)
    old_seen = int(seen.get(label, 0))
    new_seen = old_seen + len(chunk)
    if label not in reservoirs:
        reservoirs[label] = np.empty((cap, M), dtype=np.float64)
    reservoir = reservoirs[label]
    fill = min(max(cap - old_seen, 0), len(chunk))
    if fill:
        reservoir[old_seen:old_seen + fill] = chunk[:fill]
    remainder_start = fill
    if remainder_start < len(chunk):
        positions = np.arange(old_seen + remainder_start + 1, new_seen + 1, dtype=np.int64)
        destinations = rng.integers(0, positions, size=len(positions), dtype=np.int64)
        keep = destinations < cap
        if np.any(keep):
            reservoir[destinations[keep]] = chunk[remainder_start:][keep]
    seen[label] = new_seen


def _scan_h5():
    if not os.path.isfile(H5_PATH):
        raise SystemExit(f"missing H5: {H5_PATH}")

    h5_sha256 = sha256_file(H5_PATH)
    print(f"h5_path={H5_PATH}")
    print(f"h5_sha256={h5_sha256}")
    if h5_sha256 != EXPECTED_SHA256:
        raise SystemExit(
            f"H5 checksum mismatch: expected {EXPECTED_SHA256}, got {h5_sha256}"
        )

    with tables.open_file(H5_PATH, mode="r") as h5:
        tables_found = []
        for node in h5.walk_nodes("/flows", classname="Table"):
            if "APP" in node.colnames:
                tables_found.append(node)
        if not tables_found:
            raise SystemExit("no /flows table with APP found")

        missing = []
        schema = {}
        for node in tables_found:
            for field in PHIST_FIELDS:
                if field not in node.colnames:
                    missing.append(f"{node._v_pathname}:{field}")
                else:
                    schema.setdefault(
                        field,
                        {"dtype": str(node.coldtypes[field]), "shape": list(node.coldtypes[field].shape)},
                    )
        if missing:
            print("actual_schema_missing=" + json.dumps(missing))
            raise SystemExit("required PHIST fields missing; stopped")
        print("phist_schema=" + json.dumps(schema, sort_keys=True))

        sums = {}
        counts = {}
        reservoirs = {}
        sampled_seen = {}
        rng = np.random.default_rng(SAMPLE_SEED)
        zero_vector_rows = 0
        total_rows = 0
        for node in tables_found:
            columns = list(PHIST_FIELDS) + ["APP"]
            for start in range(0, int(node.nrows), BATCH_SIZE):
                stop = min(start + BATCH_SIZE, int(node.nrows))
                # Read one bounded chunk so the H5 remains read-only and peak memory
                # is bounded by the PHIST fields for one batch.
                fields = {
                    field: node.read(start=start, stop=stop, field=field)
                    for field in columns
                }
                app = np.asarray(fields["APP"], dtype=np.int64)
                values = np.stack(
                    [np.asarray(fields[field], dtype=np.float64) for field in PHIST_FIELDS],
                    axis=1,
                ).reshape(len(app), M)
                flow_totals = values.sum(axis=1)
                zero_vector_rows += int(np.count_nonzero(flow_totals <= 0))
                valid = flow_totals > 0
                if not np.all(valid):
                    values = values[valid]
                    app = app[valid]
                    flow_totals = flow_totals[valid]
                if len(app) == 0:
                    continue
                values /= flow_totals[:, None]
                labels, inverse = np.unique(app, return_inverse=True)
                for index, label in enumerate(labels):
                    mask = inverse == index
                    label = int(label)
                    sums[label] = sums.get(label, np.zeros(M, dtype=np.float64)) + values[mask].sum(axis=0)
                    counts[label] = counts.get(label, 0) + int(mask.sum())
                    _reservoir_update(reservoirs, sampled_seen, label, values[mask], SAMPLE_CAP, rng)
                total_rows += len(app)

        if not counts:
            raise SystemExit("no valid APP-labeled PHIST rows")

        labels = sorted(counts)
        distributions = {label: sums[label] / counts[label] for label in labels}
        radius_constant = math.sqrt(M) + math.sqrt(2.0 * math.log(2.0 / ALPHA_LAW))

        thresholded_labels = [label for label in labels if counts[label] >= SERVICE_THRESHOLD]
        rows = []
        for a, b in itertools.combinations(thresholded_labels, 2):
            n_a = counts[a]
            n_b = counts[b]
            tv_hat = 0.5 * float(np.abs(distributions[a] - distributions[b]).sum())
            radius_a = radius_constant / math.sqrt(n_a)
            radius_b = radius_constant / math.sqrt(n_b)
            eps_hi = tv_hat + radius_a + radius_b
            rows.append(
                {
                    "service_a": a,
                    "service_b": b,
                    "n_a": n_a,
                    "n_b": n_b,
                    "tv_hat": tv_hat,
                    "eps_lo": None,
                    "eps_hi": eps_hi,
                    "eps_hi_raw": eps_hi,
                    "eps_hi_raw_gt_one": bool(eps_hi > 1.0),
                    "certificate_lost_raw_eps_hi_gt_one": bool(eps_hi > 1.0),
                    "eps_hi_below_half": bool(eps_hi < 0.5),
                    "bracket_nonempty": None,
                    "lower_side_status": "pending",
                    "pair_flow_count": n_a + n_b,
                    "radius_a": radius_a,
                    "radius_b": radius_b,
                }
            )

        service_counts = np.asarray([counts[label] for label in thresholded_labels], dtype=np.int64)
        thresholds = {
            "m32_eps010_rough": 3200,
            "joint95_eps010_rough": 7400,
        }
        aggregate = {
            "service_count": len(thresholded_labels),
            "pair_count": len(rows),
            "flow_count_min": int(service_counts.min()),
            "flow_count_median": float(np.median(service_counts)),
            "flow_count_max": int(service_counts.max()),
            "services_reaching_m32_eps010_rough": int(np.count_nonzero(service_counts >= thresholds["m32_eps010_rough"])),
            "services_reaching_joint95_eps010_rough": int(np.count_nonzero(service_counts >= thresholds["joint95_eps010_rough"])),
            "fraction_bracket_nonempty": None,
            "fraction_eps_hi_below_half": (
                float(np.mean([row["eps_hi_below_half"] for row in rows])) if rows else None
            ),
            "pairs_tv_hat_above_pair_zero_tv_radius": int(
                sum(row["tv_hat"] > row["radius_a"] + row["radius_b"] for row in rows)
            ),
            "fraction_pairs_tv_hat_above_pair_zero_tv_radius": (
                float(
                    np.mean(
                        [
                            row["tv_hat"] > row["radius_a"] + row["radius_b"]
                            for row in rows
                        ]
                    )
                )
                if rows
                else None
            ),
            "pairs_eps_hi_raw_gt_one": int(
                sum(row["certificate_lost_raw_eps_hi_gt_one"] for row in rows)
            ),
            "fraction_eps_hi_raw_gt_one": (
                float(np.mean([row["certificate_lost_raw_eps_hi_gt_one"] for row in rows]))
                if rows
                else None
            ),
            "bracket_fraction_status": "pending until classifier lower side is computed",
        }
        result = {
            "experiment": "E7",
            "question": "Can the rectified PHIST object yield a non-empty two-sided certificate on the XS H5?",
            "h5_path": H5_PATH,
            "h5_sha256": h5_sha256,
            "total_valid_rows": total_rows,
            "zero_vector_rows": zero_vector_rows,
            "sampling_unit": "flow",
            "preprocessing": (
                "For each flow, concatenate the four separate 8-bin marginal histograms "
                "into a 32-vector and normalize that vector to sum to 1; pool flows within "
                "each APP service by averaging the normalized vectors."
            ),
            "certified_object": (
                "Concatenation of PHIST_SRC_SIZES, PHIST_DST_SIZES, PHIST_SRC_IPT, "
                "PHIST_DST_IPT; four separate marginal histograms, 32 coordinates total; "
                "not a joint 8x8x2 object."
            ),
            "schema": schema,
            "alphabet": {
                "m": M,
                "a_priori_fixed": True,
                "unobserved_cells_retained": True,
                "bin_edges": "[0,16), [16,32), [32,64), [64,128), [128,256), [256,512), [512,1024), [1024,inf)",
                "binning_rule": "value < 16 -> bin 1; value > 1023 -> bin 8",
            },
            "confidence": {
                "alpha_overall": ALPHA,
                "alpha_law": ALPHA_LAW,
                "split_convention": "two laws, alpha/2 = 0.025 per law; radius uses sqrt(2*log(2/alpha_law)) = sqrt(2*log(80))",
                "radius_constant": radius_constant,
                "upper_side_guarantee": "finite-sample, distribution-free plug-in UCB",
                "lower_side_guarantee": "asymptotic HPLB estimate, not an exact finite-sample certificate",
            },
            "upper_side_formula": "eps_hi = tv_hat + radius_a + radius_b; radius_i = (sqrt(m) + sqrt(2*log(2/alpha_law))) / sqrt(n_i)",
            "lower_side": {
                "status": "pending",
                "method": "michel",
                "alpha_passed": ALPHA_LAW,
                "alpha_internal_binomial_witness": "alpha/3 inside tv_lower_bound; no additional split applied",
                "guarantee": "asymptotic HPLB estimate, not an exact finite-sample certificate",
                "sample_cap_per_service": SAMPLE_CAP,
                "sample_seed": SAMPLE_SEED,
                "input_unit": "per-flow feature matrix, one row per normalized 32-vector",
            },
            "aggregate": aggregate,
            "service_flow_counts": {str(label): int(counts[label]) for label in labels},
            "rows": rows,
            "top_pairs_sort": "descending n_a + n_b (pair_flow_count)",
            "sanity_check": "Upper eps_hi is raw and never clipped; eps_hi > 1 is flagged as certificate-lost.",
            "threshold": {
                "flow_count_per_service": SERVICE_THRESHOLD,
                "rule": "retain services with n >= 2000 for pairwise analysis",
                "services_at_no_threshold": len(labels),
                "pairs_at_no_threshold": len(list(itertools.combinations(labels, 2))),
            },
            "routine_execution_report": [
                {"routine": "/root/eibo/e7_phist_certificate.py:sha256_file", "executed": True, "output_consumed_by_reported_numbers": True, "purpose": "H5 and JSON SHA-256 verification"},
                {"routine": "/root/eibo/e7_phist_certificate.py:_scan_h5", "executed": True, "output_consumed_by_reported_numbers": True, "purpose": "read-only H5 schema, counts, normalized per-flow vectors, and tv_hat/eps_hi"},
                {"routine": "/root/eibo/e7_phist_certificate.py:_reservoir_update", "executed": True, "output_consumed_by_reported_numbers": True, "purpose": "fixed-seed per-service raw-flow subsamples for lower-side fitting"},
                {"routine": "/root/eibo/src/eibo/statcore.py:599 tv_lower_bound", "executed": True, "output_consumed_by_reported_numbers": True, "purpose": "Michel asymptotic HPLB lower-side estimate"},
                {"routine": "/root/eibo/e7_phist_certificate.py:main", "executed": True, "output_consumed_by_reported_numbers": True, "purpose": "pair aggregation, JSON serialization, and report printout"},
            ],
        }
        state = {
            "h5_sha256": h5_sha256,
            "schema": schema,
            "total_valid_rows": total_rows,
            "zero_vector_rows": zero_vector_rows,
            "labels": labels,
            "thresholded_labels": thresholded_labels,
            "counts": counts,
            "distributions": distributions,
            "reservoirs": {label: reservoirs[label][:min(counts[label], SAMPLE_CAP)] for label in labels},
            "result": result,
            "rows": rows,
            "scan_complete": True,
        }
    Path(STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    _atomic_pickle_dump(state, STATE_PATH)
    return state


def _safe_lower_diagnostics(diagnostics):
    return {key: value for key, value in diagnostics.items() if key != "classifier"}


def _finish_result(state):
    result = state["result"]
    rows = state["rows"]
    done = [row for row in rows if row["lower_side_status"] == "computed"]
    pending = [row for row in rows if row["lower_side_status"] != "computed"]
    result["rows"] = rows
    result["lower_side"]["status"] = "computed" if not pending else "in_progress"
    result["aggregate"]["bracket_fraction_status"] = (
        "computed" if not pending else "in progress; aggregate covers completed pairs only"
    )
    result["aggregate"]["fraction_bracket_nonempty"] = (
        float(np.mean([row["bracket_nonempty"] for row in done])) if done else None
    )
    result["aggregate"]["fraction_eps_lo_positive"] = (
        float(np.mean([row["eps_lo"] > 0 for row in done])) if done else None
    )
    result["aggregate"]["pairs_eps_lo_positive"] = int(sum(row["eps_lo"] > 0 for row in done))
    result["aggregate"]["pairs_eps_lo_positive_and_eps_hi_below_half"] = int(
        sum(row["eps_lo"] > 0 and row["eps_hi_below_half"] for row in done)
    )
    result["aggregate"]["fraction_eps_lo_positive_and_eps_hi_below_half"] = (
        float(np.mean([row["eps_lo"] > 0 and row["eps_hi_below_half"] for row in done])) if done else None
    )
    if done:
        values = np.asarray([row["eps_lo"] for row in done], dtype=float)
        quantiles = np.quantile(values, [0.0, 0.05, 0.25, 0.5, 0.75, 0.95, 1.0])
        result["eps_lo_distribution"] = {
            "min": float(quantiles[0]), "q5": float(quantiles[1]), "q25": float(quantiles[2]),
            "median": float(quantiles[3]), "q75": float(quantiles[4]), "q95": float(quantiles[5]),
            "max": float(quantiles[6]),
        }
    previous_rows = []
    if os.path.isfile(PREVIOUS_OUT_PATH):
        with open(PREVIOUS_OUT_PATH, "r", encoding="utf-8") as handle:
            previous_rows = json.load(handle).get("rows", [])
    previous_by_pair = {
        (int(row["service_a"]), int(row["service_b"])): row for row in previous_rows
    }
    matched_previous = [
        row for row in rows
        if (int(row["service_a"]), int(row["service_b"])) in previous_by_pair
    ]
    changed = sum(
        previous_by_pair[(int(row["service_a"]), int(row["service_b"]))].get("lower_side_status") == "not_computed"
        for row in matched_previous
        if row["lower_side_status"] == "computed"
    )
    result["previous_run_comparison"] = {
        "path": PREVIOUS_OUT_PATH,
        "previous_row_count": len(previous_rows),
        "previous_not_computed_row_count": sum(
            row.get("lower_side_status") == "not_computed" for row in previous_rows
        ),
        "current_pairs_matching_previous": len(matched_previous),
        "current_pairs_changed_from_previous_not_computed": int(changed),
        "previous_rows_excluded_by_current_threshold": len(previous_rows) - len(matched_previous),
    }
    result["aggregate"]["pairs_changed_from_previous_not_computed"] = int(changed)
    result["aggregate"]["pairs_remaining_not_computed"] = len(pending)
    return result


def _write_result(result):
    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    temporary = OUT_PATH + ".tmp"
    with open(temporary, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True, default=json_default)
        handle.write("\n")
    os.replace(temporary, OUT_PATH)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-pairs", type=int, default=PAIR_CHUNK)
    args = parser.parse_args()
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "rb") as handle:
            state = pickle.load(handle)
        if state.get("h5_sha256") != EXPECTED_SHA256 or not state.get("scan_complete"):
            state = _scan_h5()
    else:
        state = _scan_h5()

    rows = state["rows"]
    reservoirs = state["reservoirs"]
    processed = 0
    for row in rows:
        if row["lower_side_status"] == "computed":
            continue
        if processed >= args.max_pairs:
            break
        a, b = int(row["service_a"]), int(row["service_b"])
        X1 = reservoirs[a]
        X2 = reservoirs[b]
        eps_lo, diagnostics = tv_lower_bound(X1, X2, alpha=ALPHA_LAW, method="michel")
        row["eps_lo"] = float(eps_lo)
        row["bracket_nonempty"] = bool(row["eps_lo"] < row["eps_hi"])
        row["lower_side_status"] = "computed"
        row["lower_side_guarantee"] = "asymptotic HPLB estimate; not an exact finite-sample certificate"
        row["lower_n_a"] = int(len(X1))
        row["lower_n_b"] = int(len(X2))
        row["lower_diagnostics"] = _safe_lower_diagnostics(diagnostics)
        processed += 1
        if processed % 5 == 0:
            _atomic_pickle_dump(state, STATE_PATH)
            print(f"progress computed_lower_pairs={processed}")

    _atomic_pickle_dump(state, STATE_PATH)
    result = _finish_result(state)
    if result["lower_side"]["status"] == "computed":
        _write_result(result)

    if not os.path.exists(OUT_PATH):
        print(f"progress_total_pairs={len(rows)} computed={len(rows) - len([row for row in rows if row['lower_side_status'] != 'computed'])} remaining={len([row for row in rows if row['lower_side_status'] != 'computed'])}")
        return
    artifact_sha256 = sha256_file(OUT_PATH)
    artifact_size = os.path.getsize(OUT_PATH)
    print(f"json_path={OUT_PATH}")
    print(f"json_bytes={artifact_size}")
    print(f"json_sha256={artifact_sha256}")
    print(f"row_count={len(rows)}")
    print("aggregate=" + json.dumps(result["aggregate"], sort_keys=True))
    print("eps_lo_distribution=" + json.dumps(result.get("eps_lo_distribution"), sort_keys=True))
    print("top15_pairs_by_n_a_plus_n_b")
    print("service_a\tservice_b\tn_a\tn_b\tpair_flow_count\ttv_hat\teps_lo\teps_hi")
    for row in sorted(rows, key=lambda item: (-item["pair_flow_count"], item["service_a"], item["service_b"]))[:15]:
        print(
            f"{row['service_a']}\t{row['service_b']}\t{row['n_a']}\t{row['n_b']}\t"
            f"{row['pair_flow_count']}\t{row['tv_hat']:.8f}\t{row['eps_lo']:.8f}\t{row['eps_hi']:.8f}"
        )
    print("json_parse_check=" + str(json.load(open(OUT_PATH, "r", encoding="utf-8")) is not None))


if __name__ == "__main__":
    main()
