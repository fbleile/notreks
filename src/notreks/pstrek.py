"""Standalone PSTrek value/gradient kernels.

The kernel is deliberately independent of an optimizer.  A solver supplies a
weight matrix ``W`` and receives the penalty value and its gradient.  For an
unordered pair set ``I`` we use the normalized matrix form used by the legacy
implementation,

    R_I(W) = 1/2 * (2/(d-1)) * sum(M * (F.T @ F)),
    F = f(W * W),

where ``M`` is the symmetric indicator matrix of the supplied pairs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import scipy.linalg as sla

Pair = tuple[int, int]


@dataclass(frozen=True)
class PSTrekResult:
    value: float
    gradient: np.ndarray


def _pairs_and_mask(pairs: Sequence[Pair], d: int) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(pairs, dtype=int)
    if raw.size == 0:
        return np.empty((0, 2), dtype=int), np.zeros((d, d), dtype=float)
    if raw.ndim != 2 or raw.shape[1] != 2:
        raise ValueError("pairs must have shape (m, 2)")
    if np.any(raw < 0) or np.any(raw >= d) or np.any(raw[:, 0] == raw[:, 1]):
        raise ValueError("pair indices must be distinct and in range")
    canonical = np.sort(raw, axis=1)
    if len({tuple(p) for p in canonical}) != len(canonical):
        raise ValueError("duplicate no-trek pairs")
    mask = np.zeros((d, d), dtype=float)
    for i, j in canonical:
        mask[i, j] = 1.0
        mask[j, i] = 1.0
    return canonical, mask


def _path_matrix(A: np.ndarray, function: str, log_terms: int, inverse_epsilon: float) -> np.ndarray:
    eye = np.eye(A.shape[0], dtype=float)
    if function == "exp":
        return sla.expm(A)
    if function == "inv":
        return sla.solve(eye - A + inverse_epsilon * eye, eye, check_finite=False)
    if function == "log":
        result = eye.copy()
        power = eye.copy()
        for k in range(1, log_terms + 1):
            power = power @ A
            result += power / k
        return result
    if function == "binom":
        return np.linalg.matrix_power(eye + A, A.shape[0])
    raise ValueError("function must be one of: exp, inv, log, binom")


def _power_adjoint(B: np.ndarray, G: np.ndarray, degree: int, coefficient: float = 1.0) -> np.ndarray:
    powers = [np.eye(B.shape[0], dtype=float)]
    for _ in range(degree):
        powers.append(powers[-1] @ B)
    result = np.zeros_like(B, dtype=float)
    for r in range(degree):
        result += powers[r].T @ G @ powers[degree - 1 - r].T
    return coefficient * result


def value_and_grad(
    W: np.ndarray,
    pairs: Sequence[Pair],
    *,
    function: str = "inv",
    log_terms: int | None = None,
    inverse_epsilon: float = 1e-8,
) -> PSTrekResult:
    """Return the normalized PSTrek penalty and gradient with respect to ``W``.

    ``function='inv'`` is the form used alongside DAGMA's inverse resolvent;
    ``exp``, ``log``, and ``binom`` retain the reference kernel choices for
    isolated numerical checks and later optimizer integration.
    """
    W = np.asarray(W, dtype=float)
    if W.ndim != 2 or W.shape[0] != W.shape[1]:
        raise ValueError("W must be a square matrix")
    d = W.shape[0]
    _, mask = _pairs_and_mask(pairs, d)
    if d < 2 or not np.any(mask):
        return PSTrekResult(0.0, np.zeros_like(W))
    if inverse_epsilon < 0:
        raise ValueError("inverse_epsilon must be non-negative")
    terms = 2 * d if log_terms is None else int(log_terms)
    if terms < 1:
        raise ValueError("log_terms must be positive")

    A = W * W
    F = _path_matrix(A, function, terms, inverse_epsilon)
    scale = 2.0 / (d - 1)
    Gf = scale * (F @ mask)
    value = 0.5 * scale * float(np.sum(mask * (F.T @ F)))
    if function == "exp":
        Ga = sla.expm_frechet(A.T, Gf, compute_expm=False)
    elif function == "inv":
        Ga = F.T @ Gf @ F.T
    elif function == "log":
        Ga = np.zeros_like(A)
        for k in range(1, terms + 1):
            Ga += _power_adjoint(A, Gf, k, 1.0 / k)
    else:
        Ga = _power_adjoint(np.eye(d) + A, Gf, d)
    return PSTrekResult(value, 2.0 * W * Ga)


def resolvent_value_and_grad(
    adjacency: np.ndarray,
    resolvent: np.ndarray,
    pairs: Sequence[Pair],
    *,
    resolvent_scale: float = 1.0,
    penalty_scale: float = 1.0,
) -> tuple[float, np.ndarray]:
    """Evaluate the selected-column adjoint using a caller's resolvent.

    ``resolvent`` is the matrix supplied by a DAGMA stage.  The function
    returns the penalty and the gradient with respect to ``adjacency``; the
    caller is responsible for the final pullback through its adjacency map.
    Keeping this boundary explicit allows one factorization to serve both the
    log-det DAG term and PSTrek.
    """
    adjacency = np.asarray(adjacency, dtype=float)
    resolvent = np.asarray(resolvent, dtype=float)
    if adjacency.ndim != 2 or adjacency.shape[0] != adjacency.shape[1]:
        raise ValueError("adjacency must be square")
    if resolvent.shape != adjacency.shape or not np.all(np.isfinite(resolvent)):
        raise ValueError("resolvent must be finite and match adjacency")
    if resolvent_scale <= 0 or not np.isfinite(resolvent_scale):
        raise ValueError("resolvent_scale must be finite and positive")
    if penalty_scale < 0 or not np.isfinite(penalty_scale):
        raise ValueError("penalty_scale must be finite and non-negative")
    d = adjacency.shape[0]
    canonical, _ = _pairs_and_mask(pairs, d)
    if not len(canonical):
        return 0.0, np.zeros_like(adjacency)
    nodes = np.unique(canonical.reshape(-1))
    positions = {int(node): index for index, node in enumerate(nodes)}
    B = np.zeros((len(nodes), len(nodes)))
    for i, j in canonical:
        left, right = positions[int(i)], positions[int(j)]
        B[left, right] += 1.0
        B[right, left] += 1.0
    Y = resolvent[:, nodes]
    effective_scale = (2.0 / (d - 1)) * penalty_scale if d > 1 else 0.0
    value = 0.5 * effective_scale * float(np.sum(B * (Y.T @ Y)))
    gy = effective_scale * (Y @ B)
    gradient = ((resolvent.T @ gy) @ Y.T) / float(resolvent_scale)
    return value, gradient


def main() -> None:
    """Small human-checkable smoke test for the kernel contract."""
    rng = np.random.default_rng(7)
    W = rng.normal(scale=0.08, size=(4, 4))
    np.fill_diagonal(W, 0.0)
    result = value_and_grad(W, [(0, 2), (1, 3)])
    print(f"PSTrek value={result.value:.8g} gradient_norm={np.linalg.norm(result.gradient):.8g}")


if __name__ == "__main__":
    main()
