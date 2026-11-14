"""Preflight checks for local and cluster execution environments."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import sys
from typing import Any

from .integrations import DIRECT_METHODS


def check(*, methods: tuple[str, ...]) -> dict[str, Any]:
    """Return explicit checks without importing or running a solver."""
    checks: dict[str, Any] = {
        "python": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "backend": "direct",
        "methods": list(methods),
        "packages": {},
        "executables": {},
        "errors": [],
    }
    missing_methods = set(methods) - DIRECT_METHODS
    if missing_methods:
        checks["errors"].append(
            "backend adapters not implemented for: " + ", ".join(sorted(missing_methods)))
    packages = {"numpy": "numpy", "scipy": "scipy"}
    if any(method.startswith("flop") for method in methods):
        packages["flopsearch"] = "flopsearch"
    if any(method.startswith("dagma") for method in methods):
        packages["dagma"] = "dagma"
        packages["torch"] = "torch"
    for label, package in packages.items():
        try:
            checks["packages"][label] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            checks["packages"][label] = None
            checks["errors"].append(f"missing package: {package}")
    if any(method.startswith("flop") for method in methods):
        try:
            import flopsearch
        except ImportError:
            pass
        else:
            needs_notreks = any(
                method in {"flop_notreks", "flop-nt-edge-mask", "flop-nt-post"}
                for method in methods
            )
            if needs_notreks and not callable(getattr(flopsearch, "flop_notreks", None)):
                checks["errors"].append(
                    "installed flopsearch lacks flop_notreks; install the source-built "
                    "NOTREKS backend (vanilla FLOP is not a substitute)"
                )
    checks["executables"]["python"] = shutil.which("python") or sys.executable
    checks["executables"]["Rscript"] = shutil.which("Rscript")
    checks["ok"] = not checks["errors"]
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-preflight")
    parser.add_argument("--methods", nargs="+", default=["flop_notreks"])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = check(methods=tuple(args.methods))
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
