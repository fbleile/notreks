import numpy as np

from notreks.constraint_diagnostics import compare_constraints, run_diagnostic


def test_constraint_diagnostic_is_reproducible():
    first = run_diagnostic(4, 2, 17)
    second = run_diagnostic(4, 2, 17)
    assert first == second
    assert first["pstrek"]["relative_gradient_error"] < 1e-5
    assert first["pstrek"]["gradient_check_passed"] is True
    assert np.isfinite(first["tcc"]["relative_gradient_error"])
    assert first["tcc"]["relative_gradient_error"] < 1e-5
    assert first["tcc"]["gradient_check_passed"] is True


def test_constraint_diagnostic_accepts_empty_pair_set():
    matrix = np.zeros((3, 3))
    result = compare_constraints(matrix, [])
    assert result["pstrek"]["value"] == 0.0
    assert result["tcc"]["value"] == 0.0
