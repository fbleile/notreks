import json

import pytest

from notreks.analysis import (adjacent_changes, clustered_fixed_effects, graph_k_cells,
                               holm_adjust, k_summaries, paired_metric_differences,
                               paired_wilcoxon, paired_wilcoxon_family)


def test_trend_cli_can_retain_json_report(tmp_path, capsys):
    input_path = tmp_path / "rows.csv"
    input_path.write_text("graph_id,target_chromatic_number,SHD_cpdag\n"
                          "g1,2,4\ng1,3,3\ng2,2,5\ng2,3,4\n")
    output_path = tmp_path / "report.json"
    from notreks.analysis import main
    main([str(input_path), "--output", str(output_path)])
    assert json.loads(output_path.read_text())["trend"]["graphs"] == 2
    assert '"trend"' in capsys.readouterr().out


def test_graph_k_cells_gives_each_graph_k_one_observation():
    rows = [
        {"graph_id": "a", "K": "2", "SHD": "4"},
        {"graph_id": "a", "K": "2", "SHD": "6"},
        {"graph_id": "a", "K": "3", "SHD": "3"},
        {"graph_id": "b", "K": "2", "SHD": "5"},
        {"graph_id": "b", "K": "3", "SHD": "2"},
    ]
    cells = graph_k_cells(rows, graph="graph_id", k="K", metric="SHD")
    assert len(cells) == 4
    assert next(row["mean"] for row in cells if row["graph"] == "a" and row["K"] == 2) == 5.0


def test_clustered_fixed_effects_detects_negative_trend():
    cells = ([{"graph": graph, "K": target, "mean": 10 - target}
              for graph in ("a", "b", "c") for target in (2, 3, 4)] +
             [{"graph": "singleton", "K": 2, "mean": 8}])
    result = clustered_fixed_effects(cells)
    assert result.slope == pytest.approx(-1.0)
    assert result.graphs == 3
    assert result.cells == 9
    assert result.p_two_sided < 0.05


def test_holm_adjust_preserves_order_and_monotonicity():
    adjusted = holm_adjust([0.01, 0.2, 0.03])
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[2] == pytest.approx(0.06)
    assert adjusted[1] == pytest.approx(0.2)


def test_k_summaries_and_adjacent_changes_use_graph_level_cells():
    cells = [{"graph": graph, "K": target, "mean": value}
             for graph, value in (("a", 8), ("b", 6)) for target in (2, 3)
             for value in [value - target + 2]]
    summaries = k_summaries(cells)
    assert summaries[0]["graphs"] == 2
    assert summaries[0]["variance"] == pytest.approx(2.0)
    changes = adjacent_changes(cells)
    assert changes[0]["graphs"] == 2
    assert changes[0]["mean_change"] == pytest.approx(-1.0)


def test_paired_wilcoxon_is_two_sided():
    result = paired_wilcoxon([-4, -3, -5, -2, -6])
    assert result.pairs == 5
    assert result.p_two_sided < 0.1
    assert paired_wilcoxon([0, 0, 0]).p_two_sided == 1.0


def test_paired_metric_differences_average_duplicate_rows():
    rows = [
        {"graph_id": "g1", "method": "vanilla", "SHD": 5},
        {"graph_id": "g1", "method": "notreks", "SHD": 3},
        {"graph_id": "g1", "method": "notreks", "SHD": 1},
        {"graph_id": "g2", "method": "vanilla", "SHD": 4},
        {"graph_id": "g2", "method": "notreks", "SHD": 4},
    ]
    differences = paired_metric_differences(rows, treatment="notreks", baseline="vanilla",
                                             metric="SHD")
    assert differences == pytest.approx([-3.0, 0.0])


def test_paired_wilcoxon_family_adds_holm_values():
    rows = [{"graph_id": graph, "method": method, "SHD": value}
            for graph, values in {"g1": {"vanilla": 5, "notreks": 1, "other": 5},
                                  "g2": {"vanilla": 2, "notreks": 2, "other": 4}}.items()
            for method, value in values.items()]
    result = paired_wilcoxon_family(rows, comparisons=[("notreks", "vanilla"),
                                                       ("other", "vanilla")], metric="SHD")
    assert len(result) == 2
    assert all("p_holm" in item and item["p_holm"] >= item["p_two_sided"] for item in result)
