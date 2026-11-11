import numpy as np

from notreks.objectives import ObjectiveConfig, value_and_grad


def test_objective_zero_constraint_weights_matches_components():
    W = np.array([[0.0, 0.1], [0.02, 0.0]])
    covariance = np.eye(2)
    total, gradient, terms = value_and_grad(W, covariance, [(0, 1)])
    assert terms["pstrek"] == 0.0
    assert terms["tcc"] == 0.0
    assert np.isfinite(total)
    assert gradient.shape == W.shape


def test_objective_adds_pstrek_term():
    W = np.array([[0.0, 0.1], [0.02, 0.0]])
    covariance = np.eye(2)
    base = value_and_grad(W, covariance, [(0, 1)])
    constrained = value_and_grad(
        W, covariance, [(0, 1)], config=ObjectiveConfig(pstrek_weight=2.0))
    assert constrained[2]["pstrek"] > 0.0
    assert constrained[0] > base[0]
