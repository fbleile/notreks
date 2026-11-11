import numpy as np
import pytest

from notreks.graphs import GraphGenerationError, er_dag, generate


def test_er_backend_is_reproducible_and_dispatches():
    first = er_dag(10, 4, seed=8)
    assert np.array_equal(first, er_dag(10, 4, seed=8))
    assert np.array_equal(first, generate("er", 10, 4, seed=8))
    assert np.all(np.diag(first) == 0)


def test_unknown_family_is_explicit():
    with pytest.raises(GraphGenerationError, match="unknown graph family"):
        generate("random", 10, 4, seed=8)
