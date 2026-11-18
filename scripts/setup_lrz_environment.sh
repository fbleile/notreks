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
  "$MICROMAMBA_BIN" create -y -p "$ENV_DIR" -c conda-forge -c bioconda \
    python=3.11 numpy scipy pip \
    r-pcalg rust
else
  "$MICROMAMBA_BIN" install -y -p "$ENV_DIR" -c conda-forge -c bioconda \
    python=3.11 numpy scipy pip \
    r-pcalg rust
fi

if command -v module >/dev/null 2>&1; then
  r_module="${NOTREKS_R_MODULE:-none}"
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
"$ENV_DIR/bin/python" -m pip install -e "$ROOT_DIR[analysis,solvers]" maturin
PYTHON_BIN="$ENV_DIR/bin/python" "$ROOT_DIR/scripts/install_flopsearch.sh"

"$ENV_DIR/bin/python" -m notreks.preflight \
  --methods flop flop_notreks dagma dagma_notreks \
  --require-ancestor-aid
"$R_BIN" -e 'library(pcalg); cat("pcalg available\n")'

echo "NOTREKS LRZ environment ready: $ENV_DIR"
