"""Collect completed run artifacts into auditable analysis tables."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .cpdag import CPDAGError
from .evaluation import causalman_metrics, synthetic_metrics
from .runner import stage


def collect(output_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return result rows and a separate report for failed/incomplete runs."""
    results: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for run_json in sorted((output_root / "runs").glob("*/run.json")):
        run_root = run_json.parent
        run = json.loads(run_json.read_text())
        solve_status = run_root / "solve" / "status.json"
        if not solve_status.exists():
            issues.append({"run_key": run["run_key"], "state": "incomplete", "path": str(run_root)})
            continue
        status = json.loads(solve_status.read_text())
        if status.get("state") != "succeeded":
            issues.append({"run_key": run["run_key"], "state": status.get("state", "unknown"),
                           "path": str(run_root)})
            continue
        try:
            with stage(run_root, "evaluate"):
                row = _evaluate_run(output_root, run_root, run)
        except Exception as error:
            issues.append({"run_key": run["run_key"], "state": "evaluation_failed",
                           "error": f"{type(error).__name__}: {error}", "path": str(run_root)})
        else:
            results.append(row)
    return results, issues


def write_tables(output_root: Path, results: list[dict[str, Any]], issues: list[dict[str, Any]]) -> None:
    """Write stable CSV tables with a fixed union of columns."""
    output_root.mkdir(parents=True, exist_ok=True)
    _write_csv(output_root / "aggregate_results.csv", results)
    _write_csv(output_root / "aggregate_issues.csv", issues)


def _evaluate_run(output_root: Path, run_root: Path, run: dict[str, Any]) -> dict[str, Any]:
    shared = output_root / "shared" / run["data_id"]
    estimate = np.load(run_root / "solve" / "adjacency.npy")
    if run["data_model"].endswith("_observational"):
        metadata_path = shared / "external.json"
        if not metadata_path.exists():
            raise RuntimeError(f"missing external dataset metadata: {metadata_path}")
        metadata = json.loads(metadata_path.read_text())
        if metadata.get("evaluation_target") == "synthetic_cpdag":
            truth = np.load(shared / "graph.npy")
            record = synthetic_metrics(truth, estimate, include_ancestor_aid=True)
            return {
                **{key: value for key, value in run.items() if key != "run_key"},
                "run_key": run["run_key"],
                **record.metrics,
                "evaluation_target": record.target,
            }
        projection_path = metadata.get("projection")
        if not projection_path:
            raise RuntimeError(
                "external run has no projection metadata; refusing to label it as CPDAG metrics")
        projection = json.loads(Path(projection_path).read_text())
        nodes = metadata.get("nodes", [])
        record = causalman_metrics(estimate, projection, nodes)
        return {
            **{key: value for key, value in run.items() if key != "run_key"},
            "run_key": run["run_key"],
            **record.metrics,
            "evaluation_target": record.target,
        }
    truth = np.load(shared / "graph.npy")
    record = synthetic_metrics(truth, estimate, include_ancestor_aid=False)
    row = {
        **{key: value for key, value in run.items() if key != "run_key"},
        "run_key": run["run_key"],
        **record.metrics,
        "ancestor_aid_status": "not_installed",
    }
    try:
        aid = synthetic_metrics(truth, estimate, include_ancestor_aid=True).metrics
    except CPDAGError:
        pass
    else:
        row.update(aid)
        row["ancestor_aid_status"] = "ok"
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-aggregate")
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args(argv)
    results, issues = collect(args.output_root)
    write_tables(args.output_root, results, issues)
    print(f"results={len(results)} issues={len(issues)}")
    return 0 if not issues else 2


if __name__ == "__main__":
    raise SystemExit(main())
