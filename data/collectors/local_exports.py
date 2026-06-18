"""Normalize first-party engagement exports into the V2 labels schema.

This collector intentionally does not scrape social platforms. It transforms
CSV/JSONL exports that the user has obtained legally (official APIs, creator
analytics export, or internal logs) into labels consumed by build_dataset.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data.schema import EngagementLabels


def normalize_export(input_path: Path, output_path: Path) -> int:
    rows = _read_rows(input_path)
    labels: list[EngagementLabels] = []
    for row in rows:
        normalized = _normalize_row(row)
        label = EngagementLabels.from_mapping(normalized)
        errors = label.validate()
        if errors:
            raise ValueError(f"Invalid row for analysis_id={label.analysis_id}: {errors}")
        labels.append(label)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for label in labels:
            f.write(json.dumps(label.__dict__, ensure_ascii=False) + "\n")
    return len(labels)


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    views = _float(row.get("views"), default=0.0)
    duration = max(_float(row.get("duration_seconds"), default=0.0), 1e-6)
    avg_watch_time = _float(row.get("avg_watch_time_seconds"), default=None)
    watch_time_ratio = row.get("watch_time_ratio")
    if watch_time_ratio in {None, ""} and avg_watch_time is not None:
        watch_time_ratio = avg_watch_time / duration

    return {
        "analysis_id": row.get("analysis_id") or row.get("id") or row.get("video_id"),
        "watch_time_ratio": _rate_or_existing(row, "watch_time_ratio", watch_time_ratio),
        "shares_rate": _rate_or_existing(row, "shares_rate", _ratio(row.get("shares"), views)),
        "saves_rate": _rate_or_existing(row, "saves_rate", _ratio(row.get("saves"), views)),
        "rewatch_rate": _rate_or_existing(row, "rewatch_rate", _ratio(row.get("rewatches"), views)),
        "retention_score": row.get("retention_score") or row.get("completion_rate"),
        "hook_strength": row.get("hook_strength"),
        "shareability": row.get("shareability"),
        "novelty": row.get("novelty"),
        "ragebait": row.get("ragebait"),
        "memeability": row.get("memeability"),
        "retention_curve": row.get("retention_curve") or [],
        "source_platform": row.get("source_platform") or row.get("platform"),
        "source_url": row.get("source_url") or row.get("url"),
        "license": row.get("license"),
    }


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("items", data.get("labels", []))
    raise ValueError("input must be .csv, .jsonl, .ndjson, or .json")


def _rate_or_existing(row: dict[str, Any], key: str, fallback: float | str | None) -> float | str | None:
    value = row.get(key)
    return fallback if value in {None, ""} else value


def _ratio(numerator: Any, denominator: float) -> float | None:
    if denominator <= 0:
        return None
    value = _float(numerator, default=None)
    if value is None:
        return None
    return min(1.0, max(0.0, value / denominator))


def _float(value: Any, *, default: float | None) -> float | None:
    if value in {None, ""}:
        return default
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    count = normalize_export(args.input, args.output)
    print(f"Wrote {count} labels to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
