"""Auditable statistical summaries for aggregated NOTREKS experiments.

The chromatic analysis treats the generated graph as the independent sampling
unit.  Run-level rows are first averaged within graph and target K; a graph
with many prior sets therefore contributes no more weight than another graph.
The fixed-effects slope is estimated after removing graph means and its
standard error is clustered by graph.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import csv
import math
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np


@dataclass(frozen=True)
class TrendResult:
    slope: float
    clustered_se: float
    ci_low: float
    ci_high: float
    t_statistic: float
    df: int
    p_two_sided: float
    graphs: int
    cells: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class WilcoxonResult:
    """Two-sided paired Wilcoxon signed-rank result."""

    statistic: float
    p_two_sided: float
    pairs: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def graph_k_cells(rows: Iterable[Mapping[str, object]], *, graph: str,
                  k: str, metric: str) -> list[dict[str, float | str]]:
    """Average a metric within each graph/K cell."""
    values: dict[tuple[str, float], list[float]] = {}
    for row in rows:
        try:
            key = (str(row[graph]), float(row[k]))
            value = float(row[metric])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        values.setdefault(key, []).append(value)
    return [{"graph": graph_id, "K": target, "mean": float(np.mean(observations)),
             "n": len(observations)}
            for (graph_id, target), observations in sorted(values.items())]


def k_summaries(cells: Iterable[Mapping[str, object]]) -> list[dict[str, float | int]]:
    """Summarize graph-level means, spread, and graph counts at each K."""
    grouped: dict[float, list[float]] = {}
    for row in cells:
        grouped.setdefault(float(row["K"]), []).append(float(row["mean"]))
    return [{"K": target, "graphs": len(values), "mean": float(np.mean(values)),
             "std": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
             "variance": float(np.var(values, ddof=1)) if len(values) > 1 else 0.0}
            for target, values in sorted(grouped.items())]


def adjacent_changes(cells: Iterable[Mapping[str, object]]) -> list[dict[str, float | int]]:
    """Return paired mean changes for each adjacent observed K pair."""
    by_graph: dict[str, dict[float, float]] = {}
    for row in cells:
        by_graph.setdefault(str(row["graph"]), {})[float(row["K"])] = float(row["mean"])
    targets = sorted({target for values in by_graph.values() for target in values})
    summaries = []
    for left, right in zip(targets, targets[1:]):
        changes = [values[right] - values[left] for values in by_graph.values()
                   if left in values and right in values]
        if not changes:
            continue
        summaries.append({"from_K": left, "to_K": right, "graphs": len(changes),
                          "mean_change": float(np.mean(changes)),
                          "std_change": float(np.std(changes, ddof=1)) if len(changes) > 1 else 0.0})
    return summaries


def clustered_fixed_effects(cells: Iterable[Mapping[str, object]], *, critical: float = 0.95) -> TrendResult:
    """Fit graph fixed effects with graph-clustered uncertainty.

    The finite-cluster convention is a Student-t reference distribution with
    ``G-1`` degrees of freedom.  The variance uses the CR1 correction
    ``G/(G-1) * (N-1)/(N-p)`` for ``G`` graph clusters, ``N`` cells, and ``p``
    fitted coefficients including graph effects and the slope.
    """
    records = [(str(row["graph"]), float(row["K"]), float(row["mean"])) for row in cells]
    graph_targets: dict[str, set[float]] = {}
    for graph, target, _ in records:
        graph_targets.setdefault(graph, set()).add(target)
    graphs = sorted(graph for graph, targets in graph_targets.items() if len(targets) >= 2)
    if len(graphs) < 2:
        raise ValueError("at least two graphs with at least two K values are required")
    by_graph = {graph: [] for graph in graphs}
    for graph, target, value in records:
        if graph in by_graph:
            by_graph[graph].append((target, value))
    centered = [(target - np.mean([item[0] for item in by_graph[graph]]),
                 value - np.mean([item[1] for item in by_graph[graph]]), graph)
                for graph in graphs for target, value in by_graph[graph]]
    x = np.asarray([item[0] for item in centered], dtype=float)
    y = np.asarray([item[1] for item in centered], dtype=float)
    sxx = float(np.dot(x, x))
    if sxx <= 0:
        raise ValueError("no within-graph K variation remains")
    slope = float(np.dot(x, y) / sxx)
    residual = y - slope * x
    meat = sum(float(np.sum(x[[item[2] == graph for item in centered]] *
                             residual[[item[2] == graph for item in centered]])) ** 2
                for graph in graphs)
    n, g, p = len(centered), len(graphs), len(graphs) + 1
    correction = (g / (g - 1)) * ((n - 1) / max(1, n - p))
    variance = correction * meat / (sxx * sxx)
    se = math.sqrt(max(0.0, variance))
    df = g - 1
    if se == 0:
        t_stat = math.copysign(math.inf, slope) if slope else 0.0
    else:
        t_stat = slope / se
    critical_value, p_value = _student_t_values(t_stat, df, critical)
    return TrendResult(slope, se, slope - critical_value * se, slope + critical_value * se,
                       t_stat, df, p_value, g, n)


def paired_wilcoxon(differences: Iterable[float]) -> WilcoxonResult:
    """Test paired differences against zero using a two-sided alternative."""
    values = np.asarray([float(value) for value in differences], dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 2:
        raise ValueError("at least two finite paired differences are required")
    if np.all(values == 0):
        return WilcoxonResult(float(len(values) * (len(values) + 1) / 4), 1.0, len(values))
    try:
        from scipy.stats import wilcoxon
    except ImportError as error:
        raise RuntimeError("Wilcoxon inference requires scipy") from error
    result = wilcoxon(values, alternative="two-sided", zero_method="wilcox", method="auto")
    return WilcoxonResult(float(result.statistic), float(result.pvalue), len(values))


def paired_metric_differences(rows: Iterable[Mapping[str, object]], *, treatment: str,
                              baseline: str, metric: str,
                              pair_keys: tuple[str, ...] = ("graph_id",)) -> list[float]:
    """Return treatment-minus-baseline differences for explicitly paired rows."""
    values: dict[tuple[object, ...], dict[str, list[float]]] = {}
    for row in rows:
        try:
            key = tuple(row[name] for name in pair_keys)
            method = str(row["method"])
            value = float(row[metric])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isfinite(value) or method not in {treatment, baseline}:
            continue
        values.setdefault(key, {}).setdefault(method, []).append(value)
    differences = []
    for methods in values.values():
        if treatment in methods and baseline in methods:
            differences.append(float(np.mean(methods[treatment]) - np.mean(methods[baseline])))
    if not differences:
        raise ValueError("no complete treatment/baseline pairs found")
    return differences


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    """Return Holm-adjusted p-values in the original order."""
    values = list(float(value) for value in p_values)
    order = sorted(range(len(values)), key=values.__getitem__)
    adjusted = [0.0] * len(values)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (len(values) - rank) * values[index]))
        adjusted[index] = running
    return adjusted


def paired_wilcoxon_family(rows: Iterable[Mapping[str, object]], *, comparisons: list[tuple[str, str]],
                           metric: str, pair_keys: tuple[str, ...] = ("graph_id",)) -> list[dict[str, object]]:
    """Run a two-sided paired Wilcoxon family and apply Holm correction."""
    rows = list(rows)
    results = []
    raw = []
    for treatment, baseline in comparisons:
        result = paired_wilcoxon(paired_metric_differences(
            rows, treatment=treatment, baseline=baseline, metric=metric, pair_keys=pair_keys))
        results.append({"treatment": treatment, "baseline": baseline,
                        **result.to_dict()})
        raw.append(result.p_two_sided)
    for result, adjusted in zip(results, holm_adjust(raw)):
        result["p_holm"] = adjusted
    return results


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _student_t_values(t_statistic: float, df: int, confidence: float) -> tuple[float, float]:
    try:
        from scipy.stats import t
    except ImportError as error:
        raise RuntimeError("trend inference requires scipy") from error
    critical = float(t.ppf((1 + confidence) / 2, df))
    lower = float(t.cdf(t_statistic, df))
    p_value = min(1.0, 2.0 * min(lower, 1.0 - lower))
    return critical, p_value


def main(argv: list[str] | None = None) -> None:
    """Run the trend analysis on a CSV with graph, K, and metric columns."""
    import argparse
    parser = argparse.ArgumentParser(prog="notreks-trend")
    parser.add_argument("input", type=Path)
    parser.add_argument("--graph", default="graph_id")
    parser.add_argument("--k", default="target_chromatic_number")
    parser.add_argument("--metric", default="SHD_cpdag")
    parser.add_argument("--treatment")
    parser.add_argument("--baseline")
    parser.add_argument("--comparison", action="append",
                        help="treatment:baseline; repeat for a Holm-corrected family")
    parser.add_argument("--pair-keys", default="graph_id")
    parser.add_argument("--output", type=Path,
                        help="write the JSON report here as well as printing it")
    args = parser.parse_args(argv)
    cells = graph_k_cells(read_csv(args.input), graph=args.graph, k=args.k, metric=args.metric)
    import json
    output = {"trend": clustered_fixed_effects(cells).to_dict(),
              "by_K": k_summaries(cells),
              "adjacent_changes": adjacent_changes(cells)}
    if args.treatment and args.baseline:
        differences = paired_metric_differences(
            read_csv(args.input), treatment=args.treatment, baseline=args.baseline,
            metric=args.metric, pair_keys=tuple(args.pair_keys.split(",")))
        output["paired_wilcoxon"] = paired_wilcoxon(differences).to_dict()
    if args.comparison:
        comparisons = []
        for specification in args.comparison:
            try:
                treatment, baseline = specification.split(":", 1)
            except ValueError as error:
                raise SystemExit("--comparison must have the form treatment:baseline") from error
            comparisons.append((treatment, baseline))
        output["paired_wilcoxon_family"] = paired_wilcoxon_family(
            read_csv(args.input), comparisons=comparisons, metric=args.metric,
            pair_keys=tuple(args.pair_keys.split(",")))
    rendered = json.dumps(output, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
