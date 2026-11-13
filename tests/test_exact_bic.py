import numpy as np

from notreks.exact_bic import all_labeled_dags, exact_bic


def test_exact_dag_enumeration_counts_dimension_four():
    assert len(all_labeled_dags(4)) == 543


def test_exact_bic_returns_complete_optimal_mec_set():
    rng = np.random.default_rng(4)
    data = rng.normal(size=(80, 4))
    truth = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1], [0, 0, 0, 0]], dtype=np.uint8)
    result = exact_bic(data, [], truth)
    assert result["candidate_dag_count"] == 543
    assert result["feasible_dag_count"] == 543
    assert result["optimal_mec_count"] >= 1
    assert isinstance(result["optimal_cpdags"], list)
