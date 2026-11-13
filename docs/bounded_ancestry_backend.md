# Bounded ancestry implementation note

The public NOTREKS protocol already carries `ancestry_depth`. The remaining
backend change belongs in the FLOP Rust implementation, not in pair-set
generation.

In the archived FLOP source, `NoTrekConstraints` currently stores one
unbounded descendant-signature bitset per node in `no_treks.rs`. The same state
is consumed by `allowed_parent`, `promotion_is_valid`, `missing_payload`,
`canonical_signatures`, and the constrained order-search loop in
`constrained_algo.rs`. Changing only the initial table would therefore leave
later promotions and reinsertion moves unconstrained.

The bounded implementation should add an optional total trek-length boundary
to that state. For a supplied pair `(i,j)`, a candidate violates depth `r` if
it contains a directed trek between the endpoints whose two directed arms
have total length at most `r`. Consequently, depth one contains only the two
direct endpoint edges; depth two additionally contains a two-edge directed
path and a common-parent fork. The full mode keeps the current unbounded
signature logic.

For a graph with `d` nodes, a simple DAG has no directed arm longer than
`d-1`; requests greater than `d-1` are normalized to full ancestry by the
NOTREKS adapter. The backend must apply the same normalization before building
its constraint state.

The FLOP extension must expose `ancestry_depth` on `flop_notreks`, preserve
the current full-ancestry behavior when it is omitted, and validate bounded
constraints during all proposal, promotion, compression, and reinsertion
paths. Its diagnostics should report both the requested and effective depth.
The Python adapter already passes and validates this contract when the backend
exposes it; until then, depth two and larger fail explicitly rather than being
implemented by post-solution deletion.
