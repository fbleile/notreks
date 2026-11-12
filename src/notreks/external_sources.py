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
CAUSALMAN_PAPER = "https://arxiv.org/abs/2502.12707"


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


def _as_frame(value, name: str):
    import pandas as pd
    if isinstance(value, pd.DataFrame):
        return value.copy()
    try:
        return pd.DataFrame(value)
    except Exception as error:
        raise ValueError(f"CausalMan returned an invalid {name}") from error


def _observational_mask(table, rows: int) -> np.ndarray:
    """Keep rows without an active intervention in any intervention column."""
    import pandas as pd
    if table is None or table.empty:
        return np.ones(rows, dtype=bool)
    if len(table) != rows:
        raise ValueError(f"intervention table has {len(table)} rows but observations have {rows}")
    flags = np.zeros(rows, dtype=bool)
    for column in table.columns:
        values = table[column]
        if pd.api.types.is_bool_dtype(values):
            active = values.fillna(False).to_numpy(bool)
        elif pd.api.types.is_numeric_dtype(values):
            active = values.fillna(0).to_numpy(float) != 0
        else:
            text = values.fillna("").astype(str).str.strip()
            active = (~text.isin(("", "0", "none", "None", "nan"))).to_numpy(bool)
        flags |= active
    return ~flags


def _continuous_columns(frame):
    """Return measured continuous columns, excluding identifiers and low-cardinality fields."""
    import pandas as pd
    selected = []
    for column in frame.columns:
        name = str(column).strip().lower()
        if name == "batch_id_num":
            continue
        values = frame[column]
        if pd.api.types.is_bool_dtype(values) or not pd.api.types.is_numeric_dtype(values):
            continue
        numeric = pd.to_numeric(values, errors="coerce")
        if not np.isfinite(numeric.to_numpy(float)).all():
            continue
        if numeric.nunique(dropna=True) <= 1:
            continue
        if pd.api.types.is_integer_dtype(values):
            continue
        if numeric.nunique(dropna=True) <= min(10, max(2, len(values) // 20)):
            continue
        selected.append(str(column))
    return selected


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


def import_causalman(output: Path, *, variant: str, seed: int, sample_size: int = 5000) -> Path:
    """Prepare one official CausalMan observational cache.

    The upstream package is intentionally imported only when this command is
    used. The resulting manifest targets projection diagnostics, because the
    simulator may contain latent variables and bidirected projected edges.
    """
    try:
        import networkx as nx
        import pandas as pd
        from causalman import CausalMan
        from causalman.graph_projections import get_latent_projection_single
    except ImportError as error:
        raise RuntimeError(
            "CausalMan import requires the official causalman package, "
            "networkx, and pandas; no substitute generator is used") from error
    if variant not in {"causalman_small", "causalman_medium"}:
        raise ValueError("variant must be causalman_small or causalman_medium")
    upstream_dir = output / "upstream"
    upstream_dir.mkdir(parents=True, exist_ok=True)
    simulator = CausalMan(name=variant, seed=int(seed), batch_multiplier=1,
                           parallelize=False, save_path=str(upstream_dir),
                           debug_mode=False)
    try:
        result = simulator.sample(n_samples=sample_size)
    except TypeError as error:
        if "n_samples" not in str(error):
            raise
        result = simulator.sample()
    if len(result) == 4:
        observed, intervention, _path, causal_dag = result
    elif len(result) == 6:
        observed, _mag, _admg, _full, causal_dag, intervention = result
    else:
        raise ValueError(f"unsupported CausalMan sample return arity: {len(result)}")
    observed = _as_frame(observed, "observations")
    intervention = _as_frame(intervention, "intervention table")
    observed.columns = [str(column) for column in observed.columns]
    observed = observed.loc[_observational_mask(intervention, len(observed))].reset_index(drop=True)
    graph = causal_dag if isinstance(causal_dag, nx.DiGraph) else nx.DiGraph(causal_dag)
    graph = nx.relabel_nodes(graph, {node: str(node) for node in graph.nodes}, copy=True)
    observable = [str(node) for node in graph.nodes
                  if bool(graph.nodes[node].get("Observable", graph.nodes[node].get("observable", False)))]
    nodes = [node for node in observable if node in observed.columns]
    if not nodes:
        nodes = _continuous_columns(observed)
    if len(observed) < sample_size:
        raise ValueError(f"only {len(observed)} observational rows remain; {sample_size} required")
    observed = observed.iloc[:sample_size]
    if not nodes:
        raise ValueError("CausalMan produced no nonconstant observed numeric variables")
    values = observed.loc[:, nodes].to_numpy(float)
    if not np.isfinite(values).all():
        raise ValueError("CausalMan observations contain nonfinite values")
    observed_set = set(nodes)
    for node in graph.nodes:
        graph.nodes[node]["Observable"] = node in observed_set
    projection = get_latent_projection_single(graph)
    directed, bidirected = [], []
    for left, right, data in projection.edges(data=True):
        kind = data.get("edge_type", data.get("type", "directed"))
        (bidirected if kind == "bidirected" else directed).append([str(left), str(right)])
    node_index = {node: index for index, node in enumerate(nodes)}
    truth = nx.to_numpy_array(selected_graph, nodelist=nodes, dtype=np.uint8)
    reach = truth.astype(bool).copy()
    np.fill_diagonal(reach, True)
    for pivot in range(len(nodes)):
        reach |= reach[:, [pivot]] & reach[[pivot], :]
    ancestors = reach.T
    pairs = [[left, right] for left in range(len(nodes)) for right in range(left + 1, len(nodes))
             if not np.any(ancestors[left] & ancestors[right])]
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    np.save(output / "observations.npy", values)
    np.save(output / "truth_adjacency.npy", truth)
    (output / "knowledge_pairs.json").write_text(json.dumps(pairs) + "\n")
    (output / "projection.json").write_text(json.dumps({
        "projected": {"directed": directed, "bidirected": bidirected}}, indent=2) + "\n")
    manifest = {
        "dataset_id": f"{variant}_seed{seed}_n{len(values)}",
        "observations": "observations.npy", "truth_adjacency": "truth_adjacency.npy",
        "knowledge_pairs": "knowledge_pairs.json", "projection": "projection.json",
        "nodes": nodes, "evaluation_target": "causalman_latent_projection",
        "metadata": {"source_url": CAUSALMAN_SOURCE, "paper_url": CAUSALMAN_PAPER,
                      "variant": variant, "seed": int(seed), "requested_sample_size": sample_size,
                      "stored_sample_size": len(values), "full_nodes": graph.number_of_nodes(),
                      "full_edges": graph.number_of_edges(),
                      "observed_directed_edges": len(directed),
                      "observed_bidirected_edges": len(bidirected)},
    }
    path = output / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(prog="notreks-external-import")
    parser.add_argument("dataset", choices=("causalassembly", "causalman"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--data-csv", type=Path)
    parser.add_argument("--truth-json", type=Path)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--variant", choices=("causalman_small", "causalman_medium"))
    parser.add_argument("--seed", type=int, default=1001)
    parser.add_argument("--sample-size", type=int, default=5000)
    args = parser.parse_args()
    if args.dataset == "causalassembly":
        print(import_causalassembly(args.output, data_csv=args.data_csv,
                                    truth_json=args.truth_json, download=args.download))
    elif args.variant is None:
        raise SystemExit("--variant is required for causalman")
    else:
        print(import_causalman(args.output, variant=args.variant, seed=args.seed,
                               sample_size=args.sample_size))


if __name__ == "__main__":
    main()
