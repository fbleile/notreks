import json
from pathlib import Path

from notreks.manifest import build_manifest, write_manifest


def test_manifest_is_deterministic_and_complete(tmp_path: Path):
    first = build_manifest()
    second = build_manifest()
    assert first == second
    assert "prior-structure-chrom" in first["experiments"]
    assert "traceback" in first["artifact_contract"]
    path = tmp_path / "protocol-manifest.json"
    write_manifest(path)
    assert json.loads(path.read_text()) == first
