"""Build a small, protocol-wide execution plan.

The smoke suite is deliberately separate from the production catalog.  It
keeps one representative graph, dataset, knowledge level, and solver path for
each registered experiment family while reducing dimensions, replicates, and
optimization budgets.  The resulting JSON plans and shell commands are
ordinary NOTREKS artifacts, so the same files can be inspected, run locally,
or submitted through JobFarm.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shlex

from .planning import expand_protocol, external_plan, write_plan
from .protocol import ProtocolSpec


METHODS = (
    "flop", "flop_notreks", "flop-nt-edge-mask", "flop-nt-post",
    "dagma", "dagma_notreks", "dagma-nt-edge-mask", "dagma-nt-post",
    "var_sortnregress", "r2_sortnregress",
)
SOLVER_METHODS = ("flop", "flop_notreks", "dagma", "dagma_notreks")


def _attempts(methods: tuple[str, ...]) -> dict[str, int]:
    return {method: 1 for method in methods}


def _protocol(name: str, model: str, *, methods: tuple[str, ...] = METHODS,
              families: tuple[str, ...] = ("er", "ws"),
              fractions: tuple[float, ...] = (0.0, 0.25),
              target_k: tuple[int, ...] = (),
              strategies: tuple[str, ...] = ("random",)) -> ProtocolSpec:
    return ProtocolSpec(
        name=name, dimensions=(6,), sample_sizes=(32,),
        graph_families=families, densities=(2,), methods=methods,
        knowledge_fractions=fractions, knowledge_strategies=strategies,
        target_k_values=target_k, infeasible_policy="skip", partial_rounds=1,
        graph_replicates=1, method_attempts=_attempts(methods),
    )


def _external_plan(manifest: Path, name: str, methods: tuple[str, ...],
                   fractions: tuple[float, ...], seed: int) -> dict[str, object]:
    return external_plan(manifest.resolve(), name=name, methods=methods,
                         fractions=fractions, partial_rounds=1,
                         attempts=_attempts(methods), master_seed=seed)


def build_protocol_smoke(output: Path, *, project_root: Path,
                         python: Path, master_seed: int = 20260917) -> dict[str, object]:
    """Write all smoke plans and one executable command file."""
    output = output.resolve()
    plans = output / "plans"
    results = output / "results"
    plans.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []

    synthetic = (
        ("main", "linear_gaussian"),
        ("main-misspec-linear-nongaussian", "linear_nongaussian"),
        ("main-misspec-nonlinear-gaussian", "nonlinear_gaussian"),
    )
    for name, model in synthetic:
        spec = _protocol(name, model)
        path = plans / f"{name}.json"
        runs = expand_protocol(spec, data_model=model, master_seed=master_seed)
        write_plan(path, spec, runs, master_seed=master_seed)
        entries.append({"name": name, "kind": "synthetic", "plan": str(path),
                        "output_root": str(results / name), "run_count": len(runs)})

    chrom = _protocol("prior-structure-chrom", "linear_gaussian",
                      methods=SOLVER_METHODS, families=("er", "ws"),
                      fractions=(0.0, 0.25), target_k=(2,), strategies=("random", "target-k"))
    chrom_path = plans / "prior-structure-chrom.json"
    runs = expand_protocol(chrom, data_model="linear_gaussian", master_seed=master_seed)
    write_plan(chrom_path, chrom, runs, master_seed=master_seed)
    entries.append({"name": chrom.name, "kind": "chromatic", "plan": str(chrom_path),
                    "output_root": str(results / chrom.name), "run_count": len(runs)})

    tcc = _protocol("pstrek-vs-tcc", "linear_gaussian", methods=(
        "dagma", "dagma_notreks", "dagma_tcc"), families=("er",),
        fractions=(0.0, 0.25, 1.0))
    tcc_path = plans / "pstrek-vs-tcc.json"
    runs = expand_protocol(tcc, data_model="linear_gaussian", master_seed=master_seed)
    write_plan(tcc_path, tcc, runs, master_seed=master_seed)
    entries.append({"name": tcc.name, "kind": "constraint-comparison", "plan": str(tcc_path),
                    "output_root": str(results / tcc.name), "run_count": len(runs)})

    external_specs = (
        ("causalman-small", project_root / "data/external/causalman/canonical/causalman_small/seed_1001/manifest.json"),
        ("causalman-medium", project_root / "data/external/causalman/canonical/causalman_medium/seed_1001/manifest.json"),
        ("causalassembly", project_root / "data/external/causalassembly/canonical/seed_1001/manifest.json"),
    )
    for name, manifest in external_specs:
        if not manifest.is_file():
            raise FileNotFoundError(f"protocol smoke requires bundled manifest: {manifest}")
        payload = _external_plan(manifest, name, SOLVER_METHODS, (0.0, 0.25), master_seed)
        path = plans / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        entries.append({"name": name, "kind": "external", "plan": str(path),
                        "output_root": str(results / name), "run_count": payload["run_count"]})

    exact_commands = [
        ["env", f"PYTHONPATH={project_root / 'src'}", str(python), "-m", "notreks.exact", "--dimension", "5", "--pair-budgets", "2",
         "--target-K", "2", "--sets-per-cell", "1", "--output", str(results / "exact-feasibility-pilot")],
        ["env", f"PYTHONPATH={project_root / 'src'}", str(python), "-m", "notreks.exact_bic", "--dimension", "5", "--sample-size", "32",
         "--output", str(results / "exact-bic")],
        ["env", f"PYTHONPATH={project_root / 'src'}", str(python), "-m", "notreks.exact_bic_dp", "--dimension", "6", "--sample-size", "32",
         "--output", str(results / "exact-bic-dp")],
    ]
    commands: list[str] = []
    low_budget = ("--attempts", "1", "--flop-sweeps", "2", "--dagma-stages", "1",
                  "--dagma-warm-iter", "20", "--dagma-max-iter", "40")
    for entry in entries:
        payload = json.loads(Path(str(entry["plan"])).read_text())
        for index in range(int(payload["run_count"])):
            commands.append(" ".join(shlex.quote(part) for part in (
                "env", f"PYTHONPATH={project_root / 'src'}", "OMP_NUM_THREADS=1",
                "MKL_NUM_THREADS=1", "OPENBLAS_NUM_THREADS=1", str(python), "-m",
                "notreks.cli", "run", str(entry["plan"]), str(entry["output_root"]),
                *low_budget, "--start", str(index), "--limit", "1")))
    commands.extend(" ".join(shlex.quote(part) for part in command) for command in exact_commands)
    command_file = output / "protocol_smoke.cmd"
    command_file.write_text("\n".join(commands) + "\n")
    manifest = {
        "suite": "protocol-smoke", "master_seed": master_seed,
        "reduction": {"dimensions": [6], "sample_sizes": [32], "graph_replicates": 1,
                       "partial_rounds": 1, "attempts": 1, "flop_sweeps": 2,
                       "dagma_stages": 1, "dagma_warm_iter": 20, "dagma_max_iter": 40},
        "entries": entries, "exact_entries": ["exact-feasibility-pilot", "exact-bic", "exact-bic-dp"],
        "command_file": str(command_file), "command_count": len(commands),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-protocol-smoke")
    parser.add_argument("output", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--python", type=Path)
    parser.add_argument("--master-seed", type=int, default=20260917)
    args = parser.parse_args(argv)
    python = args.python or Path(__import__("sys").executable)
    manifest = build_protocol_smoke(args.output, project_root=args.project_root,
                                    python=python, master_seed=args.master_seed)
    print(f"planned {manifest['command_count']} protocol-smoke commands -> {manifest['command_file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
