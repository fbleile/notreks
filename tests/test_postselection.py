import numpy as np

from notreks.postselection import direct_mask_edges, order_parent_postselection


def test_mask_and_order_postselection_are_feasible():
    assert direct_mask_edges([(0, 2)]) == [(0, 2), (2, 0)]
    rng = np.random.default_rng(5)
    observations = rng.normal(size=(64, 4))
    candidate = np.array([[0, 1, 1, 0], [0, 0, 1, 0], [0, 0, 0, 1], [0, 0, 0, 0]], dtype=np.uint8)
    result, diagnostics = order_parent_postselection(observations, candidate, [(0, 3)])
    assert diagnostics["postselection_final_violations"] == 0
    assert result.shape == candidate.shape
