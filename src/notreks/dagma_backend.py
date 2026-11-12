"""Custom linear DAGMA path built from the checked NOTREKS components."""
from __future__ import annotations

from typing import Sequence

import numpy as np
import scipy.linalg as sla

from .continuation import ContinuationConfig, ContinuationResult, fit
from .dagma_math import ValueGradient, logdet_acyclicity, profile_gaussian_score
from .pstrek import resolvent_value_and_grad
from .postselection import order_parent_postselection
from .scores import is_dag


def fit_profile_pstrek(
    observations: np.ndarray,
    pairs: Sequence[tuple[int, int]],
    *,
    config: ContinuationConfig | None = None,
) -> ContinuationResult:
    """Fit profile-Gaussian DAGMA with the shifted PSTrek resolvent."""
    observations = np.asarray(observations, dtype=float)
    if observations.ndim != 2 or observations.shape[0] < 2:
        raise ValueError("observations must be a two-dimensional data matrix")
    means = observations.mean(axis=0, keepdims=True)
    standard_deviations = np.maximum(observations.std(axis=0, ddof=0, keepdims=True), 1e-12)
    standardized = (observations - means) / standard_deviations
    covariance = standardized.T @ standardized / float(standardized.shape[0])
    d = standardized.shape[1]
    config = ContinuationConfig() if config is None else config

    def score(W: np.ndarray) -> ValueGradient:
        return profile_gaussian_score(W, covariance, config.variance_epsilon)

    def structural(W: np.ndarray, s: float) -> ValueGradient:
        return logdet_acyclicity(W, s)

    def prior(W: np.ndarray, s: float) -> ValueGradient:
        if not pairs or config.prior_weight == 0.0:
            return ValueGradient(0.0, np.zeros_like(W))
        adjacency = W * W
        matrix = (s + config.inverse_epsilon) * np.eye(d) - adjacency
        resolvent = sla.solve(matrix, np.eye(d), check_finite=False)
        value, gradient_adjacency = resolvent_value_and_grad(
            adjacency, s * resolvent, pairs,
            resolvent_scale=s, penalty_scale=s * s / 2.0)
        return ValueGradient(value, 2.0 * W * gradient_adjacency)

    def domain(W: np.ndarray, s: float) -> bool:
        matrix = (s + config.inverse_epsilon) * np.eye(d) - W * W
        try:
            inverse = sla.solve(matrix, np.eye(d), check_finite=False)
        except np.linalg.LinAlgError:
            return False
        return bool(np.all(np.isfinite(inverse)) and np.all(inverse >= -1e-12))

    return fit(score, structural, prior, d, config=config, domain=domain)


def finalize_profile_pstrek(
    observations: np.ndarray,
    pairs: Sequence[tuple[int, int]],
    result: ContinuationResult,
    *,
    lambda_bic: float = 2.0,
) -> tuple[np.ndarray, dict[str, object]]:
    """Post-process a thresholded candidate and retain auditable diagnostics."""
    data = np.asarray(observations, dtype=float)
    means = data.mean(axis=0, keepdims=True)
    stds = np.maximum(data.std(axis=0, ddof=0, keepdims=True), 1e-12)
    standardized = (data - means) / stds
    candidate = np.asarray(result.adjacency, dtype=np.uint8)
    diagnostics: dict[str, object] = {
        "candidate_edges": int(candidate.sum()),
        "postselection_policy": "order_parent_shrink_growback",
    }
    if not is_dag(candidate):
        diagnostics["postselection_status"] = "skipped_candidate_not_dag"
        diagnostics["final_edges"] = int(candidate.sum())
        return candidate, diagnostics
    final, postselection = order_parent_postselection(
        standardized, candidate, pairs, lambda_bic=lambda_bic)
    diagnostics.update({
        "postselection_status": "applied",
        "final_edges": int(final.sum()),
        "postselection_deletions": postselection["postselection_deletions"],
        "postselection_feasibility_deletions": postselection["postselection_feasibility_deletions"],
        "postselection_growback_additions": postselection["postselection_growback_additions"],
        "postprocessed_bic": postselection["postprocessed_bic"],
    })
    return final, diagnostics


def main() -> None:
    rng = np.random.default_rng(8)
    data = rng.normal(size=(32, 4))
    result = fit_profile_pstrek(
        data, [(0, 2)],
        config=ContinuationConfig(stages=1, warm_iter=2, max_iter=3,
                                  checkpoint=1, prior_weight=2.0))
    print(f"custom DAGMA edges={result.adjacency.sum()} stages={len(result.stages)}")


if __name__ == "__main__":
    main()
