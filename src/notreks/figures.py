"""Project-consistent summary figures from run-level or aggregate CSV files."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np

from .analysis import k_summaries, graph_k_cells


COLORS = {
    "flop": "#0072B2",
    "flop_notreks": "#D55E00",
    "dagma": "#009E73",
    "dagma_notreks": "#CC79A7",
    "dagma_tcc": "#E69F00",
}
MARKER = "o"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def plot_mean_sd(rows: Iterable[dict[str, str]], output: Path, *, x: str, y: str,
                 group: str = "method", data_label: str = "",
                 title: str | None = None, xlabel: str | None = None,
                 ylabel: str | None = None) -> None:
    """Plot grouped means and mean ± one SD without individual observations."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("figure generation requires matplotlib") from error
    grouped: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        try:
            x_value, y_value = float(row[x]), float(row[y])
        except (KeyError, TypeError, ValueError):
            continue
        grouped[row.get(group, "all")][x_value].append(y_value)
    if not grouped:
        raise ValueError(f"no numeric rows found for x={x!r}, y={y!r}")

    figure, axis = plt.subplots(figsize=(6.6, 4.2))
    for name, values in sorted(grouped.items()):
        positions = np.array(sorted(values))
        means = np.array([np.mean(values[position]) for position in positions])
        deviations = np.array([np.std(values[position], ddof=1) if len(values[position]) > 1 else 0.0
                               for position in positions])
        color = COLORS.get(name, "#333333")
        axis.fill_between(positions, means - deviations, means + deviations,
                          color=color, alpha=0.16, linewidth=0, zorder=1)
        axis.plot(positions, means, color=color, marker=MARKER, markersize=5.5,
                  markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.7,
                  alpha=0.72, linewidth=1.8, label=name, zorder=3)
    axis.set_xlabel(xlabel or x)
    axis.set_ylabel(ylabel or y)
    if title:
        axis.set_title(title)
    axis.grid(axis="y", color="#dddddd", linewidth=0.7, alpha=0.7)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    if len(grouped) > 1:
        axis.legend(frameon=False)
    if data_label:
        axis.text(0.01, 0.01, data_label, transform=axis.transAxes,
                  ha="left", va="bottom", fontsize=8, color="#444444")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_graph_clustered_trend(rows: Iterable[dict[str, str]], output: Path, *,
                               graph: str = "graph_id", k: str = "target_chromatic_number",
                               y: str = "SHD_cpdag", group: str = "method",
                               data_label: str = "", title: str | None = None) -> None:
    """Plot graph-level K means and ±1 SD without weighting large cells more."""
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise RuntimeError("figure generation requires matplotlib") from error
    rows = list(rows)
    grouped: dict[str, list[dict[str, float | str]]] = defaultdict(list)
    for row in rows:
        grouped[row.get(group, "all")].append(row)
    figure, axis = plt.subplots(figsize=(6.6, 4.2))
    for name, subset in sorted(grouped.items()):
        cells = graph_k_cells(subset, graph=graph, k=k, metric=y)
        summary = k_summaries(cells)
        if not summary:
            continue
        positions = np.asarray([float(item["K"]) for item in summary])
        means = np.asarray([float(item["mean"]) for item in summary])
        deviations = np.asarray([float(item["std"]) for item in summary])
        color = COLORS.get(name, "#333333")
        axis.fill_between(positions, means - deviations, means + deviations,
                          color=color, alpha=0.16, linewidth=0, zorder=1)
        axis.plot(positions, means, color=color, marker=MARKER, markersize=5.5,
                  markerfacecolor=color, markeredgecolor="white", markeredgewidth=0.7,
                  alpha=0.72, linewidth=1.8, label=name, zorder=3)
    axis.set_xlabel("Target chromatic number K")
    axis.set_ylabel(y)
    if title:
        axis.set_title(title)
    axis.grid(axis="y", color="#dddddd", linewidth=0.7, alpha=0.7)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    if len(grouped) > 1:
        axis.legend(frameon=False)
    if data_label:
        axis.text(0.01, 0.01, data_label, transform=axis.transAxes,
                  ha="left", va="bottom", fontsize=8, color="#444444")
    figure.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(figure)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-figure")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--x", required=True)
    parser.add_argument("--y", required=True)
    parser.add_argument("--group", default="method")
    parser.add_argument("--data-label", default="")
    parser.add_argument("--title")
    parser.add_argument("--format", choices=("png", "pdf"), default="png")
    args = parser.parse_args(argv)
    output = args.output.with_suffix(f".{args.format}")
    plot_mean_sd(load_rows(args.input), output, x=args.x, y=args.y,
                 group=args.group, data_label=args.data_label, title=args.title)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
