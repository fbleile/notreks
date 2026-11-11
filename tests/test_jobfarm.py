import json
from pathlib import Path

from notreks.jobfarm import write_commands


def test_jobfarm_commands_are_one_per_run(tmp_path: Path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"runs": [{"run_key": "a"}, {"run_key": "b"}, {"run_key": "c"}]}))
    commands = tmp_path / "commands.cmd"
    count = write_commands(plan, commands, tmp_path / "results", tmp_path / "benchpress",
                           tmp_path / "python", tmp_path / "project", start=1, limit=2)
    assert count == 2
    lines = commands.read_text().splitlines()
    assert len(lines) == 2
    assert all("--limit 1" in line and "--start" in line for line in lines)
