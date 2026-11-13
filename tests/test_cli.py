import json
from pathlib import Path

from notreks.cli import main


def test_cli_plans_and_prepares_smoke_protocol(tmp_path: Path):
    protocol = Path("examples/smoke_protocol.json")
    plan = tmp_path / "plan.json"
    output = tmp_path / "results"
    assert main(["plan", str(protocol), str(plan)]) == 0
    assert json.loads(plan.read_text())["run_count"] == 2
    assert main(["prepare", str(plan), str(output)]) == 0
    assert len(list((output / "runs").glob("*/status.json"))) == 2


def test_cli_catalog_lists_registered_experiments(capsys):
    assert main(["catalog"]) == 0
    output = capsys.readouterr().out
    assert "main:" in output
    assert "prior-structure-chrom:" in output
