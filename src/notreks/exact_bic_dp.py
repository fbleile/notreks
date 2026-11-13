"""Exact uncapped Gaussian-BIC optimization for the d=10/d=15 tiers.

This is the compact, dependency-light port of the archived subset-DP and
conflict-directed hard-NOTREKS solver. It supports dimensions six through
fifteen and returns one globally optimal feasible DAG. Complete MEC
enumeration remains a separate, explicitly marked audit stage because it can
be substantially larger than the optimization itself.
"""
from __future__ import annotations

import argparse
import heapq
import json
import time
from pathlib import Path

import numpy as np

from .cpdag import dag_to_cpdag
from .exact_bic import _local_scores, _parents_to_adjacency
from .graphs import er_dag
from .knowledge import random_pairs
from .scores import common_ancestor_violations
from .synthetic import no_trek_pairs, simulate_sem


def _best_parent_tables(scores: np.ndarray, forbidden: int) -> tuple[np.ndarray, np.ndarray]:
    """Minimize every local score over all admissible parent subsets."""
    d, size = scores.shape
    values = scores.copy()
    choices = np.zeros((d, size), dtype=np.uint16)
    for child in range(d):
        for mask in range(size):
            if mask & (1 << child):
                values[child, mask] = np.inf
            else:
                choices[child, mask] = mask
            for parent in range(d):
                if (forbidden >> (parent * d + child)) & 1 and (mask >> parent) & 1:
                    values[child, mask] = np.inf
                    break
    for child in range(d):
        for bit in range(d):
            flag = 1 << bit
            for mask in range(size):
                if not (mask & flag):
                    continue
                without = mask ^ flag
                if values[child, without] < values[child, mask]:
                    values[child, mask] = values[child, without]
                    choices[child, mask] = choices[child, without]
    return values, choices


def solve_subset_dp(scores: np.ndarray, forbidden: int = 0) -> dict[str, object]:
    """Solve a decomposable score globally over all DAGs under edge bans."""
    started = time.perf_counter()
    d, size = scores.shape
    local, choices = _best_parent_tables(scores, forbidden)
    dp = np.full(size, np.inf)
    sink = np.full(size, -1, dtype=np.int16)
    dp[0] = 0.0
    for mask in range(1, size):
        bits = mask
        while bits:
            low = bits & -bits
            child = low.bit_length() - 1
            previous = mask ^ low
            candidate = dp[previous] + local[child, previous]
            if candidate < dp[mask]:
                dp[mask] = candidate
                sink[mask] = child
            bits ^= low
    if not np.isfinite(dp[-1]):
        raise RuntimeError("no finite DAG remains under the forbidden-edge state")
    parents = [0] * d
    mask = size - 1
    reverse_order = []
    while mask:
        child = int(sink[mask])
        previous = mask ^ (1 << child)
        parents[child] = int(choices[child, previous])
        reverse_order.append(child)
        mask = previous
    return {
        "objective": float(dp[-1]),
        "parents": parents,
        "order": list(reversed(reverse_order)),
        "forbidden_edges": int(forbidden),
        "runtime_seconds": time.perf_counter() - started,
    }


def _ancestors(parents: list[int], node: int) -> int:
    seen = 1 << node
    frontier = parents[node]
    while frontier:
        seen |= frontier
        next_frontier = 0
        bits = frontier
        while bits:
            bit = bits & -bits
            next_frontier |= parents[bit.bit_length() - 1]
            bits ^= bit
        frontier = next_frontier & ~seen
    return seen


def _path_edges(parents: list[int], source: int, target: int) -> list[tuple[int, int]]:
    stack = [(target, [])]
    visited: set[int] = set()
    while stack:
        node, path = stack.pop()
        if node == source:
            return list(reversed(path))
        if node in visited:
            continue
        visited.add(node)
        bits = parents[node]
        while bits:
            bit = bits & -bits
            parent = bit.bit_length() - 1
            stack.append((parent, path + [(parent, node)]))
            bits ^= bit
    raise RuntimeError("ancestor path is missing")


def _witness(parents: list[int], pair: tuple[int, int]) -> list[tuple[int, int]]:
    left, right = pair
    common = _ancestors(parents, left) & _ancestors(parents, right)
    ancestor = (common & -common).bit_length() - 1
    return sorted(set(_path_edges(parents, ancestor, left) +
                      _path_edges(parents, ancestor, right)))


