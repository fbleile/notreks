"""Run one real FLOP call through the migration adapter."""

from __future__ import annotations

import argparse
from pathlib import Path

from notreks.graphs import er_dag
from notreks.integrations import register_benchpress
from notreks.solvers import SolverConfig, SolverRegistry
from notreks.synthetic import simulate_sem


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("benchpress_root", type=Path)
    args = parser.parse_args()
    registry = SolverRegistry()
    provenance = register_benchpress(registry, args.benchpress_root)
    graph = er_dag(5, 2, seed=123)
    data = simulate_sem(graph, 32, graph_seed=123, data_seed=456)
    result = registry.run("flop", data.observations, [], 789,
                          SolverConfig(attempts=1, flop_sweeps=2))
    print({"backend": provenance["backend"], "method": result.method,
           "shape": result.adjacency.shape,
           "diagnostics": sorted(result.diagnostics)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
