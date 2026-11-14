# flopsearch

This package provides the standalone FLOP and FLOP+NOTREKS bindings used by
the NOTREKS experiments.

```python
import flopsearch

graph = flopsearch.flop_notreks(
    X,
    2.0,
    [(0, 1)],
    restarts=2,
    seed=1001,
    search_version="global_greedy_rust",
)
```

The constrained entry point uses the fixed Rust global-greedy algorithm. It
performs FLOP order reinsertion and globally scored, hard-feasible inner
search in one extension call. The version field records the implementation
used by serialized run diagnostics and is not a tuning parameter.

Pairs are zero-based integer node pairs. FLOP outputs use the package's CPDAG
encoding: directed edges are `1`, and undirected edges are represented
by symmetric `2` entries. Passing `return_dag=True` returns the selected DAG;
`return_diagnostics=True` also returns the exact final constraint certificate.

The unconstrained entry point is `flopsearch.flop(X, 2.0, restarts=50)`.
