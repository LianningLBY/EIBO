#!/usr/bin/env python3
"""Q1 verdict from a per-pair absolute-TV count table.

The gate is an ABSOLUTE comparison, never a ratio:

    lower (L):  channel_tv(M, k=5) >  T(n_a, n_b)
    upper (U):  channel_tv(M, k=5) <  0.5 - radius(M, n_a, n_b)

Both thresholds are computed here, per pair, from the pair's own sample
sizes, at a COMMON confidence convention: alpha/2 per law (union bound over
the two laws) gives joint 1 - alpha for each side. The closed form
T(n) ~ 0.05 + c/sqrt(n) holds only for equal n, so we bisect the exact
Clopper-Pearson two-cell test instead.

Input JSON (produced upstream; raw reduction only, no analysis):
{
  "pairs": [
    {"service_a": str, "service_b": str, "M": int,
     "n_a": int, "n_b": int,          # eligible flows at k=5, per service
     "tv_k5_masked": float},          # TV between rung-M k=5 symbol laws
    ...
  ],
  "chosen_k": int, "alt_k": int,      # for provenance only
  "source": str, "label": str
}

Usage:
    python3 scripts/evaluate_q1_absolute.py <count_table.json> [--out report.json]
"""
import argparse
import json
import math
from collections import defaultdict

ALPHA = 0.05
# Each side of the gate is a statement about a PAIR, so it needs a union bound
# over the two laws: per-law alpha/2 gives joint 1-alpha. Both sides use the
# same convention -- if the lower side split alpha while the upper did not, one
# gate would claim two different confidence levels.
ALPHA_PER_LAW = ALPHA / 2
LOWER_THRESHOLD = 0.05  # eps_lo must exceed this for the lower side to fire
RUNGS = (1, 2, 4, 8, 16)
K_DEFAULT = 5  # rows may carry their own "k"; this is the fallback


def betacf(a, b, x):
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def betai(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lb = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    fr = math.exp(lb + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return fr * betacf(a, b, x) / a
    return 1.0 - fr * betacf(b, a, 1.0 - x) / b


def beta_inv(p, a, b):
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if betai(a, b, mid) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def cp_upper(k, m, alpha):
    """Clopper-Pearson one-sided upper limit for k successes in m trials."""
    if m <= 0:
        return 1.0
    if k >= m:
        return 1.0
    return beta_inv(1.0 - alpha, k + 1, m - k)


def eps_lo_two_cell(tv, n_a, n_b, alpha=ALPHA):
    """Optimal 2-cell test on P=(1-tv,tv), Q=(1-tv,0) with unequal samples.

    Under H0 the minimal misclassification probability is (1-tv)/2 for each
    law; each estimate is truncated at 0.5 (the value at tv=0) so the bound
    degenerates to 0 exactly when the two-cell test can no longer separate.
    """
    if tv <= 0.0 or n_a <= 0 or n_b <= 0:
        return 0.0
    p = (1.0 - tv) / 2.0
    u_a = cp_upper(p * n_a, n_a, alpha / 2.0)
    u_b = cp_upper(p * n_b, n_b, alpha / 2.0)
    return max(0.0, 1.0 - min(u_a, 0.5) - min(u_b, 0.5))


def t_of_n(n_a, n_b):
    """Smallest channel TV giving eps_lo > LOWER_THRESHOLD for these n."""
    if eps_lo_two_cell(0.5, n_a, n_b) <= LOWER_THRESHOLD:
        return None
    lo, hi = 0.0, 0.5
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if eps_lo_two_cell(mid, n_a, n_b) > LOWER_THRESHOLD:
            hi = mid
        else:
            lo = mid
    return hi


def radius_sum(M, n_a, n_b, k=K_DEFAULT, alpha_per_law=ALPHA_PER_LAW):
    """Two-sided concentration radius (sum over the two laws) at prefix length k.

    `k` MUST be passed per row. The alphabet is (2M)^k, so using the wrong k
    silently computes a radius for a different observation length -- at k=10
    the alphabet is (2M)^5 times larger than at k=5, which changes which rungs
    certify at all. `alpha_per_law` must be the PER-LAW level: the upper side
    needs the same joint confidence as the lower side, which uses alpha/2 per
    law via a union bound over the two laws; passing bare alpha here would make
    one gate claim joint 0.90 on one side and 0.95 on the other.
    """
    m = (2 * M) ** k
    c = math.sqrt(2 * math.log(2 / alpha_per_law))
    term_a = 0.5 * math.sqrt(m / n_a) + 0.5 * c / math.sqrt(n_a)
    term_b = 0.5 * math.sqrt(m / n_b) + 0.5 * c / math.sqrt(n_b)
    return term_a + term_b


def evaluate(table):
    by_rung_k = defaultdict(list)
    for row in table["pairs"]:
        by_rung_k[(row.get("k", K_DEFAULT), row["M"])].append(row)

    out = {
        "label": table.get("label", ""),
        "source": table.get("source", ""),
        "chosen_k": table.get("chosen_k"),
        "alt_k": table.get("alt_k"),
        "alpha": ALPHA,
        "alpha_per_law": ALPHA_PER_LAW,
        "confidence_convention": (
            "alpha/2 per law, union bound over the two laws => joint 1-alpha "
            "for EACH side; both sides use the same level"
        ),
        "lower_threshold_eps_lo": LOWER_THRESHOLD,
        "per_rung": [],
        "known_limitations": [
            "tv_k5_masked must be computed on the k=5-eligible subset with "
            "padding masked by PPI_LEN; unmasked values are not citable.",
            "eps_hi is not clipped: values >1 are reported raw and mean the "
            "certificate is lost, not that it is loose.",
        ],
    }

    for k in sorted({kk for kk, _ in by_rung_k}):
        for M in RUNGS:
            rows = by_rung_k.get((k, M), [])
            if not rows:
                out["per_rung"].append({"k": k, "M": M, "pairs": 0, "note": "no rows"})
                continue
            n_lower = n_upper = n_both = 0
            t_values, radii = [], []
            for row in rows:
                n_a, n_b = int(row["n_a"]), int(row["n_b"])
                tv = float(row.get("tv_masked", row.get("tv_k5_masked")))
                t_n = t_of_n(n_a, n_b)
                r = radius_sum(M, n_a, n_b, k)
                lower_ok = t_n is not None and tv > t_n
                upper_ok = tv < 0.5 - r
                if t_n is not None:
                    t_values.append(t_n)
                radii.append(r)
                n_lower += lower_ok
                n_upper += upper_ok
                n_both += (lower_ok and upper_ok)

            total = len(rows)
            out["per_rung"].append(
                {
                    "k": k,
                    "M": M,
                    "pairs": total,
                    "n_median": sorted(
                        int(min(r["n_a"], r["n_b"])) for r in rows
                    )[total // 2],
                    "lower_side_pairs": n_lower,
                    "lower_side_fraction": n_lower / total,
                    "upper_side_pairs": n_upper,
                    "upper_side_fraction": n_upper / total,
                    "gate_pairs_both": n_both,
                    "gate_fraction_both": n_both / total,
                    "T_n_median": sorted(t_values)[len(t_values) // 2] if t_values else None,
                    "radius_median": sorted(radii)[len(radii) // 2],
                }
        )
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("count_table")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(args.count_table) as fh:
        table = json.load(fh)
    report = evaluate(table)

    text = json.dumps(report, indent=1)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
