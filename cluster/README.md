# Cluster execution

The cluster uses the same plan and CLI as local runs. Generate a plan once, inspect it, then let JobFarm execute disjoint index ranges. `PROJECT_DIR`, `PLAN`, and `OUTPUT_ROOT` must be absolute paths. Use `--backend benchpress` with an explicit checkout for legacy reproduction, or `--backend direct` for the installable FLOP/DAGMA backends. Solver budgets are written into every generated command, so smoke jobs cannot silently inherit production iteration counts.

The final JobFarm command file is generated from the registered protocol rather than maintained as a second hand-written experiment definition.

For the production CoolMUC-4 allocation, use the repository wrapper
`cluster/lrz_jobfarm.sh`. It requests four `cm4_std` nodes, 448 one-core
tasks, and 24 hours, and records the command-file checksum, repository commit,
environment, and per-task success markers. It deliberately preflights
`python -m notreks --help`; it does not call the old Benchpress protocol
scripts. The wrapper accepts `PROJECT_DIR`, `CMD_FILE`, and optionally
`NOTREKS_ENVIRONMENT`.

The wrapper is a submission template, not a replacement for the site's current
queue policy. If the queue limits change, update the SBATCH directives and the
documented allocation together, then rerun the smoke job before production.
