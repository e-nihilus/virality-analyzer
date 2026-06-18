"""Multimodal valence/arousal fusion."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ...schemas.analysis import TextHook, TimelineEntry, TranscriptSegment
from .face_emotion import EmotionSignal, emotion_from_valence_arousal, face_signals_from_deepface
from .text_emotion import TextEmotionSegment, TextHookSignal, text_emotion_signals


@dataclass(frozen=True)
class MultimodalEmotionPoint:
    timestamp: float
    valence: float
    arousal: float
    emotion: str
    confidence: float
    providers: list[str] = field(default_factory=list)


def fuse_timeline_valence_arousal(
    *,
    timeline: list[TimelineEntry],
    face_valence: list[float] | None = None,
    face_arousal: list[float] | None = None,
    face_dominant_emotions: list[str | None] | None = None,
    audio_voice_intensity: list[float] | None = None,
    audio_beat_drop: list[float] | None = None,
    audio_laughter_scream: list[float] | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    text_hooks: list[TextHook] | None = None,
    sample_interval_seconds: float = 1.0,
) -> list[MultimodalEmotionPoint]:
    """Fuse facial + audio + text signals and mutate timeline V/A in place."""
    timestamps = [entry.time_seconds for entry in timeline]
    face_signals = face_signals_from_deepface(
        valence=face_valence,
        arousal=face_arousal,
        dominant_emotions=face_dominant_emotions,
    )
    text_signals = text_emotion_signals(
        timestamps=timestamps,
        segments=[
            TextEmotionSegment(start=s.start, end=s.end, text=s.text)
            for s in transcript_segments or []
        ],
        hooks=[
            TextHookSignal(timestamp=h.timestamp, hook_type=h.hook_type, confidence=h.confidence)
            for h in text_hooks or []
        ],
        window_seconds=sample_interval_seconds,
    )

    points: list[MultimodalEmotionPoint] = []
    for index, entry in enumerate(timeline):
        signals = [
            EmotionSignal(
                valence=entry.valence if entry.valence is not None else 0.5,
                arousal=entry.arousal if entry.arousal is not None else 0.5,
                emotion=emotion_from_valence_arousal(
                    entry.valence if entry.valence is not None else 0.5,
                    entry.arousal if entry.arousal is not None else 0.5,
                ),
                confidence=0.32,
                provider="timeline_base",
            )
        ]
        if index < len(face_signals):
            signals.append(face_signals[index])
        audio_signal = _audio_signal_for_index(
            index=index,
            voice_intensity=audio_voice_intensity,
            beat_drop=audio_beat_drop,
            laughter_scream=audio_laughter_scream,
        )
        if audio_signal.confidence > 0.0:
            signals.append(audio_signal)
        if index < len(text_signals) and text_signals[index].confidence > 0.0:
            signals.append(text_signals[index])

        point = _weighted_fusion(entry.time_seconds, signals)
        entry.valence = point.valence
        entry.arousal = point.arousal
        entry.emotion = point.emotion
        entry.emotion_confidence = point.confidence
        points.append(point)
    return points


def dominant_emotion_from_points(points: list[MultimodalEmotionPoint]) -> str | None:
    confident = [point.emotion for point in points if point.confidence >= 0.3]
    if not confident:
        return None
    return Counter(confident).most_common(1)[0][0]


def _audio_signal_for_index(
    *,
    index: int,
    voice_intensity: list[float] | None,
    beat_drop: list[float] | None,
    laughter_scream: list[float] | None,
) -> EmotionSignal:
    voice = _at(voice_intensity, index, 0.0)
    beat = _at(beat_drop, index, 0.0)
    vocal_event = _at(laughter_scream, index, 0.0)
    arousal = min(1.0, max(voice, beat, vocal_event, 0.45 + 0.35 * voice))
    valence = 0.5
    if vocal_event > 0.0:
        valence = 0.58
    if beat > 0.0:
        valence = max(valence, 0.56)
    confidence = min(0.72, max(voice, beat, vocal_event) * 0.75)
    return EmotionSignal(
        valence=round(valence, 6),
        arousal=round(arousal, 6),
        emotion=emotion_from_valence_arousal(valence, arousal),
        confidence=round(confidence, 6),
        provider="audio_prosody",
    )


def _weighted_fusion(timestamp: float, signals: list[EmotionSignal]) -> MultimodalEmotionPoint:
    total_weight = sum(max(signal.confidence, 0.0) for signal in signals) or 1.0
    valence = sum(signal.valence * max(signal.confidence, 0.0) for signal in signals) / total_weight
    arousal = sum(signal.arousal * max(signal.confidence, 0.0) for signal in signals) / total_weight
    emotion = emotion_from_valence_arousal(valence, arousal)
    providers = [signal.provider for signal in signals if signal.confidence > 0.0]
    confidence = min(1.0, total_weight / max(len(providers), 1))
    return MultimodalEmotionPoint(
        timestamp=timestamp,
        valence=round(min(1.0, max(0.0, valence)), 3),
        arousal=round(min(1.0, max(0.0, arousal)), 3),
        emotion=emotion,
        confidence=round(confidence, 3),
        providers=providers,
    )


def _at(values: list[float] | None, index: int, default: float) -> float:
    if values is not None and 0 <= index < len(values):
        try:
            return min(1.0, max(0.0, float(values[index])))
        except (TypeError, ValueError):
            return default
    return default
