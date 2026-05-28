"""Timeline builder — converts raw frame signals into normalized timeline entries."""

from __future__ import annotations

import math

from ..schemas.analysis import TimelineEntry


def _normalize(values: list[float]) -> list[float]:
    """Min-max normalize a list of values to [0, 1]."""
    if not values:
        return values
    lo, hi = min(values), max(values)
    spread = hi - lo
    if spread < 1e-9:
        return [0.5] * len(values)
    return [(v - lo) / spread for v in values]


def _smooth(values: list[float], window: int = 3) -> list[float]:
    """Simple moving average smoothing."""
    if len(values) <= window:
        return values
    smoothed: list[float] = []
    half = window // 2
    for i in range(len(values)):
        start = max(0, i - half)
        end = min(len(values), i + half + 1)
        smoothed.append(sum(values[start:end]) / (end - start))
    return smoothed


def build_timeline(
    duration_seconds: float,
    frame_diffs: list[float],
    brightness: list[float],
    interval_seconds: float = 1.0,
) -> list[TimelineEntry]:
    """Build a heuristic timeline from visual signals.

    Scores computed:
    - virality: based on motion/novelty (frame diffs)
    - arousal: rising pattern + motion peaks
    - valence: derived from brightness stability
    - retention: high at start, dips at low-motion areas, recovers at peaks
    """
    n = len(frame_diffs)
    if n == 0:
        return []

    # Normalize raw signals
    norm_diffs = _normalize(frame_diffs)
    norm_bright = _normalize(brightness) if brightness else [0.5] * n

    # Smooth for less noisy curves
    smooth_diffs = _smooth(norm_diffs, window=3)

    entries: list[TimelineEntry] = []
    retention_values_so_far: list[float] = []
    for i in range(n):
        t = i * interval_seconds
        if t > duration_seconds:
            break

        motion = smooth_diffs[i]
        bright = norm_bright[i] if i < len(norm_bright) else 0.5

        # Virality: heavily motion-driven with hook bonus for first 3 seconds
        hook_bonus = 0.15 * math.exp(-t / 3.0)
        virality = min(1.0, 0.3 + 0.5 * motion + hook_bonus + 0.1 * bright)

        # Arousal: ramps up from baseline, motion adds peaks
        ramp = min(1.0, 0.3 + 0.4 * (1 - math.exp(-t / 8.0)))
        arousal = min(1.0, ramp * 0.6 + motion * 0.4)

        # Valence: brightness-driven with slight stability bonus
        valence = min(1.0, 0.4 + 0.4 * bright + 0.1 * motion)

        # Retention: starts high, decays slowly, motion peaks recover it
        base_retention = 0.92 - 0.15 * (t / max(duration_seconds, 1.0))
        retention = min(1.0, max(0.3, base_retention + 0.2 * motion))

        # Labels for notable moments
        label = None
        if i == 0:
            label = "Hook open"
        elif motion > 0.8 and (i == 0 or smooth_diffs[i - 1] < 0.6):
            label = "Pattern disruption"
        elif i > 2 and retention < 0.6 and retention_values_so_far and retention < min(retention_values_so_far[-3:]):
            label = "Retention dip"
        elif i > 0 and motion > 0.55 and smooth_diffs[i - 1] < 0.3:
            label = "Motion spike"
        elif i == n - 1:
            label = "End frame"
        retention_values_so_far.append(retention)

        entries.append(
            TimelineEntry(
                time_seconds=round(t, 2),
                virality=round(virality, 3),
                valence=round(valence, 3),
                arousal=round(arousal, 3),
                retention=round(retention, 3),
                label=label,
            )
        )

    return entries
