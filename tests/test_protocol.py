from notreks.protocol import ProtocolError, ProtocolSpec, RunSpec


def test_protocol_validates_and_run_keys_are_stable():
    spec = ProtocolSpec(
        name="test",
        dimensions=(6,),
        sample_sizes=(32,),
        graph_families=("er",),
        densities=(2,),
        methods=("flop",),
        method_attempts={"flop": 20},
    )
    spec.validate()
    run = RunSpec("test", "g", "g_n32", "flop", 6, 32, "er", 2, 1, 2, 3, .25, 0)
    assert run.key() == run.key()
    assert run.to_dict()["run_key"] == run.key()


def test_protocol_rejects_invalid_fraction():
    spec = ProtocolSpec("bad", (6,), (32,), ("er",), (2,), ("flop",), (-.1,))
    try:
        spec.validate()
    except ProtocolError as error:
        assert "fractions" in str(error)
    else:
        raise AssertionError("invalid fraction was accepted")


def test_protocol_accepts_absolute_and_target_k_knowledge_controls():
    spec = ProtocolSpec(
        "custom", (8,), (100,), ("er",), (4,), ("flop_notreks",),
        knowledge_fractions=(0.25,), knowledge_pair_counts=(12,),
        knowledge_strategies=("target-k",), target_k_values=(2, 3),
        infeasible_policy="skip")
    spec.validate()

