#!/usr/bin/env bash
set -euo pipefail

# Create or update the complete standalone LRZ environment. This is the one
# installation step; lrz_session_setup.sh only activates the result.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${NOTREKS_ENVIRONMENT:-$ROOT_DIR/.venv-lrz}"
MICROMAMBA_BIN="${MICROMAMBA_BIN:-$(command -v micromamba || true)}"

[[ -n "$MICROMAMBA_BIN" ]] || {
  echo "micromamba is required and was not found in PATH" >&2
  exit 2
}

eval "$($MICROMAMBA_BIN shell hook --shell bash)"
if [[ ! -x "$ENV_DIR/bin/python" ]]; then
  "$MICROMAMBA_BIN" create -y -p "$ENV_DIR" -c conda-forge \
    python=3.11 numpy scipy pip \
    r-base rust
else
  "$MICROMAMBA_BIN" install -y -p "$ENV_DIR" -c conda-forge \
    python=3.11 numpy scipy pip \
    r-base rust
fi

if command -v module >/dev/null 2>&1; then
  r_module="${NOTREKS_R_MODULE:-r/4.3.3-gcc13-mkl}"
  if [[ "$r_module" != "none" ]]; then
    module load "$r_module"
    echo "Using R module: $r_module"
  fi
fi
R_BIN="${NOTREKS_RSCRIPT:-$(command -v Rscript || true)}"
[[ -n "$R_BIN" ]] || {
  echo "Rscript is unavailable after environment setup" >&2
  exit 2
}
R_TMPDIR="${NOTREKS_R_TMPDIR:-/tmp/notreks-r-${USER:-user}}"
mkdir -p "$R_TMPDIR" "$ENV_DIR/lib/R/library"
chmod 700 "$R_TMPDIR"
TMPDIR="$R_TMPDIR" TMP="$R_TMPDIR" TEMP="$R_TMPDIR" \
  LC_ALL=C LANG=C R_LIBS_USER="$ENV_DIR/lib/R/library" \
  "$R_BIN" -e \
  'lib <- Sys.getenv("R_LIBS_USER"); dir.create(lib, recursive=TRUE, showWarnings=FALSE); if (!requireNamespace("BiocManager", quietly=TRUE)) install.packages("BiocManager", lib=lib, repos="https://cloud.r-project.org"); BiocManager::install("pcalg", lib=lib, ask=FALSE, update=FALSE); if (!requireNamespace("pcalg", quietly=TRUE)) stop("pcalg installation did not produce an importable package")'
"$ENV_DIR/bin/python" -m pip install -e "$ROOT_DIR[analysis,solvers]" maturin
PYTHON_BIN="$ENV_DIR/bin/python" "$ROOT_DIR/scripts/install_flopsearch.sh"

"$ENV_DIR/bin/python" -m notreks.preflight \
  --methods flop flop_notreks dagma dagma_notreks \
  --require-ancestor-aid
TMPDIR="$R_TMPDIR" TMP="$R_TMPDIR" TEMP="$R_TMPDIR" LC_ALL=C LANG=C \
  "$R_BIN" -e 'library(pcalg); cat("pcalg available\n")'

echo "NOTREKS LRZ environment ready: $ENV_DIR"
