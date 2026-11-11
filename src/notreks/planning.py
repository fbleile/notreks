"""Expand a validated protocol into deterministic, inspectable run plans."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from .experiment import SeedBook
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
                                knowledge_seed = seeds.derive(
                                    "knowledge", data_id, fraction, knowledge_round)
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
                                        data_model=data_model,
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


def main() -> None:
    """Print the number of runs in a tiny planning smoke test."""
    spec = ProtocolSpec("smoke", (6,), (32,), ("er",), (2,), ("flop",), graph_replicates=2)
    print(len(expand_protocol(spec)))


if __name__ == "__main__":
    main()
