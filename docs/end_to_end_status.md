# End-to-end execution status

The new repository has two distinct meanings of “end to end.” The execution
backbone is complete and tested locally and on LRZ through the same plan-based
interface. The complete paper reproduction is still being migrated method by
method and must not be described as standalone-complete yet.

## Verified now

The following path has been executed successfully with zero aggregate issues:

```text
protocol JSON → plan JSON → graph/data/knowledge artifacts → direct solver
→ evaluation → aggregate_results.csv and aggregate_issues.csv
```

It has been tested for a tiny synthetic FLOP run and for a bundled CausalMan
manifest. The LRZ smoke exercises the same plan-based path under JobFarm. Direct
FLOP, direct vanilla DAGMA, direct DAGMA+PSTrek, and direct DAGMA+TCC are the
currently registered solver paths.

## Still requiring migration or the legacy checkout

The paper catalog also names edge-masking and post-selection ablations, and the
Var-SortnRegress and $R^2$-SortnRegress baselines. Their exact adapters are not
yet registered in the new repository. CausalAssembly and CausalMan data
manifests are available, but a complete paper-scale external run still requires
the corresponding solver set and budgets. The exact combinatorial pilot remains
an analysis-only entry.

The preflight command now reports unsupported method names before a farm is
submitted:

```bash
notreks-preflight --backend direct --methods flop dagma var_sortnregress
```

This boundary is deliberate: the repository never substitutes a simpler method
under a paper method label. Until the remaining adapters are ported and checked
against the archived outputs, use the legacy Benchpress checkout for exact
historical reproduction and use this repository for the verified core path.
