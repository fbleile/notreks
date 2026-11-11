"""Command-line entry point for planning and executing NOTREKS stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .aggregate import collect, write_tables
from .integrations import register_benchpress
from .figures import load_rows, plot_mean_sd
from .jobfarm import write_commands
from .manifest import write_manifest
from .provenance import write as write_provenance
from .planning import PlanSelection, expand_protocol, write_plan
from .protocol import ProtocolSpec, RunSpec
from .runner import prepare_run, solve_prepared
from .solvers import SolverConfig, SolverRegistry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks")
    commands = parser.add_subparsers(dest="command", required=True)
    plan_parser = commands.add_parser("plan", help="expand a protocol JSON into a run plan")
    plan_parser.add_argument("protocol", type=Path)
    plan_parser.add_argument("output", type=Path)
    plan_parser.add_argument("--master-seed", type=int, default=20260917)
    plan_parser.add_argument("--graph-start", type=int, default=0)
    plan_parser.add_argument("--graph-limit", type=int)
    prepare_parser = commands.add_parser("prepare", help="generate graph/data/knowledge artifacts")
    prepare_parser.add_argument("plan", type=Path)
    prepare_parser.add_argument("output_root", type=Path)
    _slice_arguments(prepare_parser)
    solve_parser = commands.add_parser("solve", help="run registered solvers for planned runs")
    solve_parser.add_argument("plan", type=Path)
    solve_parser.add_argument("output_root", type=Path)
    solve_parser.add_argument("--benchpress-root", type=Path, required=True)
    solve_parser.add_argument("--attempts", type=int, default=1)
    _slice_arguments(solve_parser)
    run_parser = commands.add_parser("run", help="prepare and solve planned runs")
    run_parser.add_argument("plan", type=Path)
    run_parser.add_argument("output_root", type=Path)
    run_parser.add_argument("--benchpress-root", type=Path, required=True)
    run_parser.add_argument("--attempts", type=int, default=1)
    _slice_arguments(run_parser)
    aggregate_parser = commands.add_parser("aggregate", help="evaluate completed runs")
    aggregate_parser.add_argument("output_root", type=Path)
    manifest_parser = commands.add_parser("manifest", help="write the protocol manifest")
    manifest_parser.add_argument("output", type=Path)
    jobfarm_parser = commands.add_parser("jobfarm", help="generate JobFarm commands")
    jobfarm_parser.add_argument("plan", type=Path)
    jobfarm_parser.add_argument("output", type=Path)
    jobfarm_parser.add_argument("output_root", type=Path)
    jobfarm_parser.add_argument("benchpress_root", type=Path)
    jobfarm_parser.add_argument("python", type=Path)
    jobfarm_parser.add_argument("project_root", type=Path)
    jobfarm_parser.add_argument("--attempts", type=int, default=1)
    jobfarm_parser.add_argument("--start", type=int, default=0)
    jobfarm_parser.add_argument("--limit", type=int)
    figure_parser = commands.add_parser("figure", help="plot grouped means and standard deviations")
    figure_parser.add_argument("input", type=Path)
    figure_parser.add_argument("output", type=Path)
    figure_parser.add_argument("--x", required=True)
    figure_parser.add_argument("--y", required=True)
    figure_parser.add_argument("--group", default="method")
    figure_parser.add_argument("--data-label", default="")
    figure_parser.add_argument("--title")
    provenance_parser = commands.add_parser("provenance", help="record environment provenance")
    provenance_parser.add_argument("output", type=Path)
    provenance_parser.add_argument("--project-root", type=Path)
    commands.add_parser("smoke", help="run the dependency-light local smoke")
    args = parser.parse_args(argv)
    if args.command == "plan":
        return _plan(args)
    if args.command == "prepare":
        return _execute(args, solve=False)
    if args.command in {"solve", "run"}:
        return _execute(args, solve=args.command == "solve" or args.command == "run")
    if args.command == "aggregate":
        results, issues = collect(args.output_root)
        write_tables(args.output_root, results, issues)
        print(f"results={len(results)} issues={len(issues)}")
        return 0 if not issues else 2
    if args.command == "manifest":
        write_manifest(args.output)
        print(f"wrote {args.output}")
        return 0
    if args.command == "jobfarm":
        count = write_commands(args.plan, args.output, args.output_root,
                               args.benchpress_root, args.python,
                               args.project_root,
                               attempts=args.attempts, start=args.start,
                               limit=args.limit)
        print(f"wrote {count} JobFarm commands -> {args.output}")
        return 0
    if args.command == "figure":
        plot_mean_sd(load_rows(args.input), args.output, x=args.x, y=args.y,
                     group=args.group, data_label=args.data_label, title=args.title)
        print(f"wrote {args.output}")
        return 0
    if args.command == "provenance":
        write_provenance(args.output, args.project_root)
        print(f"wrote {args.output}")
        return 0
    _smoke()
    return 0


def _plan(args: argparse.Namespace) -> int:
    spec = _load_protocol(args.protocol)
    runs = expand_protocol(spec, master_seed=args.master_seed, selection=PlanSelection(
        graph_start=args.graph_start, graph_limit=args.graph_limit))
    write_plan(args.output, spec, runs, master_seed=args.master_seed)
    print(f"planned {len(runs)} runs -> {args.output}")
    return 0


def _execute(args: argparse.Namespace, *, solve: bool) -> int:
    payload = json.loads(args.plan.read_text())
    runs = [RunSpec(**{key: value for key, value in item.items() if key != "run_key"})
            for item in payload["runs"]]
    selected = runs[args.start: args.start + args.limit if args.limit is not None else None]
    registry = SolverRegistry()
    if solve:
        register_benchpress(registry, args.benchpress_root)
    config = SolverConfig(attempts=getattr(args, "attempts", 1))
    for run in selected:
        artifacts = prepare_run(run, args.output_root)
        if solve:
            solve_prepared(artifacts, run, registry, config)
        print(f"completed {run.key()} method={run.method}", flush=True)
    return 0


def _load_protocol(path: Path) -> ProtocolSpec:
    values = json.loads(path.read_text())
    return ProtocolSpec(
        **{key: tuple(value) if key in {"dimensions", "sample_sizes", "graph_families", "densities", "methods", "knowledge_fractions"} else value
           for key, value in values.items()})


def _slice_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int)


def _smoke() -> None:
    from tempfile import TemporaryDirectory
    from .planning import expand_protocol
    from .protocol import ProtocolSpec

    spec = ProtocolSpec("smoke", (6,), (16,), ("er",), (2,), ("flop",), graph_replicates=1)
    with TemporaryDirectory() as directory:
        prepare_run(expand_protocol(spec)[0], Path(directory))
        print("NOTREKS CLI smoke passed")


if __name__ == "__main__":
    raise SystemExit(main())
