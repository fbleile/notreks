import numpy as np
import pytest

from notreks.evaluation import EvaluationError, causalman_metrics, dag_skeleton_shd


def test_causalman_separates_directed_and_marginal_targets():
    graph = {"projected": {"directed": [("a", "b")], "bidirected": [("b", "c")]}}
    estimate = np.zeros((3, 3), dtype=np.uint8)
    result = causalman_metrics(estimate, graph, ["a", "b", "c"])
    assert result.target == "causalman_latent_projection"
    assert result.metrics["projected_directed_skeleton_shd"] == 1
    assert result.metrics["projected_marginal_adjacency_shd"] == 2
    assert result.metrics["projected_bidirected_edges"] == 1


def test_dag_skeleton_metric_and_validation():
    truth = np.array([[0, 1], [0, 0]], dtype=np.uint8)
    estimate = np.array([[0, 0], [1, 0]], dtype=np.uint8)
    assert dag_skeleton_shd(truth, estimate) == 0
    with pytest.raises(EvaluationError):
        dag_skeleton_shd(truth, np.ones((3, 3), dtype=np.uint8))
