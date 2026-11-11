"""Execution artifacts shared by local and cluster experiment stages.

The numerical stages should only depend on this module for identity and
checkpointing.  Keeping those concerns here prevents small differences between
local smoke runs and distributed production runs.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import traceback
from typing import Any, Iterator

from .protocol import RunSpec


STAGES = ("definition", "data", "knowledge", "solve", "evaluate", "figure")


def utc_now() -> str:
    """Return a sortable, timezone-explicit timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON through a sibling temporary file so checkpoints are complete."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


@dataclass(frozen=True)
class SeedBook:
    """Derive reproducible, independent integer seeds from one master seed."""

    master: int

    def derive(self, namespace: str, *parts: object) -> int:
        encoded = "|".join((str(self.master), namespace, *(str(p) for p in parts)))
        digest = hashlib.blake2b(encoded.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % (2**32 - 1)


@dataclass(frozen=True)
class RunDirectory:
    """Canonical artifact locations for one run."""

    root: Path

    def stage(self, name: str) -> Path:
        if name not in STAGES:
            raise ValueError(f"unknown stage {name!r}; expected one of {STAGES}")
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def manifest(self) -> Path:
        return self.root / "run.json"

    @property
    def status(self) -> Path:
        return self.root / "status.json"


class RunRecorder(AbstractContextManager["RunRecorder"]):
    """Record lifecycle and traceback information for one execution unit.

    A failed worker always leaves a machine-readable ``status.json`` and a
    human-readable ``error.txt``.  The context manager deliberately re-raises
    exceptions so job farms and shell callers still receive a non-zero status.
    """

    def __init__(self, directory: RunDirectory, run: RunSpec, *, command: list[str] | None = None):
        self.directory = directory
        self.run = run
        self.command = command or []

    def __enter__(self) -> "RunRecorder":
        self.directory.root.mkdir(parents=True, exist_ok=True)
        atomic_json(self.directory.manifest, self.run.to_dict())
        atomic_json(self.directory.status, {
            "run_key": self.run.key(),
            "state": "running",
            "started_at": utc_now(),
            "command": self.command,
        })
        return self

    def __exit__(self, exception_type, exception, tb) -> bool:
        if exception is None:
            atomic_json(self.directory.status, {
                "run_key": self.run.key(),
                "state": "succeeded",
                "finished_at": utc_now(),
                "command": self.command,
            })
            return False

        formatted = "".join(traceback.format_exception(exception_type, exception, tb))
        (self.directory.root / "error.txt").write_text(formatted)
        atomic_json(self.directory.status, {
            "run_key": self.run.key(),
            "state": "failed",
            "finished_at": utc_now(),
            "command": self.command,
            "error_type": exception_type.__name__ if exception_type else "Exception",
            "error": str(exception),
        })
        return False


def iter_run_directories(root: Path) -> Iterator[RunDirectory]:
    """Yield only directories with a complete run manifest."""
    if not root.exists():
        return
    for manifest in sorted(root.glob("*/run.json")):
        yield RunDirectory(manifest.parent)


def main() -> None:
    """Print the deterministic seed used by the module smoke test."""
    print(SeedBook(20260917).derive("data", "graph-00", 500))


if __name__ == "__main__":
    main()
