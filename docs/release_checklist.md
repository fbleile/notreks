# Publication release checklist

This checklist verifies the repository from a clean checkout.

## Clean local checkout

```bash
conda env create -f environment.yml
conda run -n notreks python -m pip install -e ".[test,analysis]"
conda run -n notreks make release-check
conda run -n notreks python examples/end_to_end.py /tmp/notreks-example
```

The release audit must report no missing files, no invalid external manifests, no non-portable paths in canonical manifests, and all registered experiment arms. The end-to-end example must finish with an empty issue table.

## Solver boundary

The package reproduces the protocol, analyses, and solver workflows defined in
this repository. Pixel-identical figures and byte-identical optimizer traces
are not release requirements; the recorded protocol and run artifacts are the
reproducibility contract.

The default FLOP+NOTREKS mode is full ancestry. Direct-edge mode is available as `--ancestry-depth 1`. Larger bounded ancestry depths require a backend that implements the proposal-level contract in `docs/bounded_ancestry_backend.md`; the adapter must fail explicitly otherwise.

## External data

Every bundled canonical manifest must validate without network access. Manifest paths must be relative to the manifest directory. Upstream URLs, revisions, checksums, and preparation commands belong in provenance metadata, not in place of the bundled artifacts.

## Cluster acceptance test

From a clean LRZ checkout, run the session setup, direct preflight, and the small JobFarm smoke before submitting any production plan:

```bash
source cluster/lrz_session_setup.sh
python -m pip install --no-deps -e .
python -m pip install maturin
scripts/install_flopsearch.sh
notreks-preflight --methods flop flop_notreks
export PROJECT_DIR=$PWD
export CMD_FILE=$PROJECT_DIR/cluster/notreks_cluster_smoke.cmd
sbatch --parsable --chdir="$PROJECT_DIR" \
  --export=ALL,PROJECT_DIR="$PROJECT_DIR",CMD_FILE="$CMD_FILE" \
  cluster/lrz_jobfarm_smoke.sh
```

Record the Slurm job ID, commit, environment manifest, task markers, and the result of `notreks inspect`. Timeout recovery is accepted only when the retry file contains unfinished tasks and successful run identities are not repeated.

## Paper archive

The separate result archive must contain the final plans, aggregate tables,
analysis scripts or commands, figures, tables, environment provenance, release
audit, and the exact repository commit. The source repository does not silently
claim that an absent result archive has been regenerated.
