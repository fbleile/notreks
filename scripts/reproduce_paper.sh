#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-reproduction}"
mkdir -p "$ROOT/plans" "$ROOT/provenance"

PYTHONPATH=src python -m notreks.catalog_planning all "$ROOT/plans/catalog_all.json"
PYTHONPATH=src python -m notreks.provenance \
  "$ROOT/provenance/environment.json" --project-root .
PYTHONPATH=src python -m notreks.release . \
  --output "$ROOT/provenance/release-audit.json" >/dev/null

find data/external/causalman/canonical data/external/causalassembly/canonical \
  -name manifest.json -print0 |
  while IFS= read -r -d '' manifest; do
    PYTHONPATH=src python -m notreks.external "$manifest" >/dev/null
    label=${manifest#data/external/}
    label=${label//\//_}
    PYTHONPATH=src python -m notreks.external_plan "$manifest" \
      "$ROOT/plans/${label%.json}.json" --name "external-${label%.json}" \
      --methods flop flop_notreks dagma dagma_notreks \
      --fractions 0 0.25 1 \
      --attempts flop:20 --attempts flop_notreks:20 \
      --attempts dagma:2 --attempts dagma_notreks:2 >/dev/null
  done

echo "paper protocol and bundled external data validated"
echo "synthetic plan: $ROOT/plans/catalog_all.json"
echo "provenance:     $ROOT/provenance/environment.json"
