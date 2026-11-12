"""Expand a catalog experiment into a condition-aware run plan."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .catalog import ExperimentDefinition, get
from .experiment import SeedBook
from .protocol import RunSpec


@dataclass(frozen=True)
class CatalogSelection:
    graph_start: int = 0
    graph_limit: int | None = None


def methods_for_condition(definition: ExperimentDefinition, dimension: int, fraction: float) -> tuple[str, ...]:
    """Return the registered methods appropriate for one knowledge level."""
    available = definition.methods_for_dimension(dimension)
    if definition.arm in {"well_specified", "linear_nongaussian", "nonlinear_gaussian"}:
        if fraction == 0.0:
            preferred = {"flop", "dagma", "var_sortnregress", "r2_sortnregress"}
        else:
            preferred = {method for method in available if (
                "notreks" in method or method.startswith("dagma-nt-") or method.startswith("flop-nt-"))}
        return tuple(method for method in available if method in preferred)
    if definition.arm == "chromatic":
        preferred = {"flop", "dagma"} if fraction == 0.0 else {"flop_notreks", "dagma_notreks"}
        return tuple(method for method in available if method in preferred)
    return available


def knowledge_requests(definition: ExperimentDefinition, fraction: float) -> tuple[str, ...]:
    """Expand catalog knowledge policies into deterministic strategy labels."""
    if fraction > 0 and definition.knowledge_strategies == ("target-k",):
        return tuple(f"target-k-{value}" for value in definition.target_k_values)
    return definition.knowledge_strategies


def expand_catalog(name: str, *, master_seed: int = 20260917,
                   selection: CatalogSelection = CatalogSelection()) -> tuple[ExperimentDefinition, list[RunSpec]]:
    definition = get(name)
    if not definition.cells:
        if definition.data_model.endswith("_observational"):
            raise ValueError(
                f"{name} requires external dataset manifests; provide the "
                "observations, truth, knowledge_pairs, and evaluation metadata "
                "before generating a plan")
        if definition.arm == "motivational_exact":
            raise ValueError(
                f"{name} is an analysis-only catalog entry and has no solver runs")
        return definition, []
    stop = definition.graph_replicates if selection.graph_limit is None else min(
        definition.graph_replicates, selection.graph_start + selection.graph_limit)
    if selection.graph_start < 0 or stop < selection.graph_start:
        raise ValueError("invalid graph replicate selection")
    seeds = SeedBook(master_seed)
    runs: list[RunSpec] = []
    for replicate in range(selection.graph_start, stop):
        for dimension, family, density in definition.cells:
            graph_id = f"{definition.name}_g{replicate:03d}_{family}{density}_d{dimension}"
            graph_seed = seeds.derive("graph", graph_id)
            for sample_size in definition.sample_sizes:
                data_id = f"{graph_id}_n{sample_size}"
                data_seed = seeds.derive("data", data_id, definition.data_model)
                for fraction in definition.knowledge_fractions:
                    rounds = definition.partial_rounds if 0.0 < fraction < 1.0 else 1
                    for strategy in knowledge_requests(definition, fraction):
                        for round_id in range(rounds):
                            knowledge_seed = seeds.derive("knowledge", data_id, fraction, strategy, round_id)
                            for method in methods_for_condition(definition, dimension, fraction):
                                runs.append(RunSpec(
                                protocol=definition.name, graph_id=graph_id, data_id=data_id,
                                method=method, dimension=dimension, sample_size=sample_size,
                                graph_family=family, density=density, graph_seed=graph_seed,
                                data_seed=data_seed, knowledge_seed=knowledge_seed,
                                    knowledge_fraction=fraction, knowledge_round=round_id,
                                    data_model=definition.data_model,
                                    knowledge_strategy=strategy,
                                ))
    return definition, runs


def write_catalog_plan(path: Path, definition: ExperimentDefinition, runs: list[RunSpec],
                       *, master_seed: int) -> None:
    payload = {
        "catalog_entry": definition.to_dict(),
        "master_seed": master_seed,
        "run_count": len(runs),
        "runs": [run.to_dict() for run in runs],
        "attempts_by_method": dict(definition.attempts_by_method),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-catalog-plan")
    parser.add_argument("experiment")
    parser.add_argument("output", type=Path)
    parser.add_argument("--master-seed", type=int, default=20260917)
    parser.add_argument("--graph-start", type=int, default=0)
    parser.add_argument("--graph-limit", type=int)
    args = parser.parse_args(argv)
    definition, runs = expand_catalog(args.experiment, master_seed=args.master_seed,
                                      selection=CatalogSelection(args.graph_start, args.graph_limit))
    write_catalog_plan(args.output, definition, runs, master_seed=args.master_seed)
    print(f"planned {len(runs)} runs -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
