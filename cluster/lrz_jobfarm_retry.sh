#!/usr/bin/env bash
# Retry only failed or incomplete JobFarm commands on CoolMUC-4.
# The cluster and partition are deliberately encoded here so recovery cannot
# accidentally submit a cm4_tiny job to the login/default Slurm cluster.
#SBATCH --job-name=notreks-jobfarm-retry
#SBATCH --get-user-env
#SBATCH --clusters=cm4
#SBATCH --partition=cm4_tiny
#SBATCH --qos=cm4_tiny
#SBATCH --nodes=1
#SBATCH --ntasks=17
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
#SBATCH --export=ALL
#SBATCH --mail-type=NONE

set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:?Set PROJECT_DIR to the NOTREKS checkout}"
CMD_FILE="${CMD_FILE:?Set CMD_FILE to the original JobFarm command file}"
RESULT_DIR="${RESULT_DIR:?Set RESULT_DIR to the original JobFarm result directory}"
RETRY_CMD="${RETRY_CMD:-${CMD_FILE%.cmd}.retry.cmd}"
NOTREKS_ENVIRONMENT="${NOTREKS_ENVIRONMENT:-$PROJECT_DIR/.venv-lrz}"
export PROJECT_DIR CMD_FILE RESULT_DIR RETRY_CMD NOTREKS_ENVIRONMENT

source "$PROJECT_DIR/cluster/lrz_session_setup.sh"
export PATH="$NOTREKS_ENVIRONMENT/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$PROJECT_DIR"

notreks-jobfarm-retry "$CMD_FILE" "$RESULT_DIR" "$RETRY_CMD"
count=$(grep -cve '^[[:space:]]*$' "$RETRY_CMD" || true)
if [ "$count" -eq 0 ]; then
  echo "No failed or incomplete commands remain."
  exit 0
fi

log="${RETRY_CMD%.cmd}.start.${SLURM_JOB_ID:-manual}.log"
set +e
jobfarm start "$RETRY_CMD" 2>&1 | tee "$log"
jobfarm_rc=${PIPESTATUS[0]}
set -e

result_dir="${RETRY_CMD}_res"
success=$(find "$result_dir" -maxdepth 1 -type f -regex '.*/[0-9]+' \
  -exec grep -l 'STOP SUCCESS' {} + | wc -l)
failed=$(find "$result_dir" -maxdepth 1 -type f -regex '.*/[0-9]+' \
  -exec grep -l 'STOP FAILED' {} + | wc -l)
incomplete=$(find "$result_dir" -maxdepth 1 -type f -regex '.*/[0-9]+' \
  ! -exec grep -q 'STOP SUCCESS\|STOP FAILED' {} \; | wc -l)
echo "retry_expected=$count retry_success=$success retry_failed=$failed retry_incomplete=$incomplete"
if [ "$jobfarm_rc" -ne 0 ] || [ "$success" -ne "$count" ] || [ "$failed" -ne 0 ] || [ "$incomplete" -ne 0 ]; then
  exit 1
fi
