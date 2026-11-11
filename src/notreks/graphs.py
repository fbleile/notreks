"""Graph-family backends used by the registered synthetic protocols.

ER generation is implemented directly in Python.  The WS protocol historically
uses ``pcalg::randDAG(method = "watts")``; its adapter is kept explicit so a
missing R/pcalg installation cannot silently change the benchmark.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path
import shutil
import subprocess

import numpy as np


class GraphGenerationError(RuntimeError):
    """Raised when a declared graph backend cannot produce a valid DAG."""


def er_dag(dimension: int, average_degree: int, seed: int) -> np.ndarray:
    """Generate an ER DAG with expected undirected degree ``average_degree``."""
    _validate_dimensions(dimension, average_degree)
    rng = np.random.default_rng(seed)
    order = rng.permutation(dimension)
    probability = min(1.0, average_degree / (dimension - 1))
    graph = np.zeros((dimension, dimension), dtype=np.uint8)
    upper = (rng.random((dimension, dimension)) < probability) & np.triu(
        np.ones((dimension, dimension), dtype=bool), k=1
    )
    graph[order[:, None], order[None, :]] = upper.astype(np.uint8)
    return graph


def ws_dag(dimension: int, average_degree: int, seed: int,
           rscript: str | None = None) -> np.ndarray:
    """Generate the registered WS DAG using ``pcalg::randDAG``.

    The pcalg call is intentionally tiny and inspectable.  It uses the same
    ``d`` convention as the historical protocol: expected total neighbourhood
    degree, not average indegree.
    """
    _validate_dimensions(dimension, average_degree)
    executable = rscript or shutil.which("Rscript")
    if executable is None:
        raise GraphGenerationError("WS generation requires Rscript with pcalg installed")
    expression = (
        "suppressPackageStartupMessages(library(pcalg)); "
        "args <- commandArgs(trailingOnly=TRUE); "
        "set.seed(as.integer(as.numeric(args[[1]]) %% 2147483647)); "
        "a <- as(pcalg::randDAG(n=as.integer(args[[2]]), "
        "d=as.integer(args[[3]]), method='watts', DAG=TRUE), 'matrix'); "
        "write.table(1*(a != 0), file='', sep=',', row.names=FALSE, "
        "col.names=FALSE, quote=FALSE)"
    )
    try:
        result = subprocess.run(
            [executable, "--vanilla", "-e", expression, str(seed),
             str(dimension), str(average_degree)],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        raise GraphGenerationError(f"pcalg WS generation failed: {detail}") from error
    try:
        graph = np.loadtxt(StringIO(result.stdout), delimiter=",")
    except ValueError as error:
        raise GraphGenerationError("pcalg returned no parseable adjacency matrix") from error
    graph = np.asarray(graph)
    if graph.shape != (dimension, dimension):
        raise GraphGenerationError(
            f"pcalg returned shape {graph.shape}, expected {(dimension, dimension)}")
    return _validate_graph(graph)


def generate(family: str, dimension: int, average_degree: int, seed: int,
             *, rscript: str | None = None) -> np.ndarray:
    """Dispatch a declared graph family without implicit fallbacks."""
    if family == "er":
        return er_dag(dimension, average_degree, seed)
    if family == "ws":
        return ws_dag(dimension, average_degree, seed, rscript=rscript)
    raise GraphGenerationError(f"unknown graph family {family!r}; expected 'er' or 'ws'")


def _validate_dimensions(dimension: int, average_degree: int) -> None:
    if dimension < 2:
        raise ValueError("dimension must be at least two")
    if average_degree < 1:
        raise ValueError("average_degree must be positive")


def _validate_graph(graph: np.ndarray) -> np.ndarray:
    graph = np.asarray(graph)
    if graph.ndim != 2 or graph.shape[0] != graph.shape[1]:
        raise GraphGenerationError("graph must be square")
    if np.any(np.diag(graph)) or np.any((graph != 0) & (graph != 1)):
        raise GraphGenerationError("graph must be binary with zero diagonal")
    # A topological sort is kept local to avoid coupling graph generation to
    # the data module; the explicit check catches malformed external output.
    indegree = graph.sum(axis=0).astype(int)
    remaining = set(range(graph.shape[0]))
    while remaining:
        ready = [node for node in remaining if indegree[node] == 0]
        if not ready:
            raise GraphGenerationError("graph backend returned a cyclic graph")
        for node in ready:
            remaining.remove(node)
            indegree[np.flatnonzero(graph[node]).astype(int)] -= 1
    return graph.astype(np.uint8, copy=False)


def main() -> None:
    """Run the backend smoke test without requiring R."""
    graph = generate("er", 10, 4, seed=7)
    print({"shape": graph.shape, "edges": int(graph.sum())})


if __name__ == "__main__":
    main()
