import pytest

from notreks.integrations import register_direct
from notreks.solvers import SolverRegistry


def test_direct_registration_selects_dagma_only():
    pytest.importorskip("dagma")
    registry = SolverRegistry()
    provenance = register_direct(registry, {"dagma", "dagma_notreks"})
    assert provenance["backend"] == "direct"
    assert "dagma" in registry.names()
    assert "dagma_notreks" in registry.names()
