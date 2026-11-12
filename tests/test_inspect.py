import json

from notreks.inspect import inspect_output, main


def test_inspect_reports_run_and_stage_states(tmp_path, capsys):
    run = tmp_path / "runs" / "run-a"
    run.mkdir(parents=True)
    (run / "run.json").write_text(json.dumps({"run_key": "a"}))
    (run / "status.json").write_text(json.dumps({"state": "succeeded"}))
    stage = run / "solve"
    stage.mkdir()
    (stage / "status.json").write_text(json.dumps({"state": "failed"}))
    (stage / "error.txt").write_text("traceback")
    report = inspect_output(tmp_path)
    assert report["runs"] == 1
    assert report["run_states"] == {"succeeded": 1}
    assert report["stage_states"]["solve"] == {"failed": 1}
    assert len(report["errors"]) == 1
    assert main([str(tmp_path), "--json"]) == 0
    assert '"runs": 1' in capsys.readouterr().out