def solve_hard_notreks(scores: np.ndarray, pairs: list[tuple[int, int]],
                       max_search_nodes: int = 100_000) -> dict[str, object]:
    """Find the globally optimal DAG satisfying all supplied no-trek pairs."""
    started = time.perf_counter()
    root = solve_subset_dp(scores)
    queue = [(float(root["objective"]), 0)]
    queued = {0}
    cache = {0: root}
    nodes = 0
    while queue:
        _, state = heapq.heappop(queue)
        solution = cache[state]
        nodes += 1
        if nodes > max_search_nodes:
            raise TimeoutError("hard-NOTREKS search exceeded max_search_nodes")
        adjacency = _parents_to_adjacency(tuple(solution["parents"]))
        violations = [pair for pair in pairs
                      if common_ancestor_violations(adjacency, [pair])]
        if not violations:
            return {**solution, "search_nodes": nodes,
                    "runtime_seconds": time.perf_counter() - started,
                    "status": "globally_optimal"}
        for parent, child in _witness(solution["parents"], violations[0]):
            child_state = state | (1 << (parent * scores.shape[0] + child))
            if child_state not in queued:
                queued.add(child_state)
                cache[child_state] = solve_subset_dp(scores, child_state)
                heapq.heappush(queue, (float(cache[child_state]["objective"]), child_state))
    raise RuntimeError("no feasible DAG satisfies the supplied no-trek pairs")


def _enumerate_optimal_dags(scores: np.ndarray, forbidden: int,
                            atol: float, rtol: float,
                            max_dags: int | None) -> tuple[list[tuple[int, ...]], bool, float]:
    """Enumerate all score-optimal DAGs for one forbidden-edge state."""
    d, size = scores.shape
    local, _ = _best_parent_tables(scores, forbidden)
    dp = np.full(size, np.inf)
    dp[0] = 0.0
    for mask in range(1, size):
        bits = mask
        while bits:
            low = bits & -bits
            child = low.bit_length() - 1
            previous = mask ^ low
            dp[mask] = min(dp[mask], dp[previous] + local[child, previous])
            bits ^= low
    target = float(dp[-1])
    tolerance = atol + rtol * max(1.0, abs(target))
    found: set[tuple[int, ...]] = set()
    truncated = False

    def visit(mask: int, parents: list[int]) -> None:
        nonlocal truncated
        if truncated:
            return
        if mask == 0:
            found.add(tuple(parents))
            if max_dags is not None and len(found) >= max_dags:
                truncated = True
            return
        bits = mask
        while bits and not truncated:
            low = bits & -bits
            child = low.bit_length() - 1
            previous = mask ^ low
            if abs(dp[previous] + local[child, previous] - dp[mask]) <= tolerance:
                for parent_mask in range(size):
                    if parent_mask & ~previous or parent_mask & (1 << child):
                        continue
                    if any((forbidden >> (parent * d + child)) & 1
                           for parent in range(d) if parent_mask & (1 << parent)):
                        continue
                    score = scores[child, parent_mask]
                    if np.isfinite(score) and abs(score - local[child, previous]) <= tolerance:
                        parents[child] = parent_mask
                        visit(previous, parents)
                        if truncated:
                            break
            bits ^= low

    visit(size - 1, [0] * d)
    return sorted(found), not truncated, target


def audit_optimal_mecs(scores: np.ndarray, pairs: list[tuple[int, int]],
                       atol: float = 1e-8, rtol: float = 1e-10,
                       max_dags_per_state: int | None = None,
                       max_states: int | None = None) -> dict[str, object]:
    """Enumerate score-optimal feasible DAGs and canonicalize their CPDAGs.

    The audit follows the same conflict-directed state expansion as the
    optimizer. If a state optimum violates a no-trek pair, every edge in one
    witness is banned in a child state. The returned ``complete`` flag is
    false whenever a caller-provided state or DAG cap truncates enumeration.
    """
    root = solve_subset_dp(scores)
    optimum = float(root["objective"])
    queue = [(optimum, 0)]
    queued = {0}
    cpdag_by_bytes: dict[bytes, np.ndarray] = {}
    optimal_dags: set[tuple[int, ...]] = set()
    states = 0
    complete = True
    while queue:
        _, state = heapq.heappop(queue)
        states += 1
        if max_states is not None and states > max_states:
            complete = False
            break
        dags, state_complete, state_score = _enumerate_optimal_dags(
            scores, state, atol, rtol, max_dags_per_state)
        complete &= state_complete
        if state_score > optimum + atol + rtol * max(1.0, abs(optimum)):
            continue
        for parents_tuple in dags:
            parents = list(parents_tuple)
            adjacency = _parents_to_adjacency(parents_tuple)
            violations = [pair for pair in pairs
                          if common_ancestor_violations(adjacency, [pair])]
            if not violations:
                optimal_dags.add(parents_tuple)
                cpdag = dag_to_cpdag(adjacency)
                cpdag_by_bytes.setdefault(cpdag.tobytes(), cpdag)
                continue
            for parent, child in _witness(parents, violations[0]):
                child_state = state | (1 << (parent * scores.shape[0] + child))
                if child_state not in queued:
                    queued.add(child_state)
                    child_solution = solve_subset_dp(scores, child_state)
                    if child_solution["objective"] <= optimum + atol + rtol * max(1.0, abs(optimum)):
                        heapq.heappush(queue, (float(child_solution["objective"]), child_state))
    return {
        "complete": bool(complete),
        "states_examined": states,
        "optimal_dag_count": len(optimal_dags),
        "optimal_mec_count": len(cpdag_by_bytes) if complete else None,
        "optimal_cpdags": [cpdag.tolist() for cpdag in cpdag_by_bytes.values()],
    }


