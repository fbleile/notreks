"""Checkpointable preparation runner for graph, data, and knowledge stages."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import traceback
from typing import Iterator

import numpy as np

from .experiment import RunDirectory, RunRecorder, atomic_json, utc_now
from .external import ExternalDataset
from .graphs import generate
from .protocol import RunSpec
from .solvers import SolverConfig, SolverRegistry, SolverResult
from .synthetic import no_trek_pairs, select_pairs, simulate_sem


@dataclass(frozen=True)
class PreparedArtifacts:
    run_root: Path
    graph_path: Path
    data_path: Path
    weights_path: Path
    knowledge_path: Path


@contextmanager
def stage(directory: Path, name: str) -> Iterator[None]:
    """Record one stage's state and preserve its traceback on failure."""
    stage_dir = directory / name
    stage_dir.mkdir(parents=True, exist_ok=True)
    status = stage_dir / "status.json"
    atomic_json(status, {"stage": name, "state": "running", "started_at": utc_now()})
    try:
        yield
    except Exception as error:
        (stage_dir / "error.txt").write_text(traceback.format_exc())
        atomic_json(status, {
            "stage": name, "state": "failed", "finished_at": utc_now(),
            "error_type": type(error).__name__, "error": str(error),
        })
        raise
    else:
        atomic_json(status, {"stage": name, "state": "succeeded", "finished_at": utc_now()})


def prepare_run(run: RunSpec, output_root: Path, *, rscript: str | None = None) -> PreparedArtifacts:
    """Prepare shared graph/data/knowledge artifacts for one planned run.

    Shared files are keyed by ``data_id`` and the knowledge identity, so the
    method-specific runs do not regenerate identical inputs.  Existing files
    are reused only when their provenance manifest matches the requested run.
    """
    run_dir = RunDirectory(output_root / "runs" / run.key())
    shared = output_root / "shared" / run.data_id
    with RunRecorder(run_dir, run, command=["prepare", run.key()]):
        with stage(run_dir.root, "definition"):
            atomic_json(run_dir.stage("definition") / "run.json", run.to_dict())
        with stage(run_dir.root, "data"):
            graph_path, data_path, weights_path = _prepare_data(run, shared, rscript=rscript)
        with stage(run_dir.root, "knowledge"):
            knowledge_path = _prepare_knowledge(run, shared)
    return PreparedArtifacts(run_dir.root, graph_path, data_path, weights_path, knowledge_path)


def solve_prepared(artifacts: PreparedArtifacts, run: RunSpec,
                   registry: SolverRegistry, config: SolverConfig) -> SolverResult:
    """Run one registered solver and persist its complete machine output."""
    with stage(artifacts.run_root, "solve"):
        observations = np.load(artifacts.data_path)
        knowledge = json.loads(artifacts.knowledge_path.read_text())
        pairs = [tuple(pair) for pair in knowledge["pairs"]]
        result = registry.run(run.method, observations, pairs, run.knowledge_seed, config)
        solve_dir = artifacts.run_root / "solve"
        np.save(solve_dir / "adjacency.npy", result.adjacency)
        atomic_json(solve_dir / "result.json", {
            "method": result.method,
            "runtime_seconds": result.runtime_seconds,
            "diagnostics": _json_safe(result.diagnostics),
            "solver_config": _json_safe(config.__dict__),
        })
    return result


def _prepare_data(run: RunSpec, shared: Path, *, rscript: str | None) -> tuple[Path, Path, Path]:
    manifest_path = shared / "data.json"
    graph_path, data_path, weights_path = shared / "graph.npy", shared / "data.npy", shared / "weights.npy"
    expected = {
        "graph_id": run.graph_id, "data_id": run.data_id, "dimension": run.dimension,
        "sample_size": run.sample_size, "family": run.graph_family,
        "density": run.density, "graph_seed": run.graph_seed,
        "data_seed": run.data_seed, "data_model": run.data_model,
        "external_manifest": run.external_manifest,
    }
    if manifest_path.exists() and graph_path.exists() and data_path.exists() and weights_path.exists():
        if json.loads(manifest_path.read_text()) != expected:
            raise RuntimeError(f"shared data manifest mismatch: {manifest_path}")
        return graph_path, data_path, weights_path
    shared.mkdir(parents=True, exist_ok=True)
    if run.data_model.endswith("_observational"):
        if not run.external_manifest:
            raise ValueError(
                f"{run.data_model} requires RunSpec.external_manifest; "
                "external datasets are never inferred from synthetic settings")
        dataset = ExternalDataset.from_manifest(Path(run.external_manifest))
        observations, graph, weights = dataset.validate_arrays()
        if observations.shape[0] != run.sample_size or observations.shape[1] != run.dimension:
            raise ValueError(
                f"external dataset shape {observations.shape} does not match "
                f"run (n={run.sample_size}, d={run.dimension})")
        atomic_json(shared / "external.json", {
            "manifest": str(dataset.manifest_path),
            "dataset_id": dataset.dataset_id,
            "evaluation_target": dataset.evaluation_target,
            "projection": str(dataset.projection_path) if dataset.projection_path else None,
            "nodes": list(dataset.nodes),
            "metadata": dataset.metadata,
        })
    else:
        graph = generate(run.graph_family, run.dimension, run.density, run.graph_seed, rscript=rscript)
        simulated = simulate_sem(graph, run.sample_size, run.graph_seed, run.data_seed, run.data_model)
        observations, weights = simulated.observations, simulated.weights
    np.save(graph_path, graph)
    np.save(data_path, observations)
    np.save(weights_path, weights)
    atomic_json(manifest_path, expected)
    return graph_path, data_path, weights_path


def _prepare_knowledge(run: RunSpec, shared: Path) -> Path:
    graph = np.load(shared / "graph.npy")
    all_pairs = no_trek_pairs(graph)
    pairs = select_pairs(all_pairs, run.knowledge_fraction, run.knowledge_seed)
    path = shared / "knowledge" / f"q{run.knowledge_fraction:g}_r{run.knowledge_round}.json"
    expected = {
        "data_id": run.data_id, "knowledge_seed": run.knowledge_seed,
        "knowledge_fraction": run.knowledge_fraction,
        "knowledge_round": run.knowledge_round,
        "knowledge_strategy": run.knowledge_strategy,
        "available_pairs": len(all_pairs), "selected_pairs": len(pairs),
        "pairs": [list(pair) for pair in pairs],
    }
    if path.exists() and json.loads(path.read_text()) != expected:
        raise RuntimeError(f"shared knowledge manifest mismatch: {path}")
    atomic_json(path, expected)
    return path


def _json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value

def main() -> None:
    """Run a tiny preparation smoke test under a temporary-looking directory."""
    from tempfile import TemporaryDirectory
    from .planning import expand_protocol
    from .protocol import ProtocolSpec

    spec = ProtocolSpec("smoke", (6,), (32,), ("er",), (2,), ("flop",), graph_replicates=1)
    with TemporaryDirectory() as temporary:
        artifacts = prepare_run(expand_protocol(spec)[0], Path(temporary))
        print(artifacts.data_path.exists(), artifacts.knowledge_path.exists())


if __name__ == "__main__":
    main()
