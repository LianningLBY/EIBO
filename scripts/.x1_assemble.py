#!/root/miniconda3/bin/python3
"""Rebuild the X1 headline table from existing raw and fresh intermediates."""

import hashlib
import inspect
import itertools
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, "/root/eibo/src")
from eibo.statcore import tv_upper_bound

RUNGS = (1, 2, 4, 8, 16)
KS = (5, 10, 15, 30)
PAIR_PATH = "/root/eibo/artifacts/q1_eps_lo_symbol_map.json"
FULL_N_LOWER_PATH = "/root/eibo/artifacts/q1_lower_side_full_n.json"
K5_PATH = "/root/eibo/artifacts/q1_absolute_counts.json"
K10_PATH = "/root/eibo/artifacts/q1_absolute_counts_k10.json"
K5_SUMMARY_PATH = "/root/eibo/artifacts/q1_absolute_summary.json"
K10_SUMMARY_PATH = "/root/eibo/artifacts/q1_absolute_k10_summary.json"
TMP_DIR = Path("/root/eibo/artifacts")
OUT_PATH = TMP_DIR / "x1_headline_table.json"
TARGET_ALPHA = 0.05
PER_LAW_ALPHA = TARGET_ALPHA / 2.0


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def quantile(values, q):
    vals = sorted(values)
    if not vals:
        return None
    pos = (len(vals) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return float(vals[lo])
    return float(vals[lo] + (vals[hi] - vals[lo]) * (pos - lo))


def main():
    print("tv_upper_bound_module_path=/root/eibo/src/eibo/statcore.py")
    print("tv_upper_bound_module_sha256=" + sha256("/root/eibo/src/eibo/statcore.py"))
    print("tv_upper_bound_signature=" + str(inspect.signature(tv_upper_bound)))
    print("configured_target_alpha=" + repr(TARGET_ALPHA))
    print("configured_per_law_alpha=" + repr(PER_LAW_ALPHA))

    prior = json.load(open(OUT_PATH)) if OUT_PATH.exists() else {}
    prior_cells = {
        (int(c["M"]), int(c["k"])): c
        for c in prior.get("headline_table_unified_calibre", [])
    }
    prior_m1k5 = prior_cells.get((1, 5), {})

    pair_rows = json.load(open(PAIR_PATH))["rows"]
    assert len(pair_rows) == 990
    print("pair_rows_asserted=990")
    lower_rows = json.load(open(FULL_N_LOWER_PATH))["rows"]
    assert len(lower_rows) == 990
    print("full_n_lower_rows_asserted=990")
    lower_by_pair = {
        (int(r["service_a"]), int(r["service_b"])): r for r in lower_rows
    }

    k5 = json.load(open(K5_PATH))["pairs"]
    k10 = json.load(open(K10_PATH))["pairs"]
    k5_old = {
        int(r["M"]): r
        for r in json.load(open(K5_SUMMARY_PATH))["per_rung"]
    }
    k10_old = {
        int(r["M"]): r
        for r in json.load(open(K10_SUMMARY_PATH))["per_rung"]
    }
    k5_by = {
        (int(r["service_a"]), int(r["service_b"]), int(r["M"])): r
        for r in k5
    }
    k10_by = {
        (int(r["service_a"]), int(r["service_b"]), int(r["M"])): r
        for r in k10
    }
    print("k5_rows=" + str(len(k5)) + " k10_rows=" + str(len(k10)))

    fresh = {}
    for k in (15, 30):
        for m in RUNGS:
            path = TMP_DIR / f".x1_k{k}_m{m}.json"
            doc = json.load(open(path))
            expected = 946 if k == 15 else 820
            assert doc["pair_count"] == expected
            assert len(doc["rows"]) == expected
            fresh[(k, m)] = {
                (int(r["service_a"]), int(r["service_b"])): r
                for r in doc["rows"]
            }
    print(
        "fresh_rows="
        + repr(
            {
                str(k): {str(m): len(fresh[(k, m)]) for m in RUNGS}
                for k in (15, 30)
            }
        )
    )

    denominators = {5: 990, 10: 990, 15: 946, 30: 820}
    cells = []
    all_lower_violations = []
    all_tv_violations = []
    lower_margins = []
    upper_margins = []
    effective_alphas = []

    for m in RUNGS:
        for k in KS:
            if k == 5:
                pair_map = {
                    (a, b): raw
                    for (a, b, raw_m), raw in k5_by.items()
                    if raw_m == m
                }
            elif k == 10:
                pair_map = {
                    (a, b): raw
                    for (a, b, raw_m), raw in k10_by.items()
                    if raw_m == m
                }
            else:
                pair_map = fresh[(k, m)]
            lower_is_measured = k == 5 and m == 1
            old = k5_old[m] if k == 5 else k10_old[m] if k == 10 else {}
            alphabet = (2 * m) ** k
            rows_for_cell = []
            radius_cache = {}

            def radius_for_n(n):
                key = int(n)
                if key not in radius_cache:
                    ref = tv_upper_bound(
                        itertools.repeat(0, key),
                        itertools.repeat(1, key),
                        alphabet_size=alphabet,
                        alpha=PER_LAW_ALPHA,
                    )
                    effective_alphas.append(float(ref.alpha))
                    radius_cache[key] = (float(ref.radius_1), float(ref.alpha))
                return radius_cache[key]

            for key, raw in pair_map.items():
                a, b = key
                n1 = int(raw["n_a"])
                n2 = int(raw["n_b"])
                if k == 5:
                    tv = float(raw["tv_k5_masked"])
                elif k == 10:
                    tv = float(raw["tv_k10_masked"])
                else:
                    tv = float(raw["tv_masked"])
                lo = (
                    float(lower_by_pair[key]["eps_lo"])
                    if lower_is_measured
                    else None
                )
                radius_1, alpha_1 = radius_for_n(n1)
                radius_2, alpha_2 = radius_for_n(n2)
                assert alpha_1 == alpha_2 == PER_LAW_ALPHA
                eps_hi = min(1.0, max(0.0, tv + radius_1 + radius_2))
                lower_pass = lo > 0.05 if lo is not None else None
                upper_pass = eps_hi < 0.5
                gate_pass = (
                    bool(lower_pass and upper_pass)
                    if lower_pass is not None
                    else None
                )
                if lo is not None and lo > eps_hi + 1e-12:
                    all_lower_violations.append(
                        {
                            "M": m,
                            "k": k,
                            "service_a": a,
                            "service_b": b,
                            "eps_lo": lo,
                            "eps_hi": eps_hi,
                        }
                    )
                if tv > eps_hi + 1e-12:
                    all_tv_violations.append(
                        {
                            "M": m,
                            "k": k,
                            "service_a": a,
                            "service_b": b,
                            "tv_hat": tv,
                            "eps_hi": eps_hi,
                        }
                    )
                if lo is not None:
                    lower_margins.append(
                        (
                            abs(lo - 0.05),
                            {
                                "service_a": a,
                                "service_b": b,
                                "value": lo,
                                "M": m,
                                "k": k,
                                "passing": lower_pass,
                            },
                        )
                    )
                upper_margins.append(
                    (
                        abs(eps_hi - 0.5),
                        {
                            "service_a": a,
                            "service_b": b,
                            "value": eps_hi,
                            "M": m,
                            "k": k,
                            "passing": upper_pass,
                        },
                    )
                )
                rows_for_cell.append(
                    {
                        "service_a": a,
                        "service_b": b,
                        "n_a": n1,
                        "n_b": n2,
                        "tv_hat": tv,
                        "eps_lo": lo,
                        "eps_hi": eps_hi,
                        "lower_side_measured": lo is not None,
                        "lower_pass": lower_pass,
                        "upper_pass": upper_pass,
                        "gate_pass": gate_pass,
                    }
                )

            upper_count = sum(r["upper_pass"] for r in rows_for_cell)
            lower_count = sum(
                r["lower_pass"]
                for r in rows_for_cell
                if r["lower_pass"] is not None
            )
            gate_values = [
                r["gate_pass"]
                for r in rows_for_cell
                if r["gate_pass"] is not None
            ]
            sat_count = sum(r["tv_hat"] >= 0.99 for r in rows_for_cell)
            cell = {
                "M": m,
                "k": k,
                "alphabet_cardinality": alphabet,
                "pair_denominator": denominators[k],
                "pairs_computed": len(rows_for_cell),
                "upper_alpha_per_law": PER_LAW_ALPHA,
                "upper_side_pairs": upper_count,
                "upper_side_fraction": upper_count / len(rows_for_cell),
                "lower_side_measured": lower_is_measured,
                "lower_side_measured_pairs": len(gate_values) if lower_is_measured else 0,
                "lower_side_pairs": lower_count if lower_is_measured else None,
                "lower_side_fraction": (
                    lower_count / len(rows_for_cell) if lower_is_measured else None
                ),
                "saturation_fraction_tv_ge_0_99": sat_count / len(rows_for_cell),
                "saturation_label": (
                    "INFORMATIVE" if upper_count > 0 else "CERTIFICATE_LOST"
                ),
                "upper_radius_median": quantile(
                    [r["eps_hi"] - r["tv_hat"] for r in rows_for_cell], 0.5
                ),
                "nearest_upper_margin": min(
                    (abs(r["eps_hi"] - 0.5) for r in rows_for_cell),
                    default=None,
                ),
            }
            if lower_is_measured:
                cell["gate_pairs_both"] = sum(gate_values)
                cell["gate_fraction_both"] = sum(gate_values) / len(gate_values)
            cells.append(cell)
            print(
                json.dumps(
                    {
                        "M": m,
                        "k": k,
                        "denominator": denominators[k],
                        "upper_side_pairs": upper_count,
                        "upper_side_fraction": upper_count / len(rows_for_cell),
                        "lower_side_measured": lower_is_measured,
                        "lower_side_pairs": lower_count if lower_is_measured else None,
                        "gate_pairs_both": sum(gate_values) if gate_values else None,
                        "gate_fraction_both": (
                            sum(gate_values) / len(gate_values)
                            if gate_values
                            else None
                        ),
                    },
                    sort_keys=True,
                )
            )

    assert len(cells) == 20
    assert set(effective_alphas) == {PER_LAW_ALPHA}
    effective_alpha = effective_alphas[0]
    print("effective_alpha_from_tv_upper_bound_result=" + repr(effective_alpha))
    print("effective_alpha_observation_count=" + str(len(effective_alphas)))

    m1k5_raw = [
        raw for (a, b, m), raw in k5_by.items() if m == 1
    ]

    def upper_pairs_for_alpha(alpha):
        cache = {}
        passing = set()
        for raw in m1k5_raw:
            n1 = int(raw["n_a"])
            n2 = int(raw["n_b"])
            cache.setdefault(
                n1,
                float(
                    tv_upper_bound(
                        itertools.repeat(0, n1),
                        itertools.repeat(1, n1),
                        alphabet_size=32,
                        alpha=alpha,
                    ).radius_1
                ),
            )
            cache.setdefault(
                n2,
                float(
                    tv_upper_bound(
                        itertools.repeat(0, n2),
                        itertools.repeat(1, n2),
                        alphabet_size=32,
                        alpha=alpha,
                    ).radius_1
                ),
            )
            eps_hi = min(
                1.0,
                max(
                    0.0,
                    float(raw["tv_k5_masked"]) + cache[n1] + cache[n2],
                ),
            )
            if eps_hi < 0.5:
                passing.add((int(raw["service_a"]), int(raw["service_b"])))
        return passing

    canonical_upper = upper_pairs_for_alpha(PER_LAW_ALPHA)
    unsplit_upper = upper_pairs_for_alpha(TARGET_ALPHA)
    full_lower = {
        (int(r["service_a"]), int(r["service_b"]))
        for r in lower_rows
        if bool(r["eps_lo_gt_0_05"])
    }
    capped_lower = {
        (int(r["service_a"]), int(r["service_b"]))
        for r in lower_rows
        if bool(r["capped_eps_lo_gt_0_05"])
    }
    two_by_two = [
        {
            "upper": "canonical",
            "lower": "full-n",
            "up": len(canonical_upper),
            "low": len(full_lower),
            "gate": len(canonical_upper & full_lower),
            "matches_x1": False,
        },
        {
            "upper": "unsplit",
            "lower": "full-n",
            "up": len(unsplit_upper),
            "low": len(full_lower),
            "gate": len(unsplit_upper & full_lower),
            "matches_x1": False,
        },
        {
            "upper": "canonical",
            "lower": "capped",
            "up": len(canonical_upper),
            "low": len(capped_lower),
            "gate": len(canonical_upper & capped_lower),
            "matches_x1": False,
        },
        {
            "upper": "unsplit",
            "lower": "capped",
            "up": len(unsplit_upper),
            "low": len(capped_lower),
            "gate": len(unsplit_upper & capped_lower),
            "matches_x1": True,
        },
    ]
    print("two_by_two=" + json.dumps(two_by_two, sort_keys=True))

    nearest_lower_pass = min(
        (x for x in lower_margins if x[1]["passing"]), default=(None, None)
    )[1]
    nearest_lower_fail = min(
        (x for x in lower_margins if not x[1]["passing"]), default=(None, None)
    )[1]
    nearest_upper_pass = min(
        (x for x in upper_margins if x[1]["passing"]), default=(None, None)
    )[1]
    nearest_upper_fail = min(
        (x for x in upper_margins if not x[1]["passing"]), default=(None, None)
    )[1]

    dead = prior.get("superseded_dead_numbers")
    if not dead:
        dead = {
            "upper_2x_inlined_radius": {
                "value": prior_m1k5.get("upper_side_pairs", 292),
                "convention": "2x inlined radius, omitting both 0.5 factors",
                "reason": "Superseded by the repository tv_upper_bound radius; it understates eps_hi and must not be used.",
            },
            "upper_ref_radius_wrong_alpha": {
                "value": prior_m1k5.get("upper_side_pairs_ref_radius", 342),
                "convention": "repository radius with unsplit alpha=0.05 per law",
                "reason": "Wrong confidence convention; the per-law call must use alpha/2=0.025.",
            },
            "lower_proxy_tv_hat_gt_Tn": {
                "value": prior_m1k5.get("lower_side_pairs", 987),
                "convention": "proxy tv_hat > T(n), the band's lower edge",
                "reason": "This is not a lower bound and is not a gate quantity.",
            },
            "lower_capped": {
                "value": prior_m1k5.get("lower_side_pairs_ref_radius", 985),
                "convention": "capped lower side at n=20,000",
                "reason": "Visible for sensitivity only; canonical X1 uses the full-n lower side.",
                "status": "NON-CANONICAL",
            },
            "historical_2x_proxy_gate": {
                "value": prior_m1k5.get("gate_pairs_both", 289),
                "convention": "2x upper radius plus proxy lower edge",
                "reason": "Two superseded conventions; not a valid gate.",
            },
            "historical_unsplit_capped_gate": {
                "value": prior_m1k5.get("gate_pairs_both_ref_radius", 337),
                "convention": "unsplit alpha=0.05 upper plus capped lower",
                "reason": "Matches the old X1 cell by coincidence of opposite errors; not canonical.",
            },
        }

    artifact = dict(prior)
    artifact.update(
        {
            "headline_table_unified_calibre": cells,
            "per_rung": {
                str(m): [c for c in cells if c["M"] == m] for m in RUNGS
            },
            "radius_convention": "The live upper_side_pairs field is computed by eibo.statcore.tv_upper_bound at the effective per-law alpha recorded in effective_alpha. Historical upper and lower conventions are suppressed in superseded_dead_numbers and are not peer fields.",
            "alpha": TARGET_ALPHA,
            "alpha_law": PER_LAW_ALPHA,
            "alpha_convention": "alpha=0.05; per-law alpha/2=0.025 on both sides; union bound over the two laws gives joint 0.95 for EACH side. Numbers without a stated split are NOT citable.",
            "effective_alpha": {
                "value": effective_alpha,
                "source": "TVUpperBoundResult.alpha returned by eibo.statcore.tv_upper_bound at the assembler call site",
                "call_argument": "PER_LAW_ALPHA passed as alpha=PER_LAW_ALPHA",
                "observed_call_count": len(effective_alphas),
            },
            "eps_lo_le_eps_hi_violations": len(all_lower_violations),
            "eps_lo_le_eps_hi_violation_rows": all_lower_violations,
            "tv_hat_le_eps_hi_violations": len(all_tv_violations),
            "tv_hat_le_eps_hi_violation_rows": all_tv_violations,
            "nearest_margins": {
                "lower_threshold": {
                    "threshold": 0.05,
                    "nearest_passing": nearest_lower_pass,
                    "nearest_failing": nearest_lower_fail,
                },
                "upper_threshold": {
                    "threshold": 0.5,
                    "nearest_passing": nearest_upper_pass,
                    "nearest_failing": nearest_upper_fail,
                },
            },
            "tv_upper_bound_call": "sys.path.insert(0, '/root/eibo/src'); from eibo.statcore import tv_upper_bound; tv_upper_bound(sample1, sample2, alphabet_size=(2*M)**k, alpha=0.025)",
            "tv_upper_bound_module_path": "/root/eibo/src/eibo/statcore.py",
            "tv_upper_bound_module_sha256": sha256("/root/eibo/src/eibo/statcore.py"),
            "pair_source": {
                "path": FULL_N_LOWER_PATH,
                "key": "rows",
                "row_count": len(lower_rows),
                "row_keys": list(lower_rows[0].keys()),
                "raw_tv_source": PAIR_PATH,
            },
            "lower_side_guarantee": "Only k=5/M=1 carries the measured asymptotic HPLB from q1_lower_side_full_n.json. k=5/M>1 and all k=10/15/30 cells do not carry a measured lower side in this artifact; no lower side was silently reused across k or M.",
            "lower_side_summary_caveat": "A summary field lower_side_pairs = 990 is not evidence of per-pair lower-bound values for another k or M.",
            "number_of_table_cells": len(cells),
            "superseded_dead_numbers": dead,
            "two_by_two": two_by_two,
            "flipped_pairs": {
                "upper": [[22, 36], [32, 52]],
                "lower": [[21, 23]],
            },
            "two_convention_errors_opposite_directions": "X1's 337 was wrong on BOTH sides, and the two errors point in OPPOSITE directions and nearly cancel. The upper error alone would give 338 (+2); the lower error alone would give 335 (-1); together they give 337 (+1). So '337 vs 336, close enough' is doubly wrong: the net +1 MASKS two independent convention defects. A one-count agreement at the total level is not evidence that either side is right -- which is exactly why a count-level check would have missed this, and why the differing pairs must be NAMED.",
            "coincidence_note": "The equality of the unsplit 342 upper count with the separate PHIST packet-cell count is coincidental: these are different objects and different channels. That coincidence is precisely why the error looked plausible and a count-level check missed it.",
            "alpha_convention_requirement": "The upper-side radius must be computed at per-law alpha/2 = 0.025, union-bounded over the two laws, giving joint 0.95 for each side. The UNSPLIT alpha = 0.05 form has no union bound and shifts pairs near the threshold; it produced 342 rather than 340. The repo already guards the mirror-image over-split (alpha/4, which gives 335); this artifact now records the under-split as well.",
        }
    )
    artifact["gate_convention_sensitivity"] = {
        "canonical": {
            "upper": len(canonical_upper),
            "lower": len(full_lower),
            "gate": len(canonical_upper & full_lower),
            "fraction": len(canonical_upper & full_lower) / len(lower_rows),
        },
        "capped_non_canonical": {
            "upper": len(canonical_upper),
            "lower": len(capped_lower),
            "gate": len(canonical_upper & capped_lower),
            "fraction": len(canonical_upper & capped_lower) / len(lower_rows),
        },
        "boundary_pair": [21, 23],
        "status": "NON-CANONICAL capped variant retained for sensitivity only",
    }

    tmp = str(OUT_PATH) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, OUT_PATH)
    print("eps_lo_le_eps_hi_violations=" + str(len(all_lower_violations)))
    print("tv_hat_le_eps_hi_violations=" + str(len(all_tv_violations)))
    print("nearest_margins=" + json.dumps(artifact["nearest_margins"], sort_keys=True))
    print("rebuilt_20_cell_table=" + json.dumps(cells, sort_keys=True))
    print("sha256sum=" + sha256(str(OUT_PATH)) + "  " + str(OUT_PATH))


if __name__ == "__main__":
    main()
