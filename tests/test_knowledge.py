from itertools import combinations

import numpy as np

from notreks.knowledge import (bounded_target_k_pair_pool, canonical_pair_set_hash,
                               random_pairs_count, target_k_partite_pairs)


def test_target_k_sets_are_fixed_size_and_hashable():
    pairs = list(combinations(range(8), 2))
    first = target_k_partite_pairs(pairs, 8, .5, seed=3, target=3, budget=12)
    second = target_k_partite_pairs(pairs, 8, .5, seed=3, target=3, budget=12)
    assert first == second
    assert len(first) == 12
    assert canonical_pair_set_hash(first) == canonical_pair_set_hash(reversed(first))


def test_target_pool_is_bounded_and_reports_availability():
    pairs = list(combinations(range(6), 2))
    pool, audit = bounded_target_k_pair_pool(pairs, 6, .5, 2, seed=4, requested=3)
    assert len(pool) == audit["available"]
    assert audit["attempts"] <= 1000


def test_absolute_pair_selection_is_exact_and_bounded():
    pairs = [(0, 1), (0, 2), (1, 2), (2, 3)]
    assert len(random_pairs_count(pairs, 3, seed=4)) == 3
    import pytest
    with pytest.raises(ValueError, match="only 4"):
        random_pairs_count(pairs, 5, seed=4)
