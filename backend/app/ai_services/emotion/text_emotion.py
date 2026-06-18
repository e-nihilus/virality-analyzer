"""Text emotion fallback adapter.

This is a deterministic lexicon/hook based substitute for GoEmotions/DeBERTa
until a licensed model is selected. It supports English and common Spanish
short-form-video emotion words.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from .face_emotion import EmotionSignal, emotion_from_valence_arousal


@dataclass(frozen=True)
class TextEmotionSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class TextHookSignal:
    timestamp: float
    hook_type: str
    confidence: float


_POSITIVE = {
    "amazing", "awesome", "best", "happy", "love", "wow", "incredible",
    "genial", "increible", "increíble", "feliz", "amo", "mejor", "brutal",
}
_NEGATIVE = {
    "bad", "angry", "hate", "sad", "wrong", "terrible", "problem", "fear",
    "malo", "odio", "triste", "mal", "error", "problema", "miedo", "fatal",
}
_AROUSAL = {
    "now", "urgent", "shocking", "crazy", "insane", "secret", "wait", "stop",
    "ahora", "urgente", "impactante", "loco", "secreto", "espera", "mira", "atención",
}

_HOOK_AROUSAL = {
    "curiosity_gap": 0.72,
    "urgency": 0.82,
    "conflict": 0.78,
    "question": 0.62,
    "command": 0.72,
    "surprise": 0.82,
}


def text_emotion_signals(
    *,
    timestamps: list[float],
    segments: list[TextEmotionSegment],
    hooks: list[TextHookSignal] | None = None,
    window_seconds: float = 1.0,
) -> list[EmotionSignal]:
    signals: list[EmotionSignal] = []
    for timestamp in timestamps:
        window_end = timestamp + window_seconds
        text = " ".join(
            segment.text
            for segment in segments
            if segment.text and segment.end > timestamp and segment.start < window_end
        )
        hook = next(
            (
                h for h in hooks or []
                if timestamp <= h.timestamp < window_end
            ),
            None,
        )
        signals.append(_signal_for_text(text, hook))
    return signals


def _signal_for_text(text: str, hook: TextHookSignal | None) -> EmotionSignal:
    tokens = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", text.lower())
    if not tokens and hook is None:
        return EmotionSignal(0.5, 0.5, "Neutral", 0.0, "text_lexicon")

    positive = sum(1 for token in tokens if token in _POSITIVE)
    negative = sum(1 for token in tokens if token in _NEGATIVE)
    arousal_hits = sum(1 for token in tokens if token in _AROUSAL)
    sentiment_total = max(positive + negative, 1)
    valence = 0.5 + 0.28 * ((positive - negative) / sentiment_total)
    arousal = 0.45 + min(0.25, 0.08 * arousal_hits)
    confidence = min(0.55, 0.18 + 0.08 * (positive + negative + arousal_hits))

    if hook is not None:
        arousal = max(arousal, _HOOK_AROUSAL.get(hook.hook_type, 0.6))
        confidence = max(confidence, min(0.75, 0.35 + hook.confidence * 0.35))
        if hook.hook_type == "conflict":
            valence = min(valence, 0.42)
        elif hook.hook_type in {"surprise", "curiosity_gap"}:
            valence = max(valence, 0.56)

    valence = min(1.0, max(0.0, valence))
    arousal = min(1.0, max(0.0, arousal))
    return EmotionSignal(
        valence=round(valence, 6),
        arousal=round(arousal, 6),
        emotion=emotion_from_valence_arousal(valence, arousal),
        confidence=round(confidence, 6),
        provider="text_lexicon",
    )
