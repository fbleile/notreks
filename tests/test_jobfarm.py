import json
from pathlib import Path

from notreks.jobfarm import write_commands


def test_jobfarm_commands_are_one_per_run(tmp_path: Path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"runs": [{"run_key": "a", "method": "flop"},
                                          {"run_key": "b", "method": "dagma"},
                                          {"run_key": "c", "method": "flop"}],
                              "attempts_by_method": {"flop": 20, "dagma": 2}}))
    commands = tmp_path / "commands.cmd"
    count = write_commands(plan, commands, tmp_path / "results", tmp_path / "benchpress",
                           tmp_path / "python", tmp_path / "project", start=1, limit=2)
    assert count == 2
    lines = commands.read_text().splitlines()
    assert len(lines) == 2
    assert all("--limit 1" in line and "--start" in line for line in lines)
    assert "--attempts 2" in lines[0]
    assert "--attempts 20" in lines[1]
