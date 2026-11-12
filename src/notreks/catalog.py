"""Final experiment catalog used to build plans and cluster command files.

This is the scientific registry, not a second execution engine.  Each entry
describes what is to be run; the planner and runners remain shared.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ExperimentDefinition:
    name: str
    arm: str
    data_model: str
    cells: tuple[tuple[int, str, int], ...]
    sample_sizes: tuple[int, ...]
    knowledge_fractions: tuple[float, ...]
    partial_rounds: int
    methods: tuple[str, ...]
    graph_replicates: int
    attempts_by_method: tuple[tuple[str, int], ...]
    knowledge_strategies: tuple[str, ...] = ("random",)
    notes: str = ""
    one_run_per_prior_set: bool = False
    analysis_cutoff: str | None = None
    excluded_methods_by_dimension: tuple[tuple[int, tuple[str, ...]], ...] = ()
    target_k_values: tuple[int, ...] = ()

    def cells_for_dimension(self, dimension: int) -> tuple[tuple[int, str, int], ...]:
        return tuple(cell for cell in self.cells if cell[0] == dimension)

    def methods_for_dimension(self, dimension: int) -> tuple[str, ...]:
        excluded = dict(self.excluded_methods_by_dimension).get(dimension, ())
        return tuple(method for method in self.methods if method not in excluded)

    def attempts_for(self, method: str) -> int:
        family = dict(self.attempts_by_method)
        try:
            return family[method]
        except KeyError as error:
            raise KeyError(f"no attempt budget registered for {method!r}") from error

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SYNTHETIC_CELLS = tuple(
    (dimension, family, density)
    for dimension in (20, 50, 100)
    for family in ("er", "ws")
    for density in (2, 4, 8)
    if not (dimension == 20 and density == 8)
)
SYNTHETIC_METHODS = (
    "flop", "flop_notreks", "flop-nt-edge-mask", "flop-nt-post",
    "dagma", "dagma_notreks", "dagma-nt-edge-mask", "dagma-nt-post",
    "var_sortnregress", "r2_sortnregress",
)


def _synthetic(name: str, arm: str, model: str) -> ExperimentDefinition:
    return ExperimentDefinition(
        name=name, arm=arm, data_model=model, cells=SYNTHETIC_CELLS,
        sample_sizes=(100, 500, 2000), knowledge_fractions=(0.0, 0.25, 1.0),
        partial_rounds=5, methods=SYNTHETIC_METHODS, graph_replicates=20,
        attempts_by_method=(("flop", 20), ("flop_notreks", 20),
                            ("flop-nt-edge-mask", 20), ("flop-nt-post", 20),
                            ("dagma", 2), ("dagma_notreks", 2),
                            ("dagma-nt-edge-mask", 2), ("dagma-nt-post", 2),
                            ("var_sortnregress", 1), ("r2_sortnregress", 1)),
        notes="DAGMA is omitted from d=100 production cells for runtime reasons.",
        excluded_methods_by_dimension=((100, ("dagma", "dagma_notreks",
                                              "dagma-nt-edge-mask", "dagma-nt-post")),),
    )


CATALOG: dict[str, ExperimentDefinition] = {
    "main": _synthetic("main", "well_specified", "linear_gaussian"),
    "main-misspec-linear-nongaussian": _synthetic(
        "main-misspec-linear-nongaussian", "linear_nongaussian", "linear_nongaussian"),
    "main-misspec-nonlinear-gaussian": _synthetic(
        "main-misspec-nonlinear-gaussian", "nonlinear_gaussian", "nonlinear_gaussian"),
    "prior-structure-chrom": ExperimentDefinition(
        "prior-structure-chrom", "chromatic", "linear_gaussian",
        ((50, "er", 4), (50, "ws", 4), (100, "er", 4), (100, "ws", 4)),
        (500,), (0.0, 0.25), 50,
        ("flop", "flop_notreks", "dagma", "dagma_notreks"), 100,
        (("flop", 1), ("flop_notreks", 1), ("dagma", 1), ("dagma_notreks", 1)),
        ("target-k",), "Fixed pair budget; one solver run per generated prior set.",
        one_run_per_prior_set=True, analysis_cutoff="target K represented for >=90% of graphs",
        excluded_methods_by_dimension=((50, ("flop", "flop_notreks")),
                                       (100, ("dagma", "dagma_notreks"))),
        target_k_values=tuple(range(2, 21))),
    "pstrek-vs-tcc": ExperimentDefinition(
        "pstrek-vs-tcc", "constraint_comparison", "linear_gaussian",
        tuple((dimension, "er", density) for dimension in (8, 10, 12) for density in (2, 4)),
        (100,), (0.0, 0.25, 1.0), 5,
        ("dagma", "dagma_notreks", "dagma_tcc", "var_sortnregress", "r2_sortnregress"), 20,
        (("dagma", 2), ("dagma_notreks", 2), ("dagma_tcc", 2),
         ("var_sortnregress", 1), ("r2_sortnregress", 1)),
        notes="Compares PSTrek and TCC under the same supplied pairs."),
    "causalman-small": ExperimentDefinition(
        "causalman-small", "causalman", "causalman_observational", (),
        (500, 2000, 5000), (0.25, 1.0), 5,
        ("flop", "flop_notreks", "dagma", "dagma_notreks"), 10,
        (("flop", 20), ("flop_notreks", 20), ("dagma", 2), ("dagma_notreks", 2)),
        notes="Evaluated with latent-projection diagnostics."),
    "causalman-medium": ExperimentDefinition(
        "causalman-medium", "causalman", "causalman_observational", (),
        (500, 2000, 5000), (0.25, 1.0), 5,
        ("flop", "flop_notreks", "dagma", "dagma_notreks"), 10,
        (("flop", 20), ("flop_notreks", 20), ("dagma", 2), ("dagma_notreks", 2)),
        notes="Evaluated with latent-projection diagnostics."),
    "causalassembly": ExperimentDefinition(
        "causalassembly", "causalassembly", "causalassembly_observational", (),
        (500,), (0.25, 1.0), 5,
        ("flop", "flop_notreks", "dagma", "dagma_notreks"), 10,
        (("flop", 20), ("flop_notreks", 20), ("dagma", 2), ("dagma_notreks", 2)),
        notes="Registered CausalAssembly datasets and estimated/oracle priors."),
    "exact-feasibility-pilot": ExperimentDefinition(
        "exact-feasibility-pilot", "motivational_exact", "none", (), (), (), 0,
        (), 0, (), notes="Small bounded combinatorial pilot; not a recovery benchmark."),
}


def get(name: str) -> ExperimentDefinition:
    try:
        return CATALOG[name]
    except KeyError as error:
        raise KeyError(f"unknown experiment {name!r}; choose from {sorted(CATALOG)}") from error


def main() -> None:
    """List registered experiments and their arms."""
    for definition in CATALOG.values():
        print(f"{definition.name}: {definition.arm}")


if __name__ == "__main__":
    main()
