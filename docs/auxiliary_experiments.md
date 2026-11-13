# Auxiliary experiments and migration map

The main catalog contains the common synthetic, chromatic, and external
benchmark protocol. A small number of paper artifacts have a different
scientific purpose and therefore use the same artifact lifecycle with a
specialized computation stage.

## Inventory

| Study | Scientific purpose | Current status | Canonical destination |
|---|---|---|---|
| Exact hard-NOTREKS/BIC motivation | Globally optimize Gaussian BIC under supplied no-trek constraints and audit optimal MECs | The exhaustive d=5 tier is available as `notreks-exact-bic`; the uncapped d=6--15 subset-DP tier and its optional complete-MEC audit are available as `notreks-exact-bic-dp` | `notreks-exact-bic` for exhaustive d≤5 cases and `notreks-exact-bic-dp --audit-mecs` for the larger tier |
| Fixed-order feasibility pilot | Enumerate feasible DAGs for small ordered graphs and compare structural properties of prior sets | Implemented as `notreks-exact` | Existing `exact-feasibility-pilot` output layout |
| PSTrek/TCC value comparison | Compare the constraint values and gradients on identical matrices, independently of structure recovery | Implemented as `notreks-constraint-check`; both analytic gradients are checked against finite differences | `notreks-constraint-check` JSON output |
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
reproducible summary. The d=6--15 port uses the same contracts and writes one
run directory per graph--dataset--prior condition, with the exact subset-DP
objective, conflict-directed constraint states, search certificate, and
reconstructed optimum. It intentionally reports one global optimum; complete
MEC enumeration is a separate audit and is not silently substituted by this
optimization tier. The fixed-order pilot remains separate because it answers
a different combinatorial question. Use `--audit-mecs` for complete optimal-MEC
retrieval; state and DAG caps make incompleteness explicit in `run.json`.

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
diagnostic study. Similar names do not imply the same estimand. The TCC
diagnostic uses the exact block spectral-radius difference and its analytic
Perron pullback; the strict finite-difference check is expected to pass for
matrices with simple Perron roots.

The command is `notreks-constraint-check`. Its `--fail-on-error` option is
intentionally strict. Both analytic gradients pass the default deterministic
finite-difference check when the spectral-radius root is simple; the output
records the root degeneracy caveat explicitly.

## Rule for future special studies

An auxiliary study may have its own scientific computation, but it must reuse
the repository's protocol identity, stage status files, traceback handling,
provenance, aggregation conventions, and figure/analysis output contract.
Notebook code is therefore retained as an explanatory front end or historical
reference, never as a second source of experiment logic.
