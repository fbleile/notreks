import json
from pathlib import Path

import numpy as np
import pytest

from notreks.planning import expand_protocol
from notreks.protocol import ProtocolSpec
from notreks.runner import prepare_run, solve_prepared
from notreks.solvers import SolverConfig, SolverRegistry, SolverResult


def test_prepare_run_reuses_shared_inputs(tmp_path: Path):
    spec = ProtocolSpec("test", (6,), (32,), ("er",), (2,), ("flop", "flop_notreks"),
                        knowledge_fractions=(0.25,), partial_rounds=2, graph_replicates=1)
    runs = expand_protocol(spec)
    first = prepare_run(runs[0], tmp_path)
    second = prepare_run(runs[1], tmp_path)
    assert first.graph_path == second.graph_path
    assert first.data_path == second.data_path
    assert first.knowledge_path == second.knowledge_path
    assert len(list((tmp_path / "runs").glob("*/status.json"))) == 2
    assert json.loads(first.knowledge_path.read_text())["selected_pairs"] >= 1


def test_solve_stage_persists_adjacency_and_diagnostics(tmp_path: Path):
    spec = ProtocolSpec("test", (6,), (32,), ("er",), (2,), ("toy",),
                        knowledge_fractions=(0.25,), graph_replicates=1)
    run = expand_protocol(spec)[0]
    artifacts = prepare_run(run, tmp_path)
    registry = SolverRegistry()
    registry.register("toy", lambda observations, pairs, seed, config: SolverResult(
        "toy", np.zeros((6, 6), dtype=np.uint8), {"seed": seed}))
    result = solve_prepared(artifacts, run, registry, SolverConfig())
    assert result.method == "toy"
    assert (artifacts.run_root / "solve" / "adjacency.npy").exists()
    assert json.loads((artifacts.run_root / "solve" / "result.json").read_text())["method"] == "toy"


def test_target_k_knowledge_artifacts_reject_duplicate_sets(tmp_path: Path):
    from notreks.protocol import RunSpec

    first = RunSpec("chrom", "g", "g_n", "flop_notreks", 6, 32, "er", 2,
                    1, 2, 3, 0.25, 0, knowledge_strategy="target-k-2")
    second = RunSpec("chrom", "g", "g_n", "flop_notreks", 6, 32, "er", 2,
                     1, 2, 3, 0.25, 1, knowledge_strategy="target-k-2")
    prepare_run(first, tmp_path)
    with pytest.raises(ValueError, match="duplicate target-K"):
        prepare_run(second, tmp_path)
