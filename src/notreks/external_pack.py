"""Copy a validated external dataset into a portable Git/data bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from .external import ExternalDataset


def pack(manifest: Path, destination: Path) -> Path:
    """Copy only manifest-referenced artifacts and rewrite paths relatively."""
    dataset = ExternalDataset.from_manifest(manifest)
    observations, truth, _weights = dataset.validate_arrays()
    source_root = dataset.manifest_path.parent
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    files = {
        "observations": dataset.observations_path,
        "truth_adjacency": dataset.truth_adjacency_path,
        "weights": dataset.weights_path,
        "knowledge_pairs": dataset.knowledge_pairs_path,
        "projection": dataset.projection_path,
    }
    rewritten = {}
    for label, source in files.items():
        if source is None:
            continue
        target = destination / source.name
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        rewritten[label] = target.name
    payload = json.loads(dataset.manifest_path.read_text())
    for label, relative_name in rewritten.items():
        payload[label] = relative_name
    metadata = dict(payload.get("metadata", {}))
    metadata["packed_from"] = str(dataset.manifest_path)
    metadata["packed_shape"] = {"observations": list(observations.shape),
                                 "truth_adjacency": list(truth.shape)}
    payload["metadata"] = metadata
    output = destination / "manifest.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    ExternalDataset.from_manifest(output).validate_arrays()
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-external-pack")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    output = pack(args.manifest, args.destination)
    print(f"packed external dataset -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
