"""Deletion-only FLOP-style parent post-selection utilities."""

from __future__ import annotations

import numpy as np

from .scores import common_ancestor_violations, gaussian_bic, is_dag


def direct_mask_edges(pairs):
    """Return both directed edge orientations for each supplied pair."""
    return sorted({(int(left), int(right)) for left, right in pairs} |
                  {(int(right), int(left)) for left, right in pairs})


def local_gaussian_bic(observations: np.ndarray, child: int, parents,
                       lambda_bic: float = 2.0, variance_epsilon: float = 1e-12) -> float:
    data = np.asarray(observations, dtype=np.float64)
    centered = data - data.mean(axis=0, keepdims=True)
    selected = tuple(sorted(int(parent) for parent in parents))
    response = centered[:, child]
    if selected:
        coefficients, *_ = np.linalg.lstsq(centered[:, selected], response, rcond=None)
        residual = response - centered[:, selected] @ coefficients
    else:
        residual = response
    variance = max(float(residual @ residual) / len(data), variance_epsilon)
    return float(len(data) * np.log(variance) + lambda_bic * len(selected) * np.log(len(data)))


def order_parent_postselection(observations: np.ndarray, candidate: np.ndarray,
                               pairs, lambda_bic: float = 2.0) -> tuple[np.ndarray, dict]:
    """Shrink, repair, and grow back parents without changing the candidate order."""
    original = (np.asarray(candidate) != 0).astype(np.uint8)
    if original.ndim != 2 or original.shape[0] != original.shape[1] or not is_dag(original):
        raise ValueError("candidate must be a square DAG adjacency")
    graph = original.copy()
    order = _topological_order(original)
    position = {node: index for index, node in enumerate(order)}
    deletion_count = feasibility_deletions = growback_additions = 0

    def local(child, parents):
        return local_gaussian_bic(observations, child, parents, lambda_bic)

    for child in order:
        while True:
            parents = sorted(np.flatnonzero(graph[:, child]).tolist())
            current = local(child, parents)
            improving = []
            for parent in parents:
                proposal = [value for value in parents if value != parent]
                score = local(child, proposal)
                if score < current - 1e-10:
                    improving.append((score, parent))
            if not improving:
                break
            _, parent = min(improving, key=lambda item: (item[0], item[1]))
            graph[parent, child] = 0
            deletion_count += 1

    while common_ancestor_violations(graph, pairs):
        before = common_ancestor_violations(graph, pairs)
        edges = [(int(parent), int(child)) for parent, child in zip(*np.nonzero(graph))]
        if not edges:
            raise RuntimeError("cannot make candidate NOTREKS-feasible")
        reducing = []
        for parent, child in edges:
            proposal = graph.copy()
            proposal[parent, child] = 0
            after = common_ancestor_violations(proposal, pairs)
            if after < before:
                old_score = local(child, np.flatnonzero(graph[:, child]))
                new_score = local(child, np.flatnonzero(proposal[:, child]))
                reducing.append((new_score - old_score, position[child], parent, child))
        if reducing:
            _, _, parent, child = min(reducing)
        else:
            costs = []
            for parent, child in edges:
                old_score = local(child, np.flatnonzero(graph[:, child]))
                remaining = [value for value in np.flatnonzero(graph[:, child]) if int(value) != parent]
                costs.append((local(child, remaining) - old_score, position[child], parent, child))
            _, _, parent, child = min(costs)
        graph[parent, child] = 0
        deletion_count += 1
        feasibility_deletions += 1

    while True:
        options = []
        for parent, child in zip(*np.nonzero(original & ~graph)):
            parent, child = int(parent), int(child)
            parents = np.flatnonzero(graph[:, child]).tolist()
            old_score = local(child, parents)
            new_score = local(child, parents + [parent])
            if new_score >= old_score - 1e-10:
                continue
            proposal = graph.copy()
            proposal[parent, child] = 1
            if common_ancestor_violations(proposal, pairs):
                continue
            options.append((new_score - old_score, position[child], parent, child))
        if not options:
            break
        _, _, parent, child = min(options)
        graph[parent, child] = 1
        growback_additions += 1

    violations = common_ancestor_violations(graph, pairs)
    if violations or not is_dag(graph):
        raise RuntimeError("postselection returned infeasible DAG")
    bic = float(gaussian_bic(observations, graph, lambda_bic=lambda_bic)[0])
    return graph, {
        "candidate_graph": original.copy(), "cpdag": graph.copy(),
        "postselection_policy": "order_parent_shrink_growback",
        "postprocessed_bic": bic, "postselection_order": order,
        "postselection_deletions": deletion_count,
        "postselection_feasibility_deletions": feasibility_deletions,
        "postselection_growback_additions": growback_additions,
        "postselection_final_violations": violations,
    }


def _topological_order(adjacency: np.ndarray) -> list[int]:
    indegree = np.asarray(adjacency, dtype=bool).sum(axis=0).astype(int)
    available = list(np.flatnonzero(indegree == 0))
    order = []
    while available:
        node = min(available)
        available.remove(node)
        order.append(node)
        for child in np.flatnonzero(adjacency[node]):
            indegree[child] -= 1
            if indegree[child] == 0:
                available.append(int(child))
    if len(order) != len(adjacency):
        raise ValueError("topological order requires a DAG")
    return order


def main() -> None:
    """Run direct masking and local BIC smoke checks."""
    print(direct_mask_edges([(0, 2), (1, 3)]))


if __name__ == "__main__":
    main()