def run_exact_dp_case(output: Path, *, dimension: int = 10, sample_size: int = 100,
                      graph_seed: int = 11, data_seed: int = 12,
                      knowledge_fraction: float = 0.25,
                      audit_mecs: bool = False,
                      max_dags_per_state: int | None = None,
                      max_states: int | None = None) -> dict[str, object]:
    """Generate and persist one exact d=10 motivation case."""
    if dimension < 6 or dimension > 15:
        raise ValueError("the subset-DP motivation tier supports dimensions 6 through 15")
    output = Path(output)
    graph = er_dag(dimension, 2, graph_seed)
    data = simulate_sem(graph, sample_size, graph_seed, data_seed, "linear_gaussian")
    pairs = random_pairs(no_trek_pairs(graph), knowledge_fraction, data_seed + 1)
    solution = solve_hard_notreks(_local_scores(data.observations), pairs)
    estimate = _parents_to_adjacency(tuple(solution["parents"]))
    result = {
        "stage": "exact_bic_subset_dp",
        "tier": "d10_single_optimum",
        "dimension": dimension,
        "sample_size": sample_size,
        "graph_seed": graph_seed,
        "data_seed": data_seed,
        "knowledge_fraction": knowledge_fraction,
        "information_pairs": [list(pair) for pair in pairs],
        "graph_edges": int(graph.sum()),
        "optimal_score": solution["objective"],
        "search_nodes": solution["search_nodes"],
        "status": solution["status"],
        "true_cpdag_shd": int(np.sum(dag_to_cpdag(graph) != dag_to_cpdag(estimate))),
        "parents": solution["parents"],
        "order": solution["order"],
    }
    if audit_mecs:
        result["mec_audit"] = audit_optimal_mecs(
            _local_scores(data.observations), pairs,
            max_dags_per_state=max_dags_per_state, max_states=max_states)
    output.mkdir(parents=True, exist_ok=True)
    (output / "run.json").write_text(json.dumps(result, indent=2) + "\n")
    np.save(output / "graph.npy", graph)
    np.save(output / "estimate.npy", estimate)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-exact-bic-dp")
    parser.add_argument("--dimension", type=int, default=10)
    parser.add_argument("--sample-size", type=int, default=100)
    parser.add_argument("--graph-seed", type=int, default=11)
    parser.add_argument("--data-seed", type=int, default=12)
    parser.add_argument("--knowledge-fraction", type=float, default=0.25)
    parser.add_argument("--audit-mecs", action="store_true")
    parser.add_argument("--max-dags-per-state", type=int)
    parser.add_argument("--max-states", type=int)
    parser.add_argument("--output", type=Path, default=Path("results/exact-bic-d10-smoke"))
    args = parser.parse_args(argv)
    result = run_exact_dp_case(args.output, dimension=args.dimension,
                               sample_size=args.sample_size, graph_seed=args.graph_seed,
                               data_seed=args.data_seed,
                               knowledge_fraction=args.knowledge_fraction,
                               audit_mecs=args.audit_mecs,
                               max_dags_per_state=args.max_dags_per_state,
                               max_states=args.max_states)
    print(json.dumps({key: result[key] for key in
                      ("tier", "dimension", "status", "search_nodes", "true_cpdag_shd")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
