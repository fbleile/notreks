import numpy as np

from notreks.pstrek import value_and_grad


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
