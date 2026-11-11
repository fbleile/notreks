import json
from pathlib import Path

from notreks.cli import main


def test_cli_plans_and_prepares_smoke_protocol(tmp_path: Path):
    protocol = Path("examples/smoke_protocol.json")
    plan = tmp_path / "plan.json"
    output = tmp_path / "results"
    assert main(["plan", str(protocol), str(plan)]) == 0
    assert json.loads(plan.read_text())["run_count"] == 4
    assert main(["prepare", str(plan), str(output)]) == 0
    assert len(list((output / "runs").glob("*/status.json"))) == 4
