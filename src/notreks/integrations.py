"""Adapters for the validated solver implementations during migration.

The new repository owns the protocol and artifact contracts.  Until the
solver kernels are fully ported, this module is the only place that knows how
to call the existing Benchpress implementations.  The checkout is explicit;
there is no implicit import from the current working directory.
"""

from __future__ import annotations

from pathlib import Path
import inspect
import sys
from typing import Any, Callable

import numpy as np

from .solvers import SolverConfig, SolverError, SolverRegistry, SolverResult
from .ancestry import (bounded_ancestry_violations, describe,
                       direct_ancestry_edges)


DIRECT_METHODS = frozenset({
    "flop", "flop_notreks", "flop-nt-edge-mask", "flop-nt-post",
    "dagma", "dagma_notreks", "dagma-nt-edge-mask", "dagma-nt-post",
    "dagma_profile", "dagma_tcc", "var_sortnregress", "r2_sortnregress",
})
BENCHPRESS_METHODS = frozenset({
    "flop", "flop_notreks", "dagma", "dagma_notreks", "dagma_tcc",
})


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

    def solve_flop(observations, pairs, seed, config, method, *, forbidden_edges=(), search_version=None):
        if search_version is None:
            search_version = "global_greedy_rust" if method == "flop" else "flop_like"
        ancestry = config.ancestry_depth
        effective_pairs = list(pairs)
        effective_forbidden = tuple(forbidden_edges)
        if method == "flop_notreks" and ancestry == 1:
            # Depth one is exactly the direct-edge restriction, but it is
            # enforced by the proposal evaluator rather than by post-masking.
            effective_pairs = []
            effective_forbidden = direct_ancestry_edges(pairs)
        elif method == "flop_notreks" and ancestry is not None and ancestry > 1:
            try:
                parameters = inspect.signature(flopsearch.flop_notreks).parameters
            except (TypeError, ValueError) as error:
                raise SolverError(
                    "cannot inspect the installed flopsearch bounded-ancestry "
                    "interface; refusing to approximate depth 2+ by post-masking") from error
            if "ancestry_depth" not in parameters:
                raise SolverError(
                    "the installed flopsearch backend does not expose bounded "
                    "ancestry constraints; depth 2+ cannot be emulated by post-masking")
        candidate, diagnostics = flopsearch.flop_notreks(
            observations, 2.0, effective_pairs, restarts=max(0, config.attempts - 1),
            seed=seed, max_signature_rounds=config.flop_sweeps,
            search_version=search_version, local_greedy_passes=8,
            forbidden_edges=effective_forbidden,
            **({"ancestry_depth": ancestry} if ancestry is not None and ancestry > 1 else {}),
            return_diagnostics=True)
        selected = diagnostics.get("selected_dag_edges")
        if selected is not None:
            graph = np.zeros((observations.shape[1], observations.shape[1]), dtype=np.uint8)
            for parent, child in selected:
                graph[int(parent), int(child)] = 1
            candidate = graph
        binary_candidate = _binary(candidate)
        bounded_violations = ()
        if method == "flop_notreks" and ancestry is not None and ancestry > 1:
            bounded_violations = bounded_ancestry_violations(binary_candidate, pairs, ancestry)
            if bounded_violations:
                raise SolverError(
                    "bounded-ancestry FLOP backend returned an infeasible graph: "
                    f"{bounded_violations[:3]!r}")
        return SolverResult(method, binary_candidate, {
            **diagnostics, **describe(ancestry),
            "constraint_enforcement": "proposal_evaluator",
            "bounded_ancestry_violations": len(bounded_violations),
        })

    registry.register("flop_notreks", lambda observations, pairs, seed, config:
                      solve_flop(observations, pairs, seed, config, "flop_notreks"))
    registry.register("flop", lambda observations, pairs, seed, config:
                      solve_flop(observations, pairs, seed, config, "flop"))
    from .postselection import direct_mask_edges, order_parent_postselection

    def edge_mask(observations, pairs, seed, config):
        return solve_flop(observations, [], seed, config, "flop-nt-edge-mask",
                          forbidden_edges=direct_mask_edges(pairs),
                          search_version="local_greedy_rust")

    def postselection(observations, pairs, seed, config):
        result = solve_flop(observations, [], seed, config, "flop-nt-post")
        candidate, diagnostics = order_parent_postselection(observations, result.adjacency, pairs)
        return SolverResult("flop-nt-post", candidate,
                            {**result.diagnostics, **diagnostics, "baseline": "postselection"})

    registry.register("flop-nt-edge-mask", edge_mask)
    registry.register("flop-nt-post", postselection)
    return {"backend": "flopsearch", "version": getattr(flopsearch, "__version__", None)}


