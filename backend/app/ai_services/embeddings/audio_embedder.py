"""Audio window embedding adapters."""

from __future__ import annotations

from dataclasses import dataclass
import statistics

from ...processing.window_builder import TimeWindow, sample_indexes_for_window


@dataclass(frozen=True)
class AudioEmbeddingInput:
    rms_energy: list[float] | None = None
    silence_mask: list[bool] | None = None
    energy_change: list[float] | None = None
    pitch_hz: list[float] | None = None
    pitch_variance: list[float] | None = None
    speech_rate: list[float] | None = None
    beat_drop: list[float] | None = None
    laughter_scream: list[float] | None = None
    voice_intensity: list[float] | None = None
    sample_interval_seconds: float = 1.0


class ScalarAudioEmbedder:
    """Fallback audio embedder based on already-computed librosa signals."""

    provider_name = "scalar_audio_fallback"
    dimension = 16

    def embed_windows(
        self,
        *,
        windows: list[TimeWindow],
        inputs: AudioEmbeddingInput,
    ) -> list[list[float]]:
        sample_count = max(
            len(inputs.rms_energy or []),
            len(inputs.silence_mask or []),
            len(inputs.energy_change or []),
            len(inputs.pitch_hz or []),
            len(inputs.pitch_variance or []),
            len(inputs.speech_rate or []),
            len(inputs.beat_drop or []),
            len(inputs.laughter_scream or []),
            len(inputs.voice_intensity or []),
            1,
        )
        return [self._embed_window(window, inputs, sample_count) for window in windows]

    def _embed_window(
        self,
        window: TimeWindow,
        inputs: AudioEmbeddingInput,
        sample_count: int,
    ) -> list[float]:
        indexes = sample_indexes_for_window(
            window,
            sample_interval_seconds=inputs.sample_interval_seconds,
            sample_count=sample_count,
        )
        energy = _values_at(inputs.rms_energy, indexes, default=0.0)
        changes = _values_at(inputs.energy_change, indexes, default=0.0)
        silence = _bool_values_at(inputs.silence_mask, indexes, default=True)
        pitch = _normalize_pitch(_values_at(inputs.pitch_hz, indexes, default=0.0))
        pitch_variance = _normalize_variance(_values_at(inputs.pitch_variance, indexes, default=0.0))
        speech_rate = _values_at(inputs.speech_rate, indexes, default=0.0)
        beat_drop = _values_at(inputs.beat_drop, indexes, default=0.0)
        laughter_scream = _values_at(inputs.laughter_scream, indexes, default=0.0)
        voice_intensity = _values_at(inputs.voice_intensity, indexes, default=0.0)
        voiced_ratio = 1.0 - (sum(1 for value in silence if value) / max(len(silence), 1))

        return [
            _mean(energy),
            _std(energy),
            max(energy, default=0.0),
            _mean(changes),
            max(changes, default=0.0),
            round(voiced_ratio, 6),
            1.0 if max(changes, default=0.0) >= 0.4 else 0.0,
            _mean(pitch),
            _std(pitch),
            _mean(pitch_variance),
            max(pitch_variance, default=0.0),
            _mean(speech_rate),
            max(beat_drop, default=0.0),
            max(laughter_scream, default=0.0),
            _mean(voice_intensity),
            max(voice_intensity, default=0.0),
        ]


def _values_at(values: list[float] | None, indexes: list[int], *, default: float) -> list[float]:
    if not indexes:
        return [default]
    if not values:
        return [default for _ in indexes]
    result: list[float] = []
    for index in indexes:
        try:
            result.append(float(values[index]) if 0 <= index < len(values) else default)
        except (TypeError, ValueError):
            result.append(default)
    return result


def _bool_values_at(values: list[bool] | None, indexes: list[int], *, default: bool) -> list[bool]:
    if not indexes:
        return [default]
    if not values:
        return [default for _ in indexes]
    return [bool(values[index]) if 0 <= index < len(values) else default for index in indexes]


def _normalize_pitch(values: list[float]) -> list[float]:
    # Human voice fallback range used by audio_analyzer's YIN extraction.
    return [min(1.0, max(0.0, value / 500.0)) for value in values]


def _normalize_variance(values: list[float]) -> list[float]:
    return [min(1.0, max(0.0, value / 10_000.0)) for value in values]


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def _std(values: list[float]) -> float:
    return round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0
