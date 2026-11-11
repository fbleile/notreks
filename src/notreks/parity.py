"""Reference-versus-candidate solver parity checks."""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
from typing import Any

import numpy as np

from .solvers import SolverConfig, SolverRegistry, SolverResult


@dataclass(frozen=True)
class ParityReport:
    method: str
    adjacency_equal: bool
    adjacency_difference_count: int
    reference_runtime_seconds: float
    candidate_runtime_seconds: float
    reference_diagnostic_keys: tuple[str, ...]
    candidate_diagnostic_keys: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.adjacency_equal


def compare(reference: SolverRegistry, candidate: SolverRegistry, method: str,
            observations: np.ndarray, pairs: list[tuple[int, int]], seed: int,
            config: SolverConfig) -> ParityReport:
    """Compare a candidate against a reference on identical inputs."""
    expected = reference.run(method, observations, pairs, seed, config)
    actual = candidate.run(method, observations, pairs, seed, config)
    difference = int(np.count_nonzero(expected.adjacency != actual.adjacency))
    return ParityReport(
        method=method,
        adjacency_equal=difference == 0,
        adjacency_difference_count=difference,
        reference_runtime_seconds=expected.runtime_seconds,
        candidate_runtime_seconds=actual.runtime_seconds,
        reference_diagnostic_keys=tuple(sorted(expected.diagnostics)),
        candidate_diagnostic_keys=tuple(sorted(actual.diagnostics)),
    )


def write_report(path: Path, report: ParityReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    del argv
    registry = SolverRegistry()
    registry.register("toy", lambda observations, pairs, seed, config: SolverResult(
        "toy", np.zeros((3, 3), dtype=np.uint8)))
    report = compare(registry, registry, "toy", np.zeros((4, 3)), [], 1, SolverConfig())
    print(asdict(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
