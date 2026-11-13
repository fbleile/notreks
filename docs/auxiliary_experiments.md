# Auxiliary experiments and migration map

The main catalog contains the common synthetic, chromatic, and external
benchmark protocol. A small number of paper artifacts have a different
scientific purpose and therefore use the same artifact lifecycle with a
specialized computation stage.

## Inventory

| Study | Scientific purpose | Current status | Canonical destination |
|---|---|---|---|
| Exact hard-NOTREKS/BIC motivation | Globally optimize Gaussian BIC under supplied no-trek constraints and certify the complete optimal MEC set | The first exhaustive d=5 tier is now available as `notreks-exact-bic`; the original d=10/d=15 tiered study remains in `archive/NOTREKS` | `notreks-exact-bic` with ordinary input and summary artifacts; larger tiers remain to be ported |
| Fixed-order feasibility pilot | Enumerate feasible DAGs for small ordered graphs and compare structural properties of prior sets | Implemented as `notreks-exact` | Existing `exact-feasibility-pilot` output layout |
| PSTrek/TCC value comparison | Compare the constraint values and gradients on identical matrices, independently of structure recovery | Implemented as `notreks-constraint-check`; the current TCC gradient is exposed as a failing diagnostic | `notreks-constraint-check` JSON output |
| PSTrek versus TCC recovery | Compare DAGMA with PSTrek and TCC under the same supplied pairs | Registered as `pstrek-vs-tcc` in the catalog | Existing plan, solve, evaluate, aggregate, and figure stages |
| Chromatic-number recovery | Test whether prior structure matters beyond prior-set size | Implemented as `prior-structure-chrom` | Existing graph-clustered trend analysis |
| Synthetic ablations and misspecification | Compare vanilla, global NOTREKS, edge masking, and post-selection across data-generating arms | Registered in the three synthetic catalog arms | Existing common benchmark stages |
| CausalMan and CausalAssembly | Evaluate supplied-prior methods on semi-synthetic observational data | Implemented through canonical external manifests | Existing external-data stages |

## Exact motivation study

The archived notebook is not copied into the main package because it embeds a
second execution engine, its own checkpoint schema, and a distinct global BIC
solver. Its scientific content is nevertheless part of the intended paper
artifact. The port must preserve:

- the five graph-family definitions and hierarchical seeds;
- paired $n=100$ and $n=500$ data construction;
- the four nested prior budgets;
- exact uncapped Gaussian-BIC optimization;
- complete optimal-MEC retrieval and tie certification;
- feasible-DAG counts, CPDAG recovery, and feasibility summaries;
- resumable case-level checkpoints and a machine-readable summary.

The d=5 port calls the shared graph/data/knowledge contracts and writes a
reproducible summary. The larger port should write one run directory per
graph--dataset--prior condition. It must not silently use the current
fixed-order pilot as a substitute: that pilot answers a different
combinatorial question.

## PSTrek/TCC value comparison

The value comparison is not a solver benchmark. `notreks-constraint-check`
generates fixed-dimension, fixed-seed matrices and pair sets, evaluates PSTrek and TCC values
and gradients using the shared kernel modules, and retain:

```text
input matrix hash, pair-set hash, s, constraint parameters,
PSTrek value, TCC value, analytic gradients, finite-difference errors,
backend/version provenance, and the plotting/analysis command
```

The existing `pstrek-vs-tcc` recovery arm must remain separate from this
diagnostic study. Similar names do not imply the same estimand.

The command is `notreks-constraint-check`. Its `--fail-on-error` option is
intentionally strict. At the current commit, PSTrek passes the default
finite-difference check, while the TCC analytic gradient does not yet pass it
on the default deterministic case. This is recorded as an open kernel issue,
not hidden by loosening the test tolerance.

## Rule for future special studies

An auxiliary study may have its own scientific computation, but it must reuse
the repository's protocol identity, stage status files, traceback handling,
provenance, aggregation conventions, and figure/analysis output contract.
Notebook code is therefore retained as an explanatory front end or historical
reference, never as a second source of experiment logic.
