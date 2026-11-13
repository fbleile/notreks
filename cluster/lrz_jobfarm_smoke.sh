#!/usr/bin/env bash
# A deliberately small node-level LRZ check before submitting a production farm.
# It exercises the checkout, environment, JobFarm, one worker, and one solver.
#SBATCH --job-name=notreks-smoke
#SBATCH --get-user-env
#SBATCH --clusters=cm4
#SBATCH --partition=cm4_tiny
#SBATCH --qos=cm4_tiny
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --time=00:15:00
#SBATCH --export=ALL
#SBATCH --mail-type=NONE

set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:?Set PROJECT_DIR to the NOTREKS checkout}"
CMD_FILE="${CMD_FILE:-$PROJECT_DIR/cluster/notreks_cluster_smoke.cmd}"
NOTREKS_ENVIRONMENT="${NOTREKS_ENVIRONMENT:-$PROJECT_DIR/.venv-lrz}"
SMOKE_PLAN="${SMOKE_PLAN:-$PROJECT_DIR/cluster/slurm_logs/smoke.plan.${SLURM_JOB_ID:-manual}.json}"
export PROJECT_DIR CMD_FILE NOTREKS_ENVIRONMENT SMOKE_PLAN

source "$PROJECT_DIR/cluster/lrz_session_setup.sh" 2>/dev/null || true
export PATH="$NOTREKS_ENVIRONMENT/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$PROJECT_DIR"
mkdir -p "$PROJECT_DIR/cluster/slurm_logs"

"$NOTREKS_ENVIRONMENT/bin/python" -m notreks.cli plan \
  "$PROJECT_DIR/examples/smoke_protocol.json" "$SMOKE_PLAN" --graph-limit 1

manifest="$PROJECT_DIR/cluster/slurm_logs/jobfarm-smoke.env.${SLURM_JOB_ID:-manual}.txt"
{
  echo "timestamp=$(date -Is)"
  echo "host=$(hostname)"
  echo "job_id=${SLURM_JOB_ID:-unknown}"
  echo "project=$PROJECT_DIR"
  echo "cmd_file=$CMD_FILE"
  echo "environment=$NOTREKS_ENVIRONMENT"
  echo "smoke_plan=$SMOKE_PLAN"
  echo "python=$(command -v python || true)"
  python --version 2>&1 || true
  git rev-parse HEAD 2>/dev/null || true
  git diff --quiet 2>/dev/null && echo "git_dirty=false" || echo "git_dirty=true"
  sha256sum "$CMD_FILE"
  sha256sum "$SMOKE_PLAN"
} > "$manifest"

test -r "$CMD_FILE"
command -v jobfarm >/dev/null 2>&1
python -m notreks --help > "$manifest.notreks_help" 2>&1

log="$PROJECT_DIR/cluster/slurm_logs/jobfarm-smoke.start.${SLURM_JOB_ID:-manual}.log"
set +e
jobfarm start "$CMD_FILE" 2>&1 | tee "$log"
jobfarm_rc=${PIPESTATUS[0]}
set -e

result_dir="${CMD_FILE}_res"
if ! grep -q 'STOP SUCCESS' "$result_dir/1"; then
  echo "Smoke task failed; inspect $result_dir/1 and $log" >&2
  exit 1
fi
exit "$jobfarm_rc"
