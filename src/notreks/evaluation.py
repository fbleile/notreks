"""Evaluation metrics with explicit targets for DAG and CausalMan settings.

Ordinary synthetic benchmarks can use CPDAG-aware metrics once a CPDAG backend
is configured.  CausalMan is different: latent projection may contain
bidirected edges, so this module exposes descriptive projection diagnostics and
never labels them CPDAG SHD or CPDAG Ancestor-AID.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np

from .cpdag import ancestor_aid, cpdag_shd


class EvaluationError(ValueError):
    """Raised when truth and estimate do not describe the same variables."""


@dataclass(frozen=True)
class MetricRecord:
    metrics: dict[str, float | int]
    target: str


def causalman_metrics(candidate: np.ndarray, graph: dict[str, Any], nodes: Iterable[str]) -> MetricRecord:
    """Evaluate an estimate against CausalMan's observed latent projection."""
    nodes = [str(node) for node in nodes]
    directed = _projected_directed_adjacency(graph, nodes)
    estimate = _validate_candidate(candidate, len(nodes))
    directed_skeleton = _skeleton(directed)
    estimate_skeleton = _skeleton(estimate)
    metrics = _skeleton_metrics(directed_skeleton, estimate_skeleton, "projected_directed_skeleton")
    marginal = _projected_marginal_adjacency(graph, nodes)
    metrics.update(_skeleton_metrics(marginal, estimate_skeleton, "projected_marginal_adjacency"))
    metrics["projected_ancestor_disagreement"] = _ancestor_disagreement(directed, estimate)
    metrics["projected_directed_edges"] = int(directed.sum())
    metrics["projected_bidirected_edges"] = len(graph.get("projected", {}).get("bidirected", []))
    return MetricRecord(metrics, "causalman_latent_projection")


def dag_skeleton_shd(truth: np.ndarray, estimate: np.ndarray) -> int:
    """Return undirected skeleton SHD; this is not CPDAG SHD."""
    truth = _validate_candidate(truth, np.asarray(truth).shape[0])
    estimate = _validate_candidate(estimate, truth.shape[0])
    tri = np.triu(np.ones_like(truth, dtype=bool), 1)
    return int(np.count_nonzero(_skeleton(truth)[tri] != _skeleton(estimate)[tri]))


def synthetic_metrics(truth_dag: np.ndarray, estimate_cpdag: np.ndarray,
                      *, include_ancestor_aid: bool = True) -> MetricRecord:
    """Evaluate an ordinary DAG benchmark against a CPDAG estimate."""
    metrics: dict[str, float | int] = {
        "SHD_cpdag": cpdag_shd(truth_dag, estimate_cpdag),
    }
    if include_ancestor_aid:
        normalized, count = ancestor_aid(truth_dag, estimate_cpdag)
        metrics["Ancestor_AID_cpdag"] = count
        metrics["Ancestor_AID_cpdag_normalized"] = normalized
    return MetricRecord(metrics, "synthetic_cpdag")


def _projected_directed_adjacency(graph: dict[str, Any], nodes: list[str]) -> np.ndarray:
    truth = np.zeros((len(nodes), len(nodes)), dtype=np.uint8)
    index = {node: position for position, node in enumerate(nodes)}
    for source, target in graph.get("projected", {}).get("directed", []):
        if str(source) in index and str(target) in index:
            truth[index[str(source)], index[str(target)]] = 1
    return truth


def _projected_marginal_adjacency(graph: dict[str, Any], nodes: list[str]) -> np.ndarray:
    truth = _skeleton(_projected_directed_adjacency(graph, nodes))
    index = {node: position for position, node in enumerate(nodes)}
    for source, target in graph.get("projected", {}).get("bidirected", []):
        if str(source) in index and str(target) in index:
            left, right = index[str(source)], index[str(target)]
            truth[left, right] = truth[right, left] = 1
    np.fill_diagonal(truth, 0)
    return truth


def _skeleton_metrics(truth: np.ndarray, estimate: np.ndarray, prefix: str) -> dict[str, float | int]:
    tri = np.triu(np.ones_like(truth, dtype=bool), 1)
    truth, estimate = truth.astype(bool), estimate.astype(bool)
    tp = int(np.sum(truth & estimate & tri))
    fp = int(np.sum(~truth & estimate & tri))
    fn = int(np.sum(truth & ~estimate & tri))
    return {
        f"{prefix}_shd": fp + fn,
        f"{prefix}_precision": tp / max(1, tp + fp),
        f"{prefix}_recall": tp / max(1, tp + fn),
        f"{prefix}_f1": 2 * tp / max(1, 2 * tp + fp + fn),
    }


def _ancestor_disagreement(truth: np.ndarray, estimate: np.ndarray) -> int:
    return int(np.count_nonzero(_reachability(truth) != _reachability(estimate)))


def _reachability(adjacency: np.ndarray) -> np.ndarray:
    reach = np.asarray(adjacency, dtype=bool).copy()
    np.fill_diagonal(reach, False)
    for pivot in range(reach.shape[0]):
        reach |= reach[:, [pivot]] & reach[[pivot], :]
    np.fill_diagonal(reach, False)
    return reach


def _skeleton(adjacency: np.ndarray) -> np.ndarray:
    adjacency = np.asarray(adjacency, dtype=bool)
    result = adjacency | adjacency.T
    np.fill_diagonal(result, False)
    return result.astype(np.uint8)


def _validate_candidate(candidate: np.ndarray, dimension: int) -> np.ndarray:
    candidate = np.asarray(candidate)
    if candidate.shape != (dimension, dimension):
        raise EvaluationError(f"expected {(dimension, dimension)}, got {candidate.shape}")
    if np.any(np.diag(candidate)) or np.any((candidate != 0) & (candidate != 1)):
        raise EvaluationError("candidate must be binary with zero diagonal")
    return candidate.astype(np.uint8, copy=False)


def main() -> None:
    """Run a small projection-metric smoke test."""
    graph = {"projected": {"directed": [("a", "b")], "bidirected": [("b", "c")]}}
    result = causalman_metrics(np.zeros((3, 3), dtype=np.uint8), graph, ["a", "b", "c"])
    print(result.metrics)


if __name__ == "__main__":
    main()
