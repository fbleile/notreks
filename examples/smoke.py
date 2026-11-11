"""Human-readable smoke test for the standalone NOTREKS core."""

from notreks.protocol import ProtocolSpec, RunSpec


def main() -> None:
    spec = ProtocolSpec(
        name="example",
        dimensions=(6,),
        sample_sizes=(32,),
        graph_families=("er",),
        densities=(2,),
        methods=("flop", "dagma"),
        method_attempts={"flop": 20, "dagma": 2},
    )
    spec.validate()
    run = RunSpec(
        protocol=spec.name,
        graph_id="example_g00",
        data_id="example_g00_n32",
        method="flop",
        dimension=6,
        sample_size=32,
        graph_family="er",
        density=2,
        graph_seed=1001,
        data_seed=1002,
        knowledge_seed=1003,
        knowledge_fraction=0.25,
        knowledge_round=0,
    )
    print(f"protocol={spec.name} method={run.method} run_key={run.key()}")


if __name__ == "__main__":
    main()

