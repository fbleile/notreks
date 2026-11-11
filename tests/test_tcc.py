import numpy as np

from notreks.tcc import value_and_grad


def test_tcc_empty_pairs_are_zero():
    value, gradient = value_and_grad(np.ones((3, 3)), [])
    assert value == 0.0
    np.testing.assert_array_equal(gradient, np.zeros((3, 3)))


def test_tcc_is_deterministic():
    W = np.array([[0.0, 0.1, 0.02], [0.04, 0.0, 0.03], [0.01, 0.02, 0.0]])
    first = value_and_grad(W, [(0, 1), (1, 2)])
    second = value_and_grad(W, [(0, 1), (1, 2)])
    assert first[0] == second[0]
    np.testing.assert_array_equal(first[1], second[1])
