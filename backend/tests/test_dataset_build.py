from __future__ import annotations

import json

import numpy as np

from data.build_dataset import WINDOW_LABEL_COLUMNS, build_dataset, check_dataset
from data.schema import EngagementLabels, retention_for_window


def test_engagement_labels_validate_scores_and_align_retention_curve():
    labels = EngagementLabels.from_mapping({
        "analysis_id": "ana_1",
        "watch_time_ratio": 0.7,
        "retention_curve": [0.9, 0.7, 0.4],
    })

    assert labels.validate() == []
    assert retention_for_window(labels, 0, 4) == 0.9
    assert retention_for_window(labels, 3, 4) == 0.4

    invalid = EngagementLabels.from_mapping({"analysis_id": "ana_2", "shares_rate": 1.2})
    assert "shares_rate must be in [0, 1]" in invalid.validate()


def test_build_dataset_aligns_feature_windows_and_writes_splits(tmp_path):
    features_root = tmp_path / "uploads"
    _write_features(features_root, "ana_a", rows=3, dim=5)
    _write_features(features_root, "ana_b", rows=2, dim=5)
    labels_path = tmp_path / "labels.jsonl"
    labels_path.write_text(
        "\n".join([
            json.dumps({
                "analysis_id": "ana_a",
                "watch_time_ratio": 0.7,
                "shares_rate": 0.1,
                "retention_curve": [0.9, 0.8, 0.6],
            }),
            json.dumps({
                "analysis_id": "ana_b",
                "watch_time_ratio": 0.4,
                "shares_rate": 0.05,
                "retention_score": 0.5,
            }),
        ]),
        encoding="utf-8",
    )

    output_dir = tmp_path / "dataset"
    manifest = build_dataset(
        labels_path=labels_path,
        features_root=features_root,
        output_dir=output_dir,
        train_ratio=0.5,
        val_ratio=0.25,
    )

    assert manifest["window_rows"] == 5
    assert manifest["feature_dim"] == 5
    assert manifest["label_columns"] == WINDOW_LABEL_COLUMNS
    assert (output_dir / "manifest.json").exists()
    assert check_dataset(labels_path=labels_path, features_root=features_root, output_dir=output_dir) == 0

    total_rows = 0
    for split_name in ["train", "val", "test"]:
        with np.load(output_dir / f"{split_name}.npz") as data:
            assert data["y"].shape[1] == len(WINDOW_LABEL_COLUMNS)
            total_rows += data["x"].shape[0]
    assert total_rows == 5


def _write_features(features_root, analysis_id: str, *, rows: int, dim: int) -> None:
    feature_dir = features_root / analysis_id / "features"
    feature_dir.mkdir(parents=True)
    matrix = np.arange(rows * dim, dtype=np.float32).reshape(rows, dim)
    np.savez_compressed(
        feature_dir / "multimodal_windows.npz",
        embeddings=matrix,
        window_start=np.arange(rows, dtype=np.float32),
        window_end=np.arange(1, rows + 1, dtype=np.float32),
    )
    (feature_dir / "multimodal_windows.json").write_text(
        json.dumps({"analysis_id": analysis_id, "shape": [rows, dim]}),
        encoding="utf-8",
    )
