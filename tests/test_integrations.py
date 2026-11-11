from pathlib import Path

import pytest

from notreks.integrations import register_benchpress
from notreks.solvers import SolverError, SolverRegistry


def test_benchpress_adapter_requires_an_explicit_checkout(tmp_path: Path):
    with pytest.raises(SolverError, match="not a Benchpress checkout"):
        register_benchpress(SolverRegistry(), tmp_path)
