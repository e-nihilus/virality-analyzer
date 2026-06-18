"""Video window embedding adapters.

The default implementation intentionally uses the visual signals that the
pipeline already extracted (motion, brightness, detections, V/A) so Fase 1 can
run without downloading heavyweight V-JEPA2/InternVideo2/VideoMAE backbones. A
future model-backed adapter can keep the same ``embed_windows`` contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import statistics

from ...processing.window_builder import TimeWindow, sample_indexes_for_window


@dataclass(frozen=True)
class VideoEmbeddingInput:
    frame_diffs: list[float]
    brightness: list[float]
    detection_density: list[float] | None = None
    face_valence: list[float] | None = None
    face_arousal: list[float] | None = None
    sample_interval_seconds: float = 1.0


class ScalarVideoEmbedder:
    """Fallback video embedder based on existing per-second visual signals."""

    provider_name = "scalar_video_fallback"
    dimension = 12

    def embed_windows(
        self,
        *,
        windows: list[TimeWindow],
        inputs: VideoEmbeddingInput,
    ) -> list[list[float]]:
        normalized_inputs = VideoEmbeddingInput(
            frame_diffs=_normalize_minmax(inputs.frame_diffs),
            brightness=inputs.brightness,
            detection_density=inputs.detection_density,
            face_valence=inputs.face_valence,
            face_arousal=inputs.face_arousal,
            sample_interval_seconds=inputs.sample_interval_seconds,
        )
        sample_count = max(
            len(normalized_inputs.frame_diffs),
            len(normalized_inputs.brightness),
            len(normalized_inputs.detection_density or []),
            len(normalized_inputs.face_valence or []),
            len(normalized_inputs.face_arousal or []),
        )
        return [self._embed_window(window, normalized_inputs, sample_count) for window in windows]

    def _embed_window(
        self,
        window: TimeWindow,
        inputs: VideoEmbeddingInput,
        sample_count: int,
    ) -> list[float]:
        indexes = sample_indexes_for_window(
            window,
            sample_interval_seconds=inputs.sample_interval_seconds,
            sample_count=sample_count,
        )
        motion = _values_at(inputs.frame_diffs, indexes, default=0.0)
        brightness = _normalize_255(_values_at(inputs.brightness, indexes, default=127.5))
        detections = _values_at(inputs.detection_density, indexes, default=0.0)
        valence = _values_at(inputs.face_valence, indexes, default=0.5)
        arousal = _values_at(inputs.face_arousal, indexes, default=0.0)

        return [
            _mean(motion),
            _std(motion),
            max(motion, default=0.0),
            _mean(brightness),
            _std(brightness),
            max(brightness, default=0.0),
            _mean(detections),
            max(detections, default=0.0),
            _mean(valence),
            _std(valence),
            _mean(arousal),
            max(arousal, default=0.0),
        ]


def _values_at(values: list[float] | None, indexes: list[int], *, default: float) -> list[float]:
    if not indexes:
        return [default]
    if not values:
        return [default for _ in indexes]
    result: list[float] = []
    for index in indexes:
        if 0 <= index < len(values):
            result.append(_as_float(values[index], default=default))
        else:
            result.append(default)
    return result


def _normalize_255(values: list[float]) -> list[float]:
    return [min(1.0, max(0.0, value / 255.0)) for value in values]


def _normalize_minmax(values: list[float]) -> list[float]:
    if not values:
        return []
    numeric = [_as_float(value, default=0.0) for value in values]
    lo = min(numeric)
    hi = max(numeric)
    spread = hi - lo
    if spread < 1e-9:
        return [0.5 for _ in numeric]
    return [(value - lo) / spread for value in numeric]


def _as_float(value: object, *, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _std(values: list[float]) -> float:
    return round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0
