import numpy as np
import pytest

from notreks.synthetic import er_dag, no_trek_pairs, select_pairs, simulate_sem, topological_order


def test_er_dag_and_order_are_acyclic():
    graph = er_dag(12, 4, seed=1)
    order = topological_order(graph)
    positions = {node: index for index, node in enumerate(order)}
    assert all(positions[i] < positions[j] for i, j in zip(*np.nonzero(graph)))


def test_sem_is_standardized_and_pair_selection_is_reproducible():
    graph = er_dag(8, 2, seed=2)
    data = simulate_sem(graph, 128, 2, 3, "linear_nongaussian")
    assert np.allclose(data.observations.mean(axis=0), 0.0, atol=1e-10)
    assert np.allclose(data.observations.std(axis=0), 1.0, atol=1e-10)
    pairs = no_trek_pairs(graph)
    assert select_pairs(pairs, .25, 4) == select_pairs(pairs, .25, 4)


def test_invalid_graph_and_fraction_are_rejected():
    with pytest.raises(ValueError):
        topological_order(np.ones((3, 3), dtype=np.uint8))
    with pytest.raises(ValueError):
        select_pairs([(0, 1)], 1.1, 1)
