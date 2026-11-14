# Custom experiments

The catalog is the stable interface for paper arms. For a new study, copy
`examples/custom_protocol.json`, change only the scientific settings, and keep
the same plan and run stages.

```bash
cp examples/custom_protocol.json configs/my_experiment.json
notreks catalog
notreks-catalog-plan custom-experiment plans/my_experiment.json \
  --master-seed 20260917 --graph-limit 2
```

For a protocol that is not yet a catalog entry, use the same `RunSpec` fields
through the Python API and write a plan before executing it. The important
choices are dimension, sample size, graph family and density, graph replicate
count, solver method, restart budget, knowledge fraction or absolute pair
count, knowledge strategy, target chromatic number, and ancestry depth.

Every generated run receives deterministic graph, data, knowledge, and method
seeds. Knowledge construction must record the requested and realized pair
counts and an explicit infeasibility status; it must never silently replace an
unavailable target. The runner writes `status.json`, `error.txt`, and a
traceback for every failed stage, while aggregation retains failures in
`aggregate_issues.csv`.

Inspect a plan before running it:

```bash
notreks-inspect plans/my_experiment.json --json
notreks-preflight --methods flop_notreks
```

Run locally for a small slice:

```bash
notreks run plans/my_experiment.json results/my_experiment
notreks-aggregate results/my_experiment
```

The same plan can be split into JobFarm command ranges. Do not edit generated
commands by hand; create a new protocol or plan so its settings remain part of
the provenance record.
