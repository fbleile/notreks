"""Capture the environment needed to interpret an experiment artifact."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path
import subprocess
import sys


def collect(project_root: Path | None = None) -> dict[str, object]:
    """Collect stable interpreter, platform, package, and git information."""
    root = project_root.resolve() if project_root else None
    packages = {}
    for name in ("numpy", "scipy", "pandas", "matplotlib", "pytest", "gadjid", "flopsearch", "dagma"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": packages,
        "git": _git_info(root) if root else None,
    }


def write(path: Path, project_root: Path | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collect(project_root), indent=2, sort_keys=True) + "\n")


def _git_info(root: Path) -> dict[str, str | None]:
    def command(*args: str) -> str | None:
        try:
            return subprocess.check_output(["git", *args], cwd=root, text=True,
                                           stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    return {"commit": command("rev-parse", "HEAD"), "status": command("status", "--porcelain")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-provenance")
    parser.add_argument("output", type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args(argv)
    write(args.output, args.project_root)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
