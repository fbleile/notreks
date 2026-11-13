# NOTREKS

Reproducible experiments for learning causal DAGs with supplied marginal-independence information represented as absence of treks.

This repository is intentionally small and inspectable. The experiment pipeline is divided into explicit stages:

1. define and validate a protocol;
2. generate or load graphs and data;
3. construct and record NOTREKS knowledge;
4. run a method in an isolated run directory;
5. evaluate the result;
6. aggregate, test, and plot.

## Installation

For a development environment, use `conda env create -f environment.yml` and
then activate the resulting `notreks` environment. A pip-only installation is
also supported: `python -m pip install -e ".[test,analysis,solvers]"`.
The checked-in reference versions are in `requirements/lock.txt`; production
outputs should additionally include `notreks provenance`.

The protocol, artifact lifecycle, evaluation, figure, cluster, FLOP, and
vanilla DAGMA layers are available. The direct DAGMA+PSTrek path is also
available as a checked migration backend; the legacy continuation remains the
reference until full end-to-end parity is complete.

For FLOP+NOTREKS, omitting ``--ancestry-depth`` selects the paper's full
ancestry constraint. ``--ancestry-depth 1`` selects the genuine in-search
direct-edge restriction. Larger depths require a solver backend that exposes
bounded-ancestry proposal constraints; they are never emulated by deleting
edges after a completed search.

## Development smoke test

```bash
make check
python examples/smoke.py
```

For a solver-coverage smoke that includes the ablation and SortnRegress
adapters, use `examples/ablation_smoke_protocol.json` with the direct backend;
keep its iteration budgets small and never treat its results as scientific
benchmarks.

After installation, the same entry points are available as `notreks` and the
focused commands `notreks-catalog-plan`, `notreks-jobfarm`, `notreks-figure`,
and `notreks-aggregate`. A plan is always generated before execution, so a local
smoke, a selected slice, and a cluster job all consume the same run manifest.

To materialize all runnable catalog entries in one plan, use `all`. External
benchmarks without supplied manifests and the analysis-only exact pilot are
listed explicitly under `excluded_entries` rather than becoming empty jobs:

```bash
notreks catalog-plan all plans/all.json --graph-limit 1
```

Use `notreks catalog` to inspect the registered arms before planning.

Before aggregation, inspect a result root without loading scientific table
dependencies:

```bash
notreks-inspect results/ --json
```

The report counts run and stage states and lists every preserved traceback.

Before a long run, check the environment explicitly:

```bash
notreks-preflight --backend direct --methods flop_notreks dagma_notreks
```

When the legacy Benchpress checkout is available, run the fixed-input parity
comparison before treating the direct backend as a replacement:

```bash
notreks-parity --benchpress-root /path/to/benchpress \
  --method flop_notreks --output parity/flop_notreks.json
```

The current Benchpress repository remains the reference archive while the
remaining optimizer details are migrated incrementally. See
`docs/solver_porting.md` for the exact parity boundary; this repository does
not claim full standalone DAGMA parity where that document says it is pending.

Before publication, use `docs/release_checklist.md` as the acceptance gate. It
distinguishes a reproducible protocol and data release from exact historical
solver parity, which still requires the archived Benchpress closure.

## External observational data

CausalMan and CausalAssembly are registered as external-data experiment arms,
not as synthetic graph families. Prepared benchmark caches are included under
`data/external/`, with canonical per-seed manifests and checksums. A manifest
must name the observation array, truth adjacency, and (for latent-projection
evaluation) projection metadata.
Use `python -m notreks.external path/to/dataset.json` to validate one before
planning an external run. Missing files or ambiguous evaluation targets fail
at the data stage and leave a traceback in the run directory.

Once the manifest is available, create a normal executable plan around it:

```bash
notreks-external-plan path/to/manifest.json plans/causalman.json \
  --name causalman-small --methods flop flop_notreks \
  --fractions 0 0.25 1 --attempts flop:20 --attempts flop_notreks:20
```

The plan records the manifest path on every run and derives its dimension and
sample size from the validated arrays.

To convert a historical cache into the canonical manifest layout:

```bash
notreks-external-bundle causalman data/external/causalman data/external/causalman/canonical
notreks-external-bundle causalassembly data/external/causalassembly data/external/causalassembly/canonical
```

