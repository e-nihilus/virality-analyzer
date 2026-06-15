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
    audio_energy: list[float] | None = None,
    audio_silence: list[bool] | None = None,
    audio_energy_change: list[float] | None = None,
    face_valence: list[float] | None = None,
    face_arousal: list[float] | None = None,
    detection_density: list[float] | None = None,
) -> list[TimelineEntry]:
    """Build a heuristic timeline from visual and optional audio signals.

    Scores computed:
    - virality: based on motion/novelty (frame diffs) + audio energy + YOLO detection density
    - arousal: face emotion (DeepFace) blended with motion peaks + audio energy
    - valence: face emotion (DeepFace) blended with brightness stability
    - retention: high at start, dips at low-motion/silence areas, recovers at peaks

    When face emotion signals are provided (from DeepFace per-frame analysis),
    arousal and valence use 60%/70% face data blended with heuristic signals.
    When detection density is provided (from YOLO), virality gets a boost
    proportional to the number of detected objects per frame.
    """
    n = len(frame_diffs)
    if n == 0:
        return []

    has_audio = audio_energy is not None and len(audio_energy) > 0

    # Normalize raw signals
    norm_diffs = _normalize(frame_diffs)
    norm_bright = _normalize(brightness) if brightness else [0.5] * n

    # Smooth for less noisy curves
    smooth_diffs = _smooth(norm_diffs, window=3)

    # Audio signals are already normalized [0, 1] from audio_analyzer
    smooth_audio = _smooth(audio_energy, window=3) if has_audio else None
    smooth_audio_change = _smooth(audio_energy_change, window=3) if audio_energy_change else None

    entries: list[TimelineEntry] = []
    retention_values_so_far: list[float] = []
    for i in range(n):
        t = i * interval_seconds
        if t > duration_seconds:
            break

        motion = smooth_diffs[i]
        bright = norm_bright[i] if i < len(norm_bright) else 0.5
        energy = smooth_audio[i] if smooth_audio and i < len(smooth_audio) else 0.0
        is_silent = audio_silence[i] if audio_silence and i < len(audio_silence) else False
        e_change = smooth_audio_change[i] if smooth_audio_change and i < len(smooth_audio_change) else 0.0
        f_valence = face_valence[i] if face_valence and i < len(face_valence) else None
        f_arousal = face_arousal[i] if face_arousal and i < len(face_arousal) else None
        det_density = detection_density[i] if detection_density and i < len(detection_density) else 0.0

        has_face = f_valence is not None and f_arousal is not None

        # Virality: motion-driven + audio energy boost
        hook_bonus = 0.15 * math.exp(-t / 3.0)
        if has_audio:
            virality = min(1.0, 0.25 + 0.4 * motion + 0.15 * energy + hook_bonus + 0.1 * bright + 0.1 * e_change)
        else:
            virality = min(1.0, 0.3 + 0.5 * motion + hook_bonus + 0.1 * bright)

        # YOLO detection density boosts virality (more objects/people = more engaging)
        virality = min(1.0, virality + 0.12 * det_density)

        # Arousal: blend face-based with motion-based when DeepFace data is available
        ramp = min(1.0, 0.3 + 0.4 * (1 - math.exp(-t / 8.0)))
        if has_face:
            motion_arousal = ramp * 0.5 + motion * 0.3 + (energy * 0.2 if has_audio else motion * 0.1)
            arousal = min(1.0, 0.4 * motion_arousal + 0.6 * f_arousal)
        elif has_audio:
            arousal = min(1.0, ramp * 0.5 + motion * 0.3 + energy * 0.2)
        else:
            arousal = min(1.0, ramp * 0.6 + motion * 0.4)

        # Valence: use face-derived valence when available, else brightness-based
        if has_face:
            bright_valence = 0.4 + 0.4 * bright + 0.1 * motion
            valence = min(1.0, 0.3 * bright_valence + 0.7 * f_valence)
        else:
            valence = min(1.0, 0.4 + 0.4 * bright + 0.1 * motion)

        # Retention: starts high, decays slowly, motion/audio peaks recover it
        base_retention = 0.92 - 0.15 * (t / max(duration_seconds, 1.0))
        if has_audio:
            silence_penalty = -0.1 if is_silent else 0.0
            retention = min(1.0, max(0.3, base_retention + 0.15 * motion + 0.1 * energy + silence_penalty))
        else:
            retention = min(1.0, max(0.3, base_retention + 0.2 * motion))

        # Labels for notable moments
        label = None
        if i == 0:
            label = "Hook open"
        elif motion > 0.8 and (i == 0 or smooth_diffs[i - 1] < 0.6):
            label = "Pattern disruption"
        elif has_audio and is_silent and i > 1 and not (audio_silence and audio_silence[i - 1]):
            label = "Silence gap"
        elif i > 2 and retention < 0.6 and retention_values_so_far and retention < min(retention_values_so_far[-3:]):
            label = "Retention dip"
        elif i > 0 and motion > 0.55 and smooth_diffs[i - 1] < 0.3:
            label = "Motion spike"
        elif has_audio and e_change > 0.4 and i > 0:
            label = "Audio spike"
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
