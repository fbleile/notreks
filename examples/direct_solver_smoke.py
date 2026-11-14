"""Run one tiny real FLOP and FLOP+NOTREKS solve.

This is an execution smoke, not a benchmark. It checks that the installed
source-built backend can be imported, that the shared solver contract works,
and that the explicit depth-zero equivalence mode is callable.
"""

from __future__ import annotations

import argparse

import numpy as np

from notreks.integrations import register_direct
from notreks.solvers import SolverConfig, SolverError, SolverRegistry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=1001)
    args = parser.parse_args()

    data = np.random.default_rng(args.seed).normal(size=(32, 5))
    registry = SolverRegistry()
    try:
        register_direct(registry, {"flop", "flop_notreks"})
        config = SolverConfig(attempts=1, flop_sweeps=2, ancestry_depth=0)
        vanilla = registry.run("flop", data, [], args.seed, config)
        unrestricted = registry.run(
            "flop_notreks", data, [(0, 1)], args.seed, config)
    except (ImportError, SolverError) as error:
        raise SystemExit(
            "real solver smoke unavailable; install the vendored backend with "
            "scripts/install_flopsearch.sh\n"
            f"detail: {error}"
        ) from error

    if not np.array_equal(vanilla.adjacency, unrestricted.adjacency):
        raise SystemExit("depth-zero FLOP+NOTREKS output differs from vanilla FLOP")
    print("real solver smoke passed")
    print(f"  dimension={data.shape[1]} samples={data.shape[0]}")
    print(f"  edges={int(vanilla.adjacency.sum())}")
    print("  depth_zero_equivalent=True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
