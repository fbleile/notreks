"""Audit the external solver closure before and during kernel migration."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any


SOLVER_MODULE = "workflow.rules.structure_learning_algorithms.dagma_global_search.tools.systematic_notreks_d20_benchmark"
REQUIRED_SYMBOLS = ("vanilla_flop_candidate", "flop_notreks_candidate", "dagma_candidate")


def audit(repository: Path) -> dict[str, Any]:
    """Import the validated adapter closure and record its source provenance."""
    repository = repository.resolve()
    if not (repository / "workflow").is_dir():
        raise ValueError(f"not a Benchpress checkout: {repository}")
    import sys
    if str(repository) not in sys.path:
        sys.path.insert(0, str(repository))
    module = importlib.import_module(SOLVER_MODULE)
    symbols = {}
    for name in REQUIRED_SYMBOLS:
        function = getattr(module, name, None)
        if function is None:
            raise RuntimeError(f"missing required solver symbol: {name}")
        source = Path(function.__code__.co_filename).resolve()
        symbols[name] = {"source": str(source), "sha256": _sha256(source)}
    packages = {}
    for name in ("numpy", "scipy", "flopsearch", "dagma"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"repository": str(repository), "module": SOLVER_MODULE,
            "symbols": symbols, "packages": packages}


def write(path: Path, repository: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit(repository), indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-solver-audit")
    parser.add_argument("repository", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    write(args.output, args.repository)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
