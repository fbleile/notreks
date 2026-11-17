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

mkdir -p "$ENV_DIR/lib/R/library"
R_LIBS_USER="$ENV_DIR/lib/R/library" "$ENV_DIR/bin/Rscript" -e \
  'if (!requireNamespace("pcalg", quietly = TRUE)) install.packages("pcalg", lib=.libPaths()[1], repos="https://cloud.r-project.org")'
"$ENV_DIR/bin/python" -m pip install -e "$ROOT_DIR[analysis,solvers]" maturin
PYTHON_BIN="$ENV_DIR/bin/python" "$ROOT_DIR/scripts/install_flopsearch.sh"

"$ENV_DIR/bin/python" -m notreks.preflight \
  --methods flop flop_notreks dagma dagma_notreks \
  --require-ancestor-aid
"$ENV_DIR/bin/Rscript" -e 'library(pcalg); cat("pcalg available\n")'

echo "NOTREKS LRZ environment ready: $ENV_DIR"
