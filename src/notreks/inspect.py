"""Fast, dependency-free audit of a NOTREKS output directory."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def inspect_output(root: Path) -> dict[str, Any]:
    """Summarize run and stage states without reading result tables."""
    runs = sorted((root / "runs").glob("*/run.json"))
    run_states = Counter()
    stage_states: dict[str, Counter[str]] = {}
    errors = []
    for manifest in runs:
        run_root = manifest.parent
        status_path = run_root / "status.json"
        state = "missing_status"
        if status_path.is_file():
            try:
                state = str(json.loads(status_path.read_text()).get("state", "unknown"))
            except json.JSONDecodeError:
                state = "invalid_status"
        run_states[state] += 1
        for stage_dir in sorted(path for path in run_root.iterdir() if path.is_dir()):
            status = stage_dir / "status.json"
            stage_state = "missing_status"
            if status.is_file():
                try:
                    stage_state = str(json.loads(status.read_text()).get("state", "unknown"))
                except json.JSONDecodeError:
                    stage_state = "invalid_status"
            stage_states.setdefault(stage_dir.name, Counter())[stage_state] += 1
            error_file = stage_dir / "error.txt"
            if error_file.is_file():
                errors.append({"run_key": manifest.parent.name, "stage": stage_dir.name,
                               "path": str(error_file)})
        root_error = run_root / "error.txt"
        if root_error.is_file():
            errors.append({"run_key": manifest.parent.name, "stage": "run", "path": str(root_error)})
    return {
        "root": str(root.resolve()),
        "runs": len(runs),
        "run_states": dict(sorted(run_states.items())),
        "stage_states": {name: dict(sorted(states.items()))
                         for name, states in sorted(stage_states.items())},
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-inspect")
    parser.add_argument("root", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    report = inspect_output(args.root)
    if args.as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"root: {report['root']}")
        print(f"runs: {report['runs']}")
        print(f"run states: {report['run_states'] or '{}'}")
        for stage, states in report["stage_states"].items():
            print(f"stage {stage}: {states}")
        print(f"tracebacks: {len(report['errors'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
