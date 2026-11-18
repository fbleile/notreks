#!/usr/bin/env bash
# Reduced end-to-end check of every registered NOTREKS protocol family.
# Production dimensions, replicate counts, and iteration budgets are not used.
# The generated plan and command file are retained under slurm_logs for audit.
#SBATCH --job-name=notreks-protocol-smoke
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
NOTREKS_ENVIRONMENT="${NOTREKS_ENVIRONMENT:-$PROJECT_DIR/.venv-lrz}"
export PROJECT_DIR NOTREKS_ENVIRONMENT
source "$PROJECT_DIR/cluster/lrz_session_setup.sh"
export PATH="$NOTREKS_ENVIRONMENT/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$PROJECT_DIR"

suite="$PROJECT_DIR/cluster/slurm_logs/protocol-smoke.${SLURM_JOB_ID:-manual}"
mkdir -p "$suite"
python -m notreks.preflight --methods flop flop_notreks dagma dagma_notreks \
  --require-ancestor-aid > "$suite/preflight.json"
python -m notreks.cli protocol-smoke-plan "$suite" \
  --project-root "$PROJECT_DIR" --python "$NOTREKS_ENVIRONMENT/bin/python"

set +e
jobfarm start "$suite/protocol_smoke.cmd" 2>&1 | tee "$suite/jobfarm.log"
jobfarm_rc=${PIPESTATUS[0]}
set -e

command_count=$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["command_count"])' "$suite/manifest.json")
result_dir="$suite/protocol_smoke.cmd_res"
for task in $(seq 1 "$command_count"); do
  test -f "$result_dir/$task" || { echo "missing JobFarm result $task" >&2; exit 1; }
  grep -q 'STOP SUCCESS' "$result_dir/$task" || { echo "failed JobFarm task $task" >&2; cat "$result_dir/$task" >&2; exit 1; }
done

while IFS= read -r root; do
  python -m notreks.cli aggregate "$root"
done < <(python -c 'import json,sys; x=json.load(open(sys.argv[1])); print("\n".join(e["output_root"] for e in x["entries"]))' "$suite/manifest.json")

if [ "$jobfarm_rc" -ne 0 ]; then
  exit "$jobfarm_rc"
fi
echo "protocol smoke passed: $command_count JobFarm commands"
