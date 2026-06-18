"""Lightweight voice emotion/prosody fusion."""

from __future__ import annotations


def estimate_voice_intensity(
    *,
    rms_energy: list[float],
    pitch_variance: list[float],
    speech_rate: list[float],
    beat_drop: list[float] | None = None,
    laughter_scream: list[float] | None = None,
) -> list[float]:
    """Estimate per-second vocal intensity/arousal in [0, 1]."""
    n = max(
        len(rms_energy),
        len(pitch_variance),
        len(speech_rate),
        len(beat_drop or []),
        len(laughter_scream or []),
    )
    norm_pitch_variance = _normalize(pitch_variance)
    norm_speech_rate = _normalize(speech_rate)

    values: list[float] = []
    for index in range(n):
        score = 0.45 * _at(rms_energy, index, 0.0)
        score += 0.2 * _at(norm_pitch_variance, index, 0.0)
        score += 0.15 * _at(norm_speech_rate, index, 0.0)
        score += 0.1 * _at(beat_drop or [], index, 0.0)
        score += 0.1 * _at(laughter_scream or [], index, 0.0)
        values.append(round(min(1.0, max(0.0, score)), 6))
    return values


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
