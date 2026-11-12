# External benchmark caches

These directories contain the prepared external benchmark artifacts used by the
paper experiments. They are included so that the experiments can be reproduced
without rerunning the upstream simulators or downloading the original data.

## CausalMan

`causalman/` contains ten prepared seeds for each of the Small and Medium
variants. Each seed has the stored observational array, graph metadata, full
adjacency, path metadata, and a preparation manifest. The top-level manifest and
`preflight.csv` record the sample size, observed variables, projection, oracle
NOTREKS counts, provenance, and checksums.

## CausalAssembly

`causalassembly/` contains the fixed upstream dataset prepared at `n=500` for
seeds 1001--1010, the common ground-truth adjacency, and the preparation
manifest. The extra exploratory `seed_1.npz` file from the source cache is
intentionally excluded because it is not part of the paper protocol. The
manifest records that these are repeated samplings from one fixed dataset, not
independent data-generating replicates.

The manifests retain the original source URLs and checksums. The binary files
are deliberately kept separate from code and paper outputs so they can be
validated or replaced without changing the analysis implementation.
