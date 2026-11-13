#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-reproduction}"
mkdir -p "$ROOT/plans" "$ROOT/provenance"

PYTHONPATH=src python -m notreks.catalog_planning all "$ROOT/plans/catalog_all.json"
PYTHONPATH=src python -m notreks.provenance \
  "$ROOT/provenance/environment.json" --project-root .

find data/external/causalman/canonical data/external/causalassembly/canonical \
  -name manifest.json -print0 |
  while IFS= read -r -d '' manifest; do
    PYTHONPATH=src python -m notreks.external "$manifest" >/dev/null
  done

echo "paper protocol and bundled external data validated"
echo "synthetic plan: $ROOT/plans/catalog_all.json"
echo "provenance:     $ROOT/provenance/environment.json"
