"""Fixed-input value and gradient checks for PSTrek and TCC.

This is an auxiliary diagnostic study, not a structure-learning benchmark. It
uses the same kernel implementations as the optimizer and writes the exact
matrix, pair set, values, gradients, and finite-difference errors so a figure
or table can be regenerated without a notebook.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

from .knowledge import canonical_pair_set_hash
from .pstrek import value_and_grad as pstrek_value_and_grad
from .tcc import value_and_grad as tcc_value_and_grad

Pair = tuple[int, int]


def finite_difference_gradient(function: Callable[[np.ndarray], float],
                               matrix: np.ndarray, epsilon: float) -> np.ndarray:
    """Compute a central finite-difference gradient, preserving the diagonal."""
    if epsilon <= 0 or not np.isfinite(epsilon):
        raise ValueError("epsilon must be finite and positive")
    matrix = np.asarray(matrix, dtype=float)
    gradient = np.zeros_like(matrix)
    for index in np.ndindex(matrix.shape):
        if index[0] == index[1]:
            continue
        plus = matrix.copy()
        minus = matrix.copy()
        plus[index] += epsilon
        minus[index] -= epsilon
        gradient[index] = (function(plus) - function(minus)) / (2.0 * epsilon)
    return gradient


def _relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    denominator = max(1.0, float(np.linalg.norm(expected)))
    return float(np.linalg.norm(actual - expected) / denominator)


def compare_constraints(W: np.ndarray, pairs: Sequence[Pair], *, epsilon: float = 1e-6,
                        pstrek_function: str = "inv", tolerance: float = 1e-5) -> dict[str, object]:
    """Compare analytic PSTrek/TCC gradients with central differences."""
    W = np.asarray(W, dtype=float)
    d = W.shape[0]
    canonical_pairs = sorted({tuple(sorted((int(i), int(j)))) for i, j in pairs})
    pstrek = pstrek_value_and_grad(W, canonical_pairs, function=pstrek_function)
    tcc_value, tcc_gradient = tcc_value_and_grad(W, canonical_pairs)
    pstrek_fd = finite_difference_gradient(
        lambda candidate: pstrek_value_and_grad(
            candidate, canonical_pairs, function=pstrek_function).value,
        W, epsilon)
    tcc_fd = finite_difference_gradient(
        lambda candidate: tcc_value_and_grad(candidate, canonical_pairs)[0],
        W, epsilon)
    return {
        "dimension": d,
        "pairs": [list(pair) for pair in canonical_pairs],
        "pair_set_hash": canonical_pair_set_hash(canonical_pairs),
        "pstrek_function": pstrek_function,
        "finite_difference_epsilon": epsilon,
        "gradient_tolerance": tolerance,
        "pstrek": {
            "value": float(pstrek.value),
            "gradient": pstrek.gradient.tolist(),
            "finite_difference_gradient": pstrek_fd.tolist(),
            "relative_gradient_error": _relative_error(pstrek.gradient, pstrek_fd),
            "gradient_check_passed": _relative_error(pstrek.gradient, pstrek_fd) <= tolerance,
        },
        "tcc": {
            "value": float(tcc_value),
            "gradient": tcc_gradient.tolist(),
            "finite_difference_gradient": tcc_fd.tolist(),
            "relative_gradient_error": _relative_error(tcc_gradient, tcc_fd),
            "gradient_check_passed": _relative_error(tcc_gradient, tcc_fd) <= tolerance,
        },
    }


def run_diagnostic(dimension: int, pair_count: int, seed: int, *, epsilon: float = 1e-6,
                   pstrek_function: str = "inv", tolerance: float = 1e-5) -> dict[str, object]:
    """Generate one deterministic matrix/pair set and run both kernel checks."""
    if dimension < 2:
        raise ValueError("dimension must be at least two")
    all_pairs = [(i, j) for i in range(dimension) for j in range(i + 1, dimension)]
    if pair_count < 1 or pair_count > len(all_pairs):
        raise ValueError(f"pair_count must lie in [1, {len(all_pairs)}]")
    rng = np.random.default_rng(seed)
    W = rng.normal(scale=0.08, size=(dimension, dimension))
    np.fill_diagonal(W, 0.0)
    selected = [all_pairs[int(index)] for index in
                rng.permutation(len(all_pairs))[:pair_count]]
    result = compare_constraints(W, selected, epsilon=epsilon,
                                 pstrek_function=pstrek_function, tolerance=tolerance)
    result.update({"seed": int(seed), "weight_matrix": W.tolist()})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-constraint-check")
    parser.add_argument("--dimension", type=int, default=6)
    parser.add_argument("--pairs", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20261113)
    parser.add_argument("--epsilon", type=float, default=1e-6)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--fail-on-error", action="store_true",
                        help="return status 2 if either analytic gradient fails")
    parser.add_argument("--pstrek-function", choices=("inv", "exp", "log", "binom"),
                        default="inv")
    parser.add_argument("--output", type=Path, default=Path("constraint_diagnostics.json"))
    args = parser.parse_args(argv)
    result = run_diagnostic(args.dimension, args.pairs, args.seed,
                            epsilon=args.epsilon, pstrek_function=args.pstrek_function,
                            tolerance=args.tolerance)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "pair_set_hash": result["pair_set_hash"],
        "pstrek_relative_gradient_error": result["pstrek"]["relative_gradient_error"],
        "tcc_relative_gradient_error": result["tcc"]["relative_gradient_error"],
        "pstrek_gradient_check_passed": result["pstrek"]["gradient_check_passed"],
        "tcc_gradient_check_passed": result["tcc"]["gradient_check_passed"],
    }, indent=2))
    passed = bool(result["pstrek"]["gradient_check_passed"] and
                  result["tcc"]["gradient_check_passed"])
    return 0 if passed or not args.fail_on_error else 2


if __name__ == "__main__":
    raise SystemExit(main())
