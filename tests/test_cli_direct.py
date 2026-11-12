from pathlib import Path

from notreks.cli import main
from notreks.planning import expand_protocol, write_plan
from notreks.protocol import ProtocolSpec


def test_direct_cli_run_and_aggregate(tmp_path: Path):
    plan = tmp_path / "plan.json"
    output = tmp_path / "results"
    spec = ProtocolSpec(
        "cli_direct_smoke", (4,), (16,), ("er",), (2,), ("dagma_notreks",),
        knowledge_fractions=(0.25,), partial_rounds=1, graph_replicates=1,
    )
    write_plan(plan, spec, expand_protocol(spec), master_seed=8)
    assert main([
        "run", str(plan), str(output), "--backend", "direct",
        "--dagma-stages", "1", "--dagma-warm-iter", "1", "--dagma-max-iter", "1",
    ]) == 0
    assert main(["aggregate", str(output)]) == 0
    assert (output / "aggregate_results.csv").exists()
    assert not (output / "aggregate_issues.csv").read_text().strip().splitlines()[1:]
