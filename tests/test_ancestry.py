import pytest

from notreks.ancestry import describe, direct_ancestry_edges, normalize_ancestry_depth


def test_full_ancestry_is_the_default():
    assert normalize_ancestry_depth(None) is None
    assert describe(None)["ancestry_depth_interpretation"] == "all ancestral paths"


def test_depth_one_is_a_symmetric_in_search_edge_constraint():
    assert direct_ancestry_edges([(2, 0), (0, 2)]) == ((0, 2), (2, 0))
    assert describe(1)["ancestry_depth_interpretation"] == "direct endpoint edges"


def test_depth_zero_is_invalid():
    with pytest.raises(ValueError, match="at least one"):
        normalize_ancestry_depth(0)
