import numpy as np

from notreks.continuation import ContinuationResult
from notreks.dagma_backend import finalize_profile_pstrek


def test_finalize_records_candidate_and_final_graph():
    candidate = np.array([[0, 1, 0], [0, 0, 1], [0, 0, 0]], dtype=np.uint8)
    result = ContinuationResult(
        weights=candidate.astype(float), adjacency=candidate,
        stages=tuple(), converged=False,
    )
    data = np.random.default_rng(6).normal(size=(20, 3))
    final, diagnostics = finalize_profile_pstrek(data, [(0, 2)], result)
    assert final.shape == candidate.shape
    assert diagnostics["candidate_edges"] == 2
    assert diagnostics["postselection_status"] == "applied"
    assert diagnostics["final_edges"] == int(final.sum())
