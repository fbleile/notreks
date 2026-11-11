import json
from pathlib import Path

from notreks.planning import expand_protocol
from notreks.protocol import ProtocolSpec
from notreks.runner import prepare_run


def test_prepare_run_reuses_shared_inputs(tmp_path: Path):
    spec = ProtocolSpec("test", (6,), (32,), ("er",), (2,), ("flop", "flop_notreks"),
                        knowledge_fractions=(0.25,), partial_rounds=2, graph_replicates=1)
    runs = expand_protocol(spec)
    first = prepare_run(runs[0], tmp_path)
    second = prepare_run(runs[1], tmp_path)
    assert first.graph_path == second.graph_path
    assert first.data_path == second.data_path
    assert first.knowledge_path == second.knowledge_path
    assert len(list((tmp_path / "runs").glob("*/status.json"))) == 2
    assert json.loads(first.knowledge_path.read_text())["selected_pairs"] >= 1
