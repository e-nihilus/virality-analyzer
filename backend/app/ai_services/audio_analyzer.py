"""Audio analyzer — optional prosody, event, and emotion features.

Uses librosa when available and returns None when the optional dependency or
feature flag is unavailable.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from .audio_emotion import estimate_voice_intensity
from .audio_events import detect_beat_drops, detect_laughter_scream

logger = logging.getLogger(__name__)

try:
    import librosa
    import numpy as np

    _LIBROSA_IMPORTABLE = True
except ImportError:
    _LIBROSA_IMPORTABLE = False


@dataclass
class AudioFeatures:
    """Per-second audio features aligned to the video timeline."""

    rms_energy: list[float] = field(default_factory=list)
    silence_mask: list[bool] = field(default_factory=list)
    energy_change: list[float] = field(default_factory=list)
    pitch_hz: list[float] = field(default_factory=list)
    pitch_variance: list[float] = field(default_factory=list)
    speech_rate: list[float] = field(default_factory=list)
    beat_drop: list[float] = field(default_factory=list)
    laughter_scream: list[float] = field(default_factory=list)
    voice_intensity: list[float] = field(default_factory=list)
    duration_seconds: float = 0.0


def librosa_available() -> bool:
    """Return True when librosa is importable AND the feature flag is on."""
    enabled = os.environ.get("AUREA_AUDIO_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    return _LIBROSA_IMPORTABLE and enabled


def analyze_audio(wav_path: str, interval_seconds: float = 1.0) -> AudioFeatures | None:
    """Compute per-second audio features from a WAV file.

    Returns None when librosa is unavailable or on error.
    """
    if not librosa_available():
        logger.debug("librosa not available or disabled — skipping audio analysis")
        return None

    try:
        y, sr = librosa.load(wav_path, sr=22050, mono=True)
        duration = librosa.get_duration(y=y, sr=sr)

        hop_length = int(sr * interval_seconds)
        n_frames = int(len(y) / hop_length)

        if n_frames < 2:
            logger.warning("Audio too short for analysis (%0.1fs)", duration)
            return None

        rms_raw: list[float] = []
        pitch_hz: list[float] = []
        pitch_variance: list[float] = []
        speech_rate_raw: list[float] = []
        for i in range(n_frames):
            start = i * hop_length
            end = min(start + hop_length, len(y))
            chunk = y[start:end]
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            rms_raw.append(rms)
            pitch_mean, pitch_var = _estimate_pitch(chunk, sr)
            pitch_hz.append(pitch_mean)
            pitch_variance.append(pitch_var)
            speech_rate_raw.append(_estimate_speech_rate(chunk, sr))

        # Normalize RMS to [0, 1]
        max_rms = max(rms_raw) if rms_raw else 1.0
        if max_rms < 1e-9:
            max_rms = 1.0
        rms_norm = [v / max_rms for v in rms_raw]

        # Silence detection: below 5% of max RMS
        silence_threshold = 0.05
        silence_mask = [v < silence_threshold for v in rms_norm]

        # Energy changes (absolute delta between consecutive frames)
        energy_change = [0.0]
        for i in range(1, len(rms_norm)):
            energy_change.append(abs(rms_norm[i] - rms_norm[i - 1]))

        speech_rate = _normalize(speech_rate_raw)
        beat_drop = detect_beat_drops(
            rms_energy=rms_norm,
            energy_change=energy_change,
        )
        laughter_scream = detect_laughter_scream(
            rms_energy=rms_norm,
            pitch_hz=pitch_hz,
            pitch_variance=pitch_variance,
        )
        voice_intensity = estimate_voice_intensity(
            rms_energy=rms_norm,
            pitch_variance=pitch_variance,
            speech_rate=speech_rate,
            beat_drop=beat_drop,
            laughter_scream=laughter_scream,
        )

        return AudioFeatures(
            rms_energy=rms_norm,
            silence_mask=silence_mask,
            energy_change=energy_change,
            pitch_hz=[round(v, 3) for v in pitch_hz],
            pitch_variance=[round(v, 3) for v in pitch_variance],
            speech_rate=speech_rate,
            beat_drop=beat_drop,
            laughter_scream=laughter_scream,
            voice_intensity=voice_intensity,
            duration_seconds=round(duration, 3),
        )
    except Exception:
        logger.exception("Audio analysis error for %s", wav_path)
        return None


def _estimate_pitch(chunk: "np.ndarray", sr: int) -> tuple[float, float]:
    """Estimate pitch mean and variance for a short chunk.

    ``librosa.yin`` can fail on silence or extremely short chunks; in that case
    pitch defaults to zero so downstream features stay aligned.
    """
    if len(chunk) < max(32, int(sr * 0.05)):
        return 0.0, 0.0
    try:
        f0 = librosa.yin(chunk, fmin=50, fmax=500, sr=sr)
        valid = f0[np.isfinite(f0)]
        valid = valid[(valid >= 50) & (valid <= 500)]
        if len(valid) == 0:
            return 0.0, 0.0
        return float(np.median(valid)), float(np.var(valid))
    except Exception:
        return 0.0, 0.0


def _estimate_speech_rate(chunk: "np.ndarray", sr: int) -> float:
    """Approximate speech/activity rate from onset density per second."""
    if len(chunk) < max(32, int(sr * 0.05)):
        return 0.0
    try:
        onset_env = librosa.onset.onset_strength(y=chunk, sr=sr)
        if onset_env.size == 0:
            return 0.0
        threshold = float(np.mean(onset_env) + 0.5 * np.std(onset_env))
        active = float(np.sum(onset_env > threshold))
        seconds = max(len(chunk) / sr, 1e-6)
        return active / seconds
    except Exception:
        return 0.0


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    spread = hi - lo
    if spread < 1e-9:
        return [0.5 for _ in values]
    return [round((value - lo) / spread, 6) for value in values]
