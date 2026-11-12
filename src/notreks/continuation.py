"""A small, inspectable central-path continuation engine.

The engine owns iteration, Adam state, stopping, and diagnostics.  Score and
constraint mathematics stay in callback modules, which makes the optimizer
testable without coupling it to a particular data model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from .dagma_math import ValueGradient

Term = Callable[[np.ndarray, float], ValueGradient]
Score = Callable[[np.ndarray], ValueGradient]
Domain = Callable[[np.ndarray, float], bool]


@dataclass(frozen=True)
class ContinuationConfig:
    stages: int = 5
    warm_iter: int = 30_000
    max_iter: int = 60_000
    mu_init: float = 1.0
    mu_factor: float = 0.1
    s_schedule: tuple[float, ...] = (1.0, 0.9, 0.8, 0.7, 0.6)
    learning_rate: float = 3e-4
    l1_weight: float = 0.03
    prior_weight: float = 200.0
    variance_epsilon: float = 1e-8
    inverse_epsilon: float = 1e-8
    checkpoint: int = 1_000
    relative_tolerance: float = 1e-6
    threshold: float = 0.3
    backtracking_factor: float = 0.5
    minimum_learning_rate: float = 1e-16

    def validate(self) -> None:
        if self.stages < 1 or self.warm_iter < 1 or self.max_iter < 1:
            raise ValueError("iteration counts must be positive")
        if self.mu_init <= 0 or not 0 < self.mu_factor <= 1:
            raise ValueError("invalid continuation weights")
        if len(self.s_schedule) < self.stages or any(s <= 0 for s in self.s_schedule):
            raise ValueError("s_schedule must contain positive values for all stages")
        if (self.learning_rate <= 0 or self.checkpoint < 1 or self.threshold < 0
                or not 0 < self.backtracking_factor < 1
                or self.minimum_learning_rate <= 0
                or self.variance_epsilon <= 0 or self.inverse_epsilon < 0):
            raise ValueError("invalid optimizer settings")


@dataclass(frozen=True)
class StageDiagnostic:
    stage: int
    iterations: int
    mu: float
    s: float
    objective: float
    score: float
    structural: float
    prior: float
    converged: bool


@dataclass(frozen=True)
class ContinuationResult:
    weights: np.ndarray
    adjacency: np.ndarray
    stages: tuple[StageDiagnostic, ...]
    converged: bool
    domain_retries: int = 0


def fit(
    score: Score,
    structural: Term,
    prior: Term,
    dimension: int,
    *,
    config: ContinuationConfig | None = None,
    initial_weights: np.ndarray | None = None,
    domain: Domain | None = None,
    edge_mask: np.ndarray | None = None,
) -> ContinuationResult:
    """Run the central-path loop with explicit objective callbacks."""
    config = ContinuationConfig() if config is None else config
    config.validate()
    W = np.zeros((dimension, dimension), dtype=float) if initial_weights is None else np.asarray(initial_weights, dtype=float).copy()
    if W.shape != (dimension, dimension):
        raise ValueError("initial_weights has the wrong shape")
    np.fill_diagonal(W, 0.0)
    mask = np.ones_like(W) if edge_mask is None else np.asarray(edge_mask, dtype=float)
    if mask.shape != W.shape or not np.all(np.isin(mask, [0.0, 1.0])):
        raise ValueError("edge_mask must be a binary matrix matching dimension")
    diagnostics: list[StageDiagnostic] = []
    mu = config.mu_init
    for stage in range(config.stages):
        s = config.s_schedule[stage]
        limit = config.max_iter if stage == config.stages - 1 else config.warm_iter
        # Upstream DAGMA starts Adam afresh at each central-path stage.
        moment = np.zeros_like(W)
        velocity = np.zeros_like(W)
        previous = np.inf
        stage_converged = False
        for iteration in range(1, limit + 1):
            score_term = score(W)
            structural_term = structural(W, s)
            prior_term = prior(W, s)
            objective = (mu * (score_term.value + config.l1_weight * np.abs(W).sum())
                         + structural_term.value + config.prior_weight * prior_term.value)
            gradient = (mu * (score_term.gradient + config.l1_weight * np.sign(W))
                        + structural_term.gradient + config.prior_weight * prior_term.gradient)
            moment = 0.99 * moment + 0.01 * gradient
            velocity = 0.999 * velocity + 0.001 * gradient * gradient
            corrected_moment = moment / (1.0 - 0.99 ** iteration)
            corrected_velocity = velocity / (1.0 - 0.999 ** iteration)
            step = config.learning_rate
            direction = corrected_moment / (np.sqrt(corrected_velocity) + 1e-8)
            proposal = (W - step * direction) * mask
            while domain is not None and not domain(proposal, s):
                step *= config.backtracking_factor
                if step < config.minimum_learning_rate:
                    raise RuntimeError("DAGMA domain backtracking reached its minimum step")
                proposal = (W - step * direction) * mask
            W = proposal
            if iteration % config.checkpoint == 0 or iteration == limit:
                relative_change = abs((previous - objective) / previous) if np.isfinite(previous) else np.inf
                previous = objective
                if relative_change <= config.relative_tolerance:
                    stage_converged = True
                    break
        diagnostics.append(StageDiagnostic(stage + 1, iteration, mu, s, float(objective),
                                           float(score_term.value), float(structural_term.value),
                                           float(prior_term.value), stage_converged))
        mu *= config.mu_factor
    adjacency = (np.abs(W) >= config.threshold).astype(np.uint8)
    np.fill_diagonal(adjacency, 0)
    return ContinuationResult(W, adjacency, tuple(diagnostics), all(item.converged for item in diagnostics))


def main() -> None:
    def quadratic(W):
        return ValueGradient(0.5 * float(np.sum(W * W)), W.copy())

    def zero_term(W, s):
        del s
        return ValueGradient(0.0, np.zeros_like(W))

    result = fit(quadratic, zero_term, zero_term, 3,
                 config=ContinuationConfig(stages=1, warm_iter=2, max_iter=3, checkpoint=1))
    print(f"continuation stages={len(result.stages)} edges={result.adjacency.sum()}")


if __name__ == "__main__":
    main()
