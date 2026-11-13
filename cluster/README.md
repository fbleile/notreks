# Cluster execution

## First login and setup

The repository contains the small site-specific setup layer that the old
Benchpress checkout used to provide. It loads LRZ's Slurm and JobFarm modules,
activates the configured micromamba environment when available, sets the
thread limits, and exports the repository's `src/` directory. It does not submit
jobs and contains no experiment logic.

```bash
ssh -Y <cluster-host> -l <cluster-user>
git clone <repository-url> notreks        # use git pull --ff-only thereafter
cd notreks
source cluster/lrz_session_setup.sh
python -m pip install -e ".[analysis,solvers]"
python -m pip install maturin
scripts/install_flopsearch.sh
notreks-preflight --backend direct --methods flop flop_notreks
```

If the cluster environment is created at a different path, set
`NOTREKS_ENVIRONMENT=/absolute/path/to/environment` before sourcing the setup
file. The setup is intentionally generic: no user name, email address, or
Benchpress path is embedded in it.

The cluster uses the same plan and CLI as local runs. Generate a plan once, inspect it, then let JobFarm execute disjoint index ranges. `PROJECT_DIR`, `PLAN`, and `OUTPUT_ROOT` must be absolute paths. Use `--backend direct` for the standalone FLOP/DAGMA backends; the optional Benchpress backend is retained only for historical parity. Solver budgets are written into every generated command, so smoke jobs cannot silently inherit production iteration counts.

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

For a legacy Benchpress backend, add `--benchpress-root /absolute/path/to/benchpress`
to the command-generator invocation. Direct mode does not require that checkout.

## Constructing a new experiment

For a new synthetic experiment, copy `examples/custom_protocol.json` and edit
only its declarative fields. `dimensions`, `sample_sizes`, `graph_families`,
`densities`, `methods`, `graph_replicates`, and `method_attempts` define the
graph/data/solver grid. Use `knowledge_fractions` for relative information,
or set `knowledge_pair_counts` to one or more absolute budgets while retaining
a nominal fraction for labeling. Available strategies are `random`,
`source-ancestor`, and `target-k`. Use `knowledge_strategies: ["target-k"]` and
`target_k_values: [2, 3, 4]` for targeted chromatic constructions. Set
`infeasible_policy: "skip"` when a target or budget is an expected part of the
design that may not exist for every graph; the run records an explicit
`status: infeasible` manifest and JobFarm continues. Keep the default `fail`
policy when infeasibility indicates a protocol or implementation error.

The standard workflow is:

```bash
notreks plan custom_protocol.json plans/custom.json
python -m json.tool plans/custom.json | head -40
notreks jobfarm plans/custom.json cluster/custom.cmd results/custom \
  "$NOTREKS_ENVIRONMENT/bin/python" "$PROJECT_DIR" --backend direct
```

The absolute-pair-count and target-K choices are stored in every run manifest,
alongside the available-pair count and pair-set hash. This makes a reviewer-
requested variant a new plan with auditable differences rather than a manual
edit to a command file.

## Cluster smoke and timeout recovery

Run the small node-level smoke before submitting a production farm. It checks the
checkout, environment, JobFarm, one worker, and one direct FLOP run:

```bash
export PROJECT_DIR=$PWD
export CMD_FILE=$PROJECT_DIR/cluster/notreks_cluster_smoke.cmd
export NOTREKS_ENVIRONMENT=$PROJECT_DIR/.venv-lrz
sbatch --parsable --chdir="$PROJECT_DIR" \
  --export=ALL,PROJECT_DIR="$PROJECT_DIR",CMD_FILE="$CMD_FILE",NOTREKS_ENVIRONMENT="$NOTREKS_ENVIRONMENT" \
  cluster/lrz_jobfarm_smoke.sh
```

The wrapper expands `examples/smoke_protocol.json` into a fresh plan inside
`cluster/slurm_logs/`; the command file therefore exercises the same plan-based
execution path as production rather than passing a protocol where a plan is
required.

The smoke runs one tiny vanilla FLOP task and one tiny FLOP+NOTREKS task. It
writes its Slurm manifest, JobFarm log, and per-task result under
`cluster/slurm_logs/` and `${CMD_FILE}_res/`. Inspect those files with `sacct`,
`cat slurm-<jobid>.out`, and `cat ${CMD_FILE}_res/1` before starting a large job.

Every generated task keeps its own run directory and traceback. If a farm times
out, make a new command file containing only tasks without a `STOP SUCCESS`
marker:

```bash
notreks-jobfarm-retry "$CMD_FILE" "${CMD_FILE}_res" "$CMD_FILE.retry.cmd"
```

Submit the retry file with the same wrapper, setting `CMD_FILE` to the new file
and using a fresh result directory or a new command-file basename. Do not reset
the original result directory: it is the audit trail for the first allocation.
The retry command preserves the original `--start` index, so the run identity
and output location remain unchanged while successful tasks are not repeated.

For a reproducible cluster checkout, clone the public repository at an explicit
release tag or commit, install the declared environment, and record the commit
in the Slurm manifest. Do not run a production farm from an uncommitted working
tree. Once the GitHub URL exists, the intended sequence is:

```bash
git clone <repository-url> notreks
cd notreks
git checkout <release-tag-or-commit>
conda env create -f environment.yml
conda run -n notreks python -m pip install -e ".[analysis,solvers]"
```
