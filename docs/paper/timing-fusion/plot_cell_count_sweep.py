#!/usr/bin/env python3
"""Plot the archived 80-block cell-count sweep for the manuscript."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE.parents[2] / "artifacts/methodology/if_e1/timing_certificate_cell_count_sweep.json"
FIGURE = HERE / "figures/cell-count-sweep.pdf"
SIGNAL_COUNTS = (4, 8, 16)
OCCUPIED_COUNTS = (32, 88, 199)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=ARCHIVE)
    parser.add_argument("--out", type=Path, default=FIGURE)
    args = parser.parse_args()
    scenarios = json.loads(args.archive.read_text(encoding="utf-8"))["scenarios"]
    selected = [row for row in scenarios
                if row["blocks"] == 80 and row["signal_cells"] in SIGNAL_COUNTS]
    rows = {(row["signal_cells"], row["occupied_cells"]): row for row in selected}
    expected = {(signal, occupied) for signal in SIGNAL_COUNTS for occupied in OCCUPIED_COUNTS}
    if len(selected) != len(expected) or set(rows) != expected:
        raise ValueError("expected one archived row per signal and occupied cell count")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "pdf.fonttype": 42})
    fig, axes = plt.subplots(1, 3, sharey=True, figsize=(5.45, 2.30))
    for ax, signal in zip(axes, SIGNAL_COUNTS):
        panel = [rows[signal, occupied] for occupied in OCCUPIED_COUNTS]
        for method, label, color, marker, line in (
            ("cell_product", "Cell product", "#0066a0", "o", "-"),
            ("pooled_product", "Pooled product", "#a34e12", "s", "--"),
        ):
            medians = [100 * row["methods"][method]["median_lower"] for row in panel]
            ax.plot(OCCUPIED_COUNTS, medians, marker=marker, color=color, linestyle=line,
                    markersize=3.8, linewidth=1.25, label=label, zorder=3)
        ax.set_title(f"{signal} signal cells", pad=6)
        ax.set_xticks(OCCUPIED_COUNTS)
        ax.set(xlim=(17, 214), ylim=(0, 3.4), yticks=(0, 1, 2, 3))
        ax.grid(axis="y", color="#dedede", linewidth=0.6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(length=2.5)
    fig.supylabel("Median lower bound (pp)", x=0.013, y=0.54, fontsize=8)
    fig.supxlabel("Occupied cells", y=0.147, fontsize=8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=2,
               frameon=False, bbox_to_anchor=(0.53, 0.003))
    fig.subplots_adjust(left=0.103, right=0.993, bottom=0.295, top=0.875, wspace=0.15)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


if __name__ == "__main__":
    main()
