#!/usr/bin/env bash
# Four-task cluster regression before a production or protocol-smoke retry.
# It checks concurrent WS preparation plus both bundled external-plan paths.
#SBATCH --job-name=notreks-regression
#SBATCH --get-user-env
#SBATCH --clusters=cm4
#SBATCH --partition=cm4_tiny
#SBATCH --qos=cm4_tiny
#SBATCH --nodes=1
#SBATCH --ntasks=17
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --export=ALL
#SBATCH --mail-type=NONE

set -euo pipefail
PROJECT_DIR="${PROJECT_DIR:?Set PROJECT_DIR to the NOTREKS checkout}"
NOTREKS_ENVIRONMENT="${NOTREKS_ENVIRONMENT:-$PROJECT_DIR/.venv-lrz}"
NOTREKS_RSCRIPT="${NOTREKS_RSCRIPT:-$NOTREKS_ENVIRONMENT/bin/Rscript}"
export PROJECT_DIR NOTREKS_ENVIRONMENT NOTREKS_RSCRIPT
source "$PROJECT_DIR/cluster/lrz_session_setup.sh"
export PATH="$NOTREKS_ENVIRONMENT/bin:$PATH"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$PROJECT_DIR"

suite="$PROJECT_DIR/cluster/slurm_logs/regression.${SLURM_JOB_ID:-manual}"
mkdir -p "$suite/plans" "$suite/results"
python -m notreks.preflight --methods flop flop_notreks --require-ancestor-aid > "$suite/preflight.json"

python -m notreks.cli plan examples/cluster_regression_protocol.json \
  "$suite/plans/ws.json"
notreks-external-plan \
  data/external/causalman/canonical/causalman_small/seed_1001/manifest.json \
  "$suite/plans/causalman.json" --name regression-causalman \
  --methods flop --fractions 0.25 --partial-rounds 1 --attempts flop:1
notreks-external-plan \
  data/external/causalassembly/canonical/seed_1001/manifest.json \
  "$suite/plans/causalassembly.json" --name regression-causalassembly \
  --methods flop --fractions 0.25 --partial-rounds 1 --attempts flop:1

notreks-jobfarm "$suite/plans/ws.json" "$suite/ws.cmd" "$suite/results/ws" \
  "$NOTREKS_ENVIRONMENT/bin/python" "$PROJECT_DIR" --attempts 1 \
  --flop-sweeps 2 --dagma-stages 1 --dagma-warm-iter 20 --dagma-max-iter 40
notreks-jobfarm "$suite/plans/causalman.json" "$suite/causalman.cmd" "$suite/results/causalman" \
  "$NOTREKS_ENVIRONMENT/bin/python" "$PROJECT_DIR" --attempts 1 \
  --flop-sweeps 2 --dagma-stages 1 --dagma-warm-iter 20 --dagma-max-iter 40
notreks-jobfarm "$suite/plans/causalassembly.json" "$suite/causalassembly.cmd" "$suite/results/causalassembly" \
  "$NOTREKS_ENVIRONMENT/bin/python" "$PROJECT_DIR" --attempts 1 \
  --flop-sweeps 2 --dagma-stages 1 --dagma-warm-iter 20 --dagma-max-iter 40

python - "$suite" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
commands = []
for path in sorted(root.glob("*.cmd")):
    commands.extend(line for line in path.read_text().splitlines() if line.strip())
(root / "regression.cmd").write_text("\n".join(commands) + "\n")
(root / "manifest.json").write_text(
    '{"expected_commands": %d, "suite": "cluster-regression"}\n' % len(commands))
PY

set +e
jobfarm start "$suite/regression.cmd" 2>&1 | tee "$suite/jobfarm.log"
jobfarm_rc=${PIPESTATUS[0]}
set -e

for task in $(seq 1 4); do
  test -f "$suite/regression.cmd_res/$task"
  grep -q 'STOP SUCCESS' "$suite/regression.cmd_res/$task"
done
for root in "$suite"/results/*; do
  python -m notreks.cli aggregate "$root"
done
test "$jobfarm_rc" -eq 0
echo "cluster regression passed"
