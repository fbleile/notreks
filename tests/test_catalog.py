from notreks.catalog import CATALOG, get


def test_final_catalog_contains_distinct_protocol_arms():
    assert {CATALOG[name].arm for name in ("main", "main-misspec-linear-nongaussian",
                                           "main-misspec-nonlinear-gaussian")} == {
        "well_specified", "linear_nongaussian", "nonlinear_gaussian"}
    chrom = get("prior-structure-chrom")
    assert chrom.one_run_per_prior_set
    assert chrom.attempts_for("flop_notreks") == 1
    assert chrom.analysis_cutoff is not None
    assert chrom.methods_for_dimension(50) == ("dagma", "dagma_notreks")
    assert chrom.methods_for_dimension(100) == ("flop", "flop_notreks")


def test_catalog_rejects_unknown_experiment():
    try:
        get("not-an-experiment")
    except KeyError as error:
        assert "unknown experiment" in str(error)
    else:
        raise AssertionError("unknown experiment was accepted")
