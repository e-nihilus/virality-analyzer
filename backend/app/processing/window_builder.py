"""Temporal window construction for multimodal feature extraction."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class TimeWindow:
    """A fixed-width temporal window over the source video."""

    index: int
    start_seconds: float
    end_seconds: float

    @property
    def center_seconds(self) -> float:
        return round((self.start_seconds + self.end_seconds) / 2.0, 3)


def build_windows(
    duration_seconds: float,
    *,
    window_seconds: float = 3.0,
    stride_seconds: float = 1.0,
) -> list[TimeWindow]:
    """Build overlapping windows for temporal embeddings.

    Windows are 3s/stride 1s by default, as required by planV2 Fase 1. Very
    short videos still produce one partial window so every analysis can persist
    a feature tensor.
    """
    duration = max(0.0, float(duration_seconds or 0.0))
    window = max(0.001, float(window_seconds))
    stride = max(0.001, float(stride_seconds))

    if duration <= 0.0:
        return [TimeWindow(index=0, start_seconds=0.0, end_seconds=round(window, 3))]

    max_start = max(0.0, duration - window)
    count = max(1, int(math.floor(max_start / stride)) + 1)

    windows: list[TimeWindow] = []
    for index in range(count):
        start = round(index * stride, 3)
        end = round(min(duration, start + window), 3)
        windows.append(TimeWindow(index=index, start_seconds=start, end_seconds=end))
    return windows


def sample_indexes_for_window(
    window: TimeWindow,
    *,
    sample_interval_seconds: float,
    sample_count: int,
) -> list[int]:
    """Return sampled-signal indexes whose timestamps overlap a window."""
    if sample_count <= 0:
        return []
    interval = max(0.001, float(sample_interval_seconds))
    indexes: list[int] = []
    for index in range(sample_count):
        timestamp = index * interval
        if window.start_seconds <= timestamp < window.end_seconds:
            indexes.append(index)
    if indexes:
        return indexes

    nearest = min(sample_count - 1, max(0, int(round(window.start_seconds / interval))))
    return [nearest]
