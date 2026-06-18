"""Heuristic audio event detectors for per-window viral features."""

from __future__ import annotations


def detect_beat_drops(
    *,
    rms_energy: list[float],
    energy_change: list[float],
    threshold: float = 0.38,
) -> list[float]:
    """Return a per-second beat/drop likelihood in [0, 1].

    A beat drop is approximated as a sudden energy jump into a loud section.
    This is intentionally lightweight and deterministic; model-backed audio
    event classifiers can replace it later without changing downstream fields.
    """
    n = max(len(rms_energy), len(energy_change))
    events: list[float] = []
    for index in range(n):
        energy = _at(rms_energy, index, 0.0)
        change = _at(energy_change, index, 0.0)
        previous_energy = _at(rms_energy, index - 1, energy) if index > 0 else energy
        is_drop = change >= threshold and energy >= 0.45 and energy >= previous_energy
        score = min(1.0, 0.65 * change + 0.35 * energy) if is_drop else 0.0
        events.append(round(score, 6))
    return events


def detect_laughter_scream(
    *,
    rms_energy: list[float],
    pitch_hz: list[float],
    pitch_variance: list[float],
    threshold: float = 0.62,
) -> list[float]:
    """Return a rough per-second laughter/scream likelihood in [0, 1].

    High energy plus high/unstable pitch is a useful fallback signal for
    laughter, shouting, and screams when no licensed audio event model is
    configured.
    """
    n = max(len(rms_energy), len(pitch_hz), len(pitch_variance))
    norm_pitch = _normalize(pitch_hz)
    norm_variance = _normalize(pitch_variance)
    events: list[float] = []
    for index in range(n):
        energy = _at(rms_energy, index, 0.0)
        pitch = _at(norm_pitch, index, 0.0)
        variance = _at(norm_variance, index, 0.0)
        score = 0.45 * energy + 0.3 * pitch + 0.25 * variance
        events.append(round(score, 6) if score >= threshold else 0.0)
    return events


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    spread = hi - lo
    if spread < 1e-9:
        return [0.5 for _ in values]
    return [(value - lo) / spread for value in values]


def _at(values: list[float], index: int, default: float) -> float:
    if 0 <= index < len(values):
        try:
            return float(values[index])
        except (TypeError, ValueError):
            return default
    return default
