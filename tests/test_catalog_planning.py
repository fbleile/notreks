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


def test_chromatic_catalog_expands_target_k_strategies():
    definition, runs = expand_catalog("prior-structure-chrom", master_seed=3,
                                      selection=CatalogSelection(graph_limit=1))
    assert definition.target_k_values == tuple(range(2, 21))
    strategies = {run.knowledge_strategy for run in runs if run.knowledge_fraction == 0.25}
    assert strategies == {f"target-k-{k}" for k in range(2, 21)}
