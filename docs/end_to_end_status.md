# End-to-end execution status

The standalone execution backbone is complete and tested locally and on LRZ
through the same plan-based interface. The repository is intended to reproduce
the protocol and scientific summaries, not necessarily byte-identical PNG
files or every historical optimizer trace.

## Verified now

The following path has been executed successfully with zero aggregate issues:

```text
protocol JSON → plan JSON → graph/data/knowledge artifacts → direct solver
→ evaluation → aggregate_results.csv and aggregate_issues.csv
```

It has been tested for a tiny synthetic FLOP run, a bundled CausalMan manifest,
and a 20-run direct ablation smoke covering FLOP, DAGMA, edge masking,
post-selection, and both SortnRegress baselines. The LRZ smoke exercises the
same plan-based path under JobFarm. These are execution tests, not scientific
benchmark results.

FLOP+NOTREKS uses full ancestry by default. The optional ``--ancestry-depth``
setting is an in-search constraint, not a post-processing mask: depth one
forbids the two orientations of every supplied endpoint pair. Depth two and
larger require a FLOP backend exposing a bounded-ancestry proposal table; the
adapter fails explicitly when that capability is absent.

## Solver semantics

The exact combinatorial pilot has both exhaustive d≤5 and uncapped d≤15
subset-DP entry points; complete-MEC auditing is explicit and bounded by the
requested audit options. FLOP edge masking uses the installed optimizer's
forbidden-edge hook. DAGMA edge masking uses a deletion-safe post-mask because
the optimizer does not expose that constraint during optimization, and
post-selection remains a distinct ablation. These semantics are recorded in
the method diagnostics rather than inferred from filenames.

The preflight command now reports unsupported method names before a farm is
submitted:

```bash
notreks-preflight --methods flop dagma var_sortnregress
```

This boundary is deliberate: the repository never substitutes a simpler method
under a paper method label. Runs use the registered direct adapters and fail
before execution when a requested method is unavailable.
