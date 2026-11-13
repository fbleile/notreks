# Solver porting boundary

The validated solver implementation is not a single-file dependency. Vanilla FLOP
is available through the public optional `flopsearch` package, but the public
wheel does not include the `flop_notreks` extension used by this project. A
source-built NOTREKS-enabled FLOP backend is therefore required for direct
FLOP+NOTREKS runs; the repository refuses to substitute vanilla FLOP under that
method name. The top-level compatibility adapter remains the parity reference.
DAGMA and its NOTREKS objective still import the following functional layers:

- FLOP search and restart selection;
- DAGMA continuation and score objective;
- the PSTrek kernel and normalization;
- Gaussian BIC and end-of-search pruning;
- graph postprocessing and CPDAG conversion;
- causal-distance diagnostics.

The PSTrek value/gradient contract is now implemented independently in
`notreks.pstrek`. It is tested against finite differences and against the
legacy NumPy/SciPy kernel for all four supported matrix functions. The DAGMA
continuation still uses the legacy optimizer through
`notreks.integrations.register_benchpress`; replacing that continuation is the
next migration boundary. The current closure is therefore explicit rather
than pretending that a standalone kernel is already a standalone optimizer.
The `notreks solver-audit` command records the source file and SHA-256 hash for
the required solver symbols and the installed numerical package versions.

The migration rule is parity before replacement:

1. port one coherent module group;
2. run the old and new implementation on the same fixed graph, data, seed, and prior;
3. compare adjacency, objective diagnostics, feasibility violations, and runtime metadata;
4. retain the external adapter until the comparison is exact or a documented numerical tolerance is justified;
5. only then remove the corresponding legacy import.

The concrete fixed-input acceptance matrix is maintained in
`docs/solver_parity_matrix.md`. It is the checklist for each migration step;
the smoke tests alone do not establish production parity.

This avoids creating a superficially standalone repository whose solver behavior differs from the reported experiments.

`notreks.parity.compare` implements the reference-versus-candidate check. It compares the returned adjacency exactly, records diagnostic-key changes, and reports runtimes without using them as a correctness criterion.

## Current migration status

| Layer | New implementation | Validation | Remaining work |
|---|---|---|---|
| PSTrek value and gradient | `notreks.pstrek` | finite differences and four-function legacy parity | connect to continuation |
| DAGMA acyclicity and scores | `notreks.dagma_math` | finite differences and legacy parity for L2 and profile-Gaussian scores | use both score modes in continuation |
| TCC value and gradient | `notreks.tcc` | strict finite differences and legacy block-construction parity | connect to continuation |
| Objective composition | `notreks.objectives` | component and weight checks | add optimizer loop |
| Continuation loop | `notreks.continuation` | deterministic callback smoke, domain backtracking, and tiny fixed-run parity | compare full production diagnostics |
| Direct DAGMA+PSTrek smoke path | `notreks.dagma_backend` | direct solver adapter smoke | end-to-end legacy parity and proximal-L1 parity |
| DAGMA candidate post-processing | `finalize_profile_pstrek` | candidate/final graph smoke | compare standardized BIC and repair diagnostics |
| DAGMA restart selection | direct integration adapter | two-restart smoke, deterministic initialization, and BIC selection | compare exact selection metadata |
| Production DAGMA continuation | legacy adapter | end-to-end solver parity harness | remove only after the preceding checks |

The direct solver names are intentionally explicit: `dagma` is the upstream
DAGMA L2 implementation, `dagma_profile` is the standalone continuation with
the profiled Gaussian score, `dagma_notreks` adds PSTrek to that profiled path,
and `dagma_tcc` replaces PSTrek with the TCC constraint and disables the
ordinary log-det DAG penalty, as in the legacy TCC regime. The legacy
production adapter remains available for exact reported-run reproduction.

## Bounded ancestry backend contract

The protocol exposes `SolverConfig.ancestry_depth` for FLOP+NOTREKS. An omitted
value means the existing full-ancestry constraint. A value of one means that
the supplied endpoint pairs are passed as both directed forbidden-edge
orientations to the optimizer's proposal evaluator. This is the direct-edge
ablation, not a deletion mask.

The requested depth is normalized per dimension: for a graph with (d) nodes,
any value greater than (d-1) is represented as full ancestry (`None`), since
a DAG has no simple directed path longer than (d-1). The requested value is
nevertheless retained in the run diagnostics.

For values larger than one, the FLOP backend must expose a proposal-level
bounded-ancestry table. The required call contract is an
`ancestry_depth=<positive integer>` keyword on `flopsearch.flop_notreks`; the
backend must reject every candidate proposal containing an ancestry path of
length at most that value for a supplied pair and return the same diagnostics
contract as full NOTREKS. The repository deliberately does not reinterpret
the unrelated `source_prefix` or `trek_graph` arguments from older FLOP builds
as this table. Until a backend with this contract is installed, depth two and
larger fail explicitly.
