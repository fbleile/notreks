from pathlib import Path

from notreks.catalog_planning import CatalogSelection, expand_catalog, methods_for_condition, write_catalog_plan


def test_catalog_plan_respects_baseline_and_prior_method_sets(tmp_path: Path):
    definition, runs = expand_catalog("main", selection=CatalogSelection(graph_limit=1))
    assert definition.name == "main"
    assert runs
    assert all(run.knowledge_fraction == 0.0 for run in runs[:4])
    assert set(methods_for_condition(definition, 50, 0.0)) == {
        "flop", "dagma", "var_sortnregress", "r2_sortnregress"}
    assert "flop_notreks" in methods_for_condition(definition, 50, 0.25)
    path = tmp_path / "plan.json"
    write_catalog_plan(path, definition, runs, master_seed=20260917)
    assert path.exists()


def test_chromatic_methods_are_dimension_specific():
    definition, _ = expand_catalog("prior-structure-chrom", selection=CatalogSelection(graph_limit=1))
    assert methods_for_condition(definition, 50, 0.25) == ("dagma_notreks",)
    assert methods_for_condition(definition, 100, 0.25) == ("flop_notreks",)
