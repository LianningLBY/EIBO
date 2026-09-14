#!/root/miniconda3/bin/python3
"""X3 estimator-family variant with a pre-registered known-truth gate.

This runner consumes only the cached direction codes and cached synthetic
control state. It never opens or scans the H5 file.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

import x3_controls as base


PROJECT = Path("/root/eibo")
CACHE_DIR = Path("/dev/shm/eibo_x3_chain_rule")
MERGED_PATH = CACHE_DIR / "merged.pkl"
RESULTS_PATH = CACHE_DIR / "results.pkl"
LEDGER_PATH = CACHE_DIR / "ledger.json"
PAIR_PATH = PROJECT / "artifacts" / "q1_eps_lo_symbol_map.json"
OUT_PATH = PROJECT / "artifacts" / "x3_variant_a_estimator_family.json"
OLD_ARTIFACT = PROJECT / "artifacts" / "x3_chain_rule_divergence.json"
RUNNER_PATH = PROJECT / "x3_variant_a_estimator_family.py"

K_VALUES = list(range(5, 31))
MIN_SERVICE_FLOWS = 2000
SEED = 20260914
LAPLACE_ALPHA = 1.0
EXPECTED_PARTS = 360

CRITERIA_QUOTE = (
    "A curve is recovered as LINEAR iff the fitted power exponent satisfies "
    "p > 0.95, the AIC advantage of linear over sqrt is > 6, and the "
    "first-to-last median increment ratio is <= 1.10. The known-truth gate "
    "passes iff BOTH the plain-iid arm and the real-occupancy twin arm are "
    "LINEAR under all three criteria. Real data may be evaluated only after "
    "this two-arm gate passes."
)

ESTIMATOR_SENTENCE = (
    "At each prefix position and observed context, estimate both binary "
    "conditionals with Laplace alpha=1 smoothing, apply a two-sample "
    "delete-one jackknife bias correction to each directed conditional KL, "
    "project corrected directed contributions to the nonnegative half-line, "
    "weight P-to-Q terms by empirical P context frequency and Q-to-P terms "
    "by empirical Q context frequency, and sum over positions."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def cache_inventory() -> dict:
    required = [LEDGER_PATH, MERGED_PATH, RESULTS_PATH]
    parts = sorted(CACHE_DIR.glob("part_*.npz")) if CACHE_DIR.exists() else []
    present = CACHE_DIR.exists() and all(path.is_file() for path in required) and len(parts) == EXPECTED_PARTS
    sizes = {str(path): path.stat().st_size for path in required if path.is_file()}
    sizes.update({"part_*.npz": sum(path.stat().st_size for path in parts)})
    return {
        "cache_dir": str(CACHE_DIR),
        "present": bool(present),
        "required_files": [str(path) for path in required],
        "parts_pattern": str(CACHE_DIR / "part_*.npz"),
        "parts_count": len(parts),
        "expected_parts_count": EXPECTED_PARTS,
        "bytes_by_group": sizes,
        "bytes_total_required_groups": int(sum(sizes.values())),
        "h5_scan_performed": False,
        "cost_estimate": (
            "No H5 read. The run operates on one 50 MB merged code/lens cache, "
            "one 0.4 MB cached-results file for provenance, and 360 cached NPZ "
            "parts totaling about 70 MB; computation is CPU-only over 26 k values and the cached "
            "service/pair sufficient statistics."
        ),
    }


def load_merged_only() -> dict:
    import pickle

    with MERGED_PATH.open("rb") as handle:
        return pickle.load(handle)


def _kl_directed(p0: np.ndarray, p1: np.ndarray, q0: np.ndarray, q1: np.ndarray) -> np.ndarray:
    alpha = LAPLACE_ALPHA
    np_ctx = p0 + p1
    nq_ctx = q0 + q1
    pp0 = (p0 + alpha) / (np_ctx + 2.0 * alpha)
    pp1 = (p1 + alpha) / (np_ctx + 2.0 * alpha)
    qq0 = (q0 + alpha) / (nq_ctx + 2.0 * alpha)
    qq1 = (q1 + alpha) / (nq_ctx + 2.0 * alpha)
    return pp0 * np.log(pp0 / qq0) + pp1 * np.log(pp1 / qq1)


def _jackknife_directed(
    p0: np.ndarray,
    p1: np.ndarray,
    q0: np.ndarray,
    q1: np.ndarray,
) -> np.ndarray:
    """Two-sample delete-one jackknife for a directed binary conditional KL."""
    full = _kl_directed(p0, p1, q0, q1)
    np_ctx = p0 + p1
    nq_ctx = q0 + q1

    p0_minus = _kl_directed(np.maximum(p0 - 1.0, 0.0), p1, q0, q1)
    p1_minus = _kl_directed(p0, np.maximum(p1 - 1.0, 0.0), q0, q1)
    mean_delete_p = np.divide(
        p0 * p0_minus + p1 * p1_minus,
        np_ctx,
        out=np.zeros_like(full),
        where=np_ctx > 0,
    )

    q0_minus = _kl_directed(p0, p1, np.maximum(q0 - 1.0, 0.0), q1)
    q1_minus = _kl_directed(p0, p1, q0, np.maximum(q1 - 1.0, 0.0))
    mean_delete_q = np.divide(
        q0 * q0_minus + q1 * q1_minus,
        nq_ctx,
        out=np.zeros_like(full),
        where=nq_ctx > 0,
    )

    correction_p = np.where(np_ctx > 1.0, (np_ctx - 1.0) * (full - mean_delete_p), 0.0)
    correction_q = np.where(nq_ctx > 1.0, (nq_ctx - 1.0) * (full - mean_delete_q), 0.0)
    return np.maximum(full + correction_p + correction_q, 0.0)


def variant_chain_prefixes(counts_p: list[dict], counts_q: list[dict]) -> dict[int, float]:
    d_pq = 0.0
    d_qp = 0.0
    out: dict[int, float] = {}
    for position, (cp, cq) in enumerate(zip(counts_p, counts_q), start=1):
        contexts = np.union1d(
            np.union1d(cp["ctx0"], cp["ctx1"]),
            np.union1d(cq["ctx0"], cq["ctx1"]),
        )
        n_p_total = float(cp["n"])
        n_q_total = float(cq["n"])
        if contexts.size and n_p_total > 0 and n_q_total > 0:
            p0 = base.take_counts(contexts, cp["ctx0"], cp["cnt0"])
            p1 = base.take_counts(contexts, cp["ctx1"], cp["cnt1"])
            q0 = base.take_counts(contexts, cq["ctx0"], cq["cnt0"])
            q1 = base.take_counts(contexts, cq["ctx1"], cq["cnt1"])
            np_ctx = p0 + p1
            nq_ctx = q0 + q1
            corrected_pq = _jackknife_directed(p0, p1, q0, q1)
            corrected_qp = _jackknife_directed(q0, q1, p0, p1)
            d_pq += float(np.sum((np_ctx / n_p_total) * corrected_pq, where=np_ctx > 0))
            d_qp += float(np.sum((nq_ctx / n_q_total) * corrected_qp, where=nq_ctx > 0))
        if position >= 5:
            out[position] = 0.5 * (d_pq + d_qp)
    return out


def fit_linear_criteria(curve: list[dict]) -> dict:
    fit = base.fit_growth(curve)
    checks = {
        "power_exponent_p_gt_0.95": float(fit["power"]["exponent_p"]) > 0.95,
        "linear_aic_advantage_over_sqrt_gt_6": float(
            fit["linear_model_aic_advantage_over_sqrt"]
        )
        > 6.0,
        "first_to_last_median_increment_ratio_le_1.10": float(
            fit["first_to_last_median_increment_ratio"]
        )
        <= 1.10,
    }
    return {
        "fit": fit,
        "criteria": checks,
        "linear": bool(all(checks.values())),
    }


def deciding_metrics(assessment: dict) -> dict:
    fit = assessment["fit"]
    return {
        "power_exponent_p": float(fit["power"]["exponent_p"]),
        "linear_aic_advantage_over_sqrt": float(
            fit["linear_model_aic_advantage_over_sqrt"]
        ),
        "first_to_last_median_increment_ratio": float(
            fit["first_to_last_median_increment_ratio"]
        ),
        "criteria": assessment["criteria"],
        "linear": bool(assessment["linear"]),
    }


def curve_from_pair_counts(pair_rows: list[dict], counts_by_service: dict[int, list[dict]]) -> dict:
    per_pair: dict[str, float] = {}
    service_ns = {service: base.fast_service_n(counts) for service, counts in counts_by_service.items()}
    for row in pair_rows:
        service_a = int(row["service_a"])
        service_b = int(row["service_b"])
        if (
            service_ns.get(service_a, 0) >= MIN_SERVICE_FLOWS
            and service_ns.get(service_b, 0) >= MIN_SERVICE_FLOWS
        ):
            prefixes = variant_chain_prefixes(counts_by_service[service_a], counts_by_service[service_b])
            key = base.pair_key(service_a, service_b)
            for k, value in prefixes.items():
                per_pair.setdefault(str(k), {})
                per_pair[str(k)][key] = value
    curve = []
    for k in K_VALUES:
        values = np.asarray(list(per_pair[str(k)].values()), dtype=float)
        curve.append(
            {
                "k": k,
                "n_pairs": int(values.size),
                "D_k_median": float(np.median(values)) if values.size else None,
                "D_k_mean": float(np.mean(values)) if values.size else None,
                "denominator": "variable PPI_LEN >= k pair set",
                "per_pair": per_pair[str(k)],
            }
        )
    return {"curve": curve}


def curve_one_k(pair_rows: list[dict], counts_by_service: dict[int, list[dict]], k: int) -> dict:
    values = []
    per_pair = {}
    service_ns = {service: base.fast_service_n(counts) for service, counts in counts_by_service.items()}
    for row in pair_rows:
        service_a = int(row["service_a"])
        service_b = int(row["service_b"])
        if (
            service_ns.get(service_a, 0) >= MIN_SERVICE_FLOWS
            and service_ns.get(service_b, 0) >= MIN_SERVICE_FLOWS
        ):
            value = variant_chain_prefixes(counts_by_service[service_a], counts_by_service[service_b])[k]
            per_pair[base.pair_key(service_a, service_b)] = value
            values.append(value)
    arr = np.asarray(values, dtype=float)
    return {
        "k": k,
        "n_pairs": int(arr.size),
        "D_k_median": float(np.median(arr)) if arr.size else None,
        "D_k_mean": float(np.mean(arr)) if arr.size else None,
        "denominator": "variable PPI_LEN >= k pair set",
        "per_pair": per_pair,
    }


def plain_iid_control(merged: dict, p: float, q: float, per_pos: float) -> dict:
    bits_p, bits_q = base.synthetic_plain_cache(SEED)
    lens = np.full(bits_p.shape[0], 30, dtype=np.uint8)
    codes_p = base.codes_from_bits(bits_p)
    codes_q = base.codes_from_bits(bits_q)
    curve = []
    for k in K_VALUES:
        counts_p = base.service_counts_fast_from_codes(codes_p, lens, k)
        counts_q = base.service_counts_fast_from_codes(codes_q, lens, k)
        value = variant_chain_prefixes(counts_p, counts_q)[k]
        curve.append(
            {
                "k": k,
                "D_k_median": float(value),
                "D_k_mean": float(value),
                "D_k_true": float(k * per_pos),
                "D_k_estimated_over_true": float(value / (k * per_pos)),
                "n_a": int(lens.size),
                "n_b": int(lens.size),
            }
        )
    return {"curve": curve, "assessment": fit_linear_criteria(curve)}


def twin_control(merged: dict, p: float, q: float, per_pos: float) -> dict:
    services = list(map(int, merged["services"]))
    service_a, service_b = services[0], services[1]
    rng = np.random.default_rng(SEED + 1000003)
    curve = []
    occupancy_checks = {}
    for k in K_VALUES:
        real_a = base.service_counts_fast_from_codes(
            merged["by_service"][service_a]["codes"],
            merged["by_service"][service_a]["lens"],
            k,
        )
        real_b = base.service_counts_fast_from_codes(
            merged["by_service"][service_b]["codes"],
            merged["by_service"][service_b]["lens"],
            k,
        )
        counts_p = base.synthetic_counts_on_real_prefix_occupancy(merged, service_a, k, p, rng)
        counts_q = base.synthetic_counts_on_real_prefix_occupancy(merged, service_b, k, q, rng)
        value = variant_chain_prefixes(counts_p, counts_q)[k]
        curve.append(
            {
                "k": k,
                "D_k_median": float(value),
                "D_k_mean": float(value),
                "D_k_true": float(k * per_pos),
                "D_k_estimated_over_true": float(value / (k * per_pos)),
                "n_a": int(real_a[0]["n"]) if real_a else 0,
                "n_b": int(real_b[0]["n"]) if real_b else 0,
            }
        )
        if k in (5, 10, 20, 30):
            occupancy_checks[str(k)] = {
                "service_a_matches_real_prefix_occupancy": base.occupancy_signature(real_a)
                == base.occupancy_signature(counts_p),
                "service_b_matches_real_prefix_occupancy": base.occupancy_signature(real_b)
                == base.occupancy_signature(counts_q),
            }
    return {
        "services": [service_a, service_b],
        "curve": curve,
        "assessment": fit_linear_criteria(curve),
        "occupancy_match_checks": occupancy_checks,
    }


def make_base_payload(cache: dict, old_hash_before: str | None) -> dict:
    return {
        "gate": {
            "pre_registered_criteria": [CRITERIA_QUOTE],
            "analytic_truth": {
                "p": 0.30,
                "q": 0.70,
                "natural_log_symmetric_bernoulli_kl": True,
                "analytic_per_position_constant": 0.3389191441548814,
                "analytic_line": "D_k = k * 0.3389191441548814",
            },
            "control_execution_order": (
                "The plain-iid and real-occupancy twin controls are evaluated and "
                "reported before any real-data curve or real-data fit is computed."
            ),
            "cache_and_cost": cache,
            "plain_iid": None,
            "twin_real_occupancy": None,
            "old_artifact_sha256_before": old_hash_before,
        },
        "estimator_sentence": ESTIMATOR_SENTENCE,
    }


def run() -> int:
    cache = cache_inventory()
    old_hash_before = sha256_file(OLD_ARTIFACT) if OLD_ARTIFACT.is_file() else None
    payload = make_base_payload(cache, old_hash_before)
    print("CACHE_INVENTORY", json.dumps(cache, sort_keys=True))

    if not cache["present"]:
        message = (
            "Required cached state is unavailable: expected ledger.json, merged.pkl, "
            f"results.pkl, and exactly {EXPECTED_PARTS} part_*.npz files under {CACHE_DIR}. "
            "The runner did not rescan the H5."
        )
        payload["gate_outcome"] = {"status": "FAIL", "deciding_numbers": {"cache_present": False}}
        payload["if_failed"] = {
            "statement": message,
            "real_data_touched": False,
            "literal_blocker": message,
        }
        atomic_write_json(OUT_PATH, payload)
        print("GATE_OUTCOME", json.dumps(payload["gate_outcome"], sort_keys=True))
        print("FAILURE", message)
        return 2

    merged = load_merged_only()
    params = base.synthetic_params(SEED)
    p = float(params["p"])
    q = float(params["q"])
    per_pos = float(params["analytic_per_position_constant"])
    if abs(per_pos - 0.3389191441548814) > 1e-15:
        raise RuntimeError(
            "analytic per-position constant mismatch: "
            f"computed {per_pos!r} != registered 0.3389191441548814"
        )

    plain = plain_iid_control(merged, p, q, per_pos)
    twin = twin_control(merged, p, q, per_pos)
    gate_pass = bool(plain["assessment"]["linear"] and twin["assessment"]["linear"])
    payload["gate"]["plain_iid"] = plain
    payload["gate"]["twin_real_occupancy"] = twin
    deciding = {
        "plain_iid": deciding_metrics(plain["assessment"]),
        "twin_real_occupancy": deciding_metrics(twin["assessment"]),
        "plain_iid_verdict": "LINEAR" if plain["assessment"]["linear"] else "FAIL_NOT_LINEAR",
        "twin_real_occupancy_verdict": "LINEAR" if twin["assessment"]["linear"] else "FAIL_NOT_LINEAR",
    }
    payload["gate_outcome"] = {"status": "PASS" if gate_pass else "FAIL", "deciding_numbers": deciding}

    print("GATE_RESULT", json.dumps(payload["gate_outcome"], sort_keys=True))
    print(
        "GATE_FITS",
        json.dumps(
            {
                "plain_iid": plain["assessment"]["fit"],
                "twin_real_occupancy": twin["assessment"]["fit"],
            },
            sort_keys=True,
        ),
    )

    if not gate_pass:
        statement = (
            "The known-truth gate FAILED: at least one arm did not recover the "
            "analytic LINEAR truth under the pre-registered criteria. Real-data "
            "evaluation was not performed and no real-data number is reported."
        )
        payload["if_failed"] = {
            "statement": statement,
            "numbers": deciding,
            "real_data_touched": False,
        }
        atomic_write_json(OUT_PATH, payload)
        old_hash_after = sha256_file(OLD_ARTIFACT) if OLD_ARTIFACT.is_file() else None
        print("FAILURE", statement)
        print("OLD_ARTIFACT_HASHES", old_hash_before, old_hash_after)
        print("ARTIFACT", OUT_PATH, OUT_PATH.stat().st_size, sha256_file(OUT_PATH))
        return 0

    with PAIR_PATH.open("r", encoding="utf-8") as handle:
        pair_rows = json.load(handle)["rows"]
    real_curve = []
    for k in K_VALUES:
        counts = base.real_counts_fast(merged, k, fixed_long=False)
        real_curve.append(curve_one_k(pair_rows, counts, k))
    real_assessment = fit_linear_criteria(real_curve)
    payload["real_data_growth"] = {
        "curve": real_curve,
        "assessment_under_pre_registered_linear_criteria": real_assessment,
        "sampling": "variable PPI_LEN >= k pair set, unchanged from the retired estimator",
    }
    old_hash_after = sha256_file(OLD_ARTIFACT) if OLD_ARTIFACT.is_file() else None
    payload["if_failed"] = None
    payload["gate"]["old_artifact_sha256_after"] = old_hash_after
    atomic_write_json(OUT_PATH, payload)
    print("REAL_DATA_RESULT", json.dumps(real_assessment, sort_keys=True))
    print("OLD_ARTIFACT_HASHES", old_hash_before, old_hash_after)
    print("ARTIFACT", OUT_PATH, OUT_PATH.stat().st_size, sha256_file(OUT_PATH))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print(f"ERROR {type(exc).__name__}: {exc}")
        raise
