"""Dataset schema for V2 viral prediction training labels."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SCORE_LABEL_COLUMNS = [
    "watch_time_ratio",
    "shares_rate",
    "saves_rate",
    "rewatch_rate",
    "retention_score",
    "hook_strength",
    "shareability",
    "novelty",
    "ragebait",
    "memeability",
]


@dataclass(frozen=True)
class EngagementLabels:
    """Video-level engagement labels aligned to one analysis/features artifact."""

    analysis_id: str
    watch_time_ratio: float | None = None
    shares_rate: float | None = None
    saves_rate: float | None = None
    rewatch_rate: float | None = None
    retention_score: float | None = None
    hook_strength: float | None = None
    shareability: float | None = None
    novelty: float | None = None
    ragebait: float | None = None
    memeability: float | None = None
    retention_curve: list[float] = field(default_factory=list)
    source_platform: str | None = None
    source_url: str | None = None
    license: str | None = None

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "EngagementLabels":
        analysis_id = str(row.get("analysis_id") or "").strip()
        retention_curve = _list_of_scores(row.get("retention_curve"))
        return cls(
            analysis_id=analysis_id,
            watch_time_ratio=_optional_score(row.get("watch_time_ratio")),
            shares_rate=_optional_score(row.get("shares_rate")),
            saves_rate=_optional_score(row.get("saves_rate")),
            rewatch_rate=_optional_score(row.get("rewatch_rate")),
            retention_score=_optional_score(row.get("retention_score")),
            hook_strength=_optional_score(row.get("hook_strength")),
            shareability=_optional_score(row.get("shareability")),
            novelty=_optional_score(row.get("novelty")),
            ragebait=_optional_score(row.get("ragebait")),
            memeability=_optional_score(row.get("memeability")),
            retention_curve=retention_curve,
            source_platform=_optional_text(row.get("source_platform")),
            source_url=_optional_text(row.get("source_url")),
            license=_optional_text(row.get("license")),
        )

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.analysis_id:
            errors.append("analysis_id is required")
        for column in SCORE_LABEL_COLUMNS:
            value = getattr(self, column)
            if value is not None and not 0.0 <= value <= 1.0:
                errors.append(f"{column} must be in [0, 1]")
        for index, value in enumerate(self.retention_curve):
            if not 0.0 <= value <= 1.0:
                errors.append(f"retention_curve[{index}] must be in [0, 1]")
        if not any(getattr(self, column) is not None for column in SCORE_LABEL_COLUMNS) and not self.retention_curve:
            errors.append("at least one label score or retention_curve is required")
        return errors

    def score_vector(self) -> list[float]:
        """Return dense label vector; missing labels are encoded as NaN."""
        return [
            float("nan") if getattr(self, column) is None else float(getattr(self, column))
            for column in SCORE_LABEL_COLUMNS
        ]


def retention_for_window(labels: EngagementLabels, window_index: int, window_count: int) -> float:
    """Align retention labels to a feature window."""
    if labels.retention_curve:
        if window_count <= 1:
            curve_index = 0
        else:
            curve_index = round(window_index * (len(labels.retention_curve) - 1) / (window_count - 1))
        return labels.retention_curve[curve_index]
    if labels.retention_score is not None:
        return labels.retention_score
    return float("nan")


def _optional_score(value: Any) -> float | None:
    if value is None or value == "" or value == "null":
        return None
    return float(value)


def _list_of_scores(value: Any) -> list[float]:
    if value is None or value == "" or value == "null":
        return []
    if isinstance(value, str):
        import json

        parsed = json.loads(value)
    else:
        parsed = value
    if not isinstance(parsed, list):
        raise ValueError("retention_curve must be a JSON/list array")
    return [float(item) for item in parsed]


def _optional_text(value: Any) -> str | None:
    if value is None or value == "" or value == "null":
        return None
    return str(value)
