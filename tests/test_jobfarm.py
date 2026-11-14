import json
from pathlib import Path

from notreks.jobfarm import retry_failed_commands, write_commands


def test_jobfarm_commands_are_one_per_run(tmp_path: Path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"runs": [{"run_key": "a", "method": "flop"},
                                          {"run_key": "b", "method": "dagma"},
                                          {"run_key": "c", "method": "flop"}],
                              "attempts_by_method": {"flop": 20, "dagma": 2}}))
    commands = tmp_path / "commands.cmd"
    count = write_commands(plan, commands, tmp_path / "results",
                           tmp_path / "python", tmp_path / "project", start=1, limit=2)
    assert count == 2
    lines = commands.read_text().splitlines()
    assert len(lines) == 2
    assert all("--limit 1" in line and "--start" in line for line in lines)
    assert "--attempts 2" in lines[0]
    assert "--attempts 20" in lines[1]
    assert "--dagma-max-iter 60000" in lines[0]


def test_jobfarm_commands_use_the_direct_backend(tmp_path: Path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"runs": [{"run_key": "a", "method": "dagma"}],
                                "attempts_by_method": {"dagma": 2}}))
    commands = tmp_path / "direct.cmd"
    write_commands(plan, commands, tmp_path / "results",
                   tmp_path / "python", tmp_path / "project")
    line = commands.read_text()
    assert "--backend" not in line
    assert "--dagma-warm-iter 30000" in line


def test_jobfarm_inherits_protocol_ancestry_depth(tmp_path: Path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({
        "protocol": {"ancestry_depth": 2},
        "runs": [{"run_key": "a", "method": "flop_notreks"}],
        "attempts_by_method": {"flop_notreks": 1},
    }))
    commands = tmp_path / "depth.cmd"
    write_commands(plan, commands, tmp_path / "results",
                   tmp_path / "python", tmp_path / "project")
    assert "--ancestry-depth 2" in commands.read_text()


def test_retry_keeps_only_non_successful_tasks(tmp_path: Path):
    commands = tmp_path / "commands.cmd"
    commands.write_text("env first\nenv second\nenv third\n")
    results = tmp_path / "commands.cmd_res"
    results.mkdir()
    (results / "1").write_text("** STOP SUCCESS\n")
    (results / "2").write_text("** STOP FAILED\ntraceback\n")
    retry = tmp_path / "retry.cmd"
    assert retry_failed_commands(commands, results, retry) == 2
    assert retry.read_text().splitlines() == ["env second", "env third"]
