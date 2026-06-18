"""Face emotion adapter outputs for multimodal V/A fusion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmotionSignal:
    valence: float
    arousal: float
    emotion: str
    confidence: float
    provider: str


def face_signals_from_deepface(
    *,
    valence: list[float] | None,
    arousal: list[float] | None,
    dominant_emotions: list[str | None] | None = None,
) -> list[EmotionSignal]:
    """Convert DeepFace V/A arrays to fusion-ready signals."""
    n = max(len(valence or []), len(arousal or []), len(dominant_emotions or []))
    signals: list[EmotionSignal] = []
    for index in range(n):
        v = _at(valence, index, 0.5)
        a = _at(arousal, index, 0.5)
        emotion = (
            dominant_emotions[index]
            if dominant_emotions is not None and index < len(dominant_emotions) and dominant_emotions[index]
            else emotion_from_valence_arousal(v, a)
        )
        confidence = 0.78 if dominant_emotions and index < len(dominant_emotions) and dominant_emotions[index] else 0.62
        signals.append(EmotionSignal(
            valence=v,
            arousal=a,
            emotion=emotion or "Neutral",
            confidence=confidence,
            provider="deepface",
        ))
    return signals


def emotion_from_valence_arousal(valence: float, arousal: float) -> str:
    if arousal >= 0.68 and valence >= 0.6:
        return "Excitement"
    if arousal >= 0.68 and valence < 0.45:
        return "Tension"
    if arousal >= 0.62:
        return "Surprise"
    if valence >= 0.62:
        return "Joy"
    if valence <= 0.35 and arousal <= 0.5:
        return "Sadness"
    if valence <= 0.4:
        return "Tension"
    return "Neutral"


def _at(values: list[float] | None, index: int, default: float) -> float:
    if values is not None and 0 <= index < len(values):
        try:
            return min(1.0, max(0.0, float(values[index])))
        except (TypeError, ValueError):
            return default
    return default
