"""Ancestry-depth contracts for hard FLOP NOTREKS constraints.

The default is the original full-ancestry NOTREKS constraint.  A finite depth
is a deliberately separate mode: depth one is the direct-edge restriction,
while larger depths require a solver backend that exposes a bounded ancestry
table to its proposal evaluator.  This module keeps that distinction explicit
so a post-hoc deletion mask can never be mistaken for an in-search constraint.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class AncestryConstraint:
    """A normalized request passed from the protocol to a solver adapter."""

    depth: int | None

    def validate(self) -> None:
        if self.depth is not None and self.depth < 0:
            raise ValueError("ancestry depth must be omitted or non-negative")

    @property
    def label(self) -> str:
        return "full" if self.depth is None else f"depth-{self.depth}"


def normalize_ancestry_depth(depth: int | None) -> int | None:
    """Validate and normalize the CLI/configuration value."""
    value = None if depth is None else int(depth)
    AncestryConstraint(value).validate()
    return value


def effective_ancestry_depth(depth: int | None, dimension: int) -> int | None:
    """Normalize a requested depth against the largest DAG path length.

    A simple DAG on ``dimension`` nodes has no directed simple path longer
    than ``dimension - 1``. Requests above that bound therefore add nothing
    beyond full ancestry and are represented as ``None``. The boundary itself
    remains a finite request, which keeps the requested protocol value visible
    in diagnostics.
    """
    if dimension < 2:
        raise ValueError("dimension must be at least two")
    value = normalize_ancestry_depth(depth)
    return None if value is not None and value > dimension - 1 else value


def direct_ancestry_edges(pairs: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """Return both orientations of each depth-one constraint.

    These are passed to FLOP's proposal-level ``forbidden_edges`` hook.  They
    are not applied to a completed graph, and therefore implement genuine
    depth-one search constraints rather than deletion-safe post-masking.
    """
    edges = {(int(left), int(right)) for left, right in pairs}
    edges |= {(right, left) for left, right in edges}
    return tuple(sorted(edges))


def bounded_ancestry_violations(adjacency: np.ndarray,
                                pairs: Iterable[tuple[int, int]],
                                depth: int) -> tuple[tuple[int, int, int], ...]:
    """List endpoint-ancestry paths of length at most ``depth``.

    A row ``(left, right, length)`` means that the candidate contains a
    directed path of that length from ``left`` to ``right`` or, after the
    canonical ordering of the supplied pair, in the reverse direction. This
    is the finite ancestry table used by bounded backends: depth one is
    exactly direct-edge masking, and depth two additionally blocks a
    two-edge ancestor chain. Full NOTREKS remains the separate ``depth=None``
    regime because it also rules out common ancestors of arbitrary depth.
    """
    value = normalize_ancestry_depth(depth)
    if value is None:
        raise ValueError("bounded ancestry violations require a finite depth")
    graph = np.asarray(adjacency, dtype=bool)
    if graph.ndim != 2 or graph.shape[0] != graph.shape[1]:
        raise ValueError("adjacency must be square")
    powers = graph.copy()
    found: set[tuple[int, int, int]] = set()
    for length in range(1, value + 1):
        for left, right in pairs:
            u, v = sorted((int(left), int(right)))
            if powers[u, v] or powers[v, u]:
                found.add((u, v, length))
        powers = powers @ graph
    return tuple(sorted(found))


def bounded_ancestry_feasible(adjacency: np.ndarray,
                              pairs: Iterable[tuple[int, int]],
                              depth: int) -> bool:
    """Return whether a candidate has no endpoint path within ``depth``."""
    return not bounded_ancestry_violations(adjacency, pairs, depth)


def describe(depth: int | None) -> dict[str, object]:
    """Return a small manifest-friendly description of the mode."""
    value = normalize_ancestry_depth(depth)
    return {
        "ancestry_depth": value,
        "ancestry_constraint": ("full_ancestry" if value is None else
                                "none" if value == 0 else "bounded_ancestry"),
        "ancestry_depth_interpretation": (
            "all ancestral paths" if value is None else
            "no ancestry restriction" if value == 0 else
            "direct endpoint edges" if value == 1 else
            f"ancestral paths up to length {value}"
        ),
    }


def main() -> None:
    """Exercise the depth contract without optional solver dependencies."""
    assert describe(None)["ancestry_constraint"] == "full_ancestry"
    assert direct_ancestry_edges([(0, 2)]) == ((0, 2), (2, 0))
    assert normalize_ancestry_depth(0) == 0
    print("ancestry contract smoke passed")


if __name__ == "__main__":
    main()
