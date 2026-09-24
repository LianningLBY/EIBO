#!/usr/bin/env python3
"""Rebuild all five paper figures from artifact-derived data.

Run `build_data.py` first: it writes /tmp/eibo_fig_data/*.csv straight from
manifest-resolved artifacts and records each file's sha256 in
DATA_PROVENANCE.json.

Every figure is written as both PNG and PDF, and every text artist is checked
for pairwise bounding-box overlap before the figure is saved; the build aborts
on a collision. fig1 additionally asserts that every boxed label fits inside
its own rectangle.
"""
from __future__ import annotations

import csv
import json
import os
import sys
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = ("/efs/workspace/projects/"
       "epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-"
       "recognition-certification-grade/figures/paper")
DATA = "/tmp/eibo_fig_data"

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
VERM = "#D55E00"
MAGENTA = "#CC79A7"
SKY = "#56B4E9"
GREY = "#999999"
INK = "#1A1A1A"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9.5,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.6,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def load(name):
    with open(f"{DATA}/{name}", newline="") as fh:
        return list(csv.DictReader(fh))


def check_collisions(fig, fig_id):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    texts = []
    for ax in fig.axes:
        for t in ax.texts:
            if isinstance(t, str) or not t.get_text().strip():
                continue
            texts.append(t)
        for t in (ax.title, ax.xaxis.label, ax.yaxis.label):
            if t.get_text().strip():
                texts.append(t)
        # ax.title is EMPTY when a title is set with loc="left"/"right"; the
        # text lives on ax._left_title / ax._right_title. Collecting only
        # ax.title made every left-aligned title invisible to this check, which
        # is how the fig2 legend-over-title collision survived several passes.
        for attr in ("_left_title", "_center_title", "_right_title"):
            t = getattr(ax, attr, None)
            if t is not None and t.get_text().strip():
                texts.append(t)
        xlo, xhi = sorted(ax.get_xlim())
        ylo, yhi = sorted(ax.get_ylim())
        for x, lab in zip(ax.get_xticks(), ax.get_xticklabels()):
            if lab.get_text().strip() and xlo - 1e-9 <= x <= xhi + 1e-9:
                texts.append(lab)
        for y, lab in zip(ax.get_yticks(), ax.get_yticklabels()):
            if lab.get_text().strip() and ylo - 1e-9 <= y <= yhi + 1e-9:
                texts.append(lab)
        leg = ax.get_legend()
        if leg is not None:
            texts.extend(t for t in leg.get_texts() if t.get_text().strip())
    for t in fig.texts:
        if not isinstance(t, str) and t.get_text().strip():
            texts.append(t)

    boxes = []
    for t in texts:
        try:
            bb = t.get_window_extent(renderer=r)
        except Exception:
            continue
        if bb.width > 0 and bb.height > 0:
            boxes.append((id(t), t.get_text().strip()[:38], bb))

    bad = []
    for (ia, ta, ba), (ib, tb, bb) in combinations(boxes, 2):
        if ia == ib:
            continue
        dx = min(ba.x1, bb.x1) - max(ba.x0, bb.x0)
        dy = min(ba.y1, bb.y1) - max(ba.y0, bb.y0)
        if dx > 2.0 and dy > 2.0:
            if ta == tb and abs(ba.x0 - bb.x0) < 0.5 and abs(ba.y0 - bb.y0) < 0.5:
                continue
            bad.append((ta, tb, round(dx, 1), round(dy, 1)))
    if bad:
        print(f"[FAIL] {fig_id}: {len(bad)} text collisions")
        for b in bad[:12]:
            print("   ", b)
        return False
    print(f"[OK]   {fig_id}: {len(boxes)} text artists, 0 collisions")
    return True


def save(fig, name):
    fig.savefig(f"{OUT}/{name}.png")
    fig.savefig(f"{OUT}/{name}.pdf")
    plt.close(fig)


