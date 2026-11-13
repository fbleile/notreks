import json

from notreks.release import audit


def test_release_audit_reports_required_metadata(tmp_path):
    for relative in (
        "README.md", "LICENSE", "CITATION.cff", "CHANGELOG.md",
        "docs/experimental_protocol.md", "docs/solver_porting.md",
        "docs/release.md", "docs/release_checklist.md",
        "data/external/THIRD_PARTY_NOTICES.md", "pyproject.toml",
        "environment.yml", "Makefile", "scripts/reproduce_paper.sh",
        ".github/workflows/test.yml", "cluster/lrz_session_setup.sh",
        "cluster/lrz_jobfarm.sh", "cluster/lrz_jobfarm_smoke.sh",
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ok")
    report = audit(tmp_path)
    assert report["ok"] is True
    assert report["missing_required_files"] == []
    assert json.dumps(report)
