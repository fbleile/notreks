import csv
import json
from pathlib import Path

import numpy as np

from notreks.aggregate import collect, write_tables
from notreks.planning import expand_protocol
from notreks.protocol import ProtocolSpec
from notreks.runner import prepare_run, solve_prepared
from notreks.solvers import SolverConfig, SolverRegistry, SolverResult


def test_aggregate_keeps_results_and_issues_separate(tmp_path: Path):
    spec = ProtocolSpec("test", (5,), (24,), ("er",), (2,), ("toy",),
                        knowledge_fractions=(0.0,), graph_replicates=2)
    runs = expand_protocol(spec)
    registry = SolverRegistry()
    registry.register("toy", lambda observations, pairs, seed, config: SolverResult(
        "toy", np.zeros((5, 5), dtype=np.uint8)))
    prepare_run(runs[0], tmp_path)
    artifacts = prepare_run(runs[1], tmp_path)
    solve_prepared(artifacts, runs[1], registry, SolverConfig())
    results, issues = collect(tmp_path)
    assert len(results) == 1
    assert len(issues) == 1
    assert results[0]["SHD_cpdag"] >= 0
    assert json.loads((artifacts.run_root / "evaluate" / "status.json").read_text())["state"] == "succeeded"
    write_tables(tmp_path, results, issues)
    with (tmp_path / "aggregate_results.csv").open() as handle:
        assert len(list(csv.DictReader(handle))) == 1


def test_aggregate_uses_external_projection_target(tmp_path: Path):
    observations = np.zeros((4, 3))
    truth = np.zeros((3, 3), dtype=np.uint8)
    np.save(tmp_path / "observations.npy", observations)
    np.save(tmp_path / "truth.npy", truth)
    (tmp_path / "pairs.json").write_text(json.dumps([[0, 2]]))
    (tmp_path / "projection.json").write_text(json.dumps({
        "projected": {"directed": [["a", "b"]], "bidirected": [["b", "c"]]}
    }))
    manifest = tmp_path / "external.json"
    manifest.write_text(json.dumps({
        "dataset_id": "external-demo", "observations": "observations.npy",
        "truth_adjacency": "truth.npy", "projection": "projection.json",
        "knowledge_pairs": "pairs.json",
        "nodes": ["a", "b", "c"], "evaluation_target": "causalman_latent_projection",
    }))
    from notreks.protocol import RunSpec
    run = RunSpec("external", "g", "g_n", "toy", 3, 4, "external", 0,
                  1, 2, 3, 0.0, 0, data_model="causalman_observational",
                  external_manifest=str(manifest))
    artifacts = prepare_run(run, tmp_path)
    registry = SolverRegistry()
    registry.register("toy", lambda observations, pairs, seed, config: SolverResult(
        "toy", np.zeros((3, 3), dtype=np.uint8)))
    solve_prepared(artifacts, run, registry, SolverConfig())
    results, issues = collect(tmp_path)
    assert not issues
    assert results[0]["evaluation_target"] == "causalman_latent_projection"
    assert results[0]["projected_marginal_adjacency_shd"] == 2
