from notreks.exact import certified_information_set, enumerate_ordered_dags


def test_exact_fixed_order_counts_all_dags_without_constraints():
    result = enumerate_ordered_dags(3, [])
    assert result["candidate_dags"] == 8
    assert result["feasible_dags"] == 8


def test_exact_fixed_order_enforces_no_trek_pair():
    result = enumerate_ordered_dags(3, [(0, 2)])
    assert result["feasible_dags"] < result["candidate_dags"]


def test_certified_information_set_has_requested_size():
    pairs = certified_information_set(6, 6, 3, seed=4)
    assert len(pairs) == 6
    assert len(set(pairs)) == 6