To package an already prepared canonical cluster cache for an archival data
release, copy only the artifacts referenced by its manifest:

```bash
notreks-external-pack /cluster/path/manifest.json data/external/causalman-small
```

## Direct solver smoke tests

```bash
python examples/benchpress_adapter_smoke.py /path/to/benchpress --method flop
python -m notreks.dagma_backend
```

Planned runs can use the direct backends without a Benchpress checkout:

```bash
notreks run plan.json results --backend direct --start 0 --limit 1
```

JobFarm command generation accepts the same `--backend direct` choice.

The second command exercises the standalone profile-Gaussian DAGMA+PSTrek
path on a small generated data set. It is a smoke test, not a claim of parity;
the parity boundary and remaining work are recorded in
`docs/solver_porting.md`.

For chromatic summaries, use `notreks trend-figure` rather than plotting raw
rows directly. It first averages within graph and K, then displays the mean
and one standard deviation across graphs:

```bash
notreks trend-figure aggregate_results.csv figures/chromatic.png \
  --graph graph_id --k target_chromatic_number --y SHD_cpdag \
  --data-label "ER4; n=500"
```

PNG is the default output format. Pass `--format pdf` when a vector PDF is
needed.

To check the mathematical kernels independently of a solver, run:

```bash
notreks-constraint-check --fail-on-error --output constraint_diagnostics.json
```

The command checks both PSTrek and the exact TCC block spectral-radius
gradient against central finite differences. At a repeated Perron root the
diagnostic records the nondifferentiable case explicitly.

For the first globally exhaustive Gaussian-BIC motivation tier, use the
reviewer-sized command:

```bash
notreks-exact-bic --dimension 5 --output results/exact-bic-smoke
```

This enumerates every labeled DAG at `d=5`, retains all score-optimal CPDAGs,
and writes a reproducible summary. It is distinct from the fixed-order
feasibility pilot and from the larger archived MEC-retrieval study.

For the uncapped d=6--15 motivation tier, use:

```bash
notreks-exact-bic-dp --dimension 10 --output results/exact-bic-d10
notreks-exact-bic-dp --dimension 10 --audit-mecs --output results/exact-bic-d10-audit
```

The first command returns one globally optimal feasible DAG. The second also
enumerates score-optimal feasible DAGs and canonicalizes their CPDAGs; any
state or DAG cap is recorded as incomplete rather than hidden.

Use `--data-label auto` to generate the canonical compact footer from the
plotted rows. It reports only fields constant in the input, in the order
`graph-family/density; d; n; q`; mixed inputs omit the varying field instead of
silently printing a misleading label.

The paper-facing artifact registry is inspectable with:

```bash
notreks-paper-outputs
```

It lists each figure, table, and auxiliary analysis together with its expected
input artifact and regeneration command.

The package is already installable with pip. A small notebook can be added later
as a thin presentation layer over the same plan, run, aggregate, and figure
commands; it should not become a second experiment implementation.

Validate a bundled external dataset with the lightweight release smoke:

```bash
PYTHONPATH=src python examples/external_data_smoke.py \
  data/external/causalassembly/canonical/seed_1001/manifest.json
```

The same analysis can be retained as a machine-readable report:

```bash
notreks-trend aggregate_results.csv --metric SHD_cpdag \
  --output analysis/chromatic_shd.json
```

## Repository layout

```text
src/notreks/       contracts, generation, execution, evaluation, analysis
examples/           dependency-light smoke and lifecycle examples
tests/              fast unit and integration checks
docs/               architecture and protocol documentation
cluster/            JobFarm conventions and cluster notes
requirements/       dependency groups
```

The catalog and generated plans are authoritative; shell command files are
derived artifacts. Large transient result directories and solver caches do not
belong in Git. The prepared external bundles are an intentional exception and
are covered by their third-party notices.

For a new experiment, start from `examples/custom_protocol.json` and change the
declarative graph, data, method, and knowledge fields. Absolute NOTREKS budgets,
target chromatic numbers, and an explicit skip-or-fail policy are supported; the
planner records them in every run identity and the runner records infeasible
knowledge constructions instead of silently changing the requested design.

For the release procedure and paper-artifact workflow, see `docs/release.md`.

