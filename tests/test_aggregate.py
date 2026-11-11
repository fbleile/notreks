import csv
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
    write_tables(tmp_path, results, issues)
    with (tmp_path / "aggregate_results.csv").open() as handle:
        assert len(list(csv.DictReader(handle))) == 1
