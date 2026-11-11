"""Generate the checked-in protocol manifest used by local and cluster tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .catalog import CATALOG
from .experiment import STAGES


SCHEMA_VERSION = "1"
METHOD_LABELS = {
    "flop": "FLOP",
    "flop_notreks": "FLOP+NOTREKS",
    "dagma": "DAGMA",
    "dagma_notreks": "DAGMA+PSTrek",
    "dagma_tcc": "DAGMA+TCC",
}


def build_manifest() -> dict[str, Any]:
    """Return a deterministic manifest; timestamps are intentionally omitted."""
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "project": "notreks",
        "stages": list(STAGES),
        "method_labels": METHOD_LABELS,
        "artifact_contract": {
            "run_manifest": "runs/<run_key>/run.json",
            "stage_status": "runs/<run_key>/<stage>/status.json",
            "traceback": "runs/<run_key>/<stage>/error.txt",
            "shared_graph": "shared/<data_id>/graph.npy",
            "shared_data": "shared/<data_id>/data.npy",
            "knowledge": "shared/<data_id>/knowledge/*.json",
            "solver_output": "runs/<run_key>/solve/adjacency.npy",
            "aggregate_results": "aggregate_results.csv",
            "aggregate_issues": "aggregate_issues.csv",
        },
        "experiments": {name: definition.to_dict() for name, definition in sorted(CATALOG.items())},
    }
    # Dataclass tuples are excellent in Python but JSON has one sequence type;
    # normalize once here so in-memory and on-disk manifests are identical.
    return json.loads(json.dumps(manifest))


def write_manifest(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-manifest")
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    write_manifest(args.output)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
