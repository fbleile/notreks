import numpy as np

from notreks.dagma_math import l2_score, logdet_acyclicity, profile_gaussian_score


def _finite_difference(function, W):
    eps = 1e-6
    gradient = np.zeros_like(W)
    for index in np.ndindex(W.shape):
        plus = W.copy()
        minus = W.copy()
        plus[index] += eps
        minus[index] -= eps
        gradient[index] = (function(plus) - function(minus)) / (2 * eps)
    return gradient


def test_logdet_gradient_matches_finite_difference():
    W = np.array([[0.0, 0.1, -0.02], [0.04, 0.0, 0.03], [-0.01, 0.02, 0.0]])
    result = logdet_acyclicity(W)
    numerical = _finite_difference(lambda x: logdet_acyclicity(x).value, W)
    np.testing.assert_allclose(result.gradient, numerical, rtol=2e-5, atol=2e-7)


def test_profile_gaussian_gradient_matches_finite_difference():
    W = np.array([[0.0, 0.1], [0.04, 0.0]])
    covariance = np.array([[1.2, 0.15], [0.15, 0.9]])
    result = profile_gaussian_score(W, covariance)
    numerical = _finite_difference(lambda x: profile_gaussian_score(x, covariance).value, W)
    np.testing.assert_allclose(result.gradient, numerical, rtol=2e-5, atol=2e-7)


def test_l2_score_gradient_matches_finite_difference():
    W = np.array([[0.0, 0.1], [0.04, 0.0]])
    covariance = np.array([[1.2, 0.15], [0.15, 0.9]])
    result = l2_score(W, covariance)
    numerical = _finite_difference(lambda x: l2_score(x, covariance).value, W)
    np.testing.assert_allclose(result.gradient, numerical, rtol=2e-5, atol=2e-7)
