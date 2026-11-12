# Solver porting boundary

The validated solver implementation is not a single-file dependency. FLOP is now available directly through the optional `flopsearch` package; the top-level compatibility adapter remains the parity reference. DAGMA and its NOTREKS objective still import the following functional layers:

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

This avoids creating a superficially standalone repository whose solver behavior differs from the reported experiments.

`notreks.parity.compare` implements the reference-versus-candidate check. It compares the returned adjacency exactly, records diagnostic-key changes, and reports runtimes without using them as a correctness criterion.

## Current migration status

| Layer | New implementation | Validation | Remaining work |
|---|---|---|---|
| PSTrek value and gradient | `notreks.pstrek` | finite differences and four-function legacy parity | connect to continuation |
| DAGMA acyclicity and profile score | `notreks.dagma_math` | finite differences and legacy parity | use in continuation |
| TCC value and gradient | `notreks.tcc` | deterministic checks and legacy parity | connect to continuation |
| Objective composition | `notreks.objectives` | component and weight checks | add optimizer loop |
| Continuation loop | `notreks.continuation` | deterministic callback smoke and domain backtracking | compare every update detail with legacy |
| Direct DAGMA+PSTrek smoke path | `notreks.dagma_backend` | direct solver adapter smoke | end-to-end legacy parity and proximal-L1 parity |
| DAGMA candidate post-processing | `finalize_profile_pstrek` | candidate/final graph smoke | compare standardized BIC and repair diagnostics |
| Production DAGMA continuation | legacy adapter | end-to-end solver parity harness | remove only after the preceding checks |
