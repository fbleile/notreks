import json

import numpy as np
import pytest

from notreks.external import ExternalDataError, ExternalDataset


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


def test_external_manifest_requires_files(tmp_path):
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps({"observations": "missing.npy", "truth_adjacency": "truth.npy"}))
    with pytest.raises(ExternalDataError, match="does not exist"):
        ExternalDataset.from_manifest(path)
