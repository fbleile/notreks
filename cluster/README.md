# Cluster execution

The cluster uses the same plan and CLI as local runs. Generate a plan once, inspect it, then let JobFarm execute disjoint index ranges. `PROJECT_DIR`, `PLAN`, and `OUTPUT_ROOT` must be absolute paths. Use `--backend benchpress` with an explicit checkout for legacy reproduction, or `--backend direct` for the installable FLOP/DAGMA backends. Solver budgets are written into every generated command, so smoke jobs cannot silently inherit production iteration counts.

The final JobFarm command file will be generated from the registered protocol rather than maintained as a second hand-written experiment definition.
