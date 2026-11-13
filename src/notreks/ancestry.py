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


@dataclass(frozen=True)
class AncestryConstraint:
    """A normalized request passed from the protocol to a solver adapter."""

    depth: int | None

    def validate(self) -> None:
        if self.depth is not None and self.depth < 1:
            raise ValueError("ancestry depth must be omitted or at least one")

    @property
    def label(self) -> str:
        return "full" if self.depth is None else f"depth-{self.depth}"


def normalize_ancestry_depth(depth: int | None) -> int | None:
    """Validate and normalize the CLI/configuration value."""
    value = None if depth is None else int(depth)
    AncestryConstraint(value).validate()
    return value


def direct_ancestry_edges(pairs: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    """Return both orientations of each depth-one constraint.

    These are passed to FLOP's proposal-level ``forbidden_edges`` hook.  They
    are not applied to a completed graph, and therefore implement genuine
    depth-one search constraints rather than deletion-safe post-masking.
    """
    edges = {(int(left), int(right)) for left, right in pairs}
    edges |= {(right, left) for left, right in edges}
    return tuple(sorted(edges))


def describe(depth: int | None) -> dict[str, object]:
    """Return a small manifest-friendly description of the mode."""
    value = normalize_ancestry_depth(depth)
    return {
        "ancestry_depth": value,
        "ancestry_constraint": "full_ancestry" if value is None else "bounded_ancestry",
        "ancestry_depth_interpretation": (
            "all ancestral paths" if value is None else
            "direct endpoint edges" if value == 1 else
            f"ancestral paths up to length {value}"
        ),
    }


def main() -> None:
    """Exercise the depth contract without optional solver dependencies."""
    assert describe(None)["ancestry_constraint"] == "full_ancestry"
    assert direct_ancestry_edges([(0, 2)]) == ((0, 2), (2, 0))
    try:
        normalize_ancestry_depth(0)
    except ValueError:
        pass
    else:
        raise AssertionError("depth zero must be rejected")
    print("ancestry contract smoke passed")


if __name__ == "__main__":
    main()
