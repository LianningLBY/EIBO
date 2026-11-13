#!/usr/bin/env python3
"""Draw the two Bayes-gain certificates with the archived XS cell example."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parents[2] / "artifacts/methodology/if_e1_timing_service_sweep_xs_20261112_125904.json"
FIGURE = HERE / "figures/nested-fusion.pdf"
WIDTH, HEIGHT = 392, 266
INK = "#233043"
ARROW = "#54667a"
CELL = "#0066a0"
POOL = "#954711"
LABELS = {
    "coarse": r"Coarse cell $c=509$",
    "directions": r"Packet directions $(+,-,-,-,+)$",
    "sizes": r"All sizes $\geq 39$ bytes",
    "fine": r"Fine cells $(509,T)$",
    "timing": "Bin the first inter-packet interval",
    "short_bin": r"$\tau\in(0,1]$ ms $\rightarrow$ APP 31",
    "long_bin": r"$\tau\in(1,4]$ ms $\rightarrow$ APP 35",
    "score": "Block scores",
    "cell": "Cell-wise certificate",
    "cell_step": r"Bound each cell at tail probability $\alpha/M$",
    "cell_sum": "Truncate at zero, then sum",
    "cell_example": "Cell 509 adds {cell_pp:.3f} pp (product)",
    "pooled": "Pooled certificate",
    "pool_step": "Pool within blocks, then bound once",
    "pool_example": "All {cells} cells give {pooled_pp:.0f} pp (product)",
}


def draw_figure(labels, destination, *, font_family="DejaVu Sans"):
    daily = json.loads(ARCHIVE.read_text(encoding="utf-8"))["service_sweep"][
        "expanded_cohorts"]["16"]["results_by_block_width"]["1d"]
    cell = next(row for row in daily["cells"] if row["coarse_symbol"] == 509)
    cell_pp = 100 * cell["bayes_gain_lower_contribution"]
    pooled_pp = 100 * daily["certificate_comparison"]["pooled_product"]["lower"]

    plt.rcParams.update({"font.family": font_family, "pdf.fonttype": 42})
    fig = plt.figure(figsize=(WIDTH / 72, HEIGHT / 72))
    ax = fig.add_axes([0, 0, 1, 1], xlim=(0, WIDTH), ylim=(HEIGHT, 0))
    ax.set_axis_off()

    def box(x, y, w, h, fill, edge):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                                   boxstyle="round,pad=0,rounding_size=4",
                                   facecolor=fill, edgecolor=edge, linewidth=0.75))

    def line(x, y, content, *, size=9, color=INK, bold=False, align="left"):
        ax.text(x, y, content, ha=align, va="center", fontsize=size,
                color=color, weight="bold" if bold else "normal")

    def arrow(x1, y1, x2, y2, color=ARROW):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                    mutation_scale=8, linewidth=1.05,
                                    color=color, shrinkA=0, shrinkB=0))

    box(3, 3, 168, 67, "#f4f7fa", "#aab7c5")
    line(13, 16, labels["coarse"], size=10.3, bold=True)
    line(13, 35, labels["directions"], size=8.5)
    line(13, 50, labels["sizes"])
    arrow(175, 36, 198, 36)

    box(202, 3, 187, 67, "#f4f7fa", "#aab7c5")
    line(212, 16, labels["fine"], size=10.3, bold=True)
    line(212, 32, labels["timing"])
    line(212, 46, labels["short_bin"])
    line(212, 59, labels["long_bin"])

    arrow(295, 70, 295, 83)
    box(33, 83, 326, 66, "#f4f7fa", "#aab7c5")
    line(43, 95, labels["score"], size=10.3, bold=True)
    for x, block in ((43, 1), (145, 2), (267, daily["sampling_units"])):
        box(x, 104, 82, 37, "#ffffff", "#b7c3d0")
        line(x + 41, 114, rf"$b={block}$", size=9.4, align="center")
        line(x + 41, 130, rf"$X_{{c{block}}},\ v_{{c{block}}}$", size=10,
             align="center")
    line(247, 123, r"$\cdots$", size=12, align="center")

    ax.plot([196, 196], [149, 160], color=ARROW, linewidth=1.05)
    ax.plot([97, 295], [160, 160], color=ARROW, linewidth=1.05)
    arrow(97, 160, 97, 172, CELL)
    arrow(295, 160, 295, 172, POOL)

    box(3, 172, 187, 91, "#eef6fb", CELL)
    line(13, 185, labels["cell"], size=10.3, color=CELL, bold=True)
    line(13, 201, labels["cell_step"], size=8.4)
    line(13, 214, labels["cell_sum"], size=8.4)
    line(13, 231, r"$\sum_c [D_c+Q_{\alpha/M}(X_c,v_c)-A_c]_+$", size=10)
    line(13, 250, labels["cell_example"].format(cell_pp=cell_pp), size=8.8, color=CELL)

    box(202, 172, 187, 91, "#fbf3ec", POOL)
    line(212, 185, labels["pooled"], size=10.3, color=POOL, bold=True)
    line(212, 201, labels["pool_step"], size=8.4)
    line(212, 215, r"$X_b=\sum_c X_{cb},\quad v_b=\sum_c v_{cb}$", size=9.1)
    line(212, 231, r"$[\sum_c(D_c-A_c)+Q_\alpha(X,v)]_+$", size=10)
    line(212, 250, labels["pool_example"].format(
        cells=daily["occupied_coarse_cells"], pooled_pp=pooled_pp), size=8.8, color=POOL)

    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=FIGURE)
    args = parser.parse_args()
    draw_figure(LABELS, args.out)


if __name__ == "__main__":
    main()
