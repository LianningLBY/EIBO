#!/usr/bin/env python3
"""fig1 (hero): EIBO two-sided bracket overview.

Hand-built because the Agentic Figure provider failed twice on a retryable
error. Deterministic layout with a programmatic text-collision check so the
figure cannot ship with overprinted labels.
"""
import sys
from itertools import combinations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon

OUT = "/efs/workspace/projects/epsilon-indistinguishability-brackets-for-open-set-encrypted-traffic-recognition-certification-grade/figures/paper"

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
INK = "#1A1A1A"
GREY = "#8A8A8A"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["DejaVu Sans"],
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def box(ax, x, y, w, h, text, *, edge, fc="white", fs=7.6, lw=1.3, ls="-",
        weight="normal", radius=0.012):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=lw, linestyle=ls, edgecolor=edge, facecolor=fc, zorder=2))
    t = ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
                fontsize=fs, color=INK, zorder=3, weight=weight,
                linespacing=1.35)
    return (x, y, w, h), t


def arrow(ax, p0, p1, *, color, ls="-", lw=1.3, style="-|>"):
    ax.add_patch(FancyArrowPatch(
        p0, p1, arrowstyle=style, mutation_scale=9,
        linewidth=lw, linestyle=ls, color=color, zorder=1,
        shrinkA=0, shrinkB=0))


def check(fig, name, boxes=()):
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    items = []
    for ax in fig.axes:
        for t in ax.texts:
            if isinstance(t, str) or not t.get_text().strip():
                continue
            bb = t.get_window_extent(renderer=r)
            if bb.width > 0 and bb.height > 0:
                items.append((t.get_text().strip()[:34], bb))
    bad = []
    for (ta, ba), (tb, bb) in combinations(items, 2):
        dx = min(ba.x1, bb.x1) - max(ba.x0, bb.x0)
        dy = min(ba.y1, bb.y1) - max(ba.y0, bb.y0)
        if dx > 2.0 and dy > 2.0:
            bad.append((ta, tb))
    # containment: every boxed label must sit inside its own rectangle
    opts = ax.get_window_extent(renderer=r)
    for (x, y, w, h), t in boxes:
        lb = ax.transData.transform((x, y))
        ub = ax.transData.transform((x + w, y + h))
        bx0, by0 = min(lb[0], ub[0]), min(lb[1], ub[1])
        bx1, by1 = max(lb[0], ub[0]), max(lb[1], ub[1])
        tb = t.get_window_extent(renderer=r)
        if tb.x0 < bx0 - 0.5 or tb.x1 > bx1 + 0.5 or \
           tb.y0 < by0 - 0.5 or tb.y1 > by1 + 0.5:
            bad.append((f"OVERFLOW: {t.get_text().strip()[:24]}", "box edge"))
    if bad:
        print(f"[FAIL] {name}: {len(bad)} problems -> {bad[:8]}")
        return False
    print(f"[OK]   {name}: {len(items)} text artists, 0 collisions, "
          f"{len(boxes)} boxes contained")
    return True


