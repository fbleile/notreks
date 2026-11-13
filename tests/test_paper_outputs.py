from notreks.paper_outputs import PAPER_OUTPUTS, as_json


def test_paper_output_registry_is_unique_and_serializable():
    names = [item.name for item in PAPER_OUTPUTS]
    assert len(names) == len(set(names))
    assert all(item.kind in {"figure", "table", "analysis"} for item in PAPER_OUTPUTS)
    assert len(as_json()) == len(PAPER_OUTPUTS)
from notreks.paper_outputs import validate_registry


def test_paper_output_registry_is_self_consistent():
    assert validate_registry() == []
