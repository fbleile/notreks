import numpy as np
import pytest

from notreks.integrations import register_flopsearch
from notreks.solvers import SolverConfig, SolverRegistry


def test_direct_flopsearch_smoke():
    flopsearch = pytest.importorskip("flopsearch")
    if not callable(getattr(flopsearch, "flop_notreks", None)):
        pytest.skip("the public flopsearch wheel does not include the NOTREKS extension")
    registry = SolverRegistry()
    provenance = register_flopsearch(registry)
    result = registry.run("flop_notreks", np.random.default_rng(3).normal(size=(32, 5)), [], 7,
                          SolverConfig(attempts=1, flop_sweeps=2))
    assert provenance["backend"] == "flopsearch"
    assert result.adjacency.shape == (5, 5)


def test_zero_ancestry_matches_vanilla_flop():
    flopsearch = pytest.importorskip("flopsearch")
    if not callable(getattr(flopsearch, "flop_notreks", None)):
        pytest.skip("the public flopsearch wheel does not include the NOTREKS extension")
    registry = SolverRegistry()
    register_flopsearch(registry)
    data = np.random.default_rng(9).normal(size=(32, 5))
    config = SolverConfig(attempts=1, flop_sweeps=2, ancestry_depth=0)
    vanilla = registry.run("flop", data, [], 7, config)
    unrestricted = registry.run("flop_notreks", data, [(0, 1)], 7, config)
    np.testing.assert_array_equal(vanilla.adjacency, unrestricted.adjacency)
