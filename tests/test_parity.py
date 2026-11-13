import numpy as np

from notreks.parity import compare
from notreks.solvers import SolverConfig, SolverRegistry, SolverResult


def test_parity_reports_equal_and_unequal_adjacencies():
    def adapter(observations, pairs, seed, config):
        del observations, pairs, seed, config
        return SolverResult("toy", np.zeros((3, 3), dtype=np.uint8), {"version": 1})

    reference = SolverRegistry()
    candidate = SolverRegistry()
    reference.register("toy", adapter)
    candidate.register("toy", adapter)
    report = compare(reference, candidate, "toy", np.zeros((4, 3)), [], 1, SolverConfig())
    assert report.passed
    assert report.reference_diagnostic_keys == ("version",)
    assert report.first_differing_edge is None
    assert report.diagnostic_key_difference == ()
    assert report.diagnostic_checks["bic"]["status"] == "unmapped"