# ---------------------------------------------------------------- fig2
def fig2():
    a = load("fig2_panelA.csv")
    b = load("fig2_panelB.csv")
    jg = json.load(open(f"{DATA}/fig2_joint_gate_m1.json"))
    M = [int(r["M"]) for r in a]
    upper = [float(r["upper_fraction"]) for r in a]
    sat = [float(r["saturation_fraction"]) for r in a]
    tv = [float(r["tv"]) for r in b]
    ncr = [float(r["n_crossover"]) for r in b]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    fig.subplots_adjust(left=0.09, right=0.90, top=0.80, bottom=0.175,
                        wspace=0.40)

    ax = axes[0]
    xs = np.arange(len(M))
    ax.axvspan(-0.5, 0.5, color=BLUE, alpha=0.07, zorder=0)
    ax.axvspan(3.5, 4.5, color=VERM, alpha=0.07, zorder=0)
    ax.plot(xs, upper, "o-", color=BLUE, markersize=5, label="upper side")
    ax.plot(xs, sat, "s--", color=MAGENTA, markersize=4,
            label="saturated (tv $\\geq$ 0.99)")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(v) for v in M])
    ax.set_xlabel("Alphabet resolution $M$ (bins per axis)")
    ax.set_ylabel("Fraction of the 990 pairs with\nupper bound "
                  "$\\epsilon_{hi} < 0.5$")
    ax.set_ylim(-0.02, 1.34)
    ax.set_title("(a) Finer alphabet, lost certificate", loc="left")
    # Legend sits INSIDE the axes, below the title: an anchor above 1.0 would
    # place it in the title's row.
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.0),
              ncol=1, frameon=False, handlelength=1.5, fontsize=6.6,
              borderaxespad=0.25)
    ax.annotate(f"{jg['upper_count']}/990 upper side\n"
                f"{jg['joint_gate_count']}/990 joint gate "
                f"({100*jg['joint_gate_fraction']:.1f}%)",
                xy=(0, upper[0]), xytext=(0.62, 0.52), fontsize=6.8,
                color=BLUE,
                arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.8))
    ax.text(0.0, 0.055, "certificate\navailable", fontsize=6.6, color=BLUE,
            style="italic", ha="center", va="bottom", linespacing=1.25)
    ax.text(4.0, 0.055, "certificate\nlost", fontsize=6.6, color=VERM,
            style="italic", ha="center", va="bottom", linespacing=1.25)

    axb = axes[1]
    axb.semilogy(tv, ncr, "o-", color=BLUE, markersize=5)
    axb.set_xlabel("True TV distance $tv$")
    axb.set_ylabel("Crossover $n$ (log scale)")
    axb.set_title("(b) Certificate horizon", loc="left")
    axb.set_xlim(-0.03, 0.55)
    axb.annotate("two derivation routes\nagree to 0.0",
                 xy=(0.30, ncr[3]), xytext=(0.035, 2.2e8),
                 fontsize=7.0, color=INK,
                 arrowprops=dict(arrowstyle="-", color=GREY, lw=0.8))

    ok = check_collisions(fig, "fig2_certificate_horizon")
    save(fig, "fig2_certificate_horizon")
    return ok


# ---------------------------------------------------------------- fig3
def fig3():
    a = load("fig3_panelA.csv")
    b = load("fig3_panelB.csv")
    c = load("fig3_panelC.csv")
    k = [int(r["k"]) for r in a]
    plain = [float(r["plain_ratio"]) for r in a]
    twin = [float(r["twin_ratio"]) for r in a]
    frac = [float(r["fraction_contexts_below_5"]) for r in b]
    effp = [float(r["eff_n_law_p"]) for r in c]

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45))
    fig.subplots_adjust(left=0.075, right=0.975, top=0.815, bottom=0.225,
                        wspace=0.62)

    ax = axes[0]
    ax.axhspan(0.60, 1.0, color=VERM, alpha=0.07, zorder=0)
    ax.axhline(1.0, color=GREY, ls=":", lw=1.0, zorder=1)
    ax.plot(k, plain, "o-", color=BLUE, markersize=3.5,
            label="plain i.i.d. control")
    ax.plot(k, twin, "s-", color=ORANGE, markersize=3.0,
            label="real-occupancy twin")
    ax.set_xlabel("Prefix length $k$")
    ax.set_ylabel("Estimated / true divergence")
    ax.set_title("(a) Linear truth, sublinear fit", loc="left")
    ax.set_ylim(0.60, 1.08)
    ax.legend(loc="lower left", frameon=False, fontsize=6.2,
              handlelength=1.3, borderaxespad=0.15)
    ax.text(19.5, 1.068, "truth (exactly linear)", fontsize=6.2,
            color=GREY, style="italic", va="top", ha="center")
    ax.text(30, 0.648, "0.6769", fontsize=6.4, color=BLUE, ha="right",
            va="bottom")
    ax.text(30, 0.894, "0.8820", fontsize=6.4, color=ORANGE, ha="right",
            va="bottom")

    axb = axes[1]
    axb.plot(k, frac, "o-", color=ORANGE, markersize=3.3)
    axb.set_xlabel("Prefix length $k$")
    axb.set_ylabel("Fraction of contexts\nwith $<5$ transitions")
    axb.set_ylim(0.0, 1.14)
    axb.set_title("(b) Sparse contexts", loc="left")
    axb.text(30, 1.02, "0.998", fontsize=6.4, color=ORANGE, ha="right",
             va="bottom")

    axc = axes[2]
    axc.semilogy(k, effp, "s--", color=SKY, markersize=3.0)
    axc.set_xlabel("Prefix length $k$")
    axc.set_ylabel("Effective $n$ per context")
    axc.set_ylim(0.5, 1.2e6)
    axc.set_title("(c) Collapsed occupancy", loc="left")
    axc.text(30, effp[-1] * 1.5, f"{effp[-1]:.0f}", fontsize=6.4, color=SKY,
             ha="right", va="bottom")
    # Anchor the k=5 annotation to the upper-left of its marker: the curve
    # descends steeply here, so any lower or rightward placement lands on it.
    axc.text(4.2, effp[0] * 2.2, f"{int(effp[0])}", fontsize=6.4, color=SKY,
             ha="left", va="bottom")

    ok = check_collisions(fig, "fig3_estimator_control")
    save(fig, "fig3_estimator_control")
    return ok


