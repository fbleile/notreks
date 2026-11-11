"""DAG-to-CPDAG conversion and CPDAG structural Hamming distance."""

from __future__ import annotations

import numpy as np


class CPDAGError(ValueError):
    """Raised for invalid DAG or CPDAG inputs."""


def dag_to_cpdag(dag: np.ndarray) -> np.ndarray:
    """Convert a DAG to its CPDAG using collider initialization and Meek R1--R3."""
    dag = _validate_binary(dag)
    _validate_acyclic(dag)
    dimension = dag.shape[0]
    skeleton = (dag != 0) | (dag.T != 0)
    directed = np.zeros((dimension, dimension), dtype=bool)
    undirected = skeleton.copy()

    def adjacent(left: int, right: int) -> bool:
        return bool(skeleton[left, right])

    def orient(left: int, right: int) -> bool:
        if directed[left, right]:
            return False
        if directed[right, left] or not undirected[left, right]:
            raise CPDAGError("inconsistent CPDAG orientation")
        undirected[left, right] = undirected[right, left] = False
        directed[left, right] = True
        return True

    # Orient exactly the unshielded colliders present in the DAG.
    for child in range(dimension):
        parents = np.flatnonzero(dag[:, child])
        for offset, left in enumerate(parents):
            for right in parents[offset + 1:]:
                if not adjacent(int(left), int(right)):
                    orient(int(left), child)
                    orient(int(right), child)

    changed = True
    while changed:
        changed = False
        # R1: a -> b - c and a not adjacent c implies b -> c.
        for left in range(dimension):
            for middle in np.flatnonzero(directed[left]):
                for right in np.flatnonzero(undirected[middle]):
                    if not adjacent(left, int(right)):
                        changed |= orient(int(middle), int(right))
        # R2: a - b and a -> c -> b implies a -> b.
        for left in range(dimension):
            for right in np.flatnonzero(undirected[left]):
                right = int(right)
                if any(directed[left, middle] and directed[middle, right]
                       for middle in range(dimension) if middle not in (left, right)):
                    changed |= orient(left, right)
        # R3: a - b, a - c, a - d, c -> b, d -> b, c not adjacent d.
        for left in range(dimension):
            for right in np.flatnonzero(undirected[left]):
                right = int(right)
                candidates = [int(node) for node in np.flatnonzero(undirected[left])
                              if int(node) != right and directed[int(node), right]]
                if any(not adjacent(first, second)
                       for offset, first in enumerate(candidates)
                       for second in candidates[offset + 1:]):
                    changed |= orient(left, right)

    result = directed.astype(np.uint8)
    result[undirected] = 1
    return result


def cpdag_shd(truth_dag: np.ndarray, estimate_cpdag: np.ndarray) -> int:
    """Count CPDAG adjacency and edge-mark disagreements."""
    truth = dag_to_cpdag(truth_dag)
    estimate = _validate_binary(estimate_cpdag)
    if truth.shape != estimate.shape:
        raise CPDAGError("truth and estimate dimensions differ")
    distance = 0
    for left in range(truth.shape[0]):
        for right in range(left + 1, truth.shape[1]):
            truth_mark = (int(truth[left, right]), int(truth[right, left]))
            estimate_mark = (int(estimate[left, right]), int(estimate[right, left]))
            distance += int(truth_mark != estimate_mark)
    return distance


def ancestor_aid(true_dag: np.ndarray, estimate_cpdag: np.ndarray) -> tuple[float, int]:
    """Compute CPDAG Ancestor-AID through the optional ``gadjid`` package."""
    try:
        import gadjid
    except ImportError as error:
        raise CPDAGError("CPDAG Ancestor-AID requires the optional gadjid package") from error
    true_encoded = _encode_gadjid(dag_to_cpdag(true_dag))
    estimate_encoded = _encode_gadjid(_validate_binary(estimate_cpdag))
    normalized, count = gadjid.ancestor_aid(true_encoded, estimate_encoded, "from row to column")
    return float(normalized), int(count)


def _encode_gadjid(adjacency: np.ndarray) -> np.ndarray:
    result = (adjacency != 0).astype(np.int8)
    undirected = (result != 0) & (result.T != 0)
    result[undirected] = 2
    np.fill_diagonal(result, 0)
    return result


def _validate_binary(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise CPDAGError("matrix must be square")
    if np.any(np.diag(matrix)) or np.any((matrix != 0) & (matrix != 1)):
        raise CPDAGError("matrix must be binary with zero diagonal")
    return matrix.astype(np.uint8, copy=False)


def _validate_acyclic(graph: np.ndarray) -> None:
    indegree = graph.sum(axis=0).astype(int)
    remaining = set(range(graph.shape[0]))
    while remaining:
        ready = [node for node in remaining if indegree[node] == 0]
        if not ready:
            raise CPDAGError("CPDAG conversion requires an acyclic DAG")
        for node in ready:
            remaining.remove(node)
            indegree[np.flatnonzero(graph[node]).astype(int)] -= 1


def main() -> None:
    """Print the CPDAG of a three-node collider."""
    dag = np.array([[0, 0, 1], [0, 0, 1], [0, 0, 0]], dtype=np.uint8)
    print(dag_to_cpdag(dag).tolist())


if __name__ == "__main__":
    main()
