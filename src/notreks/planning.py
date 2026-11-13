"""Expand a validated protocol into deterministic, inspectable run plans."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from .experiment import SeedBook
from .external import ExternalDataset
from .protocol import ProtocolSpec, RunSpec


@dataclass(frozen=True)
class PlanSelection:
    """Optional slice of a protocol used for smoke tests or partial reruns."""

    graph_start: int = 0
    graph_limit: int | None = None
    methods: tuple[str, ...] | None = None
    sample_sizes: tuple[int, ...] | None = None


def expand_protocol(spec: ProtocolSpec, *, data_model: str = "linear_gaussian",
                    master_seed: int = 20260917,
                    selection: PlanSelection = PlanSelection()) -> list[RunSpec]:
    """Create one run per graph/data/knowledge/method combination.

    The graph seed is shared across sample sizes and methods.  Data and
    knowledge seeds are derived independently, so changing the method list
    cannot change the generated graph or prior information.
    """
    spec.validate()
    if selection.graph_start < 0 or selection.graph_start >= spec.graph_replicates:
        if selection.graph_start != 0 or spec.graph_replicates != 0:
            raise ValueError("graph_start is outside the protocol replicate range")
    methods = selection.methods or spec.methods
    unknown = set(methods) - set(spec.methods)
    if unknown:
        raise ValueError(f"methods not in protocol: {sorted(unknown)}")
    samples = selection.sample_sizes or spec.sample_sizes
    if set(samples) - set(spec.sample_sizes):
        raise ValueError("sample_sizes must be a subset of the protocol")
    stop = spec.graph_replicates if selection.graph_limit is None else min(
        spec.graph_replicates, selection.graph_start + selection.graph_limit)
    if stop < selection.graph_start:
        raise ValueError("graph_limit must not be negative")

    seeds = SeedBook(master_seed)
    runs: list[RunSpec] = []
    for replicate in range(selection.graph_start, stop):
        for family in spec.graph_families:
            for density in spec.densities:
                for dimension in spec.dimensions:
                    graph_id = f"{spec.name}_g{replicate:03d}_{family}{density}_d{dimension}"
                    graph_seed = seeds.derive("graph", graph_id)
                    for sample_size in samples:
                        data_id = f"{graph_id}_n{sample_size}"
                        data_seed = seeds.derive("data", data_id, data_model)
                        for fraction in spec.knowledge_fractions:
                            rounds = spec.partial_rounds if 0.0 < fraction < 1.0 else 1
                            for knowledge_round in range(rounds):
                                pair_counts = (spec.knowledge_pair_counts
                                               if fraction > 0 else (None,)) or (None,)
                                strategies = ("random",) if fraction == 0.0 else spec.knowledge_strategies
                                if spec.target_k_values and fraction > 0:
                                    strategies = tuple(
                                        f"target-k-{target}" for target in spec.target_k_values)
                                for pair_count in pair_counts:
                                    for strategy in strategies:
                                        knowledge_seed = seeds.derive(
                                            "knowledge", data_id, fraction, pair_count,
                                            strategy, knowledge_round)
                                        for method in methods:
                                            runs.append(RunSpec(
                                                protocol=spec.name,
                                                graph_id=graph_id,
                                                data_id=data_id,
                                                method=method,
                                                dimension=dimension,
                                                sample_size=sample_size,
                                                graph_family=family,
                                                density=density,
                                                graph_seed=graph_seed,
                                                data_seed=data_seed,
                                                knowledge_seed=knowledge_seed,
                                                knowledge_fraction=fraction,
                                                knowledge_round=knowledge_round,
                                                knowledge_pair_count=pair_count,
                                                infeasible_policy=spec.infeasible_policy,
                                                data_model=data_model,
                                                knowledge_strategy=strategy,
                                            ))
    return runs


def write_plan(path: Path, spec: ProtocolSpec, runs: Iterable[RunSpec], *, master_seed: int) -> None:
    """Write a readable plan that can be inspected before execution."""
    run_list = [run.to_dict() for run in runs]
    payload = {
        "protocol": spec.to_dict(),
        "master_seed": master_seed,
        "run_count": len(run_list),
        "runs": run_list,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def external_plan(manifest: Path, *, name: str, methods: tuple[str, ...],
                  fractions: tuple[float, ...], partial_rounds: int = 5,
                  attempts: dict[str, int] | None = None,
                  master_seed: int = 20260917) -> dict[str, object]:
    """Build ordinary run identities around one validated external dataset."""
    dataset = ExternalDataset.from_manifest(manifest)
    observations, _truth, _weights = dataset.validate_arrays()
    if not name.strip() or not methods:
        raise ValueError("external plans require a name and at least one method")
    if any(q < 0.0 or q > 1.0 for q in fractions):
        raise ValueError("knowledge fractions must lie in [0, 1]")
    attempts = attempts or {method: 1 for method in methods}
    if set(attempts) - set(methods):
        raise ValueError(f"attempt budget provided for unknown methods: {sorted(set(attempts) - set(methods))}")
    if any(attempts.get(method, 1) < 1 for method in methods):
        raise ValueError("method attempt budgets must be positive")
    seeds = SeedBook(master_seed)
    graph_id = dataset.dataset_id
    data_id = f"{dataset.dataset_id}_n{observations.shape[0]}"
    graph_seed = seeds.derive("external-graph", graph_id)
    data_seed = seeds.derive("external-data", data_id)
    runs = []
    for fraction in fractions:
        rounds = partial_rounds if 0.0 < fraction < 1.0 else 1
        for round_id in range(rounds):
            knowledge_seed = seeds.derive("external-knowledge", data_id, fraction, round_id)
            for method in methods:
                runs.append(RunSpec(
                    protocol=name, graph_id=graph_id, data_id=data_id, method=method,
                    dimension=observations.shape[1], sample_size=observations.shape[0],
                    graph_family="external", density=0, graph_seed=graph_seed,
                    data_seed=data_seed, knowledge_seed=knowledge_seed,
                    knowledge_fraction=fraction, knowledge_round=round_id,
                    data_model=dataset.evaluation_target + "_observational",
                    external_manifest=str(dataset.manifest_path),
                ))
    return {"protocol": name, "manifest": str(dataset.manifest_path),
            "dataset_id": dataset.dataset_id, "master_seed": master_seed,
            "run_count": len(runs), "runs": [run.to_dict() for run in runs],
            "attempts_by_method": attempts}


def main() -> None:
    """Print the number of runs in a tiny planning smoke test."""
    spec = ProtocolSpec("smoke", (6,), (32,), ("er",), (2,), ("flop",), graph_replicates=2)
    print(len(expand_protocol(spec)))


if __name__ == "__main__":
    main()
