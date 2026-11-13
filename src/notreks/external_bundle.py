"""Convert the bundled historical caches into standard external manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from .external_sources import _oracle_no_treks


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(root: Path, payload: dict) -> Path:
    path = root / "manifest.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def bundle_causalman(source: Path, destination: Path) -> list[Path]:
    """Create one canonical manifest per CausalMan variant and seed."""
    outputs: list[Path] = []
    for variant in ("causalman_small", "causalman_medium"):
        variant_source = source / variant
        for old_manifest in sorted(variant_source.glob("seed_*_manifest.json")):
            seed = old_manifest.stem.split("_")[1]
            graph = json.loads((variant_source / f"seed_{seed}_graph.json").read_text())
            nodes = list(graph["selected_nodes"])
            index = {node: i for i, node in enumerate(nodes)}
            truth = np.zeros((len(nodes), len(nodes)), dtype=np.uint8)
            directed = []
            for left, right in graph["projected"]["directed"]:
                if left in index and right in index:
                    truth[index[left], index[right]] = 1
                    directed.append([left, right])
            pairs = sorted({tuple(sorted((index[a], index[b])))
                            for a, b in graph["oracle_no_treks"]
                            if a in index and b in index})
            target = destination / variant / f"seed_{seed}"
            target.mkdir(parents=True, exist_ok=True)
            observations = target / "observations.npy"
            truth_path = target / "truth_adjacency.npy"
            pairs_path = target / "knowledge_pairs.json"
            projection_path = target / "projection.json"
            shutil.copy2(variant_source / f"seed_{seed}.npy", observations)
            np.save(truth_path, truth)
            pairs_path.write_text(json.dumps([list(pair) for pair in pairs]) + "\n")
            projection_path.write_text(json.dumps(graph["projected"], indent=2, sort_keys=True) + "\n")
            artifacts = {key: _sha256(path) for key, path in {
                "observations": observations, "truth_adjacency": truth_path,
                "knowledge_pairs": pairs_path, "projection": projection_path}.items()}
            payload = {
                "dataset_id": f"{variant}_seed{seed}_n{len(np.load(observations))}",
                "observations": observations.name, "truth_adjacency": truth_path.name,
                "knowledge_pairs": pairs_path.name, "projection": projection_path.name,
                "nodes": nodes, "evaluation_target": "causalman_latent_projection",
                "metadata": {
                    "source_cache_manifest": str(old_manifest.relative_to(source)),
                    "variant": variant, "seed": int(seed),
                    "artifact_sha256": artifacts,
                    "knowledge_pairs_source": "upstream_prepared_graph_json",
                    "projected_directed_edges": len(directed),
                    "projected_bidirected_edges": len(graph["projected"]["bidirected"]),
                },
            }
            outputs.append(_write_manifest(target, payload))
    return outputs


def bundle_causalassembly(source: Path, destination: Path) -> list[Path]:
    """Create one canonical manifest per checked-in CausalAssembly seed."""
    source_manifest = json.loads((source / "manifest.json").read_text())
    truth = np.asarray(np.load(source / "ground_truth.npz")["truth"], dtype=np.uint8)
    pairs = [list(pair) for pair in _oracle_no_treks(truth)]
    outputs: list[Path] = []
    for source_data in sorted(source.glob("seed_*.npz")):
        if source_data.name == "seed_1.npz":
            continue
        seed = source_data.stem.split("_")[1]
        with np.load(source_data) as archive:
            observations = np.asarray(archive["discovery"], dtype=float)
        target = destination / f"seed_{seed}"
        target.mkdir(parents=True, exist_ok=True)
        observation_path = target / "observations.npy"
        truth_path = target / "truth_adjacency.npy"
        pairs_path = target / "knowledge_pairs.json"
        np.save(observation_path, observations)
        np.save(truth_path, truth)
        pairs_path.write_text(json.dumps(pairs) + "\n")
        artifacts = {key: _sha256(path) for key, path in {
            "observations": observation_path, "truth_adjacency": truth_path,
            "knowledge_pairs": pairs_path}.items()}
        payload = {
            "dataset_id": f"causalassembly_n500_seed{seed}",
            "observations": observation_path.name, "truth_adjacency": truth_path.name,
            "knowledge_pairs": pairs_path.name, "nodes": source_manifest["nodes"],
            "evaluation_target": "synthetic_cpdag",
            "metadata": {
                "source_cache_manifest": "../manifest.json", "seed": int(seed),
                "fixed_dataset": True, "independent_seed_replicates": False,
                "oracle_knowledge_pairs": len(pairs),
                "knowledge_pairs_source": "checked_in_ground_truth_by_notreks_oracle_rule",
                "artifact_sha256": artifacts,
            },
        }
        outputs.append(_write_manifest(target, payload))
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="notreks-external-bundle")
    parser.add_argument("kind", choices=("causalman", "causalassembly"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args(argv)
    outputs = (bundle_causalman if args.kind == "causalman" else bundle_causalassembly)(
        args.source, args.destination)
    print(f"wrote {len(outputs)} canonical manifests under {args.destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
