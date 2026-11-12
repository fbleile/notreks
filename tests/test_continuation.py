import numpy as np

from notreks.continuation import ContinuationConfig, fit
from notreks.dagma_math import ValueGradient


def test_continuation_preserves_zero_diagonal_and_records_stages():
    def score(W):
        target = np.array([[0.0, 0.2], [0.0, 0.0]])
        delta = W - target
        return ValueGradient(0.5 * float(np.sum(delta * delta)), delta)

    def zero_term(W, s):
        del s
        return ValueGradient(0.0, np.zeros_like(W))

    result = fit(score, zero_term, zero_term, 2,
                 config=ContinuationConfig(stages=2, warm_iter=2, max_iter=3,
                                            checkpoint=1, learning_rate=0.05,
                                            l1_weight=0.0, threshold=0.01))
    assert len(result.stages) == 2
    assert np.all(np.diag(result.weights) == 0.0)
    assert result.adjacency.shape == (2, 2)


def test_continuation_backtracks_into_declared_domain():
    def score(W):
        target = np.array([[0.0, 2.0], [0.0, 0.0]])
        delta = W - target
        return ValueGradient(0.5 * float(np.sum(delta * delta)), delta)

    def zero_term(W, s):
        del s
        return ValueGradient(0.0, np.zeros_like(W))

    def domain(W, s):
        return float(np.abs(W).sum()) < s

    result = fit(score, zero_term, zero_term, 2,
                 config=ContinuationConfig(stages=1, warm_iter=1, max_iter=1,
                                            checkpoint=1, learning_rate=1.0,
                                            l1_weight=0.0),
                 domain=domain)
    assert np.abs(result.weights).sum() < 1.0
