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

## Optional historical parity

The paper-scale result archive remains useful for comparing against published
numbers. The exact combinatorial pilot now has both exhaustive d≤5 and uncapped
d≤15 subset-DP entry points;
complete-MEC auditing is explicit and bounded by the requested audit options.
Direct FLOP edge masking now uses
the installed optimizer's forbidden-edge hook. Direct DAGMA edge masking still
uses a deletion-safe post-mask because upstream DAGMA does not expose that
constraint during optimization, and direct post-selection remains a compact
port rather than a byte-for-byte archived implementation. For exact historical
figures, use the legacy Benchpress backend and parity harness. This is
optional and is not required for a normal standalone run.

The preflight command now reports unsupported method names before a farm is
submitted:

```bash
notreks-preflight --backend direct --methods flop dagma var_sortnregress
```

This boundary is deliberate: the repository never substitutes a simpler method
under a paper method label. Standalone runs use the registered direct adapters;
the legacy checkout is used only when historical numerical parity is being
audited.
