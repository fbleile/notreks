from notreks.preflight import check


def test_preflight_direct_reports_requested_methods():
    report = check(methods=("flop_notreks",))
    assert report["backend"] == "direct"
    assert report["methods"] == ["flop_notreks"]
