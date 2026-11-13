"""Executable release-artifact audit for the NOTREKS repository."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from typing import Any

from .inspect import inspect_output


REQUIRED_FILES = (
    "README.md", "LICENSE", "CITATION.cff", "CHANGELOG.md",
    "docs/experimental_protocol.md", "docs/solver_porting.md",
    "docs/release.md", "docs/release_checklist.md",
    "data/external/THIRD_PARTY_NOTICES.md", "pyproject.toml",
    "environment.yml", "Makefile", "scripts/reproduce_paper.sh",
    ".github/workflows/test.yml", "cluster/lrz_session_setup.sh",
    "cluster/lrz_jobfarm.sh", "cluster/lrz_jobfarm_smoke.sh",
)

REQUIRED_EXPERIMENTS = (
    "main", "main-misspec-linear-nongaussian",
    "main-misspec-nonlinear-gaussian", "prior-structure-chrom",
    "pstrek-vs-tcc", "causalman-small", "causalman-medium",
    "causalassembly", "exact-feasibility-pilot",
)


def audit(root: Path, result_root: Path | None = None) -> dict[str, Any]:
    """Return a machine-readable release audit without modifying the repository."""
    root = root.resolve()
    missing = [path for path in REQUIRED_FILES if not (root / path).is_file()]
    manifests = sorted((root / "data/external").glob("**/canonical/**/manifest.json"))
    manifest_errors = []
    nonportable_manifest_paths = []
    for manifest in manifests:
        try:
            from .external import ExternalDataset
            dataset = ExternalDataset.from_manifest(manifest)
            dataset.validate_arrays()
            dataset.available_pairs(len(dataset.nodes))
        except Exception as error:  # audit output should identify every bad artifact
            manifest_errors.append({"path": str(manifest), "error": f"{type(error).__name__}: {error}"})
        try:
            payload = json.loads(manifest.read_text())
            for key, value in _string_values(payload):
                if value.startswith("/") or "/tmp/" in value:
                    nonportable_manifest_paths.append({
                        "path": str(manifest), "field": key, "value": value,
                    })
        except (OSError, json.JSONDecodeError):
            pass
    catalog_names = _catalog_names()
    missing_experiments = [name for name in REQUIRED_EXPERIMENTS if name not in catalog_names]
    report: dict[str, Any] = {
        "root": str(root),
        "git_commit": _git(root, "rev-parse", "HEAD"),
        "git_status": _git(root, "status", "--porcelain"),
        "missing_required_files": missing,
        "canonical_manifests": len(manifests),
        "manifest_errors": manifest_errors,
        "nonportable_manifest_paths": nonportable_manifest_paths,
        "catalog_experiments": catalog_names,
        "missing_catalog_experiments": missing_experiments,
    }
    if result_root is not None:
        report["results"] = inspect_output(result_root.resolve())
        report["result_archive"] = {
            "aggregate_results": (result_root / "aggregate_results.csv").is_file(),
            "aggregate_issues": (result_root / "aggregate_issues.csv").is_file(),
        }
    report["ok"] = not missing and not manifest_errors and not nonportable_manifest_paths and not missing_experiments
    if result_root is not None:
        report["ok"] = bool(report["ok"] and report["result_archive"]["aggregate_results"])
    return report


def _string_values(value: Any, prefix: str = ""):
    """Yield JSON string leaves with their field paths."""
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _string_values(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _string_values(child, f"{prefix}[{index}]")
    elif isinstance(value, str):
        yield prefix, value


def _catalog_names() -> list[str]:
    try:
        from .catalog import CATALOG
        return sorted(CATALOG)
    except Exception:
        return []


def _git(root: Path, *args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=root, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-release-audit")
    parser.add_argument("root", type=Path)
    parser.add_argument("--results-root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = audit(args.root, args.results_root)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
