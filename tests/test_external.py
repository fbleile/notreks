import json

import numpy as np
import pytest

from notreks.external import ExternalDataError, ExternalDataset, main
from notreks.external_sources import import_causalassembly
from notreks.external_pack import pack
from notreks.external_bundle import bundle_causalassembly


def test_external_manifest_validates_arrays(tmp_path):
    observations = np.zeros((4, 3))
    truth = np.zeros((3, 3))
    np.save(tmp_path / "x.npy", observations)
    np.save(tmp_path / "truth.npy", truth)
    (tmp_path / "dataset.json").write_text(json.dumps({
        "dataset_id": "demo", "observations": "x.npy", "truth_adjacency": "truth.npy",
        "nodes": ["a", "b", "c"], "evaluation_target": "causalman_latent_projection",
    }))
    dataset = ExternalDataset.from_manifest(tmp_path / "dataset.json")
    x, graph, weights = dataset.validate_arrays()
    assert x.shape == (4, 3)
    assert graph.shape == (3, 3)
    assert np.all(weights == 1)


def test_external_pairs_are_explicit_and_validated(tmp_path):
    np.save(tmp_path / "x.npy", np.zeros((4, 3)))
    np.save(tmp_path / "truth.npy", np.zeros((3, 3)))
    (tmp_path / "pairs.json").write_text(json.dumps([[2, 0], [0, 1], [0, 1]]))
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"observations": "x.npy", "truth_adjacency": "truth.npy",
                                "knowledge_pairs": "pairs.json", "nodes": ["a", "b", "c"]}))
    dataset = ExternalDataset.from_manifest(path)
    assert dataset.available_pairs(3) == [(0, 1), (0, 2)]


def test_causalassembly_importer_writes_portable_manifest(tmp_path):
    nodes = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    truth = {"nodes": nodes, "adjacency": [[{"id": "b"}], [], []]}
    (tmp_path / "truth.json").write_text(json.dumps(truth))
    with (tmp_path / "data.csv").open("w") as handle:
        handle.write("a,b,c\n")
        handle.write("1,2,3\n")
    with pytest.raises(ValueError, match="shape"):
        import_causalassembly(tmp_path / "out", data_csv=tmp_path / "data.csv",
                              truth_json=tmp_path / "truth.json")


def test_external_manifest_requires_files(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"observations": "missing.npy", "truth_adjacency": "truth.npy"}))
    with pytest.raises(ExternalDataError, match="does not exist"):
        ExternalDataset.from_manifest(path)


def test_external_manifest_requires_node_names(tmp_path):
    np.save(tmp_path / "x.npy", np.zeros((4, 2)))
    np.save(tmp_path / "truth.npy", np.zeros((2, 2)))
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"observations": "x.npy", "truth_adjacency": "truth.npy"}))
    with pytest.raises(ExternalDataError, match="nodes"):
        ExternalDataset.from_manifest(path)


def test_external_manifest_checks_artifact_digests(tmp_path):
    np.save(tmp_path / "x.npy", np.zeros((4, 2)))
    np.save(tmp_path / "truth.npy", np.zeros((2, 2)))
    import hashlib
    digest = hashlib.sha256((tmp_path / "x.npy").read_bytes()).hexdigest()
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"observations": "x.npy", "truth_adjacency": "truth.npy",
                                "nodes": ["a", "b"],
                                "metadata": {"artifact_sha256": {"observations": digest}}}))
    ExternalDataset.from_manifest(path).validate_arrays()
    (tmp_path / "x.npy").write_bytes(b"changed")
    with pytest.raises(ExternalDataError, match="checksum mismatch"):
        ExternalDataset.from_manifest(path).validate_arrays()


def test_external_check_reports_pair_count(tmp_path, capsys):
    np.save(tmp_path / "x.npy", np.zeros((4, 2)))
    np.save(tmp_path / "truth.npy", np.zeros((2, 2)))
    (tmp_path / "pairs.json").write_text("[[0, 1]]\n")
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"dataset_id": "demo", "observations": "x.npy",
                                "truth_adjacency": "truth.npy", "knowledge_pairs": "pairs.json",
                                "nodes": ["a", "b"]}))
    main([str(path)])
    report = json.loads(capsys.readouterr().out)
    assert report["knowledge_pairs"] == 1
    assert report["nodes"] == 2


def test_external_pack_copies_only_manifest_artifacts(tmp_path):
    np.save(tmp_path / "x.npy", np.zeros((4, 2)))
    np.save(tmp_path / "truth.npy", np.zeros((2, 2)))
    (tmp_path / "pairs.json").write_text("[[0, 1]]\n")
    (tmp_path / "unreferenced.txt").write_text("do not copy")
    manifest = tmp_path / "dataset.json"
    manifest.write_text(json.dumps({"dataset_id": "demo", "observations": "x.npy",
                                    "truth_adjacency": "truth.npy", "knowledge_pairs": "pairs.json",
                                    "nodes": ["a", "b"]}))
    output = pack(manifest, tmp_path / "bundle")
    assert output.is_file()
    assert (output.parent / "x.npy").is_file()
    assert not (output.parent / "unreferenced.txt").exists()
    assert ExternalDataset.from_manifest(output).validate_arrays()[0].shape == (4, 2)


def test_external_bundle_makes_causalassembly_seed_manifest(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    nodes = ["a", "b", "c"]
    np.savez(source / "ground_truth.npz", truth=np.array([[0, 1, 0], [0, 0, 1], [0, 0, 0]], dtype=np.uint8))
    (source / "manifest.json").write_text(json.dumps({"nodes": nodes}))
    np.savez(source / "seed_1001.npz", reference=np.zeros((2, 3)), discovery=np.ones((2, 3)))
    np.savez(source / "seed_1.npz", reference=np.zeros((2, 3)), discovery=np.ones((2, 3)))
    outputs = bundle_causalassembly(source, tmp_path / "bundle")
    assert len(outputs) == 1
    dataset = ExternalDataset.from_manifest(outputs[0])
    observations, truth, _ = dataset.validate_arrays()
    assert observations.shape == (2, 3)
    assert truth.sum() == 2
    assert dataset.available_pairs(3) == []
