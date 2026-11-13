# Release and paper-artifact procedure

This repository contains the implementation and prepared external benchmark
inputs. The large synthetic result tables from the paper are intentionally not
duplicated in Git; they are generated from the checked-in protocol and stored
as a separate result archive.

## Local release check

From the repository root:

```bash
make release-check
```

This validates every canonical external manifest, checks the catalog, records
the current commit and environment, and runs the complete fast test suite.
The bundled external smoke can also be run directly:

```bash
PYTHONPATH=src python examples/external_data_smoke.py \
  data/external/causalman/canonical/causalman_small/seed_1001/manifest.json
```

## Reproduce the paper protocol

The paper protocol is defined by `src/notreks/catalog.py` and explained in
`docs/experimental_protocol.md`. Generate a complete synthetic plan with:

```bash
mkdir -p reproduction/plans reproduction/provenance
PYTHONPATH=src python -m notreks.catalog_planning all \
  reproduction/plans/catalog_all.json
PYTHONPATH=src python -m notreks.provenance \
  reproduction/provenance/environment.json --project-root .
```

External runs use the canonical per-seed manifests under
`data/external/*/canonical/`. Generate a plan for an individual seed with:

```bash
PYTHONPATH=src python -m notreks.external_plan \
  data/external/causalassembly/canonical/seed_1001/manifest.json \
  reproduction/plans/causalassembly_seed1001.json \
  --name causalassembly-seed1001 --methods flop flop_notreks \
  --fractions 0 0.25 1 --attempts flop:20 --attempts flop_notreks:20
```

The checked-in `scripts/reproduce_paper.sh` generates the synthetic plan and
one external plan for every bundled seed. It does not submit production jobs;
the resulting plans are inspected and then passed to the local or JobFarm
runner. The expected output layout is specified in `docs/result_archive.md`.

Run a selected local slice with the direct backend or submit the generated
plan through `cluster/lrz_jobfarm.sh`. Full production execution is expected
to run on LRZ and is not part of the fast CI job.

## Release claims

The direct FLOP adapter and the standalone DAGMA smoke path are included. The
legacy Benchpress continuation remains the reference for production parity in
the parts documented in `docs/solver_porting.md`; the release must not claim
that the standalone DAGMA path reproduces every historical solver run until the
listed parity checks are complete.
