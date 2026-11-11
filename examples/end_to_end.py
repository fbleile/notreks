"""Small local lifecycle example; it does not claim scientific performance."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from notreks.aggregate import collect, write_tables
from notreks.planning import expand_protocol
from notreks.protocol import ProtocolSpec
from notreks.runner import prepare_run, solve_prepared
from notreks.solvers import SolverConfig, SolverRegistry, SolverResult


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, default=Path("example-results"), nargs="?")
    args = parser.parse_args()
    spec = ProtocolSpec("example", (8,), (64,), ("er",), (2,), ("toy",),
                        knowledge_fractions=(0.0, 0.25), partial_rounds=1, graph_replicates=2)
    registry = SolverRegistry()
    registry.register("toy", lambda observations, pairs, seed, config: SolverResult(
        "toy", np.zeros((observations.shape[1], observations.shape[1]), dtype=np.uint8),
        {"purpose": "lifecycle smoke", "pair_count": len(pairs)}))
    for run in expand_protocol(spec):
        artifacts = prepare_run(run, args.output)
        solve_prepared(artifacts, run, registry, SolverConfig())
    results, issues = collect(args.output)
    write_tables(args.output, results, issues)
    print(f"end-to-end example: results={len(results)} issues={len(issues)}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
