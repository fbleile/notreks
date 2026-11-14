def test_focused_entrypoint_modules_expose_main():
    from notreks.catalog_planning import main as catalog_plan
    from notreks.figures import main as figure
    from notreks.jobfarm import main as jobfarm
    from notreks.manifest import main as manifest

    assert all(callable(function) for function in
               (catalog_plan, figure, jobfarm, manifest))