def register_direct(registry: SolverRegistry, methods: set[str]) -> dict[str, Any]:
    """Register only the installed direct backends needed by a run plan."""
    missing = set(methods) - DIRECT_METHODS
    if missing:
        raise SolverError(
            "direct backend does not yet implement: " + ", ".join(sorted(missing)))
    provenance: dict[str, Any] = {"backend": "direct", "methods": sorted(methods)}
    if any(method.startswith("flop") for method in methods):
        provenance["flopsearch"] = register_flopsearch(registry)
    if any(method.startswith("dagma") for method in methods):
        provenance["dagma"] = register_dagma(registry)
    if {"var_sortnregress", "r2_sortnregress"} & methods:
        from .sortnregress import sortnregress
        for name, kind in (("var_sortnregress", "variance"), ("r2_sortnregress", "r2")):
            if name in methods:
                def baseline(observations, pairs, seed, config, *, kind=kind, method_name=name):
                    del pairs, seed, config
                    adjacency, diagnostics = sortnregress(observations, kind)
                    return SolverResult(method_name, adjacency, diagnostics)
                registry.register(name, baseline)
    return provenance


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
            "backend": "dagma", "score": "l2", "threshold": 0.3,
            "iterations_T": config.dagma_stages,
        })

    registry.register("dagma", solve)

    from .dagma_backend import fit_pstrek

    def solve_custom(observations, pairs, seed, config, method, score_type,
                     constraint_type="pstrek"):
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
                constraint_type=constraint_type,
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
            "constraint": constraint_type,
            "threshold": 0.3,
            "stages": len(result.stages),
            "converged": result.converged,
            "domain_retries": result.domain_retries,
            "attempts_requested": config.attempts,
            "attempts_completed": len(restart_diagnostics),
            "selected_bic": float(best_bic),
            "restart_diagnostics": restart_diagnostics,
            **final_diagnostics,
        })

    def solve_notreks(observations, pairs, seed, config):
        return solve_custom(observations, pairs, seed, config,
                            "dagma_notreks", "profile_gaussian")

    def solve_tcc(observations, pairs, seed, config):
        return solve_custom(observations, pairs, seed, config,
                            "dagma_tcc", "profile_gaussian", "tcc")

    def solve_profile(observations, pairs, seed, config):
        del pairs
        return solve_custom(observations, [], seed, config,
                            "dagma_profile", "profile_gaussian")

    registry.register("dagma_notreks", solve_notreks)
    registry.register("dagma_profile", solve_profile)
    registry.register("dagma_tcc", solve_tcc)
    from .postselection import direct_mask_edges, order_parent_postselection

    def dagma_edge_mask(observations, pairs, seed, config):
        result = solve(observations, [], seed, config)
        candidate = result.adjacency.copy()
        for parent, child in direct_mask_edges(pairs):
            candidate[parent, child] = 0
        return SolverResult("dagma-nt-edge-mask", candidate,
                            {**result.diagnostics, "baseline": "edge_mask"})

    def dagma_postselection(observations, pairs, seed, config):
        result = solve(observations, [], seed, config)
        candidate, diagnostics = order_parent_postselection(observations, result.adjacency, pairs)
        return SolverResult("dagma-nt-post", candidate,
                            {**result.diagnostics, **diagnostics, "baseline": "postselection"})

    registry.register("dagma-nt-edge-mask", dagma_edge_mask)
    registry.register("dagma-nt-post", dagma_postselection)
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
        if config.ancestry_depth is not None:
            raise SolverError(
                "bounded ancestry depth is available only in the direct FLOP "
                "backend; the compatibility adapter exposes full ancestry")
        candidate, diagnostics = function(
            observations, pairs, seed, config.attempts, config.flop_sweeps,
            search_version="flop_like", local_greedy_passes=8,
        )
        return SolverResult("flop_notreks", _binary(candidate), {
            **diagnostics, **describe(None), "constraint_enforcement": "proposal_evaluator",
        })
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
