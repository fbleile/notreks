import numpy as np
import pytest

from notreks.solvers import SolverConfig, SolverError, SolverRegistry, SolverResult


def test_registry_validates_result_contract():
    registry = SolverRegistry()

    def adapter(observations, pairs, seed, config):
        del observations, pairs, seed, config
        return SolverResult("toy", np.zeros((3, 3), dtype=np.uint8), {"ok": True})

    registry.register("toy", adapter)
    result = registry.run("toy", np.zeros((4, 3)), [], 1, SolverConfig())
    assert result.method == "toy"
    assert result.runtime_seconds >= 0


def test_registry_rejects_missing_or_invalid_solver():
    registry = SolverRegistry()
    with pytest.raises(SolverError, match="not registered"):
        registry.run("missing", np.zeros((2, 2)), [], 1, SolverConfig())
    with pytest.raises(ValueError, match="positive"):
        SolverConfig(attempts=0).validate()
