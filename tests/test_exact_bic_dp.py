import numpy as np

from notreks.exact_bic_dp import audit_optimal_mecs, run_exact_dp_case, solve_subset_dp


def test_subset_dp_finds_a_valid_dag():
    rng = np.random.default_rng(4)
    solution = solve_subset_dp(np.zeros((6, 64)))
    parents = solution["parents"]
    assert len(parents) == 6
    assert all(not (parents[child] & (1 << child)) for child in range(6))


def test_exact_dp_case_writes_provenance(tmp_path):
    result = run_exact_dp_case(tmp_path / "case", dimension=6, sample_size=40)
    assert result["tier"] == "d10_single_optimum"
    assert result["status"] == "globally_optimal"
    assert (tmp_path / "case" / "run.json").is_file()


def test_exact_mec_audit_is_complete_on_small_tier():
    result = audit_optimal_mecs(np.zeros((4, 16)), [])
    assert result["complete"] is True
    assert result["optimal_mec_count"] == 185
    assert result["optimal_dag_count"] == 543
