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
```

The current Benchpress repository remains the reference archive while this standalone implementation is built incrementally.

