from notreks.preflight import check


def test_preflight_reports_missing_benchpress_checkout(tmp_path):
    report = check(backend="benchpress", methods=("flop",), benchpress_root=tmp_path)
    assert not report["ok"]
    assert any("Benchpress" in error for error in report["errors"])


def test_preflight_direct_reports_requested_methods():
    report = check(backend="direct", methods=("flop_notreks",))
    assert report["backend"] == "direct"
    assert report["methods"] == ["flop_notreks"]
