import csv
from pathlib import Path

import pytest

from notreks.figures import plot_mean_sd


def test_mean_sd_figure_has_no_raw_point_artifact(tmp_path: Path):
    pytest.importorskip("matplotlib")
    rows = [{"K": str(k), "SHD": str(value), "method": "flop"}
            for k, value in ((2, 10), (2, 12), (3, 8), (3, 9))]
    output = tmp_path / "figure.png"
    plot_mean_sd(rows, output, x="K", y="SHD", data_label="ER4; n=500")
    assert output.stat().st_size > 0
