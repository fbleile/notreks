from pathlib import Path

import pytest

from notreks.experiment import RunDirectory, RunRecorder, SeedBook, iter_run_directories
from notreks.protocol import RunSpec


def make_run() -> RunSpec:
    return RunSpec("test", "g00", "g00_n32", "flop", 6, 32, "er", 2, 1, 2, 3, .25, 0)


def test_seed_book_is_stable_and_namespaced():
    book = SeedBook(123)
    assert book.derive("data", "g00") == book.derive("data", "g00")
    assert book.derive("data", "g00") != book.derive("knowledge", "g00")


def test_recorder_writes_success_and_failure_artifacts(tmp_path: Path):
    success = RunDirectory(tmp_path / "success")
    with RunRecorder(success, make_run(), command=["demo"]):
        success.stage("data").joinpath("data.json").write_text("{}")
    assert '"state": "succeeded"' in success.status.read_text()
    assert list(iter_run_directories(tmp_path)) == [success]

    failure = RunDirectory(tmp_path / "failure")
    with pytest.raises(RuntimeError, match="deliberate"):
        with RunRecorder(failure, make_run()):
            raise RuntimeError("deliberate")
    assert '"state": "failed"' in failure.status.read_text()
    assert "RuntimeError: deliberate" in (failure.root / "error.txt").read_text()
