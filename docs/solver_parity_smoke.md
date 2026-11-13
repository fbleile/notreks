# Local solver-parity smoke

On 2026-11-13, the fixed-input parity command was run against the local legacy
Benchpress checkout with the following settings:

```text
sample size: 24 for DAGMA and 64 for FLOP
dimension:   3 for DAGMA and 6 for FLOP
seed:        20261113
attempts:    1
FLOP sweeps: 2
DAGMA stages: 1, warm iterations: 2, maximum iterations: 3
pair:        (0, d-1)
```

The five comparisons below returned identical adjacency matrices:

| Method | Adjacency differences |
|---|---:|
| vanilla FLOP | 0 |
| FLOP+NOTREKS | 0 |
| vanilla DAGMA | 0 |
| DAGMA+NOTREKS | 0 |
| DAGMA+TCC | 0 |

The direct and legacy adapters expose different diagnostic schemas. The parity
JSON therefore records diagnostic-key differences instead of treating them as
solver disagreements. Production acceptance still requires explicit mapping
of objective, feasibility, restart, and post-processing fields as specified in
`solver_parity_matrix.md`; this smoke is the fixed-input adjacency gate, not a
claim of full production parity.

To regenerate one comparison:

```bash
PYTHONPATH=src python -m notreks.parity \
  --benchpress-root /path/to/benchpress \
  --method flop_notreks --dimension 6 --sample-size 64 \
  --attempts 1 --flop-sweeps 2 --output parity/flop_notreks.json
```
