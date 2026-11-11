# Cluster execution

The cluster uses the same plan and CLI as local runs. Generate a plan once, inspect it, then let JobFarm execute disjoint index ranges. `PROJECT_DIR`, `PLAN`, and `OUTPUT_ROOT` must be absolute paths. The solver environment and the Benchpress checkout are explicit arguments; no login-shell state is assumed.

The final JobFarm command file will be generated from the registered protocol rather than maintained as a second hand-written experiment definition.
