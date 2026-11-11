import numpy as np
import pytest

from notreks.cpdag import CPDAGError, cpdag_shd, dag_to_cpdag


def test_collider_is_oriented_and_chain_is_markov_equivalent():
    collider = np.array([[0, 0, 1], [0, 0, 1], [0, 0, 0]], dtype=np.uint8)
    cpdag = dag_to_cpdag(collider)
    assert cpdag[0, 2] == 1 and cpdag[1, 2] == 1
    assert cpdag[2, 0] == 0 and cpdag[2, 1] == 0

    chain = np.array([[0, 1, 0], [0, 0, 1], [0, 0, 0]], dtype=np.uint8)
    reversed_chain = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.uint8)
    assert np.array_equal(dag_to_cpdag(chain), dag_to_cpdag(reversed_chain))


def test_cpdag_shd_and_cycle_validation():
    dag = np.array([[0, 1], [0, 0]], dtype=np.uint8)
    estimate = np.array([[0, 0], [1, 0]], dtype=np.uint8)
    assert cpdag_shd(dag, estimate) == 1
    with pytest.raises(CPDAGError):
        dag_to_cpdag(np.array([[0, 1], [1, 0]], dtype=np.uint8))
