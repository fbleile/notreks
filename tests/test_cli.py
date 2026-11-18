import json
from pathlib import Path

from notreks.cli import main


def test_cli_plans_and_prepares_smoke_protocol(tmp_path: Path):
    protocol = Path("examples/smoke_protocol.json")
    plan = tmp_path / "plan.json"
    output = tmp_path / "results"
    assert main(["plan", str(protocol), str(plan)]) == 0
    assert json.loads(plan.read_text())["run_count"] == 8
    assert main(["prepare", str(plan), str(output)]) == 0
    assert len(list((output / "runs").glob("*/status.json"))) == 8


def test_cli_catalog_lists_registered_experiments(capsys):
    assert main(["catalog"]) == 0
    output = capsys.readouterr().out
    assert "main:" in output
    assert "prior-structure-chrom:" in output


def test_protocol_smoke_covers_all_protocol_families(tmp_path: Path):
    from notreks.protocol_smoke import build_protocol_smoke

    manifest = build_protocol_smoke(
        tmp_path / "suite", project_root=Path.cwd(), python=Path("python"))
    assert manifest["command_count"] == 172
    assert {entry["kind"] for entry in manifest["entries"]} == {
        "synthetic", "chromatic", "constraint-comparison", "external"
    }
    assert len(manifest["exact_entries"]) == 3
