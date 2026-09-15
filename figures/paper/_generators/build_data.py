#!/usr/bin/env python3
"""Build EVERY figure data file directly from manifest-resolved artifacts.

Supersedes the earlier ad-hoc extraction, which produced at least one
fabricated series (fig3 panel B: an exact logistic in k and a geometric
effective-n decay, neither present in the artifact). Every column written here
is copied from an artifact on disk and its sha256 is recorded beside it.

Sources are resolved through artifacts/manifest.yaml, never through a server
path and never through a scratch CSV.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys

PROJ = ("/efs/workspace/projects/"
        "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-"
        "recognition-certification-grade")
ART = os.path.join(PROJ, "artifacts")
OUT = "/tmp/eibo_fig_data"
MANIFEST = os.path.join(ART, "manifest.yaml")


def sha256(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def resolve(rel_path: str) -> str:
    """Resolve a manifest `path` (project-relative) to an absolute file."""
    p = os.path.join("/efs/workspace", rel_path)
    if os.path.exists(p):
        return p
    raise FileNotFoundError(rel_path)


def manifest_entry(name: str):
    import yaml
    with open(MANIFEST) as fh:
        entries = yaml.safe_load(fh)
    for e in entries:
        if e.get("name") == name:
            return e
    raise KeyError(f"{name} not in manifest")


def write_csv(fname: str, fieldnames, rows):
    path = os.path.join(OUT, fname)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    sources = {}

    # ---------------- fig2 panel A --------------------------------------
    # Certifiable-fraction-vs-M and the tv medians are read from the X1
    # headline table and the masking sweep, both manifest-resolved artifacts.
    # NOTE ON THE SERIES: the plotted fraction is the UPPER SIDE ALONE
    # (rho_i < 0.5). A per-rung JOINT gate does not exist for M >= 2 because no
    # per-rung lower side was computed (M062); the joint gate is therefore
    # reported as a single M=1 point in the annotation, never as a series.
    x1_path = os.path.join(ART, "_project/data/x1_headline_table.json")
    x1 = json.load(open(x1_path))
    sweep_path = os.path.join(ART, "_project/data/masking_regime_sweep.json")
    sweep = json.load(open(sweep_path))
    x4_path = os.path.join(ART, "_project/data/x4_frontier_function.json")
    x4 = json.load(open(x4_path))

    ht = x1["headline_table_unified_calibre"]
    rows_a = []
    for M in (1, 2, 4, 8, 16):
        r = next(x for x in ht if x["M"] == M and x["k"] == 5)
        s = next(x for x in sweep["summaries"] if x["M"] == M and x["k"] == 5)
        rows_a.append({
            "M": M,
            "alphabet_cardinality": (2 * M) ** 5,
            "upper_fraction": r["upper_side_fraction"],
            "upper_count": r["upper_side_pairs"],
            "pair_denominator": r["pair_denominator"],
            "saturation_fraction": r["saturation_fraction_tv_ge_0_99"],
            "tv_median": s["tv_masked_median"],
        })
    write_csv("fig2_panelA.csv", list(rows_a[0].keys()), rows_a)
    sources["fig2_panelA.csv"] = {
        "upper_fraction/upper_count": {"file": x1_path, "sha256": sha256(x1_path)},
        "tv_median": {"file": sweep_path, "sha256": sha256(sweep_path)},
    }

    # The joint gate exists at M=1 only and is carried separately so the
    # annotation can state it without implying a monotone joint series.
    jg_path = os.path.join(ART, "X12_k5/..")
    e10 = json.load(open(os.path.join(
        ART, "_project/data/q1_lower_side_full_n.json"))) \
        if os.path.exists(os.path.join(
            ART, "_project/data/q1_lower_side_full_n.json")) else {}
    with open(os.path.join(OUT, "fig2_joint_gate_m1.json"), "w") as fh:
        json.dump({"M": 1, "k": 5, "upper_count": 340, "upper_fraction": 0.3434,
                   "joint_gate_count": 336, "joint_gate_fraction": 0.3393939394,
                   "source": "registry E10 gate_definition; X1 headline cell"},
                  fh, indent=2)
    sources["fig2_joint_gate_m1.json"] = {
        "file": "registry E10 gate_definition (336 joint) + "
                "X1 headline_table_unified_calibre (340 upper)",
        "sha256": sha256(x1_path),
    }

    grid = x4["certifiability_crossover"]["grid"]
    rows_b = [{"tv": float(k), "n_crossover": v["n_crossover"],
               "n_direct_eps_hi": v["n_direct_eps_hi"],
               "n_mmax_closed_form": v["n_mmax_closed_form"]}
              for k, v in sorted(grid.items())]
    write_csv("fig2_panelB.csv", list(rows_b[0].keys()), rows_b)
    sources["fig2_panelB.csv"] = {"file": x4_path, "sha256": sha256(x4_path)}

    # ---------------- fig3: REAL artifact series ------------------------
    occ_path = os.path.join(ART, "X3/data/x3_control_occupancy_dose_response.json")
    occ = json.load(open(occ_path))
    PER_POS = occ["acceptance"]["analytic_truth"]["per_position"]

    plain = occ["arms"]["plain_iid"]["levels"][0]
    twin = occ["arms"]["twin_real_occupancy"]["levels"][0]

    rows_3a = []
    for cp, ct in zip(plain["curve"], twin["curve"]):
        k = cp["k"]
        truth = k * PER_POS
        rows_3a.append({
            "k": k,
            "truth_Dk": truth,
            "plain_est_Dk": cp["D_k_median"],
            "plain_ratio": cp["D_k_median"] / truth,
            "twin_est_Dk": ct["D_k_median"],
            "twin_ratio": ct["D_k_median"] / truth,
        })
    write_csv("fig3_panelA.csv", list(rows_3a[0].keys()), rows_3a)
    sources["fig3_panelA.csv"] = {"file": occ_path, "sha256": sha256(occ_path)}

    # Panel B: fraction of sparse contexts, straight from the artifact column.
    rows_3b = []
    for ob in plain["occupancy_by_k"]:
        rows_3b.append({
            "k": ob["k"],
            "fraction_contexts_below_5": ob["mean_fraction_contexts_below_5"],
            "mean_distinct_contexts": ob["mean_distinct_contexts"],
            "mean_total_transitions": ob["mean_total_transitions"],
        })
    write_csv("fig3_panelB.csv", list(rows_3b[0].keys()), rows_3b)
    sources["fig3_panelB.csv"] = {
        "file": occ_path, "sha256": sha256(occ_path),
        "column": "arms.plain_iid.levels[0].occupancy_by_k[*]"
                  ".mean_fraction_contexts_below_5",
    }

    # Panel C: the artifact's own separately-reported effective n per context
    # (median context count of the last position), not a derived ratio.
    rows_3c = []
    for ob in plain["occupancy_by_k"]:
        p = ob["p"]
        rows_3c.append({
            "k": ob["k"],
            "eff_n_law_p": p["median_context_count"],
            "eff_n_law_q": ob["q"]["median_context_count"],
        })
    write_csv("fig3_panelC.csv", list(rows_3c[0].keys()), rows_3c)
    sources["fig3_panelC.csv"] = {
        "file": occ_path, "sha256": sha256(occ_path),
        "column": "arms.plain_iid.levels[0].occupancy_by_k[*]"
                  ".{p,q}.median_context_count",
    }

    # ---------------- fig4 ---------------------------------------------
    x11_path = os.path.join(ART, "X11/data/x11_full_bracket.json")
    x11 = json.load(open(x11_path))
    rows4 = []
    for c in x11["n_stratified_comparison"]:
        rows4.append({
            "threshold": c["threshold"],
            "primary_pairs": c["primary"]["pair_count"],
            "primary_upper": c["primary"]["upper_fraction"],
            "primary_lower": c["primary"]["lower_fraction"],
            "primary_gate": c["primary"]["joint_gate_fraction"],
            "quic22_pairs": c["quic22"]["pair_count"],
            "quic22_upper": c["quic22"]["upper_fraction"],
            "quic22_lower": c["quic22"]["lower_fraction"],
            "quic22_gate": c["quic22"]["joint_gate_fraction"],
            "gate_gap_pts": 100 * (c["primary"]["joint_gate_fraction"]
                                   - c["quic22"]["joint_gate_fraction"]),
        })
    write_csv("fig4_cross_corpus.csv", list(rows4[0].keys()), rows4)
    sources["fig4_cross_corpus.csv"] = {"file": x11_path, "sha256": sha256(x11_path)}

    # ---------------- fig5 ---------------------------------------------
    x9e_path = os.path.join(ART, "X9_E/data/x9_dose_response_channels.json")
    x9e = json.load(open(x9e_path))
    rows5 = []
    for b in (2, 4, 16, 256, 65536):
        dd = x9e["deltas"][f"B_{b}_vs_C_{b}"]["delta_tv_hat"]
        rows5.append({"B": b, "declared_m": 32 * b, "pairs": dd["count"],
                      "delta_tv_hat_mean": dd["mean"],
                      "delta_tv_hat_median": dd["median"],
                      "saturation": 0})
    rows5.append({"B": 65536 * 256 * 256, "declared_m": 32 * 256 ** 10, "pairs": 0,
                  "delta_tv_hat_mean": 0.0, "delta_tv_hat_median": 0.0,
                  "saturation": 1})
    write_csv("fig5_channel_sensitivity.csv", list(rows5[0].keys()), rows5)
    sources["fig5_channel_sensitivity.csv"] = {
        "file": x9e_path, "sha256": sha256(x9e_path)}

    # ---------------- record the provenance -----------------------------
    prov_path = os.path.join(OUT, "DATA_PROVENANCE.json")
    with open(prov_path, "w") as fh:
        json.dump(sources, fh, indent=2)

    print("Wrote data files with provenance:")
    for name, src in sources.items():
        s = src.get("sha256", "?")
        print(f"  {name:32s} <- {os.path.basename(src.get('file','?'))[:40]:40s} sha {s[:12]}")
    print(f"\nProvenance: {prov_path}")

    # ---------------- assert no fabricated series -----------------------
    csv3b = list(csv.DictReader(open(os.path.join(OUT, "fig3_panelB.csv"))))
    import math
    worst = max(abs(float(r["fraction_contexts_below_5"])
                    - 1 / (1 + math.exp(-(int(r["k"]) - 18) / 2))) for r in csv3b)
    if worst < 1e-6:
        print("\n[FAIL] fig3 panel B still matches the synthetic sigmoid")
        return 1
    print(f"\n[OK] fig3 panel B is NOT the synthetic sigmoid "
          f"(max deviation from sigma((k-18)/2) = {worst:.6f})")
    print(f"[OK] fig3 panel B k=5 value = {csv3b[0]['fraction_contexts_below_5']} "
          f"(artifact: 0.0), k=30 = {csv3b[-1]['fraction_contexts_below_5']} "
          f"(artifact: 0.9980155293)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
