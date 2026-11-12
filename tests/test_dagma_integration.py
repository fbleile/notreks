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
    assert provenance["backend"] == "dagma+notreks"
    assert result.adjacency.shape == (4, 4)
    assert result.diagnostics["score"] == "l2"


def test_direct_dagma_notreks_smoke():
    registry = SolverRegistry()
    provenance = register_dagma(registry)
    result = registry.run(
        "dagma_notreks", np.random.default_rng(5).normal(size=(32, 4)), [(0, 2)], 8,
        SolverConfig(attempts=2, dagma_stages=1, dagma_warm_iter=2, dagma_max_iter=3,
                     trek_weight=2.0),
    )
    assert provenance["backend"] == "dagma+notreks"
    assert result.adjacency.shape == (4, 4)
    assert result.diagnostics["backend"] == "notreks.continuation"
    assert "postselection_status" in result.diagnostics
    assert result.diagnostics["attempts_completed"] == 2


def test_direct_profile_dagma_baseline_smoke():
    registry = SolverRegistry()
    register_dagma(registry)
    result = registry.run(
        "dagma_profile", np.random.default_rng(6).normal(size=(24, 3)), [], 9,
        SolverConfig(attempts=1, dagma_stages=1, dagma_warm_iter=2, dagma_max_iter=3),
    )
    assert result.method == "dagma_profile"
    assert result.diagnostics["loss"] == "profile_gaussian"
