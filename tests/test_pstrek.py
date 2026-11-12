import numpy as np

from notreks.pstrek import resolvent_value_and_grad, value_and_grad


def _finite_difference(W, pairs, function):
    eps = 1e-6
    grad = np.zeros_like(W)
    for index in np.ndindex(W.shape):
        plus = W.copy()
        minus = W.copy()
        plus[index] += eps
        minus[index] -= eps
        grad[index] = (
            value_and_grad(plus, pairs, function=function).value
            - value_and_grad(minus, pairs, function=function).value
        ) / (2 * eps)
    return grad


def test_pstrek_empty_pairs_are_zero():
    W = np.ones((4, 4))
    result = value_and_grad(W, [])
    assert result.value == 0.0
    np.testing.assert_array_equal(result.gradient, np.zeros_like(W))


def test_pstrek_inverse_gradient_matches_finite_difference():
    rng = np.random.default_rng(11)
    W = rng.normal(scale=0.05, size=(3, 3))
    np.fill_diagonal(W, 0.0)
    result = value_and_grad(W, [(0, 1), (1, 2)], function="inv")
    numerical = _finite_difference(W, [(0, 1), (1, 2)], "inv")
    np.testing.assert_allclose(result.gradient, numerical, rtol=2e-5, atol=2e-7)


def test_pstrek_exp_gradient_matches_finite_difference():
    rng = np.random.default_rng(12)
    W = rng.normal(scale=0.05, size=(3, 3))
    np.fill_diagonal(W, 0.0)
    result = value_and_grad(W, [(0, 2)], function="exp")
    numerical = _finite_difference(W, [(0, 2)], "exp")
    np.testing.assert_allclose(result.gradient, numerical, rtol=2e-5, atol=2e-7)


def test_pstrek_rejects_duplicate_unordered_pairs():
    W = np.zeros((3, 3))
    try:
        value_and_grad(W, [(0, 1), (1, 0)])
    except ValueError as error:
        assert "duplicate" in str(error)
    else:
        raise AssertionError("duplicate pairs must be rejected")


def test_resolvent_adjoint_matches_legacy_kernel():
    rng = np.random.default_rng(13)
    adjacency = rng.normal(scale=0.02, size=(4, 4))
    resolvent = np.linalg.inv(np.eye(4) - adjacency)
    value, gradient = resolvent_value_and_grad(
        adjacency, resolvent, [(0, 1), (2, 3)], penalty_scale=0.5)
    nodes = [0, 1, 2, 3]
    pair_mask = np.zeros((4, 4))
    pair_mask[0, 1] = pair_mask[1, 0] = 1.0
    pair_mask[2, 3] = pair_mask[3, 2] = 1.0
    Y = resolvent[:, nodes]
    expected_value = 0.5 * (2.0 / 3.0) * 0.5 * np.sum(pair_mask * (Y.T @ Y))
    expected_gradient = ((resolvent.T @ ((2.0 / 3.0) * 0.5 * Y @ pair_mask)) @ Y.T)
    np.testing.assert_allclose(value, expected_value)
    np.testing.assert_allclose(gradient, expected_gradient)
