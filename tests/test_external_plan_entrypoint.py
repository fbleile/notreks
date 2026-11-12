def test_external_plan_entrypoint_exposes_main():
    from notreks.external_plan import main
    assert callable(main)
