#!/usr/bin/env python3
"""X3 chain-rule controls.

CPU-only, numpy/PyTables-compatible runner. It intentionally keeps all outputs
incremental so a stopped run leaves inspectable partial artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import sys
from collections import Counter
from pathlib import Path

import numpy as np


PROJECT = Path("/root/eibo")
ARTIFACT = PROJECT / "artifacts" / "x3_chain_rule_divergence.json"
PAIR_PATH = PROJECT / "artifacts" / "q1_eps_lo_symbol_map.json"
KNOWN_OUT = PROJECT / "artifacts" / "x3_control_known_truth.json"
FIXED_OUT = PROJECT / "artifacts" / "x3_fixed_population_and_occupancy.json"
CACHE_DIR = Path("/dev/shm/eibo_x3_chain_rule")
MERGED = CACHE_DIR / "merged.pkl"
RESULTS = CACHE_DIR / "results.pkl"
RUNNER_PATH = PROJECT / "x3_controls.py"
K_VALUES = list(range(5, 31))
MIN_SERVICE_FLOWS = 2000
PUBLISHED_MEDIANS = {
    5: 1.3813736271298078,
    10: 3.4493236537679586,
    20: 6.357055609304329,
    30: 8.52179151609541,
}
ADJUDICATION_RULE = (
    "X3's SUBLINEAR verdict is CONFIRMED only if BOTH hold:\n"
    "  (i)  it SURVIVES C2 on the fixed population, AND\n"
    "  (ii) the C1 control returns LINEAR (i.e. the estimator is CAPABLE of detecting linearity).\n"
    "Otherwise the verdict must be DOWNGRADED to INCONCLUSIVE, with the numbers."
)
DECISIVE_STATEMENT = (
    "If the estimator returns SUBLINEAR on synthetic data whose analytic truth is LINEAR, "
    "the estimator cannot distinguish the two hypotheses and X3's SUBLINEAR verdict is VOID. "
    "A control that is merely present is not a control that passed."
)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_inputs() -> tuple[dict, dict, dict, dict]:
    artifact = json.loads(ARTIFACT.read_text())
    pairs = json.loads(PAIR_PATH.read_text())["rows"]
    merged = pickle.load(MERGED.open("rb"))
    cached_results = pickle.load(RESULTS.open("rb")) if RESULTS.exists() else {}
    return artifact, {"rows": pairs}, merged, cached_results


def bit_at_from_30(code: np.ndarray, pos: int) -> np.ndarray:
    return ((code.astype(np.uint32) >> np.uint32(29 - pos)) & np.uint32(1)).astype(np.int8)


def prefix_from_30(code: np.ndarray, width: int) -> np.ndarray:
    if width == 0:
        return np.zeros(code.shape[0], dtype=np.uint32)
    return (code.astype(np.uint32) >> np.uint32(30 - width)).astype(np.uint32)


def service_counts_from_codes(codes: np.ndarray, lens: np.ndarray, k: int, fixed_long: bool = False) -> list[tuple[Counter, Counter]]:
    use = lens >= (30 if fixed_long else k)
    c = codes[use]
    out = []
    for pos in range(k):
        ctx = prefix_from_30(c, pos)
        bit = bit_at_from_30(c, pos)
        zero = Counter(map(int, ctx[bit == 0]))
        one = Counter(map(int, ctx[bit == 1]))
        out.append((zero, one))
    return out


def service_bits_from_codes(codes: np.ndarray, lens: np.ndarray, k: int, fixed_long: bool = False) -> np.ndarray:
    use = lens >= (30 if fixed_long else k)
    c = codes[use]
    bits = np.empty((c.shape[0], k), dtype=np.int8)
    for pos in range(k):
        bits[:, pos] = bit_at_from_30(c, pos)
    return bits


def counts_from_bits(bits: np.ndarray, k: int) -> list[tuple[Counter, Counter]]:
    out = []
    ctx = np.zeros(bits.shape[0], dtype=np.uint32)
    for pos in range(k):
        b = bits[:, pos]
        zero = Counter(map(int, ctx[b == 0]))
        one = Counter(map(int, ctx[b == 1]))
        out.append((zero, one))
        ctx = (ctx << np.uint32(1)) | b.astype(np.uint32)
    return out


def kl_binary(p: float, q: float) -> float:
    return p * math.log(p / q) + (1.0 - p) * math.log((1.0 - p) / (1.0 - q))


def d_chain(counts_p: list[tuple[Counter, Counter]], counts_q: list[tuple[Counter, Counter]], smoothing: float) -> float:
    d_pq = 0.0
    d_qp = 0.0
    for (p0, p1), (q0, q1) in zip(counts_p, counts_q):
        contexts = set(p0) | set(p1) | set(q0) | set(q1)
        n_p_total = sum(p0.values()) + sum(p1.values())
        n_q_total = sum(q0.values()) + sum(q1.values())
        if n_p_total <= 0 or n_q_total <= 0:
            continue
        for ctx in contexts:
            n_p0 = p0.get(ctx, 0)
            n_p1 = p1.get(ctx, 0)
            n_q0 = q0.get(ctx, 0)
            n_q1 = q1.get(ctx, 0)
            n_p = n_p0 + n_p1
            n_q = n_q0 + n_q1
            # Smoothing 0 is used only where both conditional supports are nonzero.
            if smoothing == 0:
                if n_p == 0 or n_q == 0:
                    continue
                if n_p0 == 0 or n_p1 == 0 or n_q0 == 0 or n_q1 == 0:
                    eps = 1e-12
                    pp1 = min(1.0 - eps, max(eps, n_p1 / n_p))
                    qq1 = min(1.0 - eps, max(eps, n_q1 / n_q))
                else:
                    pp1 = n_p1 / n_p
                    qq1 = n_q1 / n_q
            else:
                pp1 = (n_p1 + smoothing) / (n_p + 2.0 * smoothing)
                qq1 = (n_q1 + smoothing) / (n_q + 2.0 * smoothing)
            if n_p:
                d_pq += (n_p / n_p_total) * kl_binary(pp1, qq1)
            if n_q:
                d_qp += (n_q / n_q_total) * kl_binary(qq1, pp1)
    return 0.5 * (d_pq + d_qp)


def real_counts(merged: dict, k: int, fixed_long: bool = False) -> dict[int, list[tuple[Counter, Counter]]]:
    out = {}
    for service in merged["services"]:
        item = merged["by_service"][service]
        out[int(service)] = service_counts_from_codes(item["codes"], item["lens"], k, fixed_long=fixed_long)
    return out


def service_counts_fast_from_codes(codes: np.ndarray, lens: np.ndarray, k: int, fixed_long: bool = False) -> list[dict]:
    use = lens >= (30 if fixed_long else k)
    c = codes[use].astype(np.uint32)
    out = []
    for pos in range(k):
        ctx = prefix_from_30(c, pos)
        bit = bit_at_from_30(c, pos).astype(np.uint32)
        enc = (ctx << np.uint32(1)) | bit
        vals, counts = np.unique(enc, return_counts=True)
        ctx_vals = (vals >> np.uint32(1)).astype(np.uint32)
        bit_vals = (vals & np.uint32(1)).astype(np.uint8)
        zmask = bit_vals == 0
        omask = ~zmask
        out.append(
            {
                "ctx0": ctx_vals[zmask],
                "cnt0": counts[zmask].astype(np.float64),
                "ctx1": ctx_vals[omask],
                "cnt1": counts[omask].astype(np.float64),
                "n": int(c.shape[0]),
            }
        )
    return out


def real_counts_fast(merged: dict, k: int, fixed_long: bool = False) -> dict[int, list[dict]]:
    out = {}
    for service in merged["services"]:
        item = merged["by_service"][service]
        out[int(service)] = service_counts_fast_from_codes(item["codes"], item["lens"], k, fixed_long=fixed_long)
    return out


def fast_service_n(counts: list[dict]) -> int:
    return int(counts[0]["n"]) if counts else 0


def take_counts(contexts: np.ndarray, keys: np.ndarray, vals: np.ndarray) -> np.ndarray:
    out = np.zeros(contexts.shape[0], dtype=np.float64)
    if keys.size == 0:
        return out
    idx = np.searchsorted(keys, contexts)
    mask = idx < keys.size
    if np.any(mask):
        good = mask.copy()
        good[mask] = keys[idx[mask]] == contexts[mask]
        out[good] = vals[idx[good]]
    return out


def d_chain_fast(counts_p: list[dict], counts_q: list[dict], smoothing: float) -> float:
    d_pq = 0.0
    d_qp = 0.0
    for cp, cq in zip(counts_p, counts_q):
        contexts = np.union1d(np.union1d(cp["ctx0"], cp["ctx1"]), np.union1d(cq["ctx0"], cq["ctx1"]))
        n_p_total = float(cp["n"])
        n_q_total = float(cq["n"])
        if contexts.size == 0 or n_p_total <= 0 or n_q_total <= 0:
            continue
        p0 = take_counts(contexts, cp["ctx0"], cp["cnt0"])
        p1 = take_counts(contexts, cp["ctx1"], cp["cnt1"])
        q0 = take_counts(contexts, cq["ctx0"], cq["cnt0"])
        q1 = take_counts(contexts, cq["ctx1"], cq["cnt1"])
        np_ctx = p0 + p1
        nq_ctx = q0 + q1
        if smoothing == 0:
            valid = (np_ctx > 0) & (nq_ctx > 0)
            if not np.any(valid):
                continue
            eps = 1e-12
            pp1 = np.clip(np.divide(p1, np_ctx, out=np.zeros_like(p1), where=np_ctx > 0), eps, 1.0 - eps)
            qq1 = np.clip(np.divide(q1, nq_ctx, out=np.zeros_like(q1), where=nq_ctx > 0), eps, 1.0 - eps)
        else:
            valid = np.ones(contexts.shape[0], dtype=bool)
            pp1 = (p1 + smoothing) / (np_ctx + 2.0 * smoothing)
            qq1 = (q1 + smoothing) / (nq_ctx + 2.0 * smoothing)
        kl_pq = pp1 * np.log(pp1 / qq1) + (1.0 - pp1) * np.log((1.0 - pp1) / (1.0 - qq1))
        kl_qp = qq1 * np.log(qq1 / pp1) + (1.0 - qq1) * np.log((1.0 - qq1) / (1.0 - pp1))
        d_pq += float(np.sum((np_ctx[valid] / n_p_total) * kl_pq[valid], where=np_ctx[valid] > 0))
        d_qp += float(np.sum((nq_ctx[valid] / n_q_total) * kl_qp[valid], where=nq_ctx[valid] > 0))
    return 0.5 * (d_pq + d_qp)


def d_chain_fast_prefixes(counts_p: list[dict], counts_q: list[dict], smoothing: float) -> dict[int, float]:
    d_pq = 0.0
    d_qp = 0.0
    out = {}
    for pos, (cp, cq) in enumerate(zip(counts_p, counts_q), start=1):
        contexts = np.union1d(np.union1d(cp["ctx0"], cp["ctx1"]), np.union1d(cq["ctx0"], cq["ctx1"]))
        n_p_total = float(cp["n"])
        n_q_total = float(cq["n"])
        if contexts.size and n_p_total > 0 and n_q_total > 0:
            p0 = take_counts(contexts, cp["ctx0"], cp["cnt0"])
            p1 = take_counts(contexts, cp["ctx1"], cp["cnt1"])
            q0 = take_counts(contexts, cq["ctx0"], cq["cnt0"])
            q1 = take_counts(contexts, cq["ctx1"], cq["cnt1"])
            np_ctx = p0 + p1
            nq_ctx = q0 + q1
            if smoothing == 0:
                valid = (np_ctx > 0) & (nq_ctx > 0)
                if not np.any(valid):
                    if pos >= 5:
                        out[pos] = 0.5 * (d_pq + d_qp)
                    continue
                eps = 1e-12
                pp1 = np.clip(np.divide(p1, np_ctx, out=np.zeros_like(p1), where=np_ctx > 0), eps, 1.0 - eps)
                qq1 = np.clip(np.divide(q1, nq_ctx, out=np.zeros_like(q1), where=nq_ctx > 0), eps, 1.0 - eps)
            else:
                valid = np.ones(contexts.shape[0], dtype=bool)
                pp1 = (p1 + smoothing) / (np_ctx + 2.0 * smoothing)
                qq1 = (q1 + smoothing) / (nq_ctx + 2.0 * smoothing)
            kl_pq = pp1 * np.log(pp1 / qq1) + (1.0 - pp1) * np.log((1.0 - pp1) / (1.0 - qq1))
            kl_qp = qq1 * np.log(qq1 / pp1) + (1.0 - qq1) * np.log((1.0 - qq1) / (1.0 - pp1))
            d_pq += float(np.sum((np_ctx[valid] / n_p_total) * kl_pq[valid], where=np_ctx[valid] > 0))
            d_qp += float(np.sum((nq_ctx[valid] / n_q_total) * kl_qp[valid], where=nq_ctx[valid] > 0))
        if pos >= 5:
            out[pos] = 0.5 * (d_pq + d_qp)
    return out


def run_fixed_all_chunk(
    pairs: dict,
    merged: dict,
    smoothing: float,
    start: int,
    end: int,
) -> dict:
    rows = get_fixed_rows(pairs, merged)
    counts = real_counts_fast(merged, 30, fixed_long=True)
    eligible = [
        row
        for row in rows
        if fast_service_n(counts[int(row["service_a"])]) >= MIN_SERVICE_FLOWS
        and fast_service_n(counts[int(row["service_b"])]) >= MIN_SERVICE_FLOWS
    ]
    end = min(end, len(eligible))
    values = {str(k): {} for k in K_VALUES}
    for row in eligible[start:end]:
        a = int(row["service_a"])
        b = int(row["service_b"])
        prefixes = d_chain_fast_prefixes(counts[a], counts[b], smoothing)
        key = pair_key(a, b)
        for k in K_VALUES:
            values[str(k)][key] = prefixes[k]
    return {
        "smoothing": smoothing,
        "fixed_long": True,
        "start": start,
        "end": end,
        "n_total": len(eligible),
        "values_by_k": values,
    }


def curve_from_counts_fast(
    pair_rows: list[dict],
    counts_by_service: dict[int, list[dict]],
    smoothing: float,
    min_service_flows: int = MIN_SERVICE_FLOWS,
) -> dict:
    per_pair = {}
    service_ns = {s: fast_service_n(c) for s, c in counts_by_service.items()}
    for row in pair_rows:
        a = int(row["service_a"])
        b = int(row["service_b"])
        if (
            a in counts_by_service
            and b in counts_by_service
            and service_ns.get(a, 0) >= min_service_flows
            and service_ns.get(b, 0) >= min_service_flows
        ):
            per_pair[pair_key(a, b)] = d_chain_fast(counts_by_service[a], counts_by_service[b], smoothing)
    vals = np.asarray(list(per_pair.values()), dtype=float)
    return {
        "n_pairs": int(vals.size),
        "D_k_median": float(np.median(vals)) if vals.size else None,
        "D_k_mean": float(np.mean(vals)) if vals.size else None,
        "per_pair": per_pair,
    }


def pair_key(a: int, b: int) -> str:
    return f"{int(a)}:{int(b)}"


def service_n(counts: list[tuple[Counter, Counter]]) -> int:
    if not counts:
        return 0
    zero, one = counts[0]
    return int(sum(zero.values()) + sum(one.values()))


def curve_from_counts(
    pair_rows: list[dict],
    counts_by_service: dict[int, list[tuple[Counter, Counter]]],
    smoothing: float,
    min_service_flows: int = MIN_SERVICE_FLOWS,
) -> dict:
    per_pair = {}
    service_ns = {s: service_n(c) for s, c in counts_by_service.items()}
    for row in pair_rows:
        a = int(row["service_a"])
        b = int(row["service_b"])
        if (
            a in counts_by_service
            and b in counts_by_service
            and service_ns.get(a, 0) >= min_service_flows
            and service_ns.get(b, 0) >= min_service_flows
        ):
            per_pair[pair_key(a, b)] = d_chain(counts_by_service[a], counts_by_service[b], smoothing)
    vals = np.asarray(list(per_pair.values()), dtype=float)
    return {
        "n_pairs": int(vals.size),
        "D_k_median": float(np.median(vals)) if vals.size else None,
        "D_k_mean": float(np.mean(vals)) if vals.size else None,
        "per_pair": per_pair,
    }


def fit_growth(curve: list[dict]) -> dict:
    x = np.asarray([float(r["k"]) for r in curve], dtype=float)
    y = np.asarray([float(r["D_k_median"]) for r in curve], dtype=float)

    def ols(design: np.ndarray) -> tuple[np.ndarray, float, float, float, np.ndarray]:
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        pred = design @ beta
        rss = float(np.sum((y - pred) ** 2))
        n = len(y)
        p = design.shape[1]
        aic = float(n * math.log(max(rss / n, 1e-300)) + 2 * p)
        rmse = float(math.sqrt(rss / n))
        return beta, rss, rmse, aic, pred

    b_lin, rss_lin, rmse_lin, aic_lin, pred_lin = ols(np.column_stack([np.ones_like(x), x]))
    b_sqrt, rss_sqrt, rmse_sqrt, aic_sqrt, pred_sqrt = ols(np.column_stack([np.ones_like(x), np.sqrt(x)]))

    # Match X3's original-scale power fit: grid-search p and solve q by OLS
    # at each p. The selected p is not counted as a continuously fitted
    # parameter in the published AIC convention.
    power_grid = np.linspace(0.05, 1.50, 1451)
    best = None
    for candidate_p in power_grid:
        basis = x ** candidate_p
        coefficient = float(np.dot(basis, y) / np.dot(basis, basis))
        candidate_pred = coefficient * basis
        candidate_rss = float(np.sum((y - candidate_pred) ** 2))
        if best is None or candidate_rss < best[0]:
            best = (candidate_rss, float(candidate_p), coefficient, candidate_pred)
    assert best is not None
    rss_pow, power_p, power_coefficient, pred_pow = best
    rmse_pow = float(math.sqrt(rss_pow / len(y)))
    aic_pow = float(len(y) * math.log(max(rss_pow / len(y), 1e-300)) + 2)
    increments = np.diff(y)
    first = float(np.median(increments[:8]))
    last = float(np.median(increments[-8:]))
    ratio = float(first / last) if last != 0 else float("inf")
    verdict = "INCONCLUSIVE"
    sqrt_advantage = aic_lin - aic_sqrt
    linear_advantage = aic_sqrt - aic_lin
    if power_p < 0.90 and sqrt_advantage > 6 and ratio > 1.10:
        verdict = "SUBLINEAR"
    elif power_p > 0.95 and linear_advantage > 6 and ratio <= 1.10:
        verdict = "LINEAR"
    return {
        "power": {
            "coefficient": power_coefficient,
            "exponent_p": power_p,
            "rss": rss_pow,
            "rmse": rmse_pow,
            "aic": aic_pow,
            "predicted": [float(v) for v in pred_pow],
            "grid": {"min": 0.05, "max": 1.50, "step": 0.001, "count": 1451},
        },
        "linear": {
            "intercept": float(b_lin[0]),
            "slope": float(b_lin[1]),
            "rss": rss_lin,
            "rmse": rmse_lin,
            "aic": aic_lin,
            "predicted": [float(v) for v in pred_lin],
        },
        "sqrt_sublinear": {
            "intercept": float(b_sqrt[0]),
            "sqrt_slope": float(b_sqrt[1]),
            "rss": rss_sqrt,
            "rmse": rmse_sqrt,
            "aic": aic_sqrt,
            "predicted": [float(v) for v in pred_sqrt],
        },
        "sqrt_model_aic_advantage_over_linear": float(sqrt_advantage),
        "linear_model_aic_advantage_over_sqrt": float(linear_advantage),
        "first_to_last_median_increment_ratio": ratio,
        "increment_window": 8,
        "verdict": verdict,
    }


def reproduce(artifact: dict, pairs: dict, merged: dict, tolerance: float, out_known: dict) -> tuple[bool, dict]:
    comparisons = {}
    for k, published in PUBLISHED_MEDIANS.items():
        counts = real_counts_fast(merged, k, fixed_long=False)
        curve = curve_from_counts_fast(pairs["rows"], counts, 0.5)
        actual = curve["D_k_median"]
        comparisons[str(k)] = {
            "published": published,
            "recomputed": actual,
            "abs_diff": abs(actual - published),
            "n_pairs": curve["n_pairs"],
        }
        out_known["estimator_reproduces_published_medians"] = {
            "tolerance": tolerance,
            "comparisons": comparisons,
            "boolean": all(v["abs_diff"] <= tolerance for v in comparisons.values()),
        }
        atomic_write_json(KNOWN_OUT, out_known)
        print("REPRO", k, json.dumps(comparisons[str(k)], sort_keys=True))
    ok = all(v["abs_diff"] <= tolerance for v in comparisons.values())
    return ok, comparisons


def synthetic_bits(n: int, kmax: int, p: float, rng: np.random.Generator) -> np.ndarray:
    return (rng.random((n, kmax)) < p).astype(np.int8)


def codes_from_bits(bits: np.ndarray) -> np.ndarray:
    code = np.zeros(bits.shape[0], dtype=np.uint32)
    for pos in range(bits.shape[1]):
        code = (code << np.uint32(1)) | bits[:, pos].astype(np.uint32)
    if bits.shape[1] < 30:
        code = code << np.uint32(30 - bits.shape[1])
    return code


def synthetic_from_real_occupancy(merged: dict, service: int, p: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    item = merged["by_service"][service]
    n = len(item["lens"])
    bits = (rng.random((n, 30)) < p).astype(np.int8)
    return bits, item["lens"].copy()


def synthetic_counts_on_real_prefix_occupancy(
    merged: dict,
    service: int,
    k: int,
    p: float,
    rng: np.random.Generator,
) -> list[dict]:
    item = merged["by_service"][service]
    real = service_counts_fast_from_codes(item["codes"], item["lens"], k, fixed_long=False)
    out = []
    for trans in real:
        contexts = np.union1d(trans["ctx0"], trans["ctx1"])
        totals = take_counts(contexts, trans["ctx0"], trans["cnt0"]) + take_counts(contexts, trans["ctx1"], trans["cnt1"])
        totals_i = totals.astype(np.int64)
        ones = rng.binomial(totals_i, p).astype(np.float64)
        zeros = totals_i.astype(np.float64) - ones
        zmask = zeros > 0
        omask = ones > 0
        out.append(
            {
                "ctx0": contexts[zmask].astype(np.uint32),
                "cnt0": zeros[zmask].astype(np.float64),
                "ctx1": contexts[omask].astype(np.uint32),
                "cnt1": ones[omask].astype(np.float64),
                "n": int(trans["n"]),
            }
        )
    return out


def occupancy_signature(counts: list[dict]) -> list[dict]:
    out = []
    for pos, trans in enumerate(counts, start=1):
        contexts = np.union1d(trans["ctx0"], trans["ctx1"])
        totals = take_counts(contexts, trans["ctx0"], trans["cnt0"]) + take_counts(contexts, trans["ctx1"], trans["cnt1"])
        out.append(
            {
                "position": pos,
                "distinct_contexts": int(contexts.size),
                "total_transitions": int(np.sum(totals)),
                "contexts_observed_fewer_than_5_times": int(np.sum(totals < 5)),
            }
        )
    return out


def counts_from_synthetic(bits: np.ndarray, lens: np.ndarray, k: int, fixed_long: bool = False) -> list[tuple[Counter, Counter]]:
    use = lens >= (30 if fixed_long else k)
    return counts_from_bits(bits[use, :k], k)


def synthetic_control(merged: dict, seed: int, smoothing: float = 0.5) -> dict:
    rng = np.random.default_rng(seed)
    p = 0.30
    q = 0.70
    per_pos = 0.5 * (
        p * math.log(p / q)
        + (1.0 - p) * math.log((1.0 - p) / (1.0 - q))
        + q * math.log(q / p)
        + (1.0 - q) * math.log((1.0 - q) / (1.0 - p))
    )
    n_plain = 200000
    bits_p_plain = synthetic_bits(n_plain, 30, p, rng)
    bits_q_plain = synthetic_bits(n_plain, 30, q, rng)
    lens_plain = np.full(n_plain, 30, dtype=np.uint8)
    services = list(map(int, merged["services"]))
    twin_a = services[0]
    twin_b = services[1]

    def run_case(name: str, bp: np.ndarray, lp: np.ndarray, bq: np.ndarray, lq: np.ndarray) -> dict:
        cp_codes = codes_from_bits(bp)
        cq_codes = codes_from_bits(bq)
        curve = []
        for k in K_VALUES:
            cp = service_counts_fast_from_codes(cp_codes, lp, k)
            cq = service_counts_fast_from_codes(cq_codes, lq, k)
            d = d_chain_fast(cp, cq, smoothing)
            true_d = k * per_pos
            curve.append(
                {
                    "k": k,
                    "D_k_median": float(d),
                    "D_k_mean": float(d),
                    "D_k_true": float(true_d),
                    "D_k_estimated_over_true": float(d / true_d),
                    "n_a": int(np.sum(lp >= k)),
                    "n_b": int(np.sum(lq >= k)),
                }
            )
        fit = fit_growth(curve)
        return {"curve": curve, "fit": fit, "verdict": fit["verdict"]}

    def run_twin_count_case() -> dict:
        curve = []
        checks = {}
        for k in K_VALUES:
            real_p = service_counts_fast_from_codes(
                merged["by_service"][twin_a]["codes"],
                merged["by_service"][twin_a]["lens"],
                k,
                fixed_long=False,
            )
            real_q = service_counts_fast_from_codes(
                merged["by_service"][twin_b]["codes"],
                merged["by_service"][twin_b]["lens"],
                k,
                fixed_long=False,
            )
            cp = synthetic_counts_on_real_prefix_occupancy(merged, twin_a, k, p, rng)
            cq = synthetic_counts_on_real_prefix_occupancy(merged, twin_b, k, q, rng)
            d = d_chain_fast(cp, cq, smoothing)
            true_d = k * per_pos
            if k in (5, 10, 20, 30):
                sig_real_p = occupancy_signature(real_p)
                sig_synth_p = occupancy_signature(cp)
                sig_real_q = occupancy_signature(real_q)
                sig_synth_q = occupancy_signature(cq)
                checks[str(k)] = {
                    "service_a_matches_real_prefix_occupancy": sig_real_p == sig_synth_p,
                    "service_b_matches_real_prefix_occupancy": sig_real_q == sig_synth_q,
                    "service_a_real_signature": sig_real_p[-1],
                    "service_a_synthetic_signature": sig_synth_p[-1],
                    "service_b_real_signature": sig_real_q[-1],
                    "service_b_synthetic_signature": sig_synth_q[-1],
                }
            curve.append(
                {
                    "k": k,
                    "D_k_median": float(d),
                    "D_k_mean": float(d),
                    "D_k_true": float(true_d),
                    "D_k_estimated_over_true": float(d / true_d),
                    "n_a": int(real_p[0]["n"]) if real_p else 0,
                    "n_b": int(real_q[0]["n"]) if real_q else 0,
                }
            )
        fit = fit_growth(curve)
        return {
            "curve": curve,
            "fit": fit,
            "verdict": fit["verdict"],
            "occupancy_match_checks": checks,
        }

    return {
        "construction": {
            "p": p,
            "q": q,
            "seed": seed,
            "truth": "P(x_i|x_<i)=Bernoulli(p) and Q(x_i|x_<i)=Bernoulli(q) for every i and every prefix context",
            "natural_log": True,
            "analytic_per_position_constant": per_pos,
            "analytic_line": "D_k = k * analytic_per_position_constant",
            "plain_n_per_service": n_plain,
            "twin_real_services_used_for_occupancy": [twin_a, twin_b],
            "twin_operational_definition": (
                "Count-level synthetic draw over the estimator's sufficient statistics: "
                "for each k, service, position, and real observed prefix context, keep the exact real "
                "context transition count and draw the outgoing bit count from Binomial(n_context, p) "
                "or Binomial(n_context, q). This preserves the real per-k flow-length eligibility and "
                "prefix-occupancy distribution exactly, while the population conditional bit law is "
                "context-independent Bernoulli."
            ),
        },
        "plain_iid": run_case("plain_iid", bits_p_plain, lens_plain, bits_q_plain, lens_plain),
        "twin_real_occupancy": run_twin_count_case(),
    }


def synthetic_params(seed: int) -> dict:
    p = 0.30
    q = 0.70
    per_pos = 0.5 * (
        p * math.log(p / q)
        + (1.0 - p) * math.log((1.0 - p) / (1.0 - q))
        + q * math.log(q / p)
        + (1.0 - q) * math.log((1.0 - q) / (1.0 - p))
    )
    return {"p": p, "q": q, "seed": int(seed), "analytic_per_position_constant": per_pos}


def synthetic_plain_cache(seed: int, n_plain: int = 200000) -> tuple[np.ndarray, np.ndarray]:
    path = CACHE_DIR / f"synthetic_plain_seed{seed}_n{n_plain}.npz"
    if not path.exists():
        rng = np.random.default_rng(seed)
        bits_p = synthetic_bits(n_plain, 30, 0.30, rng)
        bits_q = synthetic_bits(n_plain, 30, 0.70, rng)
        np.savez_compressed(path, bits_p=bits_p, bits_q=bits_q)
    data = np.load(path)
    return data["bits_p"], data["bits_q"]


def synthetic_k_phase(args: argparse.Namespace) -> int:
    _, _, merged, _ = load_inputs()
    if args.k is None:
        raise SystemExit("--k is required for synthetic_k")
    params = synthetic_params(args.seed)
    p = params["p"]
    q = params["q"]
    per_pos = params["analytic_per_position_constant"]
    k = int(args.k)
    n_plain = 200000
    bits_p, bits_q = synthetic_plain_cache(args.seed, n_plain=n_plain)
    lens_plain = np.full(n_plain, 30, dtype=np.uint8)
    cp_plain = service_counts_fast_from_codes(codes_from_bits(bits_p), lens_plain, k, fixed_long=False)
    cq_plain = service_counts_fast_from_codes(codes_from_bits(bits_q), lens_plain, k, fixed_long=False)
    d_plain = d_chain_fast(cp_plain, cq_plain, args.smoothing)

    services = list(map(int, merged["services"]))
    twin_a = services[0]
    twin_b = services[1]
    rng_twin = np.random.default_rng(args.seed + 1000003 * k)
    real_p = service_counts_fast_from_codes(
        merged["by_service"][twin_a]["codes"],
        merged["by_service"][twin_a]["lens"],
        k,
        fixed_long=False,
    )
    real_q = service_counts_fast_from_codes(
        merged["by_service"][twin_b]["codes"],
        merged["by_service"][twin_b]["lens"],
        k,
        fixed_long=False,
    )
    cp_twin = synthetic_counts_on_real_prefix_occupancy(merged, twin_a, k, p, rng_twin)
    cq_twin = synthetic_counts_on_real_prefix_occupancy(merged, twin_b, k, q, rng_twin)
    d_twin = d_chain_fast(cp_twin, cq_twin, args.smoothing)
    true_d = k * per_pos
    payload = {
        "k": k,
        "seed": int(args.seed),
        "smoothing": float(args.smoothing),
        "analytic_per_position_constant": float(per_pos),
        "plain_iid": {
            "k": k,
            "D_k_median": float(d_plain),
            "D_k_mean": float(d_plain),
            "D_k_true": float(true_d),
            "D_k_estimated_over_true": float(d_plain / true_d),
            "n_a": n_plain,
            "n_b": n_plain,
        },
        "twin_real_occupancy": {
            "k": k,
            "D_k_median": float(d_twin),
            "D_k_mean": float(d_twin),
            "D_k_true": float(true_d),
            "D_k_estimated_over_true": float(d_twin / true_d),
            "n_a": int(real_p[0]["n"]) if real_p else 0,
            "n_b": int(real_q[0]["n"]) if real_q else 0,
        },
        "occupancy_match_check": {
            "service_a_matches_real_prefix_occupancy": occupancy_signature(real_p) == occupancy_signature(cp_twin),
            "service_b_matches_real_prefix_occupancy": occupancy_signature(real_q) == occupancy_signature(cq_twin),
            "service_a_last_position_real_signature": occupancy_signature(real_p)[-1],
            "service_a_last_position_synthetic_signature": occupancy_signature(cp_twin)[-1],
            "service_b_last_position_real_signature": occupancy_signature(real_q)[-1],
            "service_b_last_position_synthetic_signature": occupancy_signature(cq_twin)[-1],
        },
    }
    out = CACHE_DIR / f"synthetic_k{k}_s{args.smoothing:g}_seed{args.seed}.json"
    out.write_text(json.dumps(payload))
    print(json.dumps({"output": str(out), "k": k, "plain_ratio": payload["plain_iid"]["D_k_estimated_over_true"], "twin_ratio": payload["twin_real_occupancy"]["D_k_estimated_over_true"]}, sort_keys=True))
    return 0


def assemble_synthetic_phase(args: argparse.Namespace) -> int:
    artifact, pairs, merged, _ = load_inputs()
    payload = json.loads(KNOWN_OUT.read_text()) if KNOWN_OUT.exists() else {
        "runner_path": str(RUNNER_PATH),
        "lookup_report": {},
        "known_truth_control": {},
        "estimator_reproduces_published_medians": {},
        "verdict_on_known_linear_truth": None,
        "decisive_statement": DECISIVE_STATEMENT,
    }
    payload["runner_path"] = str(RUNNER_PATH)
    payload["decisive_statement"] = DECISIVE_STATEMENT
    existing_repro = payload.get("estimator_reproduces_published_medians", {})
    if not existing_repro.get("boolean"):
        ok, _ = reproduce(artifact, pairs, merged, args.tolerance, payload)
        if not ok:
            payload["status"] = "INADMISSIBLE_REPRODUCTION_FAILED"
            atomic_write_json(KNOWN_OUT, payload)
            return 2
    files = [CACHE_DIR / f"synthetic_k{k}_s{args.smoothing:g}_seed{args.seed}.json" for k in K_VALUES]
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        raise SystemExit("missing synthetic checkpoints: " + ", ".join(missing))
    rows = [json.loads(p.read_text()) for p in files]
    params = synthetic_params(args.seed)
    plain_curve = [r["plain_iid"] for r in rows]
    twin_curve = [r["twin_real_occupancy"] for r in rows]
    plain_fit = fit_growth(plain_curve)
    twin_fit = fit_growth(twin_curve)
    c1_pass = plain_fit["verdict"] == "LINEAR" and twin_fit["verdict"] == "LINEAR"
    payload["known_truth_control"] = {
        "construction": {
            "p": params["p"],
            "q": params["q"],
            "seed": int(args.seed),
            "truth": "P(x_i|x_<i)=Bernoulli(p) and Q(x_i|x_<i)=Bernoulli(q) for every i and every prefix context",
            "natural_log": True,
            "analytic_per_position_constant": params["analytic_per_position_constant"],
            "analytic_line": "D_k = k * analytic_per_position_constant",
            "plain_n_per_service": 200000,
            "plain_sample_convention": "one cached 200000-flow-by-30-bit sample per service reused across k",
            "twin_real_services_used_for_occupancy": list(map(int, merged["services"]))[:2],
            "twin_operational_definition": (
                "Count-level synthetic draw over the estimator's sufficient statistics: for each k, "
                "service, position, and real observed prefix context, keep the exact real context "
                "transition count and draw the outgoing bit count from Binomial(n_context, p) or "
                "Binomial(n_context, q). This preserves the real per-k flow-length eligibility and "
                "prefix-occupancy distribution exactly, while the population conditional bit law is "
                "context-independent Bernoulli."
            ),
        },
        "plain_iid": {"curve": plain_curve, "fit": plain_fit, "verdict": plain_fit["verdict"]},
        "twin_real_occupancy": {
            "curve": twin_curve,
            "fit": twin_fit,
            "verdict": twin_fit["verdict"],
            "occupancy_match_checks": {str(r["k"]): r["occupancy_match_check"] for r in rows if r["k"] in (5, 10, 20, 30)},
        },
    }
    payload["verdict_on_known_linear_truth"] = "PASS_LINEAR" if c1_pass else "FAIL_NOT_LINEAR"
    payload["status"] = "KNOWN_TRUTH_COMPLETE"
    atomic_write_json(KNOWN_OUT, payload)
    print("C1", json.dumps({"pass": c1_pass, "plain": plain_fit, "twin": twin_fit}, sort_keys=True))
    return 0


def fixed_population_and_occupancy(artifact: dict, pairs: dict, merged: dict) -> tuple[dict, list[dict]]:
    fixed_rows = get_fixed_rows(pairs, merged)
    fixed_curve = []
    occupancy = []
    for k in K_VALUES:
        counts = real_counts_fast(merged, k, fixed_long=True)
        curve = curve_from_counts_fast(fixed_rows, counts, 0.5)
        fixed_curve.append(
            {
                "k": k,
                "n_pairs": curve["n_pairs"],
                "D_k_median": curve["D_k_median"],
                "D_k_mean": curve["D_k_mean"],
                "denominator": "fixed k=30 eligible pair set",
            }
        )
        all_context_totals = []
        distinct = 0
        low = 0
        for svc_counts in counts.values():
            for trans in svc_counts:
                contexts = np.union1d(trans["ctx0"], trans["ctx1"])
                totals = take_counts(contexts, trans["ctx0"], trans["cnt0"]) + take_counts(contexts, trans["ctx1"], trans["cnt1"])
                distinct += int(contexts.size)
                if contexts.size:
                    all_context_totals.extend(map(float, totals.tolist()))
                    low += int(np.sum(totals < 5))
        occupancy.append(
            {
                "k": k,
                "distinct_prefix_contexts": int(distinct),
                "fraction_contexts_observed_fewer_than_5_times": float(low / distinct) if distinct else None,
                "effective_sample_per_context": float(np.mean(all_context_totals)) if all_context_totals else None,
            }
        )
    original_curve = [
        {
            "k": int(r["k"]),
            "n_pairs": int(r["n_pairs"]),
            "D_k_median": float(r["D_k_median"]),
            "D_k_mean": float(r["D_k_mean"]),
            "denominator": "variable PPI_LEN >= k pair set",
        }
        for r in artifact["chain_rule_joint_divergence"]["growth_fit"]["auditable_curve"]
    ]
    return {
        "fixed_rows": fixed_rows,
        "fixed_population_curve": fixed_curve,
        "original_variable_population_curve": original_curve,
        "occupancy_by_k": occupancy,
    }, fixed_rows


def occupancy_one_k(merged: dict, k: int, fixed_long: bool = False) -> dict:
    counts = real_counts_fast(merged, k, fixed_long=fixed_long)
    distinct = 0
    low = 0
    totals = []
    for svc_counts in counts.values():
        for trans in svc_counts:
            contexts = np.union1d(trans["ctx0"], trans["ctx1"])
            n0 = take_counts(contexts, trans["ctx0"], trans["cnt0"])
            n1 = take_counts(contexts, trans["ctx1"], trans["cnt1"])
            n = n0 + n1
            distinct += int(contexts.size)
            low += int(np.sum(n < 5))
            totals.extend(n.tolist())
    return {
        "k": int(k),
        "sampling": "fixed PPI_LEN >= 30" if fixed_long else "variable PPI_LEN >= k",
        "distinct_prefix_contexts": int(distinct),
        "fraction_contexts_observed_fewer_than_5_times": float(low / distinct) if distinct else None,
        "effective_sample_per_context": float(np.mean(totals)) if totals else None,
    }


def get_fixed_rows(pairs: dict, merged: dict) -> list[dict]:
    fixed_services = {
        int(s)
        for s in merged["services"]
        if int(np.sum(merged["by_service"][s]["lens"] >= 30)) >= MIN_SERVICE_FLOWS
    }
    return [
        row
        for row in pairs["rows"]
        if int(row["service_a"]) in fixed_services and int(row["service_b"]) in fixed_services
    ]


def run_one_k_chunk(
    pairs: dict,
    merged: dict,
    k: int,
    smoothing: float,
    fixed_long: bool,
    start: int,
    end: int,
) -> dict:
    rows = pairs["rows"]
    if fixed_long:
        rows = get_fixed_rows(pairs, merged)
    counts = real_counts_fast(merged, k, fixed_long=fixed_long)
    service_ns = {s: fast_service_n(c) for s, c in counts.items()}
    eligible = [
        row
        for row in rows
        if service_ns.get(int(row["service_a"]), 0) >= MIN_SERVICE_FLOWS
        and service_ns.get(int(row["service_b"]), 0) >= MIN_SERVICE_FLOWS
    ]
    end = min(end, len(eligible))
    vals = {}
    for row in eligible[start:end]:
        a = int(row["service_a"])
        b = int(row["service_b"])
        vals[pair_key(a, b)] = d_chain_fast(counts[a], counts[b], smoothing)
    return {
        "k": k,
        "smoothing": smoothing,
        "fixed_long": fixed_long,
        "start": start,
        "end": end,
        "n_total": len(eligible),
        "values": vals,
    }


def assemble_chunks(files: list[Path]) -> dict:
    values = {}
    metadata = []
    for path in sorted(files):
        item = json.loads(path.read_text())
        values.update(item["values"])
        metadata.append({k: item[k] for k in ("k", "smoothing", "fixed_long", "start", "end", "n_total")})
    arr = np.asarray(list(values.values()), dtype=float)
    return {
        "n_pairs": int(arr.size),
        "D_k_median": float(np.median(arr)) if arr.size else None,
        "D_k_mean": float(np.mean(arr)) if arr.size else None,
        "chunks": metadata,
        "per_pair": values,
    }


def occupancy_phase(args: argparse.Namespace) -> int:
    _, _, merged, _ = load_inputs()
    if args.k is None:
        raise SystemExit("--k is required for occupancy_k")
    item = occupancy_one_k(merged, args.k, fixed_long=bool(args.fixed_long))
    key = "fixed" if args.fixed_long else "variable"
    out = CACHE_DIR / f"occupancy_{key}_k{args.k}.json"
    out.write_text(json.dumps(item))
    print(json.dumps({"output": str(out), **item}, sort_keys=True))
    return 0


def variable_bundle_phase(args: argparse.Namespace) -> int:
    _, pairs, merged, _ = load_inputs()
    if args.k is None:
        raise SystemExit("--k is required for variable_bundle")
    k = int(args.k)
    counts = real_counts_fast(merged, k, fixed_long=False)
    service_ns = {s: fast_service_n(c) for s, c in counts.items()}
    eligible = [
        row
        for row in pairs["rows"]
        if service_ns.get(int(row["service_a"]), 0) >= MIN_SERVICE_FLOWS
        and service_ns.get(int(row["service_b"]), 0) >= MIN_SERVICE_FLOWS
    ]
    outputs = {}
    for smoothing in args.smoothing_values:
        vals = {}
        for row in eligible:
            a = int(row["service_a"])
            b = int(row["service_b"])
            vals[pair_key(a, b)] = d_chain_fast(counts[a], counts[b], float(smoothing))
        chunk = {
            "k": k,
            "smoothing": float(smoothing),
            "fixed_long": False,
            "start": 0,
            "end": len(eligible),
            "n_total": len(eligible),
            "values": vals,
        }
        out = CACHE_DIR / f"variable_k{k}_s{float(smoothing):g}_0_{len(eligible)}.json"
        out.write_text(json.dumps(chunk))
        outputs[str(float(smoothing))] = {
            "output": str(out),
            "n_values": len(vals),
            "median": float(np.median(list(vals.values()))) if vals else None,
        }
    occ = occupancy_one_k(merged, k, fixed_long=False)
    occ_out = CACHE_DIR / f"occupancy_variable_k{k}.json"
    occ_out.write_text(json.dumps(occ))
    print(json.dumps({"k": k, "outputs": outputs, "occupancy_output": str(occ_out), "occupancy": occ}, sort_keys=True))
    return 0


def checkpoint_phase(args: argparse.Namespace) -> int:
    _, pairs, merged, _ = load_inputs()
    if args.k is None:
        raise SystemExit("--k is required for fixed_k and variable_k")
    fixed_long = args.phase == "fixed_k"
    key = "fixed" if fixed_long else "variable"
    rows = get_fixed_rows(pairs, merged) if fixed_long else pairs["rows"]
    counts = real_counts_fast(merged, args.k, fixed_long=fixed_long)
    eligible = [
        row
        for row in rows
        if fast_service_n(counts[int(row["service_a"])]) >= MIN_SERVICE_FLOWS
        and fast_service_n(counts[int(row["service_b"])]) >= MIN_SERVICE_FLOWS
    ]
    start = int(args.start)
    end = min(int(args.end), len(eligible))
    chunk = run_one_k_chunk(pairs, merged, args.k, args.smoothing, fixed_long, start, end)
    out = CACHE_DIR / f"{key}_k{args.k}_s{args.smoothing:g}_{start}_{end}.json"
    out.write_text(json.dumps(chunk))
    print(json.dumps({"output": str(out), "k": args.k, "smoothing": args.smoothing, "fixed_long": fixed_long, "start": start, "end": end, "n_total": len(eligible), "n_values": len(chunk["values"])}, sort_keys=True))
    return 0


def fixed_all_chunk_phase(args: argparse.Namespace) -> int:
    _, pairs, merged, _ = load_inputs()
    chunk = run_fixed_all_chunk(pairs, merged, args.smoothing, int(args.start), int(args.end))
    out = CACHE_DIR / f"fixed_all_s{args.smoothing:g}_{args.start}_{args.end}.json"
    out.write_text(json.dumps(chunk))
    print(json.dumps({"output": str(out), "smoothing": args.smoothing, "start": args.start, "end": args.end, "n_total": chunk["n_total"]}, sort_keys=True))
    return 0


def assemble_fixed_phase(args: argparse.Namespace) -> int:
    artifact, pairs, merged, _ = load_inputs()
    files_arg = getattr(args, "files", None)
    files = [Path(p) for p in files_arg] if files_arg else sorted(CACHE_DIR.glob("fixed_all_s0.5_*.json"))
    values = {str(k): {} for k in K_VALUES}
    chunk_metadata = []
    for path in files:
        item = json.loads(path.read_text())
        chunk_metadata.append({k: item[k] for k in ("start", "end", "n_total")})
        for k in K_VALUES:
            values[str(k)].update(item["values_by_k"][str(k)])
    fixed_rows = get_fixed_rows(pairs, merged)
    fixed_curve = []
    counts = real_counts_fast(merged, 30, fixed_long=True)
    for k in K_VALUES:
        vals = np.asarray(list(values[str(k)].values()), dtype=float)
        fixed_curve.append(
            {
                "k": k,
                "n_pairs": int(vals.size),
                "D_k_median": float(np.median(vals)) if vals.size else None,
                "D_k_mean": float(np.mean(vals)) if vals.size else None,
                "denominator": "fixed k=30 eligible pair set",
            }
        )
    fixed_occupancy = [occupancy_one_k(merged, k, fixed_long=True) for k in K_VALUES]
    fixed_fit = fit_growth(fixed_curve)
    original_curve = [
        {
            "k": int(r["k"]),
            "n_pairs": int(r["n_pairs"]),
            "D_k_median": float(r["D_k_median"]),
            "D_k_mean": float(r["D_k_mean"]),
            "denominator": "variable PPI_LEN >= k pair set",
        }
        for r in artifact["chain_rule_joint_divergence"]["growth_fit"]["auditable_curve"]
    ]
    out = json.loads(FIXED_OUT.read_text()) if FIXED_OUT.exists() else {}
    out.update(
        {
            "runner_path": str(RUNNER_PATH),
            "fixed_population_curve": {
                "set_definition": "flows and pairs eligible at k=30; same population used for every k=5..30",
                "constant_pair_denominator": len(fixed_rows),
                "rows": fixed_curve,
            },
            "original_variable_population_curve": original_curve,
            "fixed_population_fit": fixed_fit,
            "original_variable_population_fit": artifact["chain_rule_joint_divergence"]["growth_fit"],
            "fixed_population_verdict": fixed_fit["verdict"],
            "composition_statement": (
                "Original SUBLINEAR survives the fixed-population control."
                if fixed_fit["verdict"] == "SUBLINEAR"
                else "Original SUBLINEAR is absent under the fixed-population control; the original verdict is a composition artifact or otherwise not stable."
            ),
            "fixed_population_occupancy_by_k": fixed_occupancy,
            "fixed_chunk_metadata": chunk_metadata,
            "status": "FIXED_S05_ASSEMBLED",
        }
    )
    atomic_write_json(FIXED_OUT, out)
    print(json.dumps({"fixed_fit": fixed_fit, "k5": fixed_curve[0], "k30": fixed_curve[-1], "fixed_occupancy_k5": fixed_occupancy[0], "fixed_occupancy_k30": fixed_occupancy[-1]}, sort_keys=True))
    return 0


def assemble_smoothing_phase(args: argparse.Namespace) -> int:
    artifact, _, _, _ = load_inputs()
    out = json.loads(FIXED_OUT.read_text()) if FIXED_OUT.exists() else {}
    smoothing_payload = {}
    for smoothing in args.smoothing_values:
        curve = []
        for k in K_VALUES:
            files = sorted(CACHE_DIR.glob(f"variable_k{k}_s{smoothing:g}_*.json"))
            if not files:
                raise SystemExit(f"missing variable chunks for smoothing={smoothing:g} k={k}")
            assembled = assemble_chunks(files)
            curve.append(
                {
                    "k": k,
                    "n_pairs": assembled["n_pairs"],
                    "D_k_median": assembled["D_k_median"],
                    "D_k_mean": assembled["D_k_mean"],
                }
            )
        fit = fit_growth(curve)
        smoothing_payload[str(float(smoothing))] = {"curve": curve, "fit": fit, "verdict": fit["verdict"]}

    occupancy_files = sorted(CACHE_DIR.glob("occupancy_variable_k*.json"))
    occupancy = []
    if occupancy_files:
        by_k = {int(json.loads(p.read_text())["k"]): json.loads(p.read_text()) for p in occupancy_files}
        occupancy = [by_k[k] for k in K_VALUES if k in by_k]

    c1_pass = False
    if KNOWN_OUT.exists():
        known = json.loads(KNOWN_OUT.read_text())
        c1_pass = known.get("verdict_on_known_linear_truth") == "PASS_LINEAR"
    fixed_verdict = out.get("fixed_population_verdict")
    final_confirmed = fixed_verdict == "SUBLINEAR" and c1_pass
    smoothing_verdicts = {k: v["verdict"] for k, v in smoothing_payload.items()}
    out.update(
        {
            "original_variable_population_fit": artifact["chain_rule_joint_divergence"]["growth_fit"],
            "smoothing_sensitivity": smoothing_payload,
            "occupancy_by_k": occupancy,
            "occupancy_scope": "variable population matching the original X3 sampling rule PPI_LEN >= k",
            "smoothing_stability_statement": (
                "Verdict is stable across smoothing values 0, 0.5, and 1.0."
                if len(set(smoothing_verdicts.values())) == 1
                else "Verdict is not stable across smoothing values 0, 0.5, and 1.0."
            ),
            "adjudication_rule": ADJUDICATION_RULE,
            "final_adjudication": "CONFIRMED" if final_confirmed else "DOWNGRADED-TO-INCONCLUSIVE",
            "status": "COMPLETE" if occupancy and all(str(float(s)) in smoothing_payload for s in args.smoothing_values) else "PARTIAL_SMOOTHING_ASSEMBLED",
        }
    )
    atomic_write_json(FIXED_OUT, out)
    if KNOWN_OUT.exists():
        known = json.loads(KNOWN_OUT.read_text())
        known["final_adjudication"] = out["final_adjudication"]
        if known.get("status") == "KNOWN_TRUTH_COMPLETE":
            known["status"] = "COMPLETE"
        atomic_write_json(KNOWN_OUT, known)
    print(json.dumps({"smoothing_verdicts": smoothing_verdicts, "final_adjudication": out["final_adjudication"], "occupancy_rows": len(occupancy)}, sort_keys=True))
    return 0


def synthetic_phase(args: argparse.Namespace) -> int:
    artifact, pairs, merged, _ = load_inputs()
    known_payload = json.loads(KNOWN_OUT.read_text()) if KNOWN_OUT.exists() else {
        "runner_path": str(RUNNER_PATH),
        "lookup_report": {},
        "known_truth_control": {},
        "estimator_reproduces_published_medians": {},
        "verdict_on_known_linear_truth": None,
        "decisive_statement": DECISIVE_STATEMENT,
        "status": "PARTIAL_STARTED",
    }
    known_payload["runner_path"] = str(RUNNER_PATH)
    known_payload["decisive_statement"] = DECISIVE_STATEMENT
    ok, _ = reproduce(artifact, pairs, merged, args.tolerance, known_payload)
    if not ok:
        known_payload["status"] = "INADMISSIBLE_REPRODUCTION_FAILED"
        atomic_write_json(KNOWN_OUT, known_payload)
        return 2
    synthetic = synthetic_control(merged, args.seed)
    known_payload["known_truth_control"] = synthetic
    c1_pass = synthetic["plain_iid"]["verdict"] == "LINEAR" and synthetic["twin_real_occupancy"]["verdict"] == "LINEAR"
    known_payload["verdict_on_known_linear_truth"] = "PASS_LINEAR" if c1_pass else "FAIL_NOT_LINEAR"
    known_payload["status"] = "KNOWN_TRUTH_COMPLETE"
    atomic_write_json(KNOWN_OUT, known_payload)
    print("C1", json.dumps({"pass": c1_pass, "plain": synthetic["plain_iid"]["fit"], "twin": synthetic["twin_real_occupancy"]["fit"]}, sort_keys=True))
    return 0


def smoothing_sensitivity(pairs: dict, merged: dict, smoothing_values: list[float]) -> dict:
    out = {}
    for smoothing in smoothing_values:
        curve = []
        for k in K_VALUES:
            counts = real_counts_fast(merged, k, fixed_long=False)
            c = curve_from_counts_fast(pairs["rows"], counts, smoothing)
            curve.append({"k": k, "n_pairs": c["n_pairs"], "D_k_median": c["D_k_median"], "D_k_mean": c["D_k_mean"]})
        fit = fit_growth(curve)
        out[str(smoothing)] = {"curve": curve, "fit": fit, "verdict": fit["verdict"]}
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="all", choices=["all", "reproduce", "synthetic", "synthetic_k", "assemble_synthetic", "fixed", "fixed_k", "fixed_all_chunk", "assemble_fixed", "variable_k", "variable_bundle", "occupancy_k", "assemble_smoothing", "verify"])
    parser.add_argument("--tolerance", type=float, default=1e-9)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--k", type=int)
    parser.add_argument("--smoothing", type=float, default=0.5)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=1000000)
    parser.add_argument("--files", nargs="*")
    parser.add_argument("--fixed-long", action="store_true")
    parser.add_argument("--smoothing-values", nargs="*", type=float, default=[0.0, 0.5, 1.0])
    args = parser.parse_args()

    if args.phase == "synthetic":
        return synthetic_phase(args)
    if args.phase == "synthetic_k":
        return synthetic_k_phase(args)
    if args.phase == "assemble_synthetic":
        return assemble_synthetic_phase(args)
    if args.phase == "fixed_all_chunk":
        return fixed_all_chunk_phase(args)
    if args.phase == "assemble_fixed":
        return assemble_fixed_phase(args)
    if args.phase in {"fixed_k", "variable_k"}:
        return checkpoint_phase(args)
    if args.phase == "variable_bundle":
        return variable_bundle_phase(args)
    if args.phase == "occupancy_k":
        return occupancy_phase(args)
    if args.phase == "assemble_smoothing":
        return assemble_smoothing_phase(args)

    artifact, pairs, merged, cached_results = load_inputs()
    existing_result = {
        "runner_path": str(RUNNER_PATH),
        "lookup_report": {
            "existing_artifact_read": str(ARTIFACT),
            "artifact_sha256": sha256_file(ARTIFACT),
            "cache_dir": str(CACHE_DIR),
            "cache_files_found": sorted(p.name for p in CACHE_DIR.glob("*"))[:20],
            "cache_summary": "merged.pkl contains per-service 30-bit direction-prefix codes and PPI_LEN arrays; results.pkl contains cached per-k X3 outputs.",
            "deleted_runner_search": "prior log records /root/eibo/x3_tmp_runner.py temporary runner and failed cleanup/deletion attempt; /root/eibo/x3_controls.py did not exist before this run.",
        },
    }
    known_payload = {
        **existing_result,
        "known_truth_control": {},
        "estimator_reproduces_published_medians": {},
        "verdict_on_known_linear_truth": None,
        "decisive_statement": DECISIVE_STATEMENT,
        "status": "PARTIAL_STARTED",
    }
    fixed_payload = {
        "runner_path": str(RUNNER_PATH),
        "adjudication_rule": ADJUDICATION_RULE,
        "status": "PARTIAL_STARTED",
    }
    atomic_write_json(KNOWN_OUT, known_payload)
    atomic_write_json(FIXED_OUT, fixed_payload)

    ok, comparisons = reproduce(artifact, pairs, merged, args.tolerance, known_payload)
    if not ok:
        known_payload["status"] = "INADMISSIBLE_REPRODUCTION_FAILED"
        fixed_payload["status"] = "NOT_RUN_REPRODUCTION_FAILED"
        atomic_write_json(KNOWN_OUT, known_payload)
        atomic_write_json(FIXED_OUT, fixed_payload)
        print("STOP reproduction_failed")
        return 2

    known_payload["status"] = "REPRODUCTION_PASSED"
    atomic_write_json(KNOWN_OUT, known_payload)

    synthetic = synthetic_control(merged, args.seed)
    known_payload["known_truth_control"] = synthetic
    c1_pass = synthetic["plain_iid"]["verdict"] == "LINEAR" and synthetic["twin_real_occupancy"]["verdict"] == "LINEAR"
    known_payload["verdict_on_known_linear_truth"] = "PASS_LINEAR" if c1_pass else "FAIL_NOT_LINEAR"
    known_payload["status"] = "KNOWN_TRUTH_COMPLETE"
    atomic_write_json(KNOWN_OUT, known_payload)
    print("C1", json.dumps({"pass": c1_pass, "plain": synthetic["plain_iid"]["fit"], "twin": synthetic["twin_real_occupancy"]["fit"]}, sort_keys=True))

    fixed_data, fixed_rows = fixed_population_and_occupancy(artifact, pairs, merged)
    fixed_fit = fit_growth(fixed_data["fixed_population_curve"])
    original_fit = artifact["chain_rule_joint_divergence"]["growth_fit"]
    fixed_verdict = fixed_fit["verdict"]
    original_verdict = artifact["chain_rule_joint_divergence"]["adjudication"]
    smoothing = smoothing_sensitivity(pairs, merged, [0.0, 0.5, 1.0])
    survives = fixed_verdict == "SUBLINEAR"
    fixed_payload.update(
        {
            "fixed_population_curve": {
                "set_definition": "flows and pairs eligible at k=30; same population used for every k=5..30",
                "constant_pair_denominator": len(fixed_rows),
                "rows": fixed_data["fixed_population_curve"],
            },
            "original_variable_population_curve": fixed_data["original_variable_population_curve"],
            "fixed_population_fit": fixed_fit,
            "original_variable_population_fit": original_fit,
            "fixed_population_verdict": fixed_verdict,
            "composition_statement": (
                "Original SUBLINEAR survives the fixed-population control."
                if survives
                else "Original SUBLINEAR is absent under the fixed-population control; the original verdict is a composition artifact or otherwise not stable."
            ),
            "occupancy_by_k": fixed_data["occupancy_by_k"],
            "smoothing_sensitivity": smoothing,
            "adjudication_rule": ADJUDICATION_RULE,
        }
    )
    smoothing_verdicts = {k: v["verdict"] for k, v in smoothing.items()}
    final_confirmed = survives and c1_pass
    fixed_payload["final_adjudication"] = "CONFIRMED" if final_confirmed else "DOWNGRADED-TO-INCONCLUSIVE"
    fixed_payload["status"] = "COMPLETE"
    fixed_payload["smoothing_stability_statement"] = (
        "Verdict is stable across smoothing values 0, 0.5, and 1.0."
        if len(set(smoothing_verdicts.values())) == 1
        else "Verdict is not stable across smoothing values 0, 0.5, and 1.0."
    )
    atomic_write_json(FIXED_OUT, fixed_payload)
    known_payload["final_adjudication"] = fixed_payload["final_adjudication"]
    known_payload["status"] = "COMPLETE"
    atomic_write_json(KNOWN_OUT, known_payload)

    print("C2", json.dumps({"fixed_verdict": fixed_verdict, "original_verdict": original_verdict, "fit": fixed_fit}, sort_keys=True))
    print("C3", json.dumps({"smoothing_verdicts": smoothing_verdicts, "occupancy_first": fixed_data["occupancy_by_k"][0], "occupancy_last": fixed_data["occupancy_by_k"][-1]}, sort_keys=True))
    print("FINAL", fixed_payload["final_adjudication"])
    for path in [KNOWN_OUT, FIXED_OUT]:
        print("FILE", path, sha256_file(path), path.stat().st_size)
        json.loads(path.read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
