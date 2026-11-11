"""Trek-cycle constraint (TCC) value and gradient.

TCC is kept separate from PSTrek because it uses a spectral-radius proxy for
each supplied pair rather than the differentiable path-series penalty.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np

Pair = tuple[int, int]


def value_and_grad(
    W: np.ndarray,
    pairs: Sequence[Pair],
    *,
    coupling: float = 1.0,
    max_iter: int = 48,
    tolerance: float = 1e-8,
) -> tuple[float, np.ndarray]:
    """Return the mean pairwise TCC spectral proxy and its gradient."""
    W = np.asarray(W, dtype=float)
    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        raise ValueError("W must be square")
    if coupling <= 0 or not np.isfinite(coupling):
        raise ValueError("coupling must be finite and positive")
    pairs = tuple((int(i), int(j)) for i, j in pairs)
    if not pairs:
        return 0.0, np.zeros_like(W)
    d = W.shape[0]
    if any(i < 0 or j < 0 or i >= d or j >= d or i == j for i, j in pairs):
        raise ValueError("pair indices must be distinct and in range")
    A = W * W
    np.fill_diagonal(A, 0.0)
    pair_i = np.asarray([i for i, _ in pairs], dtype=int)
    pair_j = np.asarray([j for _, j in pairs], dtype=int)
    n_pairs = len(pairs)
    x_left = np.ones((n_pairs, d))
    x_right = np.ones((n_pairs, d))
    y_left = np.ones((n_pairs, d))
    y_right = np.ones((n_pairs, d))

    def normalize(left, right):
        left_norm = np.linalg.norm(left, axis=1, keepdims=True)
        right_norm = np.linalg.norm(right, axis=1, keepdims=True)
        left_norm[left_norm == 0.0] = 1.0
        right_norm[right_norm == 0.0] = 1.0
        return left / left_norm, right / right_norm

    x_left, x_right = normalize(x_left, x_right)
    y_left, y_right = normalize(y_left, y_right)
    previous = None
    for _ in range(max(1, int(max_iter))):
        new_left = x_left @ A.T
        new_left[np.arange(n_pairs), pair_i] += coupling * x_right[np.arange(n_pairs), pair_j]
        new_right = x_left + x_right @ A
        new_y_left = y_left @ A + y_right
        new_y_right = y_right @ A.T
        new_y_right[np.arange(n_pairs), pair_j] += coupling * y_left[np.arange(n_pairs), pair_i]
        x_left, x_right = normalize(new_left, new_right)
        y_left, y_right = normalize(new_y_left, new_y_right)
        state = np.concatenate((x_left, x_right, y_left, y_right), axis=1)
        if previous is not None and np.max(np.abs(state - previous)) < tolerance:
            break
        previous = state

    hx_left = x_left @ A.T
    hx_left[np.arange(n_pairs), pair_i] += coupling * x_right[np.arange(n_pairs), pair_j]
    hx_right = x_left + x_right @ A
    hx_norm = np.linalg.norm(np.concatenate((hx_left, hx_right), axis=1), axis=1)
    x_norm = np.linalg.norm(np.concatenate((x_left, x_right), axis=1), axis=1)
    rho = np.divide(hx_norm, x_norm, out=np.zeros_like(hx_norm), where=x_norm > 0)
    rho[hx_norm <= 1e-12] = 0.0

    denom = np.sum(y_left * x_left, axis=1) + np.sum(y_right * x_right, axis=1)
    valid = np.abs(denom) > 1e-10
    grad_A = np.einsum("pi,pj->ij", y_left[valid], x_left[valid])
    grad_A += np.einsum("pi,pj->ij", x_right[valid], y_right[valid])
    gradient = (2.0 * W) * grad_A / float(n_pairs)
    return float(np.mean(rho)), gradient


def main() -> None:
    W = np.array([[0.0, 0.1], [0.2, 0.0]])
    value, gradient = value_and_grad(W, [(0, 1)])
    print(f"TCC value={value:.8g} gradient_norm={np.linalg.norm(gradient):.8g}")


if __name__ == "__main__":
    main()
