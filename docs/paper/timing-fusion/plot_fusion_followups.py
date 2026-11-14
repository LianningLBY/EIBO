#!/usr/bin/env python3
"""Plot the archived KU-HAR and exact null coverage results."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
ARCHIVES = HERE.parents[2] / "artifacts/methodology"
FIGURES = HERE / "figures"
BLUE = "#0066a0"
ORANGE = "#a34e12"
GRAY = "#67707b"


def save(fig, name):
    fig.savefig(FIGURES / name, metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


def plot_kuhar():
    archive = ARCHIVES / "fusion_kuhar_20261114T075451Z.json"
    cohorts = json.loads(archive.read_text(encoding="utf-8"))["results_by_max_leaves_per_sensor"]
    fig, axes = plt.subplots(1, 2, sharex=True, sharey=True, figsize=(5.0, 2.28))
    methods = (
        ("pooled_hoeffding", "Pooled Hoeffding", ORANGE, "///"),
        ("pooled_product", "Pooled product", ORANGE, None),
        ("cell_hoeffding", "Cell Hoeffding", BLUE, "///"),
        ("cell_product", "Cell product", BLUE, None),
    )
    for ax, (leaves, row) in zip(axes, sorted(cohorts.items(), key=lambda entry: int(entry[0]))):
        for index, (key, _, color, hatch) in enumerate(methods):
            value = 100 * row["certificate_comparison"][key]["lower"]
            ax.barh(index, value, height=0.52, color="white" if hatch else color,
                    edgecolor=color, hatch=hatch, linewidth=0.7, zorder=3)
            ax.text(value + 0.06, index, f"{value:.3f}" if value else "0", va="center",
                    color=color, fontsize=8)
        ax.set_title(f"{leaves} leaves per sensor", pad=8)
        ax.set(xlim=(0, 2.95), xticks=(0, 1, 2))
        ax.tick_params(axis="y", length=0)
        ax.grid(axis="x", color="#dce0e4", linewidth=0.65)
        ax.spines[["top", "right", "left"]].set_visible(False)
    axes[0].set_yticks(range(len(methods)), [label for _, label, _, _ in methods])
    axes[0].invert_yaxis()
    fig.supxlabel("Lower bound on Bayes gain (pp)", y=0.045, fontsize=9)
    fig.subplots_adjust(left=0.245, right=0.985, bottom=0.23, top=0.835, wspace=0.21)
    save(fig, "kuhar-certificates.pdf")


def plot_coverage():
    archive = ARCHIVES / "fusion_block_dependence_20261114T071847Z.json"
    data = json.loads(archive.read_text(encoding="utf-8"))
    fig, axes = plt.subplots(1, 2, sharey=True, figsize=(5.0, 2.63))
    for ax, (design, title) in zip(axes, (
        ("adjacent_pairs", "Independent adjacent pairs"), ("persistent_markov", "Persistent Markov chain")
    )):
        rows = sorted((row for row in data["scenarios"] if row["blocks"] == 91 and row["dependence"] == design),
                      key=lambda row: row["state_correlation_at_linked_transitions"])
        rho = [row["state_correlation_at_linked_transitions"] for row in rows]
        ax.axhline(100 * (1 - data["alpha_per_method"]), color=GRAY, linestyle=":", linewidth=1)
        for method, label, color, marker, style in (
            ("independent_product", "Ordinary product", ORANGE, "o", "-"),
            ("parity_product", "Parity product", ORANGE, "s", "--"),
            ("independent_hoeffding", "Ordinary Hoeffding", BLUE, "o", "-"),
            ("parity_hoeffding", "Parity Hoeffding", BLUE, "s", "--"),
        ):
            ax.plot(rho, [100 * row["coverage_rates"][method] for row in rows], label=label,
                    color=color, marker=marker, markerfacecolor="white" if style == "--" else color,
                    markersize=3.3, linestyle=style, linewidth=1.2, clip_on=False)
        ax.set_title(title, pad=8)
        ax.set(xlim=(-0.015, 1.015), ylim=(47, 102), yticks=(50, 65, 80, 95, 100),
               xticks=(0, 0.2, 0.4, 0.6, 0.8, 1))
        ax.grid(axis="y", color="#e8eaed", linewidth=0.55)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Exact coverage (%)", fontsize=9)
    fig.supxlabel(r"Correlation at linked transitions ($\rho$)", y=0.163, fontsize=9)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=2,
               frameon=False, bbox_to_anchor=(0.535, 0.008))
    fig.subplots_adjust(left=0.143, right=0.975, bottom=0.33, top=0.84, wspace=0.19)
    save(fig, "block-dependence.pdf")


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "pdf.fonttype": 42})
    plot_kuhar()
    plot_coverage()


if __name__ == "__main__":
    main()
