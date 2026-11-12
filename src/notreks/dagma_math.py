"""Small, optimizer-independent DAGMA mathematical primitives.

These functions are the numerical boundary between a DAGMA continuation loop
and the problem definition.  They are intentionally NumPy/SciPy-only so they
can be checked without importing the solver package.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.linalg as sla


@dataclass(frozen=True)
class ValueGradient:
    value: float
    gradient: np.ndarray


def logdet_acyclicity(W: np.ndarray, s: float = 1.0) -> ValueGradient:
    """Evaluate ``-log det(sI-W∘W) + d log(s)`` and its W-gradient."""
    W = _square(W)
    if not np.isfinite(s) or s <= 0:
        raise ValueError("s must be finite and positive")
    matrix = s * np.eye(W.shape[0]) - W * W
    sign, logdet = np.linalg.slogdet(matrix)
    if sign <= 0 or not np.isfinite(logdet):
        raise np.linalg.LinAlgError("DAGMA log-det outside its domain")
    inverse = sla.solve(matrix, np.eye(W.shape[0]), check_finite=False)
    gradient = 2.0 * W * inverse.T
    value = -float(logdet) + W.shape[0] * np.log(s)
    return ValueGradient(value, gradient)


def profile_gaussian_score(W: np.ndarray, covariance: np.ndarray, variance_epsilon: float = 1e-8) -> ValueGradient:
    """Evaluate the profiled Gaussian score used by the custom linear path."""
    W = _square(W)
    covariance = _square(covariance)
    if covariance.shape != W.shape:
        raise ValueError("covariance and W must have the same shape")
    if not np.isfinite(variance_epsilon) or variance_epsilon <= 0:
        raise ValueError("variance_epsilon must be finite and positive")
    sigma_w = covariance @ W
    residual = (np.diag(covariance) - 2.0 * np.sum(covariance * W, axis=0)
                + np.sum(W * sigma_w, axis=0))
    denominator = residual + variance_epsilon
    if np.any(denominator <= 0) or not np.all(np.isfinite(denominator)):
        raise FloatingPointError("non-positive Gaussian profile residual variance")
    value = 0.5 * float(np.log(denominator).sum())
    gradient = (sigma_w - covariance) / denominator[np.newaxis, :]
    return ValueGradient(value, gradient)


def l2_score(W: np.ndarray, covariance: np.ndarray) -> ValueGradient:
    """Evaluate the upstream DAGMA least-squares score and gradient."""
    W = _square(W)
    covariance = _square(covariance)
    if covariance.shape != W.shape:
        raise ValueError("covariance and W must have the same shape")
    identity_minus_weights = np.eye(W.shape[0]) - W
    rhs = covariance @ identity_minus_weights
    value = 0.5 * float(np.trace(identity_minus_weights.T @ rhs))
    return ValueGradient(value, -rhs)


def _square(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("matrix must be square")
    if not np.all(np.isfinite(matrix)):
        raise ValueError("matrix must be finite")
    return matrix


def main() -> None:
    """Print a small numerical smoke result."""
    W = np.array([[0.0, 0.1], [0.2, 0.0]])
    result = logdet_acyclicity(W)
    print(f"DAGMA h={result.value:.8g} gradient_norm={np.linalg.norm(result.gradient):.8g}")


if __name__ == "__main__":
    main()
