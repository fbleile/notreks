"""Canonical registry for the paper's figures, tables, and analyses.

The registry is intentionally declarative: it records the scientific input,
summary operation, and output name without embedding a second plotting engine.
This gives reviewers and future branches one place to discover how an artifact
is regenerated.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class PaperOutput:
    name: str
    kind: str
    input_artifact: str
    command: str
    notes: str


PAPER_OUTPUTS = (
    PaperOutput("main_paired_pareto", "figure", "results/main/aggregate_results.csv",
                "notreks-figure results/main/aggregate_results.csv figures/main.png --x knowledge_fraction --y SHD_cpdag --data-label auto",
                "Main synthetic paired recovery summary."),
    PaperOutput("main_ablation_rank", "figure", "results/main/aggregate_results.csv",
                "notreks-trend results/main/aggregate_results.csv figures/ablation_rank.csv",
                "Edge masking and post-selection ablation."),
    PaperOutput("chromatic_trend_flop", "figure", "results/prior-structure-chrom/aggregate_results.csv",
                "notreks-trend results/prior-structure-chrom/aggregate_results.csv figures/chromatic_flop.csv",
                "ER4 graph-clustered target-K trend for FLOP."),
    PaperOutput("chromatic_trend_dagma", "figure", "results/prior-structure-chrom/aggregate_results.csv",
                "notreks-trend results/prior-structure-chrom/aggregate_results.csv figures/chromatic_dagma.csv",
                "ER4 graph-clustered target-K trend for DAGMA."),
    PaperOutput("causalman_paired", "figure", "results/causalman-small/aggregate_results.csv",
                "notreks-figure results/causalman-small/aggregate_results.csv figures/causalman.png --x knowledge_fraction --y projected_skeleton_shd --data-label auto",
                "External CausalMan latent-projection diagnostics."),
    PaperOutput("causalassembly_paired", "figure", "results/causalassembly/aggregate_results.csv",
                "notreks-figure results/causalassembly/aggregate_results.csv figures/causalassembly.png --x knowledge_fraction --y SHD_cpdag --data-label auto",
                "External CausalAssembly paired summary."),
    PaperOutput("additional_synthetic_tests", "table", "results/*/analysis/paired_tests.csv",
                "python analysis/paired_tests.py --config configs/paper_tests.json",
                "Two-sided graph-clustered NOTREKS-versus-vanilla tests with Holm correction."),
    PaperOutput("constraint_diagnostic", "analysis", "results/constraint-diagnostics.json",
                "notreks-constraint-check --fail-on-error --output results/constraint-diagnostics.json",
                "PSTrek and exact TCC value/gradient validation."),
)


def as_json() -> list[dict[str, str]]:
    return [asdict(item) for item in PAPER_OUTPUTS]


def write_registry(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(as_json(), indent=2) + "\n")


def validate_registry(root: Path | None = None) -> list[str]:
    """Return registry errors, optionally checking input artifacts under root."""
    errors: list[str] = []
    names = [item.name for item in PAPER_OUTPUTS]
    if len(names) != len(set(names)):
        errors.append("paper-output names are not unique")
    for item in PAPER_OUTPUTS:
        if item.kind not in {"figure", "table", "analysis"}:
            errors.append(f"{item.name}: unsupported kind {item.kind!r}")
        if not item.input_artifact or not item.command or not item.notes:
            errors.append(f"{item.name}: input, command, and notes are required")
        if root is not None and not any(root.glob(item.input_artifact)):
            errors.append(f"{item.name}: missing input {item.input_artifact}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-paper-outputs")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path,
                        help="also check that registered input artifacts exist")
    args = parser.parse_args(argv)
    if args.check:
        errors = validate_registry(args.root.resolve() if args.root else None)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("paper-output registry is valid")
        return 0
    if args.output:
        write_registry(args.output)
        print(f"wrote {args.output}")
    else:
        print(json.dumps(as_json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
