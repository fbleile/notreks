"""Globally exhaustive Gaussian-BIC motivation study for very small DAGs.

This module ports the first exact tier of the archived motivation study into
the NOTREKS package. It enumerates every labeled DAG for ``d <= 5`` and keeps
all score-optimal CPDAGs, so it is an exact diagnostic rather than a solver
heuristic. Larger complete-MEC tiers remain a separate migration task.
"""

from __future__ import annotations

import argparse
import itertools
import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np

from .cpdag import dag_to_cpdag
from .graphs import er_dag
from .knowledge import random_pairs
from .scores import common_ancestor_violations
from .synthetic import no_trek_pairs, simulate_sem


def _parents_to_adjacency(parents: tuple[int, ...]) -> np.ndarray:
    d = len(parents)
    adjacency = np.zeros((d, d), dtype=np.uint8)
    for child, mask in enumerate(parents):
        for parent in range(d):
            if mask & (1 << parent):
                adjacency[parent, child] = 1
    return adjacency


def _is_dag(parents: tuple[int, ...]) -> bool:
    remaining = set(range(len(parents)))
    while remaining:
        ready = [node for node in remaining
                 if not any(parents[node] & (1 << other) for other in remaining)]
        if not ready:
            return False
        remaining.remove(min(ready))
    return True


@lru_cache(maxsize=None)
def all_labeled_dags(dimension: int) -> tuple[tuple[int, ...], ...]:
    """Enumerate every labeled DAG for dimensions up to five."""
    if dimension < 1 or dimension > 5:
        raise ValueError("the exhaustive exact tier supports dimensions 1 through 5")
    directed_edges = [(parent, child) for parent in range(dimension)
                      for child in range(dimension) if parent != child]
    dags: list[tuple[int, ...]] = []
    for mask in range(1 << len(directed_edges)):
        parents = [0] * dimension
        for bit, (parent, child) in enumerate(directed_edges):
            if mask & (1 << bit):
                parents[child] |= 1 << parent
        candidate = tuple(parents)
        if _is_dag(candidate):
            dags.append(candidate)
    return tuple(dags)


def _local_scores(observations: np.ndarray) -> np.ndarray:
    observations = np.asarray(observations, dtype=float)
    centered = observations - observations.mean(axis=0, keepdims=True)
    n, d = centered.shape
    covariance = centered.T @ centered / n
    result = np.full((d, 1 << d), np.inf, dtype=float)
    log_n = np.log(n)
    for child in range(d):
        child_bit = 1 << child
        for parent_mask in range(1 << d):
            if parent_mask & child_bit:
                continue
            parents = [node for node in range(d) if parent_mask & (1 << node)]
            if parents:
                joint = covariance[np.ix_(parents + [child], parents + [child])]
                parent_cov = covariance[np.ix_(parents, parents)]
                sign_joint, log_joint = np.linalg.slogdet(joint)
                sign_parent, log_parent = np.linalg.slogdet(parent_cov)
                if sign_joint <= 0 or sign_parent <= 0:
                    continue
                log_variance = log_joint - log_parent
            else:
                variance = float(covariance[child, child])
                if variance <= 0:
                    continue
                log_variance = np.log(variance)
            result[child, parent_mask] = n * log_variance + (len(parents) + 1) * log_n
    return result


def exact_bic(observations: np.ndarray, information_pairs: Iterable[tuple[int, int]],
              truth: np.ndarray | None = None, *, tie_tolerance: float = 1e-8) -> dict[str, object]:
    """Return the complete set of globally optimal feasible CPDAGs for d<=5."""
    observations = np.asarray(observations, dtype=float)
    if observations.ndim != 2 or observations.shape[1] > 5:
        raise ValueError("exact_bic requires an n by d matrix with d <= 5")
    local = _local_scores(observations)
    pairs = sorted({tuple(sorted((int(i), int(j)))) for i, j in information_pairs})
    feasible: list[tuple[float, tuple[int, ...]]] = []
    for parents in all_labeled_dags(observations.shape[1]):
        if common_ancestor_violations(_parents_to_adjacency(parents), pairs):
            continue
        score = sum(local[child, parents[child]] for child in range(len(parents)))
        if np.isfinite(score):
            feasible.append((float(score), parents))
    if not feasible:
        raise RuntimeError("no feasible DAGs remain")
    optimum = min(score for score, _ in feasible)
    tolerance = tie_tolerance * max(1.0, abs(optimum))
    optimal = [parents for score, parents in feasible if abs(score - optimum) <= tolerance]
    cpdag_by_bytes: dict[bytes, np.ndarray] = {}
    for parents in optimal:
        cpdag = dag_to_cpdag(_parents_to_adjacency(parents))
        cpdag_by_bytes.setdefault(cpdag.tobytes(), cpdag)
    result: dict[str, object] = {
        "dimension": observations.shape[1],
        "candidate_dag_count": len(all_labeled_dags(observations.shape[1])),
        "feasible_dag_count": len(feasible),
        "optimal_dag_count": len(optimal),
        "optimal_mec_count": len(cpdag_by_bytes),
        "optimal_score": float(optimum),
        "information_pairs": [list(pair) for pair in pairs],
        "optimal_cpdags": [cpdag.tolist() for cpdag in cpdag_by_bytes.values()],
    }
    if truth is not None:
        truth_cpdag = dag_to_cpdag(np.asarray(truth, dtype=np.uint8))
        result["true_cpdag_in_optimal_set"] = truth_cpdag.tobytes() in cpdag_by_bytes
        result["true_cpdag_only"] = (len(cpdag_by_bytes) == 1 and
                                      truth_cpdag.tobytes() in cpdag_by_bytes)
    return result


def run_exact_case(output: Path, *, dimension: int = 5, sample_size: int = 100,
                   graph_seed: int = 11, data_seed: int = 12,
                   knowledge_fraction: float = 0.25) -> dict[str, object]:
    """Generate, solve, and persist one exact-BIC case with provenance."""
    output = Path(output)
    graph = er_dag(dimension, 2, graph_seed)
    data = simulate_sem(graph, sample_size, graph_seed, data_seed, "linear_gaussian")
    pairs = random_pairs(no_trek_pairs(graph), knowledge_fraction, data_seed + 1)
    result = exact_bic(data.observations, pairs, graph)
    result.update({"graph_seed": graph_seed, "data_seed": data_seed,
                   "sample_size": sample_size, "knowledge_fraction": knowledge_fraction,
                   "graph_edges": int(graph.sum()), "model": "linear_gaussian"})
    output.mkdir(parents=True, exist_ok=True)
    (output / "run.json").write_text(json.dumps({"stage": "exact_bic", **result}, indent=2) + "\n")
    np.save(output / "graph.npy", graph)
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-exact-bic")
    parser.add_argument("--dimension", type=int, default=5)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--graph-seed", type=int, default=11)
    parser.add_argument("--data-seed", type=int, default=12)
    parser.add_argument("--knowledge-fraction", type=float, default=0.25)
    parser.add_argument("--output", type=Path, default=Path("results/exact-bic-smoke"))
    args = parser.parse_args(argv)
    result = run_exact_case(args.output, dimension=args.dimension,
                            sample_size=args.sample_size, graph_seed=args.graph_seed,
                            data_seed=args.data_seed,
                            knowledge_fraction=args.knowledge_fraction)
    print(json.dumps({key: result[key] for key in (
        "dimension", "candidate_dag_count", "feasible_dag_count",
        "optimal_dag_count", "optimal_mec_count", "true_cpdag_only")
        if key in result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
