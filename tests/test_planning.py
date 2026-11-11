from notreks.planning import PlanSelection, expand_protocol
from notreks.protocol import ProtocolSpec


def test_planner_is_slicable_and_keeps_shared_seeds():
    spec = ProtocolSpec("test", (6,), (32, 64), ("er",), (2,), ("flop", "flop_notreks"),
                        knowledge_fractions=(0.0, 0.25, 1.0), partial_rounds=2,
                        graph_replicates=3)
    runs = expand_protocol(spec, selection=PlanSelection(graph_start=1, graph_limit=1))
    assert len(runs) == 2 * 4 * 2
    assert len({run.graph_id for run in runs}) == 1
    assert len({run.graph_seed for run in runs}) == 1
    assert len({run.data_seed for run in runs}) == 2
    assert len({run.key() for run in runs}) == len(runs)
