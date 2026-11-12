#!/usr/bin/env bash
#SBATCH --job-name=notreks-jobfarm
#SBATCH --get-user-env
#SBATCH --clusters=cm4
#SBATCH --partition=cm4_std
#SBATCH --qos=cm4_std
#SBATCH --nodes=4-4
#SBATCH --ntasks=448
#SBATCH --cpus-per-task=1
#SBATCH --time=24:00:00
#SBATCH --export=ALL
#SBATCH --mail-type=BEGIN,END
#SBATCH --mail-user=f.bleile@tum.de

# Run a generated one-command-per-line file through LRZ JobFarm.  The
# allocation is intentionally explicit: four nodes and one task per core,
# matching the production farms used for the reported large experiments.
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:?Set PROJECT_DIR to the NOTREKS checkout}"
CMD_FILE="${CMD_FILE:-$PROJECT_DIR/cluster/notreks_cmd.txt}"
ENVIRONMENT="${NOTREKS_ENVIRONMENT:-$PROJECT_DIR/.venv-lrz}"

source "${PROJECT_DIR}/cluster/lrz_session_setup.sh" 2>/dev/null || true
export PATH="$ENVIRONMENT/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/cluster/slurm_logs"

manifest="$PROJECT_DIR/cluster/slurm_logs/jobfarm.env.${SLURM_JOB_ID:-manual}.txt"
{
  echo "timestamp=$(date -Is)"
  echo "host=$(hostname)"
  echo "job_id=${SLURM_JOB_ID:-unknown}"
  echo "project=$PROJECT_DIR"
  echo "cmd_file=$CMD_FILE"
  echo "environment=$ENVIRONMENT"
  echo "python=$(command -v python || true)"
  python --version 2>&1 || true
  echo "jobfarm=$(command -v jobfarm || true)"
  git rev-parse HEAD 2>/dev/null || true
  git diff --quiet 2>/dev/null && echo "git_dirty=false" || echo "git_dirty=true"
  test -r "$CMD_FILE" && sha256sum "$CMD_FILE"
  echo "command_lines=$(grep -c '^env ' "$CMD_FILE" 2>/dev/null || true)"
} > "$manifest"

test -r "$CMD_FILE" || { echo "Missing command file: $CMD_FILE" >&2; exit 2; }
command -v jobfarm >/dev/null 2>&1 || { echo "JobFarm is unavailable" >&2; exit 127; }
python -m notreks --help > "$manifest.notreks_help" 2>&1

if [[ "${RESET_JOBFARM:-0}" == "1" && -e "${CMD_FILE}_res" ]]; then
  mv -- "${CMD_FILE}_res" "${CMD_FILE}_res.archive.${SLURM_JOB_ID:-$$}"
fi

log="$PROJECT_DIR/cluster/slurm_logs/jobfarm.start.${SLURM_JOB_ID:-manual}.log"
set +e
jobfarm start "$CMD_FILE" 2>&1 | tee "$log"
jobfarm_rc=${PIPESTATUS[0]}
set -e

total=$(grep -c '^env ' "$CMD_FILE" || true)
success=0
failed=0
processed=0
shopt -s nullglob
for result in "${CMD_FILE}_res"/[0-9]*; do
  if grep -q 'STOP SUCCESS' "$result"; then
    success=$((success + 1)); processed=$((processed + 1))
  elif grep -q 'STOP FAILED' "$result"; then
    failed=$((failed + 1)); processed=$((processed + 1))
  fi
done
printf 'JobFarm markers: success=%d failed=%d processed=%d total=%d\n' \
  "$success" "$failed" "$processed" "$total"
if (( failed > 0 || processed < total )); then
  exit 1
fi
exit "$jobfarm_rc"
