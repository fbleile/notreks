from pathlib import Path

import pytest

from notreks.solver_audit import audit


def test_solver_audit_rejects_non_checkout(tmp_path: Path):
    with pytest.raises(ValueError, match="not a Benchpress checkout"):
        audit(tmp_path)