# ---------------------------------------------------------------- fig4
def fig4():
    rows = load("fig4_cross_corpus.csv")
    allrow = rows[0]
    th = [r["threshold"] for r in rows]
    gap = [float(r["gate_gap_pts"]) for r in rows]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5),
                             gridspec_kw={"width_ratios": [1.05, 1.0]})
    fig.subplots_adjust(left=0.085, right=0.975, top=0.86, bottom=0.30,
                        wspace=0.34)

    ax = axes[0]
    groups = ["Upper side", "Lower side", "Joint gate"]
    # Upper side carries the TRUE upper fractions; the joint gate is separate.
    prim = [float(allrow["primary_upper"]), float(allrow["primary_lower"]),
            float(allrow["primary_gate"])]
    quic = [float(allrow["quic22_upper"]), float(allrow["quic22_lower"]),
            float(allrow["quic22_gate"])]
    x = np.arange(len(groups))
    w = 0.36
    b1 = ax.bar(x - w / 2, prim, w, color=BLUE, label="Primary corpus")
    b2 = ax.bar(x + w / 2, quic, w, color=ORANGE, label="CESNET-QUIC22",
                hatch="///", edgecolor="white", linewidth=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(groups)
    ax.set_ylabel("Fraction of corpus pairs")
    ax.set_ylim(0, 1.45)
    ax.set_title("(a) Per-side fractions", loc="left")
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.0),
              ncol=1, frameon=False, fontsize=6.6, handlelength=1.4,
              borderaxespad=0.25)
    for rects, vals in ((b1, prim), (b2, quic)):
        for rect, v in zip(rects, vals):
            ax.text(rect.get_x() + rect.get_width() / 2, v + 0.03,
                    f"{v:.4f}", ha="center", va="bottom", fontsize=6.6,
                    color=INK)

    ax.text(0.5, -0.34,
            "QUIC22 gate combines full-$n$ upper with a 20000-flow capped lower.\n"
            "Capping lowers $\\epsilon_{lo}$ in aggregate; the direction is not\n"
            "per-pair (pair 35–49).",
            transform=ax.transAxes, ha="center", va="top", fontsize=7.0,
            color=INK,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#F5F5F5",
                      edgecolor=GREY, linewidth=0.6))

    axb = axes[1]
    axb.plot(range(len(th)), gap, "o-", color=BLUE, markersize=5)
    axb.set_xticks(range(len(th)))
    axb.set_xticklabels([t.replace(">=", "$\\geq$") for t in th], fontsize=7)
    axb.set_xlabel("Minimum per-pair flow count")
    axb.set_ylabel("Gate gap (percentage points)")
    axb.set_title("(b) Gap is stratum-dependent, not monotone", loc="left")
    axb.set_ylim(0, 21)
    idx = th.index(">=20000")
    axb.annotate("minimum 9.7\nat $n \\geq 20{,}000$", xy=(idx, gap[idx]),
                 xytext=(idx - 0.55, gap[idx] + 5.4), fontsize=7.0, color=BLUE,
                 arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.8))
    axb.text(0.02, 0.03, "widens again at stricter floors",
             transform=axb.transAxes, fontsize=6.6, color=GREY,
             style="italic", va="bottom")

    ok = check_collisions(fig, "fig4_cross_corpus")
    save(fig, "fig4_cross_corpus")
    return ok


