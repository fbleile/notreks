# Solver parity matrix

This document is the acceptance specification for replacing the archived
Benchpress solver closure. A direct implementation is not considered a
production replacement merely because it returns a graph or passes a smoke
test.

## Fixed comparison unit

Every comparison uses the same serialized graph, observations, NOTREKS pair
list, method seed, numerical precision, threshold, and restart index. The
reference and candidate receive copied inputs. Their output directories retain
the input hashes and the source revision of each solver.

## Required comparisons

| Component | Reference | Candidate | Required checks |
|---|---|---|---|
| vanilla FLOP | archived FLOP adapter | direct `flopsearch` | adjacency, edge count, feasibility, restart metadata |
| full-ancestry FLOP+NOTREKS | archived NOTREKS FLOP adapter | direct `flopsearch` | adjacency, supplied-pair violations, objective diagnostics |
| direct-edge FLOP ablation | archived edge-masking/proposal path | direct `forbidden_edges` path | proposal feasibility, adjacency, no post-mask edits |
| vanilla DAGMA | archived DAGMA adapter | upstream `DagmaLinear("l2")` | thresholded adjacency, score, acyclicity, restart metadata |
| profile-Gaussian DAGMA | archived profile path | `notreks.continuation` | objective components, continuation stages, final adjacency |
| DAGMA+PSTrek | archived PSTrek path | direct profile continuation | PSTrek value/gradient, feasibility, final BIC, selected restart |
| DAGMA+TCC | archived TCC path | direct TCC continuation | TCC value/gradient, constraint regime, final BIC, selected restart |

## Tolerances and outcomes

Adjacency matrices must agree exactly after the declared threshold. Numerical
objectives and gradients use an explicit relative/absolute tolerance recorded
in the parity report. A runtime difference is diagnostic only; it is not a
correctness failure. Any disagreement must be classified as one of:

1. expected floating-point or solver-version variation, with a documented
   tolerance;
2. diagnostic-schema variation, with an explicit field mapping; or
3. behavioral mismatch, which blocks removal of the reference adapter.

The report must include the first differing graph edge, the first differing
diagnostic field, feasibility violations before and after post-processing, and
the complete environment and solver hashes.

The report also maps adapter-specific names onto the stable concepts `bic`,
`violations`, `edge_count`, and `restart_count`. Each concept is marked as
`equal_within_tolerance`, `different`, `unmapped`, or `non_numeric`; unmapped
fields require an explicit mapping before production parity is declared.

The fixed-input comparison is executable with:

```bash
notreks-parity --benchpress-root /path/to/benchpress \
  --method flop_notreks --dimension 6 --sample-size 64 \
  --output parity/flop_notreks.json
```

The command constructs the input once, passes copies to both registrations,
stores the input seed and pair list, and returns status 2 when the adjacency
differs. Run it once for each row in this matrix before removing the legacy
adapter.

## Bounded ancestry

Full ancestry and depth one are already separate documented modes. Depth two
and larger require a proposal-level backend implementation, not a post-hoc
edge deletion. The backend must enforce both directed paths and common-parent
forks whose total trek length is within the requested bound, and must expose
the same diagnostics as full NOTREKS. Until that comparison exists, the
adapter must reject those depths.

## Completion rule

The legacy adapter can be removed only after every row above has a passing
fixed-input comparison for at least one small deterministic case and one
paper-representative case. Until then, exact historical figures continue to
use the archived solver closure and the new repository records that dependency
in provenance.
