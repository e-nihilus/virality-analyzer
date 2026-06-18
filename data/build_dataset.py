"""Build train/val/test datasets from persisted V2 window features and labels.

Example:
    python data/build_dataset.py --labels data/labels.jsonl --output data/datasets/v1

Validation-only:
    python data/build_dataset.py --check
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.schema import EngagementLabels, SCORE_LABEL_COLUMNS, retention_for_window


FEATURE_MATRIX_NAME = "multimodal_windows.npz"
FEATURE_METADATA_NAME = "multimodal_windows.json"
WINDOW_LABEL_COLUMNS = [*SCORE_LABEL_COLUMNS, "window_retention"]


@dataclass(frozen=True)
class FeatureArtifact:
    analysis_id: str
    matrix: np.ndarray
    window_start: np.ndarray
    window_end: np.ndarray
    metadata: dict[str, Any]


def load_labels(path: Path) -> list[EngagementLabels]:
    if not path.exists():
        raise FileNotFoundError(f"Labels file not found: {path}")
    if path.suffix.lower() == ".csv":
        rows = _read_csv(path)
    elif path.suffix.lower() in {".jsonl", ".ndjson"}:
        rows = _read_jsonl(path)
    elif path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("labels", [])
    else:
        raise ValueError("Labels file must be .csv, .jsonl, .ndjson, or .json")

    labels = [EngagementLabels.from_mapping(row) for row in rows]
    errors = validate_labels(labels)
    if errors:
        raise ValueError("Invalid labels:\n" + "\n".join(errors))
    return labels


def validate_labels(labels: list[EngagementLabels]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, label in enumerate(labels):
        for error in label.validate():
            errors.append(f"row {index}: {error}")
        if label.analysis_id in seen:
            errors.append(f"row {index}: duplicate analysis_id={label.analysis_id}")
        seen.add(label.analysis_id)
    return errors


def build_dataset(
    *,
    labels_path: Path,
    features_root: Path,
    output_dir: Path,
    seed: int = 42,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
) -> dict[str, Any]:
    labels = load_labels(labels_path)
    rows: list[tuple[np.ndarray, np.ndarray, str, float, float]] = []
    missing_features: list[str] = []

    for label in labels:
        artifact = load_feature_artifact(features_root=features_root, analysis_id=label.analysis_id)
        if artifact is None:
            missing_features.append(label.analysis_id)
            continue
        y_video = np.array(label.score_vector(), dtype=np.float32)
        for window_index in range(artifact.matrix.shape[0]):
            y = np.concatenate([
                y_video,
                np.array([retention_for_window(label, window_index, artifact.matrix.shape[0])], dtype=np.float32),
            ])
            rows.append((
                artifact.matrix[window_index].astype(np.float32),
                y.astype(np.float32),
                label.analysis_id,
                float(artifact.window_start[window_index]),
                float(artifact.window_end[window_index]),
            ))

    if missing_features:
        raise FileNotFoundError(
            "Missing feature artifacts for analysis ids: " + ", ".join(sorted(missing_features))
        )
    if not rows:
        raise ValueError("No labeled feature rows were produced")

    splits = split_rows(rows, seed=seed, train_ratio=train_ratio, val_ratio=val_ratio)
    output_dir.mkdir(parents=True, exist_ok=True)
    split_counts: dict[str, int] = {}
    for split_name, split_rows_value in splits.items():
        split_counts[split_name] = len(split_rows_value)
        save_split(output_dir / f"{split_name}.npz", split_rows_value)

    manifest = {
        "labels_path": str(labels_path),
        "features_root": str(features_root),
        "label_columns": WINDOW_LABEL_COLUMNS,
        "feature_dim": int(rows[0][0].shape[0]),
        "window_rows": len(rows),
        "analysis_count": len(labels),
        "splits": split_counts,
        "seed": seed,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def load_feature_artifact(*, features_root: Path, analysis_id: str) -> FeatureArtifact | None:
    feature_dir = features_root / analysis_id / "features"
    matrix_path = feature_dir / FEATURE_MATRIX_NAME
    metadata_path = feature_dir / FEATURE_METADATA_NAME
    if not matrix_path.exists() or not metadata_path.exists():
        return None
    with np.load(matrix_path) as data:
        matrix = data["embeddings"].astype(np.float32)
        window_start = data["window_start"].astype(np.float32)
        window_end = data["window_end"].astype(np.float32)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if matrix.ndim != 2:
        raise ValueError(f"Feature matrix for {analysis_id} must be 2D")
    if len(window_start) != matrix.shape[0] or len(window_end) != matrix.shape[0]:
        raise ValueError(f"Feature windows for {analysis_id} are not aligned with matrix rows")
    return FeatureArtifact(
        analysis_id=analysis_id,
        matrix=matrix,
        window_start=window_start,
        window_end=window_end,
        metadata=metadata,
    )


def split_rows(
    rows: list[tuple[np.ndarray, np.ndarray, str, float, float]],
    *,
    seed: int,
    train_ratio: float,
    val_ratio: float,
) -> dict[str, list[tuple[np.ndarray, np.ndarray, str, float, float]]]:
    analysis_ids = sorted({row[2] for row in rows})
    random.Random(seed).shuffle(analysis_ids)
    n = len(analysis_ids)
    train_end = max(1, int(round(n * train_ratio))) if n > 1 else n
    val_end = min(n, train_end + max(1, int(round(n * val_ratio)))) if n > 2 else train_end
    split_by_id: dict[str, str] = {}
    for analysis_id in analysis_ids[:train_end]:
        split_by_id[analysis_id] = "train"
    for analysis_id in analysis_ids[train_end:val_end]:
        split_by_id[analysis_id] = "val"
    for analysis_id in analysis_ids[val_end:]:
        split_by_id[analysis_id] = "test"

    splits = {"train": [], "val": [], "test": []}
    for row in rows:
        splits[split_by_id[row[2]]].append(row)
    return splits


def save_split(path: Path, rows: list[tuple[np.ndarray, np.ndarray, str, float, float]]) -> None:
    if rows:
        x = np.stack([row[0] for row in rows]).astype(np.float32)
        y = np.stack([row[1] for row in rows]).astype(np.float32)
        analysis_ids = np.array([row[2] for row in rows])
        window_start = np.array([row[3] for row in rows], dtype=np.float32)
        window_end = np.array([row[4] for row in rows], dtype=np.float32)
    else:
        x = np.empty((0, 0), dtype=np.float32)
        y = np.empty((0, len(WINDOW_LABEL_COLUMNS)), dtype=np.float32)
        analysis_ids = np.array([], dtype=str)
        window_start = np.array([], dtype=np.float32)
        window_end = np.array([], dtype=np.float32)
    np.savez_compressed(
        path,
        x=x,
        y=y,
        analysis_id=analysis_ids,
        window_start=window_start,
        window_end=window_end,
        label_columns=np.array(WINDOW_LABEL_COLUMNS),
    )


def check_dataset(*, labels_path: Path | None, features_root: Path, output_dir: Path) -> int:
    errors: list[str] = []
    if labels_path is not None and labels_path.exists():
        try:
            labels = load_labels(labels_path)
            missing = [
                label.analysis_id for label in labels
                if load_feature_artifact(features_root=features_root, analysis_id=label.analysis_id) is None
            ]
            if missing:
                errors.append("labels without feature artifacts: " + ", ".join(sorted(missing)))
        except Exception as exc:
            errors.append(str(exc))
    elif labels_path is not None:
        errors.append(f"labels file not found: {labels_path}")

    manifest_path = output_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for split_name in ["train", "val", "test"]:
                split_path = output_dir / f"{split_name}.npz"
                if not split_path.exists():
                    errors.append(f"missing split artifact: {split_path}")
                    continue
                with np.load(split_path) as data:
                    if "x" not in data or "y" not in data:
                        errors.append(f"split {split_name} missing x/y arrays")
            if manifest.get("label_columns") != WINDOW_LABEL_COLUMNS:
                errors.append("manifest label_columns do not match current schema")
        except Exception as exc:
            errors.append(f"invalid dataset manifest/artifacts: {exc}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if labels_path is None and not manifest_path.exists():
        print("OK: dataset tooling is installed; provide --labels to validate/build real labeled data")
    else:
        print("OK: dataset labels/features/artifacts are valid")
    return 0


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"line {line_number}: expected JSON object")
        rows.append(row)
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, help="CSV/JSONL/JSON labels file")
    parser.add_argument("--features-root", type=Path, default=Path("uploads"))
    parser.add_argument("--output", type=Path, default=Path("data/datasets/v1"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check:
        return check_dataset(labels_path=args.labels, features_root=args.features_root, output_dir=args.output)
    if args.labels is None:
        print("ERROR: --labels is required unless --check is used", file=sys.stderr)
        return 2
    manifest = build_dataset(
        labels_path=args.labels,
        features_root=args.features_root,
        output_dir=args.output,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
