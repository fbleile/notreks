"""Importers and provenance for official external benchmark releases.

This module does not invent replacement data. It either consumes explicitly
downloaded official files or downloads them from the upstream URLs supplied by
the benchmark authors, then writes the portable NOTREKS external manifest.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import numpy as np


CAUSALASSEMBLY_SOURCE = "https://github.com/boschresearch/causalAssembly"
CAUSALASSEMBLY_DATA_URL = (
    "https://raw.githubusercontent.com/boschresearch/causalAssembly/main/"
    "data/data_sets/n_500_synthdata/assembly_line_500.csv")
CAUSALASSEMBLY_TRUTH_URL = (
    "https://raw.githubusercontent.com/boschresearch/causalAssembly/main/"
    "data/ground_truth/ground_truth.json")
CAUSALMAN_SOURCE = "https://github.com/boschresearch/CausalMan"


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url) as response:  # nosec B310: URL is a checked-in official source
        destination.write_bytes(response.read())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _oracle_no_treks(adjacency: np.ndarray) -> list[list[int]]:
    reach = np.asarray(adjacency, dtype=bool).copy()
    np.fill_diagonal(reach, True)
    for pivot in range(len(reach)):
        reach |= reach[:, [pivot]] & reach[[pivot], :]
    ancestors = reach.T
    return [[left, right] for left in range(len(reach)) for right in range(left + 1, len(reach))
            if not np.any(ancestors[left] & ancestors[right])]


def import_causalassembly(output: Path, *, data_csv: Path | None = None,
                          truth_json: Path | None = None, download: bool = False) -> Path:
    """Create a portable official CausalAssembly n=500 external manifest."""
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    data_csv = data_csv or output / "assembly_line_500.csv"
    truth_json = truth_json or output / "ground_truth.json"
    if download:
        _download(CAUSALASSEMBLY_DATA_URL, data_csv)
        _download(CAUSALASSEMBLY_TRUTH_URL, truth_json)
    if not data_csv.is_file() or not truth_json.is_file():
        raise FileNotFoundError("provide both official CSV/JSON files or pass --download")

    truth_payload = json.loads(truth_json.read_text())
    nodes = [entry["id"] for entry in truth_payload["nodes"]]
    adjacency = np.zeros((len(nodes), len(nodes)), dtype=np.uint8)
    index = {node: position for position, node in enumerate(nodes)}
    for source, children in enumerate(truth_payload["adjacency"]):
        for child in children:
            adjacency[source, index[child["id"]]] = 1
    with data_csv.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or list(reader.fieldnames) != nodes:
            raise ValueError("CausalAssembly CSV columns do not exactly match truth node order")
        rows = [[float(row[node]) for node in nodes] for row in reader]
    observations = np.asarray(rows, dtype=float)
    if observations.shape != (500, len(nodes)) or not np.isfinite(observations).all():
        raise ValueError(f"expected finite CausalAssembly data of shape (500, {len(nodes)})")
    np.save(output / "observations.npy", observations)
    np.save(output / "truth_adjacency.npy", adjacency)
    (output / "knowledge_pairs.json").write_text(json.dumps(_oracle_no_treks(adjacency)) + "\n")
    manifest = {
        "dataset_id": "causalassembly_upstream_static_n500",
        "observations": "observations.npy", "truth_adjacency": "truth_adjacency.npy",
        "knowledge_pairs": "knowledge_pairs.json", "nodes": nodes,
        "evaluation_target": "synthetic_cpdag",
        "metadata": {"source_url": CAUSALASSEMBLY_SOURCE,
                      "data_url": CAUSALASSEMBLY_DATA_URL,
                      "truth_url": CAUSALASSEMBLY_TRUTH_URL,
                      "data_sha256": _sha256(data_csv),
                      "truth_sha256": _sha256(truth_json),
                      "fixed_dataset": True, "independent_seed_replicates": False},
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(prog="notreks-external-import")
    parser.add_argument("dataset", choices=("causalassembly",))
    parser.add_argument("output", type=Path)
    parser.add_argument("--data-csv", type=Path)
    parser.add_argument("--truth-json", type=Path)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    print(import_causalassembly(args.output, data_csv=args.data_csv,
                                 truth_json=args.truth_json, download=args.download))


if __name__ == "__main__":
    main()
