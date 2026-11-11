"""Synthetic DAGs, SEM data, and graph-derived NOTREKS pairs.

Every random choice receives an explicit seed, so graph and data artifacts can
be regenerated independently and shared across methods and knowledge levels.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class SyntheticData:
    observations: np.ndarray
    weights: np.ndarray
    topological_order: tuple[int, ...]
    model: str


def topological_order(graph: np.ndarray) -> tuple[int, ...]:
    """Return a deterministic topological order, rejecting cyclic input."""
    graph = _validate_dag_matrix(graph)
    indegree = graph.sum(axis=0).astype(int)
    remaining = set(range(graph.shape[0]))
    order: list[int] = []
    while remaining:
        ready = sorted(node for node in remaining if indegree[node] == 0)
        if not ready:
            raise ValueError("graph is cyclic")
        for node in ready:
            remaining.remove(node)
            order.append(node)
            indegree[np.flatnonzero(graph[node]).astype(int)] -= 1
    return tuple(order)


def er_dag(dimension: int, average_degree: int, seed: int) -> np.ndarray:
    """Generate an ER DAG with expected undirected degree ``average_degree``."""
    if dimension < 2:
        raise ValueError("dimension must be at least two")
    if average_degree < 1:
        raise ValueError("average_degree must be positive")
    rng = np.random.default_rng(seed)
    order = rng.permutation(dimension)
    probability = min(1.0, average_degree / (dimension - 1))
    graph = np.zeros((dimension, dimension), dtype=np.uint8)
    for left, right in combinations(range(dimension), 2):
        if rng.random() < probability:
            graph[order[left], order[right]] = 1
    return graph


def no_trek_pairs(graph: np.ndarray) -> list[tuple[int, int]]:
    """Return unordered node pairs with no common ancestor."""
    graph = _validate_dag_matrix(graph)
    reach = graph.astype(bool).copy()
    np.fill_diagonal(reach, True)
    for pivot in range(graph.shape[0]):
        reach |= reach[:, [pivot]] & reach[[pivot], :]
    ancestors = reach.T
    return [(left, right) for left in range(graph.shape[0])
            for right in range(left + 1, graph.shape[0])
            if not np.any(ancestors[left] & ancestors[right])]


def select_pairs(pairs: Iterable[tuple[int, int]], fraction: float, seed: int) -> list[tuple[int, int]]:
    """Select a reproducible random subset, preserving the requested size."""
    pairs = [tuple(map(int, pair)) for pair in pairs]
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must lie in [0, 1]")
    if not pairs or fraction == 0.0:
        return []
    if fraction == 1.0:
        return pairs
    count = max(1, int(round(fraction * len(pairs))))
    rng = np.random.default_rng(seed)
    return [pairs[int(index)] for index in rng.permutation(len(pairs))[:count]]


def simulate_sem(graph: np.ndarray, sample_size: int, graph_seed: int, data_seed: int,
                 model: str = "linear_gaussian") -> SyntheticData:
    """Simulate one standardized SEM under a registered synthetic model."""
    graph = _validate_dag_matrix(graph)
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    allowed = {"linear_gaussian", "linear_nongaussian", "nonlinear_gaussian"}
    if model not in allowed:
        raise ValueError(f"unknown model {model!r}; expected {sorted(allowed)}")
    order = topological_order(graph)
    rng = np.random.default_rng(data_seed)
    weights = np.zeros_like(graph, dtype=float)
    edges = graph.astype(bool)
    weights[edges] = rng.uniform(0.5, 2.0, size=int(edges.sum()))
    weights[edges] *= rng.choice((-1.0, 1.0), size=int(edges.sum()))
    scales = np.exp(rng.uniform(-np.log(2.0), np.log(2.0), graph.shape[0]) / 2.0)
    if model == "linear_nongaussian":
        noise = rng.laplace(size=(sample_size, graph.shape[0])) / np.sqrt(2.0)
    else:
        noise = rng.normal(size=(sample_size, graph.shape[0]))
    values = noise * scales
    for node in order:
        parents = np.flatnonzero(graph[:, node])
        if len(parents):
            signal = values[:, parents] @ weights[parents, node]
            if model == "nonlinear_gaussian":
                signal = np.tanh(signal) + 0.15 * np.sin(signal)
            values[:, node] += signal
    centered = values - values.mean(axis=0)
    standard_deviation = centered.std(axis=0)
    standard_deviation = np.where(standard_deviation > 1e-12, standard_deviation, 1.0)
    return SyntheticData(centered / standard_deviation, weights, order, model)


def _validate_dag_matrix(graph: np.ndarray) -> np.ndarray:
    graph = np.asarray(graph)
    if graph.ndim != 2 or graph.shape[0] != graph.shape[1]:
        raise ValueError("graph must be a square matrix")
    if np.any(np.diag(graph)) or np.any((graph != 0) & (graph != 1)):
        raise ValueError("graph must be a binary zero-diagonal adjacency matrix")
    return graph.astype(np.uint8, copy=False)


def main() -> None:
    """Run a small end-to-end graph/data/knowledge smoke test."""
    graph = er_dag(8, 2, seed=11)
    data = simulate_sem(graph, 32, graph_seed=11, data_seed=12)
    selected = select_pairs(no_trek_pairs(graph), 0.25, seed=13)
    print({"edges": int(graph.sum()), "samples": data.observations.shape, "pairs": len(selected)})


if __name__ == "__main__":
    main()
