"""Generate deterministic one-run-per-line JobFarm command files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex


def retry_failed_commands(command_file: Path, result_directory: Path, output: Path) -> int:
    """Write only missing, failed, or incomplete tasks to a new command file.

    JobFarm numbers result files according to their one-based command index.
    Successful tasks are deliberately omitted, so rerunning a timed-out farm
    is safe and does not duplicate completed results.
    """
    commands = [line for line in command_file.read_text().splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
    retry: list[str] = []
    for index, command in enumerate(commands, start=1):
        result = result_directory / str(index)
        if not result.is_file() or "STOP SUCCESS" not in result.read_text(errors="replace"):
            retry.append(command)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(retry) + ("\n" if retry else ""))
    return len(retry)


def write_commands(plan: Path, output: Path, output_root: Path,
                   benchpress_root: Path, python: Path, project_root: Path, *, attempts: int | None = None,
                   start: int = 0, limit: int | None = None,
                   backend: str = "benchpress", flop_sweeps: int = 16,
                   dagma_stages: int = 5, dagma_warm_iter: int = 30_000,
                   dagma_max_iter: int = 60_000, trek_weight: float = 1.0,
                   ancestry_depth: int | None = None) -> int:
    """Write commands for a contiguous plan slice and return task count."""
    payload = json.loads(plan.read_text())
    total = len(payload["runs"])
    plan_attempts = payload.get("attempts_by_method", {})
    stop = total if limit is None else min(total, start + limit)
    if start < 0 or start > total or stop < start:
        raise ValueError("invalid task slice")
    output.parent.mkdir(parents=True, exist_ok=True)
    commands = []
    for index in range(start, stop):
        method = payload["runs"][index].get("method")
        run_attempts = attempts if attempts is not None else plan_attempts.get(method, 1)
        command = [
            "env", "PYTHONPATH=" + str(project_root / "src"),
            "OMP_NUM_THREADS=1", "MKL_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1",
            str(python), "-m", "notreks.cli", "run", str(plan), str(output_root),
            "--backend", backend,
        ]
        if backend == "benchpress":
            command += ["--benchpress-root", str(benchpress_root)]
        command += [
            "--attempts", str(run_attempts),
            "--flop-sweeps", str(flop_sweeps),
            "--dagma-stages", str(dagma_stages),
            "--dagma-warm-iter", str(dagma_warm_iter),
            "--dagma-max-iter", str(dagma_max_iter),
            "--trek-weight", str(trek_weight),
            "--start", str(index), "--limit", "1",
        ]
        if ancestry_depth is not None:
            command += ["--ancestry-depth", str(ancestry_depth)]
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
    parser.add_argument("--attempts", type=int)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--backend", choices=("benchpress", "direct"), default="benchpress")
    parser.add_argument("--flop-sweeps", type=int, default=16)
    parser.add_argument("--dagma-stages", type=int, default=5)
    parser.add_argument("--dagma-warm-iter", type=int, default=30_000)
    parser.add_argument("--dagma-max-iter", type=int, default=60_000)
    parser.add_argument("--trek-weight", type=float, default=1.0)
    parser.add_argument("--ancestry-depth", type=int)
    args = parser.parse_args(argv)
    count = write_commands(args.plan, args.output, args.output_root,
                           args.benchpress_root, args.python,
                           args.project_root,
                           attempts=args.attempts, start=args.start, limit=args.limit,
                           backend=args.backend, flop_sweeps=args.flop_sweeps,
                           dagma_stages=args.dagma_stages,
                           dagma_warm_iter=args.dagma_warm_iter,
                           dagma_max_iter=args.dagma_max_iter,
                           trek_weight=args.trek_weight,
                           ancestry_depth=args.ancestry_depth)
    print(f"wrote {count} JobFarm commands -> {args.output}")
    return 0


def retry_main(argv: list[str] | None = None) -> int:
    """CLI entry point for safe continuation after a timeout or failed task."""
    parser = argparse.ArgumentParser(prog="notreks-jobfarm-retry")
    parser.add_argument("command_file", type=Path)
    parser.add_argument("result_directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    count = retry_failed_commands(args.command_file, args.result_directory, args.output)
    print(f"wrote {count} retry commands -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
