"""Small self-contained variance- and R2-SortnRegress baselines."""

from __future__ import annotations

from typing import Literal

import numpy as np


def _order(data: np.ndarray, kind: Literal["variance", "r2"]) -> tuple[list[int], np.ndarray]:
    centered = data - data.mean(axis=0, keepdims=True)
    if kind == "variance":
        values = np.var(data, axis=0)
    elif kind == "r2":
        values = np.zeros(data.shape[1])
        for target in range(data.shape[1]):
            others = [node for node in range(data.shape[1]) if node != target]
            coefficients, *_ = np.linalg.lstsq(
                centered[:, others], centered[:, target], rcond=None)
            residual = centered[:, target] - centered[:, others] @ coefficients
            total = float(centered[:, target] @ centered[:, target])
            values[target] = 0.0 if total <= 1e-12 else 1.0 - float(residual @ residual) / total
    else:
        raise ValueError(f"unknown SortnRegress order: {kind}")
    return sorted(range(data.shape[1]), key=lambda node: (float(values[node]), node)), values


def _lasso(data: np.ndarray, target: int, parents: list[int], alpha_count: int = 32):
    n = data.shape[0]
    if not parents:
        centered = data[:, target] - data[:, target].mean()
        return np.zeros(0), float(n * np.log(max(float(centered @ centered) / n, 1e-12)))
    design = data[:, parents]
    response = data[:, target] - data[:, target].mean()
    centered = design - design.mean(axis=0, keepdims=True)
    maximum = float(np.max(np.abs(centered.T @ response)) / n)
    if maximum <= 1e-14:
        return np.zeros(len(parents)), float(n * np.log(max(float(response @ response) / n, 1e-12)))
    alphas = np.geomspace(maximum, max(maximum * 1e-4, 1e-14), alpha_count)
    best = None
    norms = np.sum(centered * centered, axis=0) / n
    for alpha in alphas:
        coefficients = np.zeros(len(parents))
        residual = response.copy()
        for _ in range(10000):
            change = 0.0
            for column in range(len(parents)):
                if norms[column] <= 1e-14:
                    continue
                partial = residual + centered[:, column] * coefficients[column]
                rho = float(centered[:, column] @ partial) / n
                updated = np.sign(rho) * max(abs(rho) - alpha, 0.0) / norms[column]
                residual -= centered[:, column] * (updated - coefficients[column])
                change = max(change, abs(updated - coefficients[column]))
                coefficients[column] = updated
            if change <= 1e-8:
                break
        support = np.abs(coefficients) > 1e-10
        bic = n * np.log(max(float(residual @ residual) / n, 1e-12)) + 2.0 * int(support.sum()) * np.log(n)
        key = (float(bic), int(support.sum()), -float(alpha))
        if best is None or key < best[0]:
            best = (key, coefficients.copy())
    assert best is not None
    return best[1], float(best[0][0])


def sortnregress(observations: np.ndarray, kind: Literal["variance", "r2"]) -> tuple[np.ndarray, dict]:
    """Return the same order-then-local-Lasso construction used by the baseline."""
    data = np.asarray(observations, dtype=float)
    if data.ndim != 2 or not np.isfinite(data).all():
        raise ValueError("observations must be a finite two-dimensional array")
    order, order_values = _order(data, kind)
    if kind == "r2":
        scale = data.std(axis=0, keepdims=True)
        data = (data - data.mean(axis=0, keepdims=True)) / np.where(scale > 1e-12, scale, 1.0)
    adjacency = np.zeros((data.shape[1], data.shape[1]), dtype=np.uint8)
    bics = []
    for position, target in enumerate(order):
        parents = order[:position]
        coefficients, bic = _lasso(data, target, parents)
        if parents:
            adjacency[np.asarray(parents), target] = (np.abs(coefficients) > 1e-10).astype(np.uint8)
        bics.append(bic)
    return adjacency, {
        "backend": "notreks.sortnregress",
        "sortnregress_kind": kind,
        "sortnregress_order": order,
        "sortnregress_order_values": order_values.tolist(),
        "sortnregress_local_bics": bics,
        "optimizer_restarts": 1,
    }


def main() -> None:
    data = np.random.default_rng(1).normal(size=(32, 4))
    print(sortnregress(data, "variance")[0].shape)


if __name__ == "__main__":
    main()
