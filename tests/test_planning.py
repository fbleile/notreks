from notreks.planning import PlanSelection, expand_protocol
from notreks.planning import external_plan
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


def test_external_plan_uses_manifest_shape_and_target(tmp_path):
    import json
    import numpy as np
    np.save(tmp_path / "x.npy", np.zeros((12, 4)))
    np.save(tmp_path / "truth.npy", np.zeros((4, 4)))
    (tmp_path / "pairs.json").write_text("[[0, 1]]\n")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"dataset_id": "demo", "observations": "x.npy",
                                    "truth_adjacency": "truth.npy",
                                    "knowledge_pairs": "pairs.json",
                                    "nodes": ["a", "b", "c", "d"],
                                    "evaluation_target": "causalman_latent_projection"}))
    payload = external_plan(manifest, name="demo-external", methods=("flop",),
                            fractions=(0.0, 0.25, 1.0), attempts={"flop": 20})
    assert payload["run_count"] == 7
    assert all(run["external_manifest"] == str(manifest.resolve()) for run in payload["runs"])
    assert all(run["dimension"] == 4 for run in payload["runs"])
    assert payload["attempts_by_method"] == {"flop": 20}


def test_plan_expands_absolute_target_k_controls():
    spec = ProtocolSpec(
        "custom", (8,), (100,), ("er",), (4,), ("flop_notreks",),
        knowledge_fractions=(0.25,), knowledge_pair_counts=(12,),
        knowledge_strategies=("target-k",), target_k_values=(2, 3),
        graph_replicates=1)
    runs = expand_protocol(spec)
    assert {run.knowledge_strategy for run in runs} == {"target-k-2", "target-k-3"}
    assert {run.knowledge_pair_count for run in runs} == {12}
