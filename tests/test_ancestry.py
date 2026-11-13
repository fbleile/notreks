import pytest
import numpy as np

from notreks.ancestry import (bounded_ancestry_feasible,
                              bounded_ancestry_violations, describe,
                              direct_ancestry_edges, effective_ancestry_depth,
                              normalize_ancestry_depth)


def test_full_ancestry_is_the_default():
    assert normalize_ancestry_depth(None) is None
    assert describe(None)["ancestry_depth_interpretation"] == "all ancestral paths"


def test_depth_one_is_a_symmetric_in_search_edge_constraint():
    assert direct_ancestry_edges([(2, 0), (0, 2)]) == ((0, 2), (2, 0))
    assert describe(1)["ancestry_depth_interpretation"] == "direct endpoint edges"


def test_depth_zero_means_no_ancestry_restriction():
    assert normalize_ancestry_depth(0) == 0
    assert describe(0)["ancestry_constraint"] == "none"


def test_bounded_table_distinguishes_depth_one_and_two():
    graph = np.zeros((3, 3), dtype=np.uint8)
    graph[0, 1] = graph[1, 2] = 1
    assert bounded_ancestry_feasible(graph, [(0, 2)], 1)
    assert bounded_ancestry_violations(graph, [(0, 2)], 2) == ((0, 2, 2),)


def test_depth_beyond_dag_path_bound_selects_full_ancestry():
    assert effective_ancestry_depth(5, 6) == 5
    assert effective_ancestry_depth(6, 6) is None
    assert effective_ancestry_depth(None, 6) is None
