"""Adapters for the validated solver implementations during migration.

The new repository owns the protocol and artifact contracts.  Until the
solver kernels are fully ported, this module is the only place that knows how
to call the existing Benchpress implementations.  The checkout is explicit;
there is no implicit import from the current working directory.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Callable

import numpy as np

from .solvers import SolverConfig, SolverError, SolverRegistry, SolverResult


def register_benchpress(registry: SolverRegistry, repository: Path) -> dict[str, Any]:
    """Register exact FLOP/DAGMA adapters from a validated checkout.

    Returns provenance for the run manifest.  The caller should record it
    alongside the solver result so a result never depends on an undocumented
    source tree.
    """
    repository = repository.resolve()
    if not (repository / "workflow").is_dir():
        raise SolverError(f"not a Benchpress checkout: {repository}")
    if str(repository) not in sys.path:
        sys.path.insert(0, str(repository))
    try:
        module = __import__(
            "workflow.rules.structure_learning_algorithms.dagma_global_search.tools.systematic_notreks_d20_benchmark",
            fromlist=["vanilla_flop_candidate", "flop_notreks_candidate", "dagma_candidate"],
        )
    except ImportError as error:
        raise SolverError(f"could not import Benchpress NOTREKS solvers: {error}") from error

    registry.register("flop", _flop_adapter(module.vanilla_flop_candidate, "flop"))
    registry.register("flop_notreks", _flop_notreks_adapter(module.flop_notreks_candidate))
    registry.register("dagma", _dagma_adapter(module.dagma_candidate, "dagma"))
    registry.register("dagma_notreks", _dagma_adapter(module.dagma_candidate, "dagma_notreks"))
    registry.register("dagma_tcc", _dagma_adapter(module.dagma_candidate, "dagma_tcc"))
    return {
        "backend": "benchpress",
        "repository": str(repository),
        "module": module.__name__,
    }


def register_flopsearch(registry: SolverRegistry) -> dict[str, Any]:
    """Register FLOP directly from the independently installable package."""
    try:
        import flopsearch
    except ImportError as error:
        raise SolverError("direct FLOP integration requires the flopsearch package") from error

    def solve_flop(observations, pairs, seed, config, method):
        candidate, diagnostics = flopsearch.flop_notreks(
            observations, 2.0, pairs, restarts=max(0, config.attempts - 1),
            seed=seed, max_signature_rounds=config.flop_sweeps,
            search_version="local_greedy_rust", local_greedy_passes=8,
            return_diagnostics=True)
        return SolverResult(method, _binary(candidate), diagnostics)

    registry.register("flop_notreks", lambda observations, pairs, seed, config:
                      solve_flop(observations, pairs, seed, config, "flop_notreks"))
    registry.register("flop", lambda observations, pairs, seed, config:
                      solve_flop(observations, pairs, seed, config, "flop"))
    return {"backend": "flopsearch", "version": getattr(flopsearch, "__version__", None)}


def register_dagma(registry: SolverRegistry) -> dict[str, Any]:
    """Register upstream vanilla DAGMA and the standalone PSTrek path."""
    try:
        from dagma.linear import DagmaLinear
    except ImportError as error:
        raise SolverError("direct DAGMA integration requires the dagma package") from error

    def solve(observations, pairs, seed, config):
        del pairs
        try:
            import torch
            torch.manual_seed(int(seed))
        except ImportError:
            pass
        model = DagmaLinear("l2", verbose=False)
        weights = model.fit(
            observations, lambda1=0.03, w_threshold=0.3,
            T=config.dagma_stages, warm_iter=config.dagma_warm_iter,
            max_iter=config.dagma_max_iter,
        )
        adjacency = (np.abs(np.asarray(weights)) > 0.3).astype(np.uint8)
        return SolverResult("dagma", adjacency, {
            "backend": "dagma", "threshold": 0.3,
            "iterations_T": config.dagma_stages,
        })

    registry.register("dagma", solve)

    from .dagma_backend import fit_pstrek

    def solve_custom(observations, pairs, seed, config, method, score_type):
        from .continuation import ContinuationConfig
        from .dagma_backend import finalize_profile_pstrek
        from .scores import gaussian_bic, is_dag
        best = None
        best_bic = np.inf
        restart_diagnostics = []
        from .dagma_backend import deterministic_initial_weights
        for restart in range(config.attempts):
            initial = (np.zeros((observations.shape[1],) * 2)
                       if restart == 0 else deterministic_initial_weights(
                           observations.shape[1], int(seed) + restart))
            default_s = (1.0, 0.9, 0.8, 0.7, 0.6)
            s_schedule = default_s + (default_s[-1],) * max(0, config.dagma_stages - len(default_s))
            result = fit_pstrek(
                observations, pairs,
                config=ContinuationConfig(
                    stages=config.dagma_stages,
                    warm_iter=config.dagma_warm_iter,
                    max_iter=config.dagma_max_iter,
                    prior_weight=config.trek_weight,
                    s_schedule=s_schedule,
                    threshold=0.3,
                ),
                initial_weights=initial,
                score_type=score_type,
            )
            adjacency, final_diagnostics = finalize_profile_pstrek(observations, pairs, result)
            bic = (gaussian_bic(observations, adjacency, lambda_bic=2.0)[0]
                   if is_dag(adjacency) else np.inf)
            restart_diagnostics.append({"restart": restart, "bic": float(bic), **final_diagnostics})
            if bic < best_bic:
                best_bic = bic
                best = (result, adjacency, final_diagnostics)
        if best is None:
            raise SolverError("DAGMA+PSTrek produced no restart result")
        result, adjacency, final_diagnostics = best
        return SolverResult(method, adjacency, {
            "backend": "notreks.continuation",
            "loss": score_type,
            "threshold": 0.3,
            "stages": len(result.stages),
            "converged": result.converged,
            "attempts_requested": config.attempts,
            "attempts_completed": len(restart_diagnostics),
            "selected_bic": float(best_bic),
            "restart_diagnostics": restart_diagnostics,
            **final_diagnostics,
        })

    def solve_notreks(observations, pairs, seed, config):
        return solve_custom(observations, pairs, seed, config,
                            "dagma_notreks", "profile_gaussian")

    def solve_profile(observations, pairs, seed, config):
        del pairs
        return solve_custom(observations, [], seed, config,
                            "dagma_profile", "profile_gaussian")

    registry.register("dagma_notreks", solve_notreks)
    registry.register("dagma_profile", solve_profile)
    return {"backend": "dagma+notreks", "loss": "l2/profile_gaussian", "threshold": 0.3,
            "profile_baseline": "dagma_profile"}


def _flop_adapter(function: Callable[..., tuple[np.ndarray, dict[str, Any]]], name: str):
    def solve(observations, pairs, seed, config):
        del pairs
        candidate, diagnostics = function(observations, seed, config.attempts)
        return SolverResult(name, _binary(candidate), diagnostics)
    return solve


def _flop_notreks_adapter(function: Callable[..., tuple[np.ndarray, dict[str, Any]]]):
    def solve(observations, pairs, seed, config):
        candidate, diagnostics = function(
            observations, pairs, seed, config.attempts, config.flop_sweeps,
            search_version="flop_like", local_greedy_passes=8,
        )
        return SolverResult("flop_notreks", _binary(candidate), diagnostics)
    return solve


def _dagma_adapter(function: Callable[..., tuple[np.ndarray, dict[str, Any]]], name: str):
    def solve(observations, pairs, seed, config):
        use_notreks = name != "dagma"
        constraint_regime = "tcc" if name == "dagma_tcc" else "pstrek"
        kwargs = {"trek_weight": config.trek_weight}
        if name == "dagma_tcc":
            kwargs.update({"constraint_regime": constraint_regime,
                           "tcc_coupling": 1.0, "dag_penalty_weight": 0.0})
        candidate, diagnostics = function(
            observations, pairs if use_notreks else [], use_notreks, False,
            seed, config.attempts, config.dagma_warm_iter,
            config.dagma_max_iter, config.dagma_stages, **kwargs,
        )
        return SolverResult(name, _binary(candidate), diagnostics)
    return solve


def _binary(candidate: np.ndarray) -> np.ndarray:
    matrix = np.asarray(candidate)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise SolverError("solver returned a non-square adjacency matrix")
    return (matrix != 0).astype(np.uint8)


def main() -> None:
    """Explain how to activate the migration adapter."""
    print("register_benchpress(registry, Path('/path/to/benchpress'))")


if __name__ == "__main__":
    main()
