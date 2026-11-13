"""Method contract and registry for optional causal discovery backends.

The core package does not silently vendor or substitute a solver.  FLOP,
DAGMA, and TCC integrations register adapters here once their dependencies are
available; the rest of the pipeline sees the same result and diagnostics shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Callable, Protocol

import numpy as np


class SolverError(RuntimeError):
    """Raised when a declared solver cannot complete a run."""


@dataclass(frozen=True)
class SolverConfig:
    """Method-specific settings recorded with every solver result."""

    attempts: int = 1
    flop_sweeps: int = 16
    dagma_stages: int = 5
    dagma_warm_iter: int = 30_000
    dagma_max_iter: int = 60_000
    trek_weight: float = 1.0
    tcc: bool = False
    ancestry_depth: int | None = None

    def validate(self) -> None:
        if self.attempts < 1 or self.flop_sweeps < 1:
            raise ValueError("attempts and flop_sweeps must be positive")
        if self.dagma_stages < 1 or self.dagma_warm_iter < 1 or self.dagma_max_iter < 1:
            raise ValueError("DAGMA iteration settings must be positive")
        if self.trek_weight < 0:
            raise ValueError("trek_weight must be non-negative")
        if self.ancestry_depth is not None and self.ancestry_depth < 0:
            raise ValueError("ancestry_depth must be omitted or non-negative")


@dataclass(frozen=True)
class SolverResult:
    """Common output contract before evaluation translates graphs to metrics."""

    method: str
    adjacency: np.ndarray
    diagnostics: dict[str, Any] = field(default_factory=dict)
    runtime_seconds: float = 0.0

    def validate(self) -> None:
        matrix = np.asarray(self.adjacency)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise SolverError("solver returned a non-square adjacency matrix")
        if np.any(np.diag(matrix)) or np.any((matrix != 0) & (matrix != 1)):
            raise SolverError("solver returned a non-binary adjacency matrix")


class SolverAdapter(Protocol):
    def __call__(self, observations: np.ndarray, pairs: list[tuple[int, int]],
                 seed: int, config: SolverConfig) -> SolverResult: ...


class SolverRegistry:
    """Explicit method registry; registration is local to a process."""

    def __init__(self) -> None:
        self._adapters: dict[str, SolverAdapter] = {}

    def register(self, name: str, adapter: SolverAdapter) -> None:
        if not name.strip():
            raise ValueError("solver name must not be empty")
        if name in self._adapters:
            raise ValueError(f"solver already registered: {name}")
        self._adapters[name] = adapter

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))

    def run(self, name: str, observations: np.ndarray, pairs: list[tuple[int, int]],
            seed: int, config: SolverConfig) -> SolverResult:
        config.validate()
        try:
            adapter = self._adapters[name]
        except KeyError as error:
            available = ", ".join(self.names()) or "none"
            raise SolverError(f"solver {name!r} is not registered; available: {available}") from error
        started = time.perf_counter()
        result = adapter(observations, pairs, seed, config)
        result.validate()
        if result.method != name:
            raise SolverError(f"solver returned method {result.method!r}, expected {name!r}")
        return SolverResult(result.method, result.adjacency, result.diagnostics,
                            time.perf_counter() - started)


def register_optional_solvers(registry: SolverRegistry) -> None:
    """Register only installed integrations; unavailable methods stay visible."""
    # Imports will be added here once each integration has a tested adapter.
    # Keeping this function explicit makes the dependency boundary inspectable.
    del registry


def main() -> None:
    """Exercise registry validation without pretending to solve a graph."""
    registry = SolverRegistry()
    try:
        registry.run("flop", np.zeros((2, 2)), [], 1, SolverConfig())
    except SolverError as error:
        print(error)


if __name__ == "__main__":
    main()
