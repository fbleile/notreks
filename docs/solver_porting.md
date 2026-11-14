# Solver backends

NOTREKS runs from the solver implementations installed in the active Python
environment. The repository owns the protocol, data generation, knowledge
construction, execution, evaluation, and analysis layers; no external
research checkout is required.

## FLOP and FLOP+NOTREKS

The public FLOP package supplies vanilla FLOP. The source distribution in
`vendor/flopsearch/` adds the NOTREKS proposal-level constraints. Build it in
the active environment with:

```bash
python scripts/install_flopsearch.sh
```

The installer uses the checked-in source and `maturin`; it does not download a
solver implementation from an unrelated checkout. `flop` and
`flop_notreks --ancestry-depth 0` deliberately use the same vanilla solver
path. Omitting the depth selects full ancestry; depth one is the direct-edge
constraint, and larger depths require the bounded-ancestry interface exposed by
the installed backend. Unsupported depths fail explicitly rather than being
approximated by post-processing.

## DAGMA and auxiliary solvers

The DAGMA integration, PSTrek penalty, TCC constraint, edge-masking and
post-selection ablations, and SortnRegress adapters are registered directly in
`src/notreks/`. Their solver diagnostics are written beside the returned
adjacency in each run directory. The shared solver contract in
`src/notreks/solvers.py` keeps method names, seeds, attempts, and failure
handling independent of the numerical implementation.

## Validation

Run the focused mathematical and backend checks with:

```bash
PYTHONPATH=src python -m pytest -q
notreks-preflight --methods flop flop_notreks
```

The preflight command checks installed package versions and required backend
entry points before an experiment is submitted. Every failed stage records a
traceback in its run directory, so a timeout or solver error can be retried
without losing the original evidence.
