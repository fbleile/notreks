import pytest

from notreks.analysis import clustered_fixed_effects, graph_k_cells, holm_adjust


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
    cells = [{"graph": graph, "K": target, "mean": 10 - target}
             for graph in ("a", "b", "c", "d") for target in (2, 3, 4)]
    result = clustered_fixed_effects(cells)
    assert result.slope == pytest.approx(-1.0)
    assert result.graphs == 4
    assert result.cells == 12
    assert result.p_one_sided < 0.05


def test_holm_adjust_preserves_order_and_monotonicity():
    adjusted = holm_adjust([0.01, 0.2, 0.03])
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[2] == pytest.approx(0.06)
    assert adjusted[1] == pytest.approx(0.2)
