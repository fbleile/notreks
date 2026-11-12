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

## Development smoke test

```bash
make check
python examples/smoke.py
```

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

The current Benchpress repository remains the reference archive while the
remaining optimizer details are migrated incrementally.

## External observational data

CausalMan and CausalAssembly are registered as external-data experiment arms,
not as synthetic graph families. A manifest must name the observation array,
truth adjacency, and (for latent-projection evaluation) projection metadata.
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

The catalog and generated plans are authoritative; shell command files are derived artifacts. Large datasets, solver caches, and result directories do not belong in Git.

