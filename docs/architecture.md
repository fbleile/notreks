# Architecture

NOTREKS is organized around one immutable run identity and a small number of explicit stages.

```text
catalog/protocol
      ↓
      plan.json
      ↓
shared graph + data + knowledge artifacts
      ↓
method adapter → solve/adjacency.npy + diagnostics
      ↓
evaluation stage → aggregate_results.csv
      ↓
figures and statistical analysis
```

## Authority and responsibilities

- `src/notreks/catalog.py` is the scientific experiment catalog.
- `src/notreks/catalog_planning.py` expands one catalog entry into run identities and applies condition-specific method policies.
- `src/notreks/protocol.py` defines serializable protocol and run contracts.
- `src/notreks/graphs.py` and `src/notreks/synthetic.py` generate graph/data/knowledge inputs from explicit seeds.
- `src/notreks/external.py` validates manifest-backed observational datasets. CausalMan and CausalAssembly are not silently treated as synthetic DAGs; their observations, truth adjacency, projection metadata, and node names must be supplied explicitly.
- `src/notreks/runner.py` owns artifact creation, checkpointing, and stage errors.
- `src/notreks/solvers.py` defines the solver contract; `src/notreks/integrations.py` provides the direct FLOP, FLOP+NOTREKS, DAGMA, and auxiliary solver integrations.
- `src/notreks/cpdag.py` and `src/notreks/evaluation.py` own evaluation targets and metric names.
- `src/notreks/aggregate.py` evaluates completed solves through the explicit
  `evaluate` stage, then writes aggregate tables without changing solver
  artifacts.
- `src/notreks/figures.py` consumes tables and applies the shared figure style.
- `src/notreks/jobfarm.py` projects a plan into one-command-per-task JobFarm input.

Shared inputs are keyed by `data_id`; method-specific outputs are keyed by `run_key`. A failed stage leaves `status.json` and `error.txt`, and is reported in `aggregate_issues.csv` rather than being silently omitted.

External datasets use the same shared artifact layout after validation. Their
evaluation target is read from the manifest and projection diagnostics are
kept separate from ordinary CPDAG metrics.

The import and provenance procedure is documented in
`docs/external_data.md`; external arrays are intentionally not repository
fixtures.

## Solver boundary

The repository is the authority for protocol definitions, seeds, artifacts,
evaluation, analysis, figures, and the solver integrations used by the
experiments. Unsupported catalog methods are rejected by preflight rather than
discovered after a long job has started. Solver implementations may keep their
own numerical details, but they must satisfy the shared solver contract and
write diagnostics through the common run-artifact layer.

## Running a bounded experiment

```bash
notreks catalog-plan prior-structure-chrom chrom-plan.json --graph-limit 1
notreks jobfarm chrom-plan.json chrom.cmd results/ /path/to/python /path/to/notreks
notreks aggregate results/
```

Inspect `plan.json` before submitting any expensive command file. The same plan can be sliced with `--start` and `--limit` for local debugging or JobFarm sharding.