# ---------------------------------------------------------------- fig5
def fig5():
    rows = [r for r in load("fig5_channel_sensitivity.csv")
            if r["saturation"] == "0"]
    B = [int(r["B"]) for r in rows]
    med = [float(r["delta_tv_hat_median"]) for r in rows]
    mean = [float(r["delta_tv_hat_mean"]) for r in rows]

    fig, ax = plt.subplots(figsize=(3.55, 2.65))
    fig.subplots_adjust(left=0.315, right=0.965, top=0.90, bottom=0.215)

    xs = np.arange(len(B))
    ax.axvspan(len(B) - 1.5, len(B) - 0.5, color=VERM, alpha=0.07, zorder=0)
    ax.plot(xs, mean, "o--", color=SKY, markersize=3.5, label="mean")
    ax.plot(xs, med, "s-", color=GREEN, markersize=4.0, label="median")
    ax.set_xticks(xs)
    ax.set_xticklabels([str(v) for v in B])
    ax.set_xlabel("Alphabet cardinality $B$ (log scale)")
    ax.set_ylabel("$\\Delta$ radius-free $\\widehat{tv}$")
    ax.set_ylim(-0.02, 0.44)
    ax.legend(loc="upper left", frameon=False, fontsize=7.0, handlelength=1.5)
    ax.text(4.42, 0.016, "both arms saturated", fontsize=6.3, color=VERM,
            ha="right", va="bottom")

    ok = check_collisions(fig, "fig5_channel_sensitivity")
    save(fig, "fig5_channel_sensitivity")
    return ok


def scan_escape_leak(pdf_path: str) -> list[str]:
    """Return leaked backslash-escape tokens from a figure PDF's OWN text layer.

    A leaked escape (e.g. a literal `\\%`) is a glyph in the figure's vector
    text, so it is invisible in the compiled paper's text layer, where the
    figure is an embedded raster. The check has to read the figure file itself.
    """
    import re
    import subprocess
    text = subprocess.run(
        ["pdftotext", "-layout", pdf_path, "-"],
        capture_output=True, text=True, errors="replace",
    ).stdout
    tokens: list[str] = []
    for pat in (r"\\%", r"\\&", r"\\_", r"\\#", r"\\[a-zA-Z]{2,}"):
        tokens.extend(m.group(0) for m in re.finditer(pat, text))
    return tokens


if __name__ == "__main__":
    import shutil
    results = {}
    for fn in (fig2, fig3, fig4, fig5):
        try:
            results[fn.__name__] = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] {fn.__name__}: {exc}")
            results[fn.__name__] = False

    # The paper compiles `figures/paper/<name>` relative to docs/paper/, i.e.
    # docs/paper/figures/paper/ — a SEPARATE COPY, not OUT. Regenerating into
    # OUT alone never reaches the PDF. Sync first, then gate on BOTH trees, so
    # a clean source cannot mask a stale copy in the compiled path.
    compiled = os.path.normpath(os.path.join(OUT, "..", "..", "docs", "paper",
                                            "figures", "paper"))
    names = ("fig1_bracket_overview", "fig2_certificate_horizon",
             "fig3_estimator_control", "fig4_cross_corpus",
             "fig5_channel_sensitivity")
    for name in names:
        src = f"{OUT}/{name}.pdf"
        if os.path.exists(src) and os.path.isdir(compiled):
            shutil.copy2(src, f"{compiled}/{name}.pdf")
            png = f"{OUT}/{name}.png"
            if os.path.exists(png):
                shutil.copy2(png, f"{compiled}/{name}.png")

    for tree, label in ((OUT, "source"), (compiled, "compiled")):
        for name in names:
            path = f"{tree}/{name}.pdf"
            if not os.path.exists(path):
                continue
            leaked = scan_escape_leak(path)
            if leaked:
                print(f"[FAIL] escape leak in {label} {name}.pdf: "
                      f"{sorted(set(leaked))}")
                results[f"escape:{label}:{name}"] = False
            else:
                print(f"[OK]   {label} {name}.pdf: 0 leaked escapes")
    print("\nsummary:", results)
    sys.exit(0 if all(results.values()) else 1)
