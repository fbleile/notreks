"""Validate one bundled external dataset through the normal data boundary."""

from __future__ import annotations

import argparse
from pathlib import Path

from notreks.external import ExternalDataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    dataset = ExternalDataset.from_manifest(args.manifest)
    observations, truth, weights = dataset.validate_arrays()
    pairs = dataset.available_pairs(observations.shape[1])
    print({"dataset": dataset.dataset_id,
           "observations": observations.shape,
           "truth": truth.shape,
           "weights": weights.shape,
           "knowledge_pairs": len(pairs),
           "evaluation_target": dataset.evaluation_target})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
