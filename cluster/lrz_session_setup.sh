#!/usr/bin/env bash
# Site-specific shell setup for CoolMUC-4. Source this after login; it never
# submits a job. All experiment definitions remain in the Python package.

if [[ -n "${BASH_SOURCE:-}" ]]; then
  _notreks_setup_file="${BASH_SOURCE[0]}"
else
  _notreks_setup_file="$PWD/cluster/lrz_session_setup.sh"
fi
PROJECT_DIR="${PROJECT_DIR:-$(cd "$(dirname "$_notreks_setup_file")/.." && pwd)}"
NOTREKS_ENVIRONMENT="${NOTREKS_ENVIRONMENT:-$PROJECT_DIR/.venv-lrz}"
export PROJECT_DIR NOTREKS_ENVIRONMENT

module load slurm_setup >/dev/null 2>&1 || true
module load jobfarm >/dev/null 2>&1 || true

if command -v micromamba >/dev/null 2>&1; then
  eval "$(micromamba shell hook --shell bash)"
  micromamba activate "$NOTREKS_ENVIRONMENT"
elif [[ ! -x "$NOTREKS_ENVIRONMENT/bin/python" ]]; then
  echo "No micromamba environment or Python at $NOTREKS_ENVIRONMENT" >&2
  return 1
fi

export PATH="$NOTREKS_ENVIRONMENT/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export TMPDIR="${TMPDIR:-/tmp}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-/tmp/notreks-matplotlib}"
mkdir -p "$MPLCONFIGDIR" "$PROJECT_DIR/cluster/slurm_logs"
cd "$PROJECT_DIR" || return 1

echo "NOTREKS LRZ session ready"
echo "  project:      $PROJECT_DIR"
echo "  environment:  $NOTREKS_ENVIRONMENT"
echo "  python:       $(command -v python)"
echo "  jobfarm:      $(command -v jobfarm || echo unavailable)"
echo "  commit:       $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
unset _notreks_setup_file
