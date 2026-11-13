# Development guide

NOTREKS has three intended users: a reviewer checking a released artifact, a
user running a small example, and a developer adding a new experiment. Keep
those paths separate.

## Branches

Create one branch per scientific or infrastructure change:

```bash
git switch -c feature/short-description
```

Do not edit generated results, cluster command files, or paper figures as the
definition of an experiment. Change the protocol/catalog or an analysis
command, regenerate the derived artifacts, and retain the command and commit
in the result archive.

## A new experiment

1. Add or extend one declarative protocol entry.
2. Reuse the graph, data, knowledge, runner, evaluation, and aggregation
   stages. A special scientific computation may add a module, but it must
   write the same status and traceback artifacts.
3. Add a dependency-light smoke case before adding production budgets.
4. Add a focused unit test for the new contract and a deterministic example
   when the feature is user-facing.
5. Update `docs/experimental_protocol.md` and the release audit if the study
   is part of the paper artifact.
6. Run `make release-check` before committing.

## Local exploration

Use a disposable output directory and a small plan:

```bash
notreks catalog-plan prior-structure-chrom /tmp/chrom-plan.json --graph-limit 1
notreks run /tmp/chrom-plan.json /tmp/chrom-results --backend direct --limit 1
notreks aggregate /tmp/chrom-results
```

Never put temporary outputs under tracked source directories. The run manifest,
stage status files, and `error.txt` are the first debugging objects to inspect.

## Reviewer reproduction

Use a tagged commit, `scripts/reproduce_paper.sh`, the release checklist, and
the separately archived production results. Do not require a reviewer to find
an old Benchpress checkout unless the release documentation explicitly marks a
solver parity boundary.

## Adding a figure

Figures consume aggregate tables or dedicated auxiliary-analysis outputs, not
raw solver rows. Add a command-level generator, canonical data label, and a
small plotting test. Keep PNG as the default; PDF is an explicit option.
