import numpy as np
import pytest

from notreks.scores import common_ancestor_violations, gaussian_bic, is_dag, trek_violation_mass


def test_scores_and_violations():
    graph = np.array([[0, 1, 1], [0, 0, 0], [0, 0, 0]], dtype=np.uint8)
    observations = np.random.default_rng(4).normal(size=(64, 3))
    bic, coefficients = gaussian_bic(observations, graph)
    assert np.isfinite(bic)
    assert coefficients.shape == graph.shape
    assert is_dag(graph)
    assert common_ancestor_violations(graph, [(1, 2)]) == 1
    assert trek_violation_mass(graph, [(1, 2)]) == 1
    with pytest.raises(ValueError):
        gaussian_bic(observations, np.ones((3, 3), dtype=np.uint8))
