"""Audio analyzer — optional RMS energy, silence detection, and energy
change analysis using librosa.  Returns None when librosa is unavailable."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

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
        for i in range(n_frames):
            start = i * hop_length
            end = min(start + hop_length, len(y))
            chunk = y[start:end]
            rms = float(np.sqrt(np.mean(chunk ** 2)))
            rms_raw.append(rms)

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

        return AudioFeatures(
            rms_energy=rms_norm,
            silence_mask=silence_mask,
            energy_change=energy_change,
            duration_seconds=round(duration, 3),
        )
    except Exception:
        logger.exception("Audio analysis error for %s", wav_path)
        return None
