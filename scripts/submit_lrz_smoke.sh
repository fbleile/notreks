#!/usr/bin/env bash
set -euo pipefail

# Submit the repository's tiny LRZ smoke from the checkout root. The batch
# script owns the cm4_tiny resource request; this wrapper only supplies paths.
PROJECT_DIR="${PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
if [[ -z "$PROJECT_DIR" || ! -f "$PROJECT_DIR/cluster/lrz_jobfarm_smoke.sh" ]]; then
  echo "Run this command from a NOTREKS checkout (or set PROJECT_DIR)." >&2
  exit 2
fi
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
NOTREKS_ENVIRONMENT="${NOTREKS_ENVIRONMENT:-$PROJECT_DIR/.venv-lrz}"
CMD_FILE="${CMD_FILE:-$PROJECT_DIR/cluster/notreks_cluster_smoke.cmd}"

[[ -x "$NOTREKS_ENVIRONMENT/bin/python" ]] || {
  echo "Missing environment Python: $NOTREKS_ENVIRONMENT/bin/python" >&2
  echo "Create or activate the repository environment before submitting." >&2
  exit 2
}
[[ -r "$CMD_FILE" ]] || { echo "Missing command file: $CMD_FILE" >&2; exit 2; }

export PROJECT_DIR NOTREKS_ENVIRONMENT CMD_FILE
job=$(sbatch --parsable \
  --chdir="$PROJECT_DIR" \
  --export=ALL,PROJECT_DIR="$PROJECT_DIR",NOTREKS_ENVIRONMENT="$NOTREKS_ENVIRONMENT",CMD_FILE="$CMD_FILE" \
  "$PROJECT_DIR/cluster/lrz_jobfarm_smoke.sh")
printf 'submitted NOTREKS LRZ smoke: job %s\n' "$job"
