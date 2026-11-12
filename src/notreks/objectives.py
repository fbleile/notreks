"""Composable smooth objectives for the continuous NOTREKS solver."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from .dagma_math import l2_score, logdet_acyclicity, profile_gaussian_score
from .pstrek import value_and_grad as pstrek_value_and_grad
from .tcc import value_and_grad as tcc_value_and_grad


@dataclass(frozen=True)
class ObjectiveConfig:
    score_type: str = "profile_gaussian"
    dagma_weight: float = 1.0
    pstrek_weight: float = 0.0
    tcc_weight: float = 0.0
    trek_function: str = "inv"
    inverse_epsilon: float = 1e-8
    variance_epsilon: float = 1e-8

    def validate(self) -> None:
        if self.score_type not in {"l2", "profile_gaussian"}:
            raise ValueError("score_type must be l2 or profile_gaussian")
        weights = (self.dagma_weight, self.pstrek_weight, self.tcc_weight)
        if any(not np.isfinite(x) or x < 0 for x in weights):
            raise ValueError("objective weights must be finite and non-negative")


def value_and_grad(
    W: np.ndarray,
    covariance: np.ndarray,
    pairs: Sequence[tuple[int, int]],
    *,
    s: float = 1.0,
    config: ObjectiveConfig | None = None,
) -> tuple[float, np.ndarray, dict[str, float]]:
    """Evaluate the smooth continuous objective and return term diagnostics."""
    config = ObjectiveConfig() if config is None else config
    config.validate()
    score = (l2_score(W, covariance) if config.score_type == "l2"
             else profile_gaussian_score(W, covariance, config.variance_epsilon))
    total = score.value
    gradient = score.gradient.copy()
    diagnostics = {"score": float(score.value), "dagma": 0.0, "pstrek": 0.0, "tcc": 0.0}
    if config.dagma_weight:
        dagma = logdet_acyclicity(W, s)
        total += config.dagma_weight * dagma.value
        gradient += config.dagma_weight * dagma.gradient
        diagnostics["dagma"] = float(dagma.value)
    if config.pstrek_weight and pairs:
        pstrek = pstrek_value_and_grad(
            W, pairs, function=config.trek_function,
            inverse_epsilon=config.inverse_epsilon)
        total += config.pstrek_weight * pstrek.value
        gradient += config.pstrek_weight * pstrek.gradient
        diagnostics["pstrek"] = float(pstrek.value)
    if config.tcc_weight and pairs:
        tcc, tcc_gradient = tcc_value_and_grad(W, pairs)
        total += config.tcc_weight * tcc
        gradient += config.tcc_weight * tcc_gradient
        diagnostics["tcc"] = float(tcc)
    return float(total), gradient, diagnostics


def main() -> None:
    rng = np.random.default_rng(4)
    W = rng.normal(scale=0.02, size=(3, 3))
    np.fill_diagonal(W, 0.0)
    covariance = np.eye(3)
    total, _, terms = value_and_grad(W, covariance, [(0, 2)], config=ObjectiveConfig(pstrek_weight=1.0))
    print(f"objective={total:.8g} terms={terms}")


if __name__ == "__main__":
    main()
