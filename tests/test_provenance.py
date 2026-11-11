from pathlib import Path

from notreks.provenance import collect, write


def test_provenance_is_json_serializable(tmp_path: Path):
    value = collect(tmp_path)
    assert value["python_executable"]
    output = tmp_path / "provenance.json"
    write(output, tmp_path)
    assert output.exists()
