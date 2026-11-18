#!/usr/bin/env bash
# Run the same reduced protocol-wide smoke sequentially on a local machine.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-$PROJECT_DIR/.venv-local-smoke/bin/python}"
OUTPUT="${1:-$PROJECT_DIR/results/protocol_smoke_local}"
export PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
"$PYTHON" -m notreks.cli protocol-smoke-plan "$OUTPUT" \
  --project-root "$PROJECT_DIR" --python "$PYTHON"
while IFS= read -r command; do
  [ -z "$command" ] && continue
  bash -lc "$command"
done < "$OUTPUT/protocol_smoke.cmd"
for root in "$OUTPUT"/results/*; do
  [ -d "$root" ] || continue
  case "$(basename "$root")" in exact-*) continue ;; esac
  "$PYTHON" -m notreks.cli aggregate "$root"
done
echo "protocol smoke passed: $("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["command_count"])' "$OUTPUT/manifest.json") commands"