def build():
    fig, ax = plt.subplots(figsize=(7.2, 2.55))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # --- stage 1: raw records -------------------------------------------
    # Every card is a containment target, not just the bottom one: the label
    # must clear the TOPMOST card's edges, which is the rectangle a reader
    # actually sees (cards are drawn back-to-front). Checking only the bottom
    # card passed a label that visibly clipped the top card's right edge.
    card_x, card_y, card_w, card_h = 0.010, 0.30, 0.142, 0.30
    for i, off in enumerate((0.030, 0.018, 0.006)):
        ax.add_patch(FancyBboxPatch(
            (card_x + off, card_y + off), card_w, card_h,
            boxstyle="round,pad=0,rounding_size=0.010",
            linewidth=1.0, edgecolor=GREY, facecolor="white", zorder=1 + i))
    # The offsets run +0.030 .. +0.006, so the stack steps up and to the RIGHT:
    # the card drawn last (smallest offset) supplies the visible left edge, and
    # the card drawn first (largest offset) supplies the right edge. The label
    # must clear BOTH, so centre it on the span of the whole stack and register
    # that span as the containment target.
    offs = (0.030, 0.018, 0.006)
    span_x0 = card_x + min(offs)
    span_x1 = card_x + max(offs) + card_w
    t_cards = ax.text((span_x0 + span_x1) / 2, 0.45,
                      "Raw QUIC\nflow records",
                      ha="center", va="center", fontsize=8.6, color=INK,
                      zorder=6, linespacing=1.35)

    arrow(ax, (0.160, 0.45), (0.185, 0.45), color=GREY)

    # --- stage 2: channel quantization ----------------------------------
    boxes = [((span_x0, card_y + min(offs), span_x1 - span_x0,
               card_h + (max(offs) - min(offs))), t_cards)]
    boxes.append(box(ax, 0.170, 0.235, 0.230, 0.43,
        "Channel\nquantization\n\n$k$-prefix symbol\nresolution $M$\n$m=(2M)^k$",
        edge=INK, lw=1.4, fs=6.6, weight="normal"))

    # split point
    ax.plot([0.400, 0.424], [0.45, 0.45], color=INK, lw=1.3, zorder=1)
    ax.plot([0.424, 0.424], [0.3075, 0.5875], color=INK, lw=1.3, zorder=1)

    # --- upper branch ---------------------------------------------------
    arrow(ax, (0.424, 0.5875), (0.452, 0.5875), color=BLUE)
    boxes.append(box(ax, 0.452, 0.520, 0.236, 0.135,
        "Plug-in TV estimate\n$+$ confidence radius",
        edge=BLUE, fc="#F2F8FC", fs=6.8, lw=1.5))
    arrow(ax, (0.688, 0.5875), (0.712, 0.5875), color=BLUE)

    # upper hexagon
    hx = 0.778
    hexu = [(hx - 0.058, 0.5875), (hx - 0.034, 0.625), (hx + 0.034, 0.625),
            (hx + 0.058, 0.5875), (hx + 0.034, 0.550), (hx - 0.034, 0.550)]
    ax.add_patch(Polygon(hexu, closed=True, edgecolor=BLUE, facecolor="#F2F8FC",
                         linewidth=1.5, zorder=2))
    ax.text(hx, 0.5875, r"$\epsilon_{hi}$", ha="center", va="center",
            fontsize=11.0, color=BLUE, zorder=3)

    # --- lower branch ---------------------------------------------------
    arrow(ax, (0.424, 0.3075), (0.452, 0.3075), color=ORANGE, ls=(0, (4, 2)))
    boxes.append(box(ax, 0.445, 0.228, 0.250, 0.159,
        "Classifier-based\nhigh-probability\nlower bound",
        edge=ORANGE, fc="#FDF6EC", fs=6.6, lw=1.5))
    arrow(ax, (0.695, 0.3075), (0.716, 0.3075), color=ORANGE, ls=(0, (4, 2)))

    hexl = [(hx - 0.058, 0.3075), (hx - 0.034, 0.345), (hx + 0.034, 0.345),
            (hx + 0.058, 0.3075), (hx + 0.034, 0.270), (hx - 0.034, 0.270)]
    ax.add_patch(Polygon(hexl, closed=True, edgecolor=ORANGE, facecolor="#FDF6EC",
                         linewidth=1.5, zorder=2))
    ax.text(hx, 0.3075, r"$\epsilon_{lo}$", ha="center", va="center",
            fontsize=11.0, color=ORANGE, zorder=3)

    # --- merge into the interval ----------------------------------------
    ax.plot([0.836, 0.868], [0.5875, 0.5875], color=BLUE, lw=1.3, zorder=1)
    ax.plot([0.836, 0.868], [0.3075, 0.3075], color=ORANGE, lw=1.3,
            ls=(0, (4, 2)), zorder=1)
    ax.plot([0.868, 0.868], [0.3075, 0.5875], color=INK, lw=1.3, zorder=1)
    arrow(ax, (0.868, 0.4475), (0.902, 0.4475), color=INK)

    # the interval bar
    ax.plot([0.908, 0.984], [0.4475, 0.4475], color=INK, lw=1.8, zorder=3,
            solid_capstyle="butt")
    ax.plot([0.908, 0.908], [0.4285, 0.4665], color=INK, lw=1.8, zorder=3)
    ax.plot([0.984, 0.984], [0.4285, 0.4665], color=INK, lw=1.8, zorder=3)
    ax.text(0.946, 0.378, "per-pair\n$\\epsilon$-bracket", ha="center",
            va="top", fontsize=10.2, color=INK, linespacing=1.3)

    # gate
    ax.text(0.946, 0.612, "gate:\n$\\epsilon_{lo}>0.05$ AND $\\epsilon_{hi}<0.5$",
            ha="center", va="bottom", fontsize=10.0, color=GREEN,
            linespacing=1.35)

    # branch guarantee labels, placed clear of every box
    ax.text(0.5625, 0.695, "finite-sample, joint 0.975", fontsize=9.9,
            color=BLUE, ha="center", va="bottom")
    ax.text(0.5625, 0.195, "nominal 1-alpha level", fontsize=9.9, color=ORANGE,
            ha="center", va="top")

    ok = check(fig, "fig1_bracket_overview", boxes)
    fig.savefig(f"{OUT}/fig1_bracket_overview.png")
    fig.savefig(f"{OUT}/fig1_bracket_overview.pdf")
    plt.close(fig)
    return ok


if __name__ == "__main__":
    sys.exit(0 if build() else 1)
