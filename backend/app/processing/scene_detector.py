"""Optional scene-cut detection for pacing estimation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def detect_scene_cuts(video_path: str) -> list[float] | None:
    """Return scene-cut timestamps in seconds using PySceneDetect when present."""
    try:
        from scenedetect import ContentDetector, detect
    except ImportError:
        logger.warning("PySceneDetect is not installed; pacing score unavailable")
        return None

    try:
        scenes = detect(video_path, ContentDetector())
    except Exception:
        logger.warning("Scene detection failed", exc_info=True)
        return None

    cuts: list[float] = []
    for start, _end in scenes[1:]:
        cuts.append(round(start.get_seconds(), 3))
    return cuts


def pacing_score_from_cuts(cut_timestamps: list[float], duration_seconds: float) -> float | None:
    if duration_seconds <= 0:
        return None
    if not cut_timestamps:
        return 0.0
    cuts_per_second = len(cut_timestamps) / max(duration_seconds, 1.0)
    if cuts_per_second < 0.3:
        return round(cuts_per_second / 0.3 * 0.35, 3)
    if cuts_per_second <= 0.8:
        return round(0.35 + ((cuts_per_second - 0.3) / 0.5) * 0.45, 3)
    return round(min(1.0, 0.8 + ((cuts_per_second - 0.8) / 0.7) * 0.2), 3)
