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

For legacy Benchpress reproduction, retain the Benchpress checkout path and
the solver audit JSON alongside the archive. This is necessary because the
production DAGMA continuation remains the parity reference until the direct
continuation has passed the documented comparison checks.
