"""Small exact fixed-order NOTREKS feasibility enumeration.

This is the bounded motivational experiment, not a score-based discovery
solver. A fixed order makes every candidate DAG a subset of forward edges;
the module exhaustively counts the candidates whose ancestor sets satisfy all
supplied no-trek pairs.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import time
from typing import Callable

import numpy as np

from .knowledge import canonical_pair_set_hash


def stable_seed(master: int, *parts: object) -> int:
    payload = json.dumps([master, *parts], separators=(",", ":"), sort_keys=True)
    return int.from_bytes(hashlib.sha256(payload.encode()).digest()[:8], "big")


def certified_information_set(dimension: int, size: int, target_k: int,
                              seed: int) -> list[tuple[int, int]]:
    """Construct a size-m pair graph with a planted K-clique and K-colouring."""
    if not 2 <= target_k <= dimension:
        raise ValueError("target K must satisfy 2 <= K <= dimension")
    if size < target_k * (target_k - 1) // 2:
        raise ValueError("pair budget is too small for the planted K-clique")
    rng = np.random.default_rng(seed)
    clique = sorted(int(value) for value in rng.choice(dimension, target_k, replace=False))
    colours = {vertex: index for index, vertex in enumerate(clique)}
    remaining = [vertex for vertex in range(dimension) if vertex not in colours]
    for vertex in remaining:
        colours[vertex] = int(rng.integers(target_k))
    all_pairs = list(itertools.combinations(range(dimension), 2))
    crossing = [pair for pair in all_pairs if colours[pair[0]] != colours[pair[1]]]
    planted = list(itertools.combinations(clique, 2))
    extras = [pair for pair in crossing if pair not in set(planted)]
    if len(extras) < size - len(planted):
        raise ValueError("sampled colouring cannot supply the requested pair budget")
    rng.shuffle(extras)
    return sorted(planted + extras[:size - len(planted)])


def enumerate_ordered_dags(dimension: int, information_pairs: list[tuple[int, int]],
                           progress: Callable[[int, int, int], None] | None = None) -> dict[str, int | float]:
    """Exhaustively count feasible DAGs under order 0 < 1 < ... < d-1."""
    forward_edges = list(itertools.combinations(range(dimension), 2))
    total = 1 << len(forward_edges)
    feasible = 0
    edge_sum = 0
    for mask in range(total):
        parents = [0] * dimension
        edge_count = 0
        for index, (source, target) in enumerate(forward_edges):
            if mask & (1 << index):
                parents[target] |= 1 << source
                edge_count += 1
        ancestors = [0] * dimension
        for node in range(dimension):
            ancestor_mask = 1 << node
            parent_mask = parents[node]
            while parent_mask:
                bit = parent_mask & -parent_mask
                ancestor_mask |= ancestors[bit.bit_length() - 1]
                parent_mask ^= bit
            ancestors[node] = ancestor_mask
        if all(not (ancestors[left] & ancestors[right]) for left, right in information_pairs):
            feasible += 1
            edge_sum += edge_count
        if progress and ((mask + 1) % max(1, total // 8) == 0 or mask + 1 == total):
            progress(mask + 1, total, feasible)
    return {"candidate_dags": total, "feasible_dags": feasible,
            "mean_edges": edge_sum / feasible if feasible else float("nan")}


def run_pilot(dimension: int, sizes: list[int], target_ks: list[int], sets_per_cell: int,
              master_seed: int, output: Path) -> None:
    """Run and persist the bounded pilot with progress on stdout."""
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for size in sizes:
        for target_k in target_ks:
            if size < target_k * (target_k - 1) // 2:
                print(f"SKIP size={size} K={target_k}: insufficient pair budget", flush=True)
                continue
            seen = set()
            for set_index in range(sets_per_cell):
                attempt = set_index
                while True:
                    pairs = certified_information_set(
                        dimension, size, target_k,
                        stable_seed(master_seed, "set", size, target_k, attempt))
                    pair_hash = canonical_pair_set_hash(pairs)
                    if pair_hash not in seen:
                        seen.add(pair_hash)
                        break
                    attempt += 1
                print(f"SET START size={size} K={target_k} set={set_index + 1}/{sets_per_cell}", flush=True)
                started = time.perf_counter()
                result = enumerate_ordered_dags(
                    dimension, pairs,
                    lambda done, total, feasible: print(
                        f"  progress={done}/{total} feasible={feasible}", flush=True))
                result.update({"dimension": dimension, "pair_budget": size, "target_K": target_k,
                               "set_index": set_index, "pair_set_hash": pair_hash,
                               "pairs": [list(pair) for pair in pairs],
                               "runtime_seconds": time.perf_counter() - started})
                records.append(result)
                (output / f"size{size}_K{target_k}_set{set_index:03d}.json").write_text(
                    json.dumps(result, indent=2, allow_nan=False) + "\n")
                print(f"SET DONE size={size} K={target_k} set={set_index + 1}/{sets_per_cell} "
                      f"feasible={result['feasible_dags']}/{result['candidate_dags']}", flush=True)
    (output / "summary.json").write_text(json.dumps(records, indent=2, allow_nan=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(prog="notreks-exact")
    parser.add_argument("--dimension", type=int, default=6)
    parser.add_argument("--pair-budgets", type=int, nargs="+", default=[6, 8])
    parser.add_argument("--target-K", type=int, nargs="+", default=[2, 3, 4])
    parser.add_argument("--sets-per-cell", type=int, default=10)
    parser.add_argument("--master-seed", type=int, default=20261106)
    parser.add_argument("--output", type=Path, default=Path("results/exact-feasibility-pilot"))
    args = parser.parse_args()
    if args.dimension > 8:
        raise SystemExit("the exact pilot is intentionally bounded to dimension <= 8")
    run_pilot(args.dimension, args.pair_budgets, args.target_K,
              args.sets_per_cell, args.master_seed, args.output)


if __name__ == "__main__":
    main()
