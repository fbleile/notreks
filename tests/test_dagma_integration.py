import numpy as np
import pytest

from notreks.integrations import register_dagma
from notreks.solvers import SolverConfig, SolverRegistry


def test_direct_dagma_smoke():
    pytest.importorskip("dagma")
    registry = SolverRegistry()
    provenance = register_dagma(registry)
    result = registry.run("dagma", np.random.default_rng(4).normal(size=(32, 4)), [], 7,
                          SolverConfig(attempts=1, dagma_stages=1,
                                       dagma_warm_iter=5, dagma_max_iter=10))
    assert provenance["backend"] == "dagma"
    assert result.adjacency.shape == (4, 4)
