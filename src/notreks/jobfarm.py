"""Generate deterministic one-run-per-line JobFarm command files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex


def write_commands(plan: Path, output: Path, output_root: Path,
                   benchpress_root: Path, python: Path, project_root: Path, *, attempts: int = 1,
                   start: int = 0, limit: int | None = None) -> int:
    """Write commands for a contiguous plan slice and return task count."""
    payload = json.loads(plan.read_text())
    total = len(payload["runs"])
    stop = total if limit is None else min(total, start + limit)
    if start < 0 or start > total or stop < start:
        raise ValueError("invalid task slice")
    output.parent.mkdir(parents=True, exist_ok=True)
    commands = []
    for index in range(start, stop):
        command = [
            "env", "PYTHONPATH=" + str(project_root / "src"),
            "OMP_NUM_THREADS=1", "MKL_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1",
            str(python), "-m", "notreks.cli", "run", str(plan), str(output_root),
            "--benchpress-root", str(benchpress_root), "--attempts", str(attempts),
            "--start", str(index), "--limit", "1",
        ]
        commands.append(" ".join(shlex.quote(part) for part in command))
    output.write_text("\n".join(commands) + ("\n" if commands else ""))
    return len(commands)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-jobfarm")
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("benchpress_root", type=Path)
    parser.add_argument("python", type=Path)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    count = write_commands(args.plan, args.output, args.output_root,
                           args.benchpress_root, args.python,
                           args.project_root,
                           attempts=args.attempts, start=args.start, limit=args.limit)
    print(f"wrote {count} JobFarm commands -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
