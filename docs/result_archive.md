# Paper result archive

The source repository contains the implementation, protocol, prepared external
inputs, and smoke-scale validation. Full production result tables and rendered
paper figures are kept in a separate archive because they are large and are
outputs rather than source inputs.

A result archive is complete when it contains:

```text
results/
  aggregate_results.csv
  aggregate_issues.csv
  analysis/
  figures/
  tables/
  plans/
  provenance/environment.json
  provenance/release-audit.json
```

The `aggregate_results.csv` file must be produced by `notreks-aggregate` from
the run directories, and `aggregate_issues.csv` must be retained even when it
is empty. Every analysis output must retain the input table, the command or
script version, and the repository commit recorded in provenance. Every figure
must be generated from an aggregate table, not directly from ad hoc raw rows.

Record the repository commit, environment manifest, command or script used for
each analysis, and the solver diagnostics needed to interpret the run. The
archive must remain usable from the standalone repository and must not depend
on an untracked development checkout.
