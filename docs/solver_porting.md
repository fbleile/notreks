# Solver porting boundary

The current validated solver implementation is not a single-file dependency. The top-level adapter imports the following functional layers:

- FLOP search and restart selection;
- DAGMA continuation and score objective;
- the PSTrek kernel and normalization;
- Gaussian BIC and end-of-search pruning;
- graph postprocessing and CPDAG conversion;
- causal-distance diagnostics.

The current closure is kept behind `notreks.integrations.register_benchpress`. The `notreks solver-audit` command records the source file and SHA-256 hash for the required solver symbols and the installed numerical package versions.

The migration rule is parity before replacement:

1. port one coherent module group;
2. run the old and new implementation on the same fixed graph, data, seed, and prior;
3. compare adjacency, objective diagnostics, feasibility violations, and runtime metadata;
4. retain the external adapter until the comparison is exact or a documented numerical tolerance is justified;
5. only then remove the corresponding legacy import.

This avoids creating a superficially standalone repository whose solver behavior differs from the reported experiments.

`notreks.parity.compare` implements the reference-versus-candidate check. It compares the returned adjacency exactly, records diagnostic-key changes, and reports runtimes without using them as a correctness criterion.
