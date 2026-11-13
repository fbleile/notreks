"""Reference-versus-candidate solver parity checks."""

from __future__ import annotations

import argparse
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
    diagnostic_key_difference: tuple[str, ...] = ()
    first_differing_edge: tuple[int, int] | None = None
    diagnostic_checks: dict[str, dict[str, Any]] | None = None

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
    differing = np.argwhere(expected.adjacency != actual.adjacency)
    first_edge = (tuple(int(value) for value in differing[0])
                  if len(differing) else None)
    reference_keys = tuple(sorted(expected.diagnostics))
    candidate_keys = tuple(sorted(actual.diagnostics))
    diagnostic_checks = _compare_diagnostics(expected.diagnostics, actual.diagnostics)
    return ParityReport(
        method=method,
        adjacency_equal=difference == 0,
        adjacency_difference_count=difference,
        reference_runtime_seconds=expected.runtime_seconds,
        candidate_runtime_seconds=actual.runtime_seconds,
        reference_diagnostic_keys=reference_keys,
        candidate_diagnostic_keys=candidate_keys,
        diagnostic_key_difference=tuple(sorted(set(reference_keys) ^ set(candidate_keys))),
        first_differing_edge=first_edge,
        diagnostic_checks=diagnostic_checks,
    )


def write_report(path: Path, report: ParityReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n")


_DIAGNOSTIC_ALIASES = {
    "bic": ("optimizer_final_bic", "final_bic", "selected_bic", "postprocessed_bic"),
    "violations": ("optimizer_violations", "final_no_trek_violation_count"),
    "edge_count": ("selected_dag_edge_count", "final_edges", "candidate_edges"),
    "restart_count": ("optimizer_restarts", "restarts_requested", "attempts_requested"),
}


def _first_present(diagnostics: dict[str, Any], names: tuple[str, ...]) -> tuple[str, Any] | None:
    for name in names:
        if name in diagnostics:
            return name, diagnostics[name]
    return None


def _compare_diagnostics(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Compare stable diagnostic concepts despite adapter-specific field names."""
    checks: dict[str, dict[str, Any]] = {}
    for concept, aliases in _DIAGNOSTIC_ALIASES.items():
        left = _first_present(reference, aliases)
        right = _first_present(candidate, aliases)
        if left is None or right is None:
            checks[concept] = {"status": "unmapped", "reference": left[0] if left else None,
                               "candidate": right[0] if right else None}
            continue
        left_name, left_value = left
        right_name, right_value = right
        try:
            difference = abs(float(left_value) - float(right_value))
            scale = max(1.0, abs(float(left_value)), abs(float(right_value)))
            checks[concept] = {
                "status": "equal_within_tolerance" if difference <= 1e-8 * scale else "different",
                "reference_field": left_name, "candidate_field": right_name,
                "reference": left_value, "candidate": right_value,
                "absolute_difference": difference,
            }
        except (TypeError, ValueError):
            checks[concept] = {"status": "non_numeric", "reference_field": left_name,
                               "candidate_field": right_name}
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-parity")
    parser.add_argument("--benchpress-root", type=Path, required=True)
    parser.add_argument("--method", choices=("flop", "flop_notreks", "dagma", "dagma_notreks", "dagma_tcc"), default="flop_notreks")
    parser.add_argument("--dimension", type=int, default=6)
    parser.add_argument("--sample-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20261113)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--flop-sweeps", type=int, default=2)
    parser.add_argument("--dagma-stages", type=int, default=1)
    parser.add_argument("--dagma-warm-iter", type=int, default=4)
    parser.add_argument("--dagma-max-iter", type=int, default=8)
    parser.add_argument("--output", type=Path, default=Path("parity_report.json"))
    args = parser.parse_args(argv)
    if args.dimension < 2 or args.sample_size <= args.dimension:
        raise SystemExit("dimension must be at least 2 and sample-size must exceed dimension")
    from .integrations import register_benchpress, register_direct
    observations = np.random.default_rng(args.seed).normal(size=(args.sample_size, args.dimension))
    pairs = [(0, args.dimension - 1)]
    config = SolverConfig(attempts=args.attempts, flop_sweeps=args.flop_sweeps,
                          dagma_stages=args.dagma_stages,
                          dagma_warm_iter=args.dagma_warm_iter,
                          dagma_max_iter=args.dagma_max_iter)
    reference = SolverRegistry()
    candidate = SolverRegistry()
    reference_provenance = register_benchpress(reference, args.benchpress_root)
    candidate_provenance = register_direct(candidate, {args.method})
    report = compare(reference, candidate, args.method, observations, pairs, args.seed, config)
    payload = {"reference": reference_provenance, "candidate": candidate_provenance,
               "inputs": {"dimension": args.dimension, "sample_size": args.sample_size,
                          "seed": args.seed, "pairs": [list(pair) for pair in pairs]},
               **asdict(report)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if report.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
