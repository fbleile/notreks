"""Focused entry point for manifest-backed external plans."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .planning import external_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-external-plan")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--methods", nargs="+", required=True)
    parser.add_argument("--fractions", nargs="+", type=float, default=[0.0, 0.25, 1.0])
    parser.add_argument("--partial-rounds", type=int, default=5)
    parser.add_argument("--master-seed", type=int, default=20260917)
    parser.add_argument("--attempts", action="append", default=[],
                        help="method:n; repeat for method-specific budgets")
    args = parser.parse_args(argv)
    attempts = {}
    for specification in args.attempts:
        try:
            method, count = specification.rsplit(":", 1)
            if not method or method in attempts:
                raise ValueError
            attempts[method] = int(count)
        except ValueError as error:
            raise SystemExit("--attempts must use unique method:n specifications") from error
    payload = external_plan(args.manifest, name=args.name,
                            methods=tuple(args.methods), fractions=tuple(args.fractions),
                            partial_rounds=args.partial_rounds, attempts=attempts or None,
                            master_seed=args.master_seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"planned {payload['run_count']} runs -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
