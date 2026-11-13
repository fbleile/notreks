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
