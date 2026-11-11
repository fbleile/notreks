# NOTREKS

Reproducible experiments for learning causal DAGs with supplied marginal-independence information represented as absence of treks.

This repository is intentionally small and inspectable. The experiment pipeline is divided into explicit stages:

1. define and validate a protocol;
2. generate or load graphs and data;
3. construct and record NOTREKS knowledge;
4. run a method in an isolated run directory;
5. evaluate the result;
6. aggregate, test, and plot.

The first implementation stage contains only the protocol and provenance contracts. Solver integrations, cluster execution, and figure production will be added on top of these contracts and tested against the existing Benchpress-based implementation.

## Development smoke test

```bash
python -m pytest -q
python examples/smoke.py
python -m notreks.cli smoke
```

After installation, the same entry points are available as `notreks` and
`notreks-aggregate`. A plan is always generated before execution, so a local
smoke, a selected slice, and a cluster job all consume the same run manifest.

The current Benchpress repository remains the reference archive while this standalone implementation is built incrementally.

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

