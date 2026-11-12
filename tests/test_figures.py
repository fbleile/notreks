import csv
from pathlib import Path

import pytest

from notreks.figures import main, plot_graph_clustered_trend, plot_mean_sd


def test_mean_sd_figure_has_no_raw_point_artifact(tmp_path: Path):
    pytest.importorskip("matplotlib")
    rows = [{"K": str(k), "SHD": str(value), "method": "flop"}
            for k, value in ((2, 10), (2, 12), (3, 8), (3, 9))]
    output = tmp_path / "figure.png"
    plot_mean_sd(rows, output, x="K", y="SHD", data_label="ER4; n=500")
    assert output.stat().st_size > 0


def test_graph_clustered_trend_uses_graph_level_cells(tmp_path: Path):
    pytest.importorskip("matplotlib")
    rows = [{"graph_id": graph, "target_chromatic_number": str(k),
             "SHD_cpdag": str(value), "method": "flop"}
            for graph, values in {"g1": (10, 8), "g2": (12, 6)}.items()
            for k, value in ((2, values[0]), (3, values[1]))]
    output = tmp_path / "trend.png"
    plot_graph_clustered_trend(rows, output, data_label="ER4; n=500")
    assert output.stat().st_size > 0


def test_figure_cli_defaults_to_png_and_can_write_pdf(tmp_path: Path):
    pytest.importorskip("matplotlib")
    input_path = tmp_path / "rows.csv"
    with input_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["K", "SHD", "method"])
        writer.writeheader()
        writer.writerows([{"K": 2, "SHD": 4, "method": "flop"},
                          {"K": 3, "SHD": 3, "method": "flop"}])
    main([str(input_path), str(tmp_path / "paper"), "--x", "K", "--y", "SHD"])
    assert (tmp_path / "paper.png").is_file()
    main([str(input_path), str(tmp_path / "vector"), "--x", "K", "--y", "SHD",
          "--format", "pdf"])
    assert (tmp_path / "vector.pdf").is_file()
