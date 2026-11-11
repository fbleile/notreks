"""Deterministic NOTREKS prior-set construction utilities."""

from __future__ import annotations

from itertools import combinations
import hashlib
import json
from typing import Iterable

import numpy as np


def canonical_pair_set_hash(pairs: Iterable[tuple[int, int]]) -> str:
    """Hash a pair set independently of pair and endpoint ordering."""
    canonical = sorted({tuple(sorted(map(int, pair))) for pair in pairs})
    return hashlib.sha256(json.dumps(canonical, separators=(",", ":")).encode()).hexdigest()


def random_pairs(pairs: Iterable[tuple[int, int]], fraction: float, seed: int) -> list[tuple[int, int]]:
    pairs = [tuple(map(int, pair)) for pair in pairs]
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must lie in [0, 1]")
    if fraction == 0.0 or not pairs:
        return []
    if fraction == 1.0:
        return pairs
    count = max(1, int(round(fraction * len(pairs))))
    rng = np.random.default_rng(seed)
    return [pairs[int(index)] for index in rng.permutation(len(pairs))[:count]]


def source_ancestor_pairs(pairs: Iterable[tuple[int, int]], truth: np.ndarray,
                          fraction: float, seed: int) -> list[tuple[int, int]]:
    """Select pairs by cycling source-ancestor endpoint classes."""
    if not 0.0 < fraction <= 1.0:
        raise ValueError("source-ancestor fraction must lie in (0, 1]")
    pairs = [tuple(map(int, pair)) for pair in pairs]
    classes, node_sources = source_ancestor_classes(truth)
    del classes
    buckets: dict[tuple[tuple[int, ...], tuple[int, ...]], list[tuple[int, int]]] = {}
    for left, right in pairs:
        a, b = node_sources[left], node_sources[right]
        key = (a, b) if a <= b else (b, a)
        buckets.setdefault(key, []).append((left, right))
    rng = np.random.default_rng(seed + 104729)
    for values in buckets.values():
        rng.shuffle(values)
    keys = sorted(buckets, key=lambda key: (len(key[0]), key, len(buckets[key])))
    ordered = []
    while any(buckets.values()):
        for key in keys:
            if buckets[key]:
                ordered.append(buckets[key].pop())
    return ordered[:max(1, int(round(fraction * len(ordered))))]


def source_ancestor_classes(truth: np.ndarray) -> tuple[dict[int, tuple[int, ...]], dict[int, tuple[int, ...]]]:
    truth = np.asarray(truth, dtype=bool)
    reach = truth.copy()
    np.fill_diagonal(reach, True)
    for pivot in range(truth.shape[0]):
        reach |= reach[:, [pivot]] & reach[[pivot], :]
    sources = np.flatnonzero(~truth.any(axis=0))
    classes = {int(source): tuple(np.flatnonzero(reach[source]).tolist()) for source in sources}
    node_sources = {int(node): tuple(int(source) for source in sources if reach[source, node])
                    for node in range(truth.shape[0])}
    return classes, node_sources


def target_k_partite_pairs(all_pairs: Iterable[tuple[int, int]], dimension: int,
                           fraction: float, seed: int, target: int,
                           budget: int | None = None) -> list[tuple[int, int]]:
    """Construct a fixed-size prior with chromatic number exactly ``target``."""
    if target < 2:
        raise ValueError("target chromatic number must be at least two")
    pairs = [tuple(map(int, pair)) for pair in all_pairs]
    budget = max(1, int(round(fraction * len(pairs)))) if budget is None else int(budget)
    required = target * (target - 1) // 2
    if budget < required:
        raise ValueError(f"target K={target} needs {required} pairs, budget is {budget}")
    clique = _bounded_greedy_clique(pairs, dimension, seed, restarts=128)
    if len(clique) < target:
        raise ValueError(f"no bounded K-clique found for target K={target}")
    planted = tuple(clique[:target])
    rng = np.random.default_rng(seed + 104729)
    best_crossing: list[tuple[int, int]] = []
    vertices = list(range(dimension))
    for _ in range(128):
        colours = {vertex: index for index, vertex in enumerate(planted)}
        remaining = [vertex for vertex in vertices if vertex not in colours]
        rng.shuffle(remaining)
        for index, vertex in enumerate(remaining):
            colours[vertex] = int(rng.integers(target))
        crossing = [pair for pair in pairs if colours[pair[0]] != colours[pair[1]]]
        if len(crossing) > len(best_crossing):
            best_crossing = crossing
        if len(crossing) >= budget:
            break
    if len(best_crossing) < budget:
        raise ValueError(f"target K={target} has only {len(best_crossing)} crossing pairs; budget is {budget}")
    selected = set(combinations(planted, 2))
    remaining = [pair for pair in best_crossing if tuple(sorted(pair)) not in selected]
    order = rng.permutation(len(remaining))
    selected.update(tuple(sorted(remaining[int(index)])) for index in order[:budget - len(selected)])
    return sorted(selected)


def bounded_target_k_pair_pool(all_pairs: Iterable[tuple[int, int]], dimension: int,
                               fraction: float, target: int, seed: int,
                               requested: int, max_attempts: int = 1000) -> tuple[list[list[tuple[int, int]]], dict[str, int | str]]:
    """Build a bounded unique pool and report partial availability explicitly."""
    pool: list[list[tuple[int, int]]] = []
    hashes: set[str] = set()
    attempts = 0
    while len(pool) < requested and attempts < max_attempts:
        try:
            candidate = target_k_partite_pairs(all_pairs, dimension, fraction,
                                               seed + attempts, target)
        except ValueError:
            attempts += 1
            continue
        identity = canonical_pair_set_hash(candidate)
        if identity not in hashes:
            hashes.add(identity)
            pool.append(candidate)
        attempts += 1
    return pool, {"status": "complete" if len(pool) == requested else "partial",
                  "requested": requested, "available": len(pool), "attempts": attempts}


def _bounded_greedy_clique(pairs: list[tuple[int, int]], dimension: int,
                           seed: int, restarts: int = 96) -> tuple[int, ...]:
    adjacency = [set() for _ in range(dimension)]
    for left, right in pairs:
        adjacency[left].add(right)
        adjacency[right].add(left)
    rng = np.random.default_rng(seed)
    best: list[int] = []
    for _ in range(max(1, restarts)):
        candidates = set(range(dimension))
        clique: list[int] = []
        while candidates:
            scores = np.asarray([len(adjacency[node] & candidates) + rng.random() * 1e-6
                                 for node in candidates])
            node = list(candidates)[int(np.argmax(scores))]
            clique.append(node)
            candidates &= adjacency[node]
        if len(clique) > len(best) or (len(clique) == len(best) and tuple(sorted(clique)) < tuple(sorted(best))):
            best = clique
    return tuple(sorted(best))


def main() -> None:
    """Run a bounded target-K construction smoke test."""
    pairs = [(left, right) for left in range(6) for right in range(left + 1, 6)]
    result = target_k_partite_pairs(pairs, 6, 0.5, seed=3, target=2, budget=8)
    print({"pairs": len(result), "hash": canonical_pair_set_hash(result)[:12]})


if __name__ == "__main__":
    main()
