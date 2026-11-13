"""Protocol and run contracts shared by local and cluster execution.

This module deliberately contains no solver or plotting code. It validates the
small piece of information that every later stage needs and can be exercised
without installing numerical or cluster dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any


class ProtocolError(ValueError):
    """Raised when a protocol would produce an ambiguous or invalid run."""


@dataclass(frozen=True)
class ProtocolSpec:
    """A compact, serializable description of one experiment family."""

    name: str
    dimensions: tuple[int, ...]
    sample_sizes: tuple[int, ...]
    graph_families: tuple[str, ...]
    densities: tuple[int, ...]
    methods: tuple[str, ...]
    knowledge_fractions: tuple[float, ...] = (0.0, 0.25, 1.0)
    knowledge_pair_counts: tuple[int, ...] = ()
    knowledge_strategies: tuple[str, ...] = ("random",)
    target_k_values: tuple[int, ...] = ()
    infeasible_policy: str = "fail"
    partial_rounds: int = 5
    graph_replicates: int = 20
    method_attempts: dict[str, int] = field(default_factory=dict)
    ancestry_depth: int | None = None

    def validate(self) -> None:
        """Check protocol invariants before expensive work is started."""
        if not self.name.strip():
            raise ProtocolError("protocol name must not be empty")
        if not self.dimensions or any(d < 2 for d in self.dimensions):
            raise ProtocolError("dimensions must contain values >= 2")
        if not self.sample_sizes or any(n < 1 for n in self.sample_sizes):
            raise ProtocolError("sample_sizes must contain positive values")
        if not self.graph_families or not self.methods:
            raise ProtocolError("graph_families and methods must not be empty")
        if not self.densities or any(k < 1 for k in self.densities):
            raise ProtocolError("densities must contain positive values")
        if not 1 <= self.partial_rounds:
            raise ProtocolError("partial_rounds must be positive")
        if not 1 <= self.graph_replicates:
            raise ProtocolError("graph_replicates must be positive")
        if any(q < 0.0 or q > 1.0 for q in self.knowledge_fractions):
            raise ProtocolError("knowledge fractions must lie in [0, 1]")
        if any(count < 0 for count in self.knowledge_pair_counts):
            raise ProtocolError("knowledge pair counts must be non-negative")
        if not self.knowledge_strategies:
            raise ProtocolError("knowledge_strategies must not be empty")
        if any(target < 2 for target in self.target_k_values):
            raise ProtocolError("target chromatic numbers must be at least two")
        if self.ancestry_depth is not None and self.ancestry_depth < 1:
            raise ProtocolError("ancestry_depth must be omitted or at least one")
        if self.target_k_values and "target-k" not in self.knowledge_strategies:
            raise ProtocolError("target_k_values require the 'target-k' strategy")
        if self.infeasible_policy not in {"fail", "skip"}:
            raise ProtocolError("infeasible_policy must be 'fail' or 'skip'")
        for method in self.methods:
            attempts = self.method_attempts.get(method, 1)
            if attempts < 1:
                raise ProtocolError(f"attempts for {method!r} must be positive")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class RunSpec:
    """One deterministic graph/data/knowledge/method execution unit."""

    protocol: str
    graph_id: str
    data_id: str
    method: str
    dimension: int
    sample_size: int
    graph_family: str
    density: int
    graph_seed: int
    data_seed: int
    knowledge_seed: int
    knowledge_fraction: float
    knowledge_round: int
    knowledge_pair_count: int | None = None
    infeasible_policy: str = "fail"
    data_model: str = "linear_gaussian"
    knowledge_strategy: str = "random"
    external_manifest: str | None = None

    def key(self) -> str:
        """Return the stable key used for checkpointing and deduplication."""
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "run_key": self.key()}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write a readable JSON artifact, creating only its parent directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    """Run a dependency-free protocol-contract smoke test."""
    spec = ProtocolSpec(
        name="smoke",
        dimensions=(6,),
        sample_sizes=(32,),
        graph_families=("er",),
        densities=(2,),
        methods=("flop",),
        method_attempts={"flop": 20},
    )
    spec.validate()
    run = RunSpec(
        protocol=spec.name,
        graph_id="smoke_g00",
        data_id="smoke_g00_n32",
        method="flop",
        dimension=6,
        sample_size=32,
        graph_family="er",
        density=2,
        graph_seed=1,
        data_seed=2,
        knowledge_seed=3,
        knowledge_fraction=0.25,
        knowledge_round=0,
    )
    print(json.dumps({"protocol": spec.to_dict(), "run": run.to_dict()}, indent=2))


if __name__ == "__main__":
    main()

