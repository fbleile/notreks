"""Trek-cycle coupling (TCC) value and gradient.

The block construction follows the original NOTREKS implementation. For a
pair ``(i, j)``, let ``W2 = W \\circ W`` and
``A = [[W2, w E_ij], [I, W2.T]]``. The exact TCC value is
``rho(A) - rho(B)``, where ``B`` is the same block matrix without the
coupling block. The gradient uses the simple Perron-eigenvalue identity and
the chain rule through ``W \\circ W``.
"""
from __future__ import annotations

from typing import Literal, Sequence

import numpy as np

Pair = tuple[int, int]
TCCVersion = Literal["exact_trek_graph", "dag_learning"]


def _perron_radius_and_gradient(matrix: np.ndarray) -> tuple[float, np.ndarray]:
    """Return the spectral radius and its derivative at a simple Perron root."""
    values, right = np.linalg.eig(matrix)
    index = int(np.argmax(values.real))
    root = float(values[index].real)
    if abs(values[index].imag) > 1e-8 * max(1.0, abs(root)):
        raise ValueError("TCC Perron root is not real")
    ties = np.flatnonzero(np.isclose(values.real, root, rtol=1e-8, atol=1e-10))
    if len(ties) > 1:
        # At W=0 the block is nilpotent and rho is exactly zero.  The
        # pullback through W\circ W is zero there, so the zero subgradient is
        # the stable optimizer-compatible choice.
        if abs(root) <= 1e-12:
            return root, np.zeros_like(matrix)
        raise ValueError("TCC spectral-radius gradient is undefined at a repeated root")
    right_vec = right[:, index].real
    left_values, left_vectors = np.linalg.eig(matrix.T)
    left_index = int(np.argmin(np.abs(left_values - values[index].real)))
    left_vec = left_vectors[:, left_index].real
    if np.dot(left_vec, right_vec) < 0:
        left_vec = -left_vec
    denominator = float(np.dot(left_vec, right_vec))
    if abs(denominator) <= 1e-12:
        raise ValueError("TCC left/right Perron eigenvectors are ill-conditioned")
    return root, np.outer(left_vec, right_vec) / denominator


def _one_pair(W: np.ndarray, pair: Pair, coupling: float) -> tuple[float, np.ndarray]:
    d = W.shape[0]
    squared = W * W
    identity = np.eye(d, dtype=float)
    selector = np.zeros((d, d), dtype=float)
    selector[pair] = 1.0
    bottom = np.concatenate((identity, squared.T), axis=1)
    coupled = np.concatenate((np.concatenate((squared, coupling * selector), axis=1), bottom), axis=0)
    rho_a, grad_a = _perron_radius_and_gradient(coupled)
    # The uncoupled block is block-triangular and has the same spectral
    # radius as W2, but its eigenvalue is repeated by construction.  Taking
    # its eigengradient directly would therefore be undefined.  Use the
    # equivalent simple-root problem rho(W2) instead.
    rho_b, grad_squared_b = _perron_radius_and_gradient(squared)

    def pullback(block_gradient: np.ndarray) -> np.ndarray:
        grad_squared = block_gradient[:d, :d] + block_gradient[d:, d:].T
        return 2.0 * W * grad_squared

    return rho_a - rho_b, pullback(grad_a) - 2.0 * W * grad_squared_b


def value_and_grad(
    W: np.ndarray,
    pairs: Sequence[Pair],
    *,
    coupling: float = 1.0,
    max_iter: int = 48,
    tolerance: float = 1e-8,
    version: TCCVersion = "exact_trek_graph",
) -> tuple[float, np.ndarray]:
    """Return the mean TCC value and analytic gradient.

    ``max_iter`` and ``tolerance`` remain accepted for API compatibility; the
    exact eigensolver does not use them. ``dag_learning`` reports ``rho(A)``
    instead of the exact trek-cycle difference.
    """
    del max_iter, tolerance
    W = np.asarray(W, dtype=float)
    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        raise ValueError("W must be square")
    if coupling <= 0 or not np.isfinite(coupling):
        raise ValueError("coupling must be finite and positive")
    if version not in {"exact_trek_graph", "dag_learning"}:
        raise ValueError("version must be 'exact_trek_graph' or 'dag_learning'")
    normalized = tuple((int(i), int(j)) for i, j in pairs)
    d = W.shape[0]
    if any(i < 0 or j < 0 or i >= d or j >= d or i == j for i, j in normalized):
        raise ValueError("pair indices must be distinct and in range")
    if not normalized:
        return 0.0, np.zeros_like(W)
    if version == "exact_trek_graph":
        values = [_one_pair(W, pair, coupling) for pair in normalized]
        return float(np.mean([x[0] for x in values])), np.mean([x[1] for x in values], axis=0)

    squared = W * W
    identity = np.eye(d, dtype=float)
    bottom = np.concatenate((identity, squared.T), axis=1)
    values, gradients = [], []
    for pair in normalized:
        selector = np.zeros((d, d), dtype=float)
        selector[pair] = 1.0
        matrix = np.concatenate((np.concatenate((squared, coupling * selector), axis=1), bottom), axis=0)
        root, block_gradient = _perron_radius_and_gradient(matrix)
        grad_squared = block_gradient[:d, :d] + block_gradient[d:, d:].T
        values.append(root)
        gradients.append(2.0 * W * grad_squared)
    return float(np.mean(values)), np.mean(gradients, axis=0)


def main() -> None:
    W = np.array([[0.0, 0.1], [0.2, 0.0]])
    value, gradient = value_and_grad(W, [(0, 1)])
    print(f"TCC value={value:.8g} gradient_norm={np.linalg.norm(gradient):.8g}")


if __name__ == "__main__":
    main()
