"""Shared Gaussian score and hard NOTREKS feasibility utilities."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from scipy import linalg


def is_dag(adjacency: np.ndarray) -> bool:
    """Return whether a binary support is acyclic."""
    matrix = np.asarray(adjacency, dtype=bool)
    indegree = matrix.sum(axis=0).astype(int)
    stack = list(np.flatnonzero(indegree == 0))
    seen = 0
    while stack:
        node = stack.pop()
        seen += 1
        for child in np.flatnonzero(matrix[node]):
            indegree[child] -= 1
            if indegree[child] == 0:
                stack.append(int(child))
    return seen == len(matrix)


def gaussian_bic(observations: np.ndarray, adjacency: np.ndarray,
                 variance_epsilon: float = 1e-8,
                 lambda_bic: float = 1.0) -> tuple[float, np.ndarray]:
    """Return ``n sum(log(RSS/n)) + lambda |E| log(n)`` and coefficients."""
    observations = np.asarray(observations, dtype=float)
    matrix = np.asarray(adjacency, dtype=bool)
    if observations.ndim != 2 or matrix.shape != (observations.shape[1],) * 2:
        raise ValueError("adjacency shape is incompatible with observations")
    if np.any(np.diag(matrix)) or not is_dag(matrix):
        raise ValueError("Gaussian DAG BIC requires an acyclic zero-diagonal support")
    centered = observations - observations.mean(axis=0, keepdims=True)
    n, dimension = centered.shape
    coefficients = np.zeros((dimension, dimension), dtype=float)
    log_variances = 0.0
    for child in range(dimension):
        parents = np.flatnonzero(matrix[:, child])
        if len(parents):
            beta, *_ = linalg.lstsq(centered[:, parents], centered[:, child], lapack_driver="gelsy")
            residual = centered[:, child] - centered[:, parents] @ beta
            coefficients[parents, child] = beta
        else:
            residual = centered[:, child]
        variance = max(float(residual @ residual) / n, variance_epsilon)
        log_variances += np.log(variance)
    return float(n * log_variances + lambda_bic * matrix.sum() * np.log(n)), coefficients


def common_ancestor_violations(adjacency: np.ndarray,
                               pairs: Sequence[tuple[int, int]]) -> int:
    """Count supplied pairs with at least one common ancestor, including self."""
    reach = np.asarray(adjacency, dtype=bool).copy()
    np.fill_diagonal(reach, True)
    for pivot in range(len(reach)):
        reach |= reach[:, [pivot]] & reach[[pivot], :]
    return sum(bool(np.any(reach[:, left] & reach[:, right])) for left, right in pairs)


def trek_violation_mass(adjacency: np.ndarray,
                        pairs: Sequence[tuple[int, int]]) -> int:
    """Sum the number of common ancestors across supplied pairs."""
    reach = np.asarray(adjacency, dtype=bool).copy()
    np.fill_diagonal(reach, True)
    for pivot in range(len(reach)):
        reach |= reach[:, [pivot]] & reach[[pivot], :]
    return int(sum(np.count_nonzero(reach[:, left] & reach[:, right])
                   for left, right in pairs))


def main() -> None:
    """Print the score and feasibility of a tiny DAG."""
    observations = np.arange(20, dtype=float).reshape(10, 2)
    adjacency = np.array([[0, 1], [0, 0]], dtype=np.uint8)
    print(gaussian_bic(observations, adjacency)[0], common_ancestor_violations(adjacency, [(0, 1)]))


if __name__ == "__main__":
    main()
