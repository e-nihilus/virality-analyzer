"""Emotion analyzer adapters for heuristic and DeepFace providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .provider_exceptions import ProviderDependencyError


class EmotionAnalyzerAdapter(ABC):
    """Abstraction for deriving dominant emotion from a timeline."""

    provider_name = "heuristic"

    def validate_dependencies(self) -> None:
        """Validate optional provider dependencies."""

    @abstractmethod
    def dominant_emotion(self, *, timeline: list[object]) -> str:
        """Return a dominant emotion label for the analyzed video."""


class HeuristicEmotionAnalyzer(EmotionAnalyzerAdapter):
    """Current dominant-emotion heuristic based on arousal/valence averages."""

    provider_name = "heuristic"

    def dominant_emotion(self, *, timeline: list[object]) -> str:
        if not timeline:
            return "Neutral"

        avg_arousal = sum(getattr(e, "arousal", None) or 0.5 for e in timeline) / len(timeline)
        avg_valence = sum(getattr(e, "valence", None) or 0.5 for e in timeline) / len(timeline)

        if avg_arousal > 0.65 and avg_valence > 0.6:
            return "Excitement"
        if avg_arousal > 0.65 and avg_valence <= 0.6:
            return "Tension"
        if avg_arousal > 0.5 and avg_valence > 0.5:
            return "Surprise"
        if avg_valence > 0.6:
            return "Joy"
        if avg_valence < 0.4:
            return "Sadness"
        return "Neutral"


class DeepFaceEmotionAnalyzer(EmotionAnalyzerAdapter):
    """DeepFace provider placeholder.

    This adapter currently returns the heuristic emotion while preserving lazy
    dependency checks and provider wiring for future real model integration.
    """

    provider_name = "deepface"

    def __init__(self, fallback: EmotionAnalyzerAdapter | None = None) -> None:
        self._fallback = fallback or HeuristicEmotionAnalyzer()

    def validate_dependencies(self) -> None:
        try:
            import deepface  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "DeepFace provider requested but 'deepface' is not installed"
            ) from exc

    def dominant_emotion(self, *, timeline: list[object]) -> str:
        self.validate_dependencies()

        # TODO(phase-14): analyze sampled video frames with DeepFace and fuse
        # temporal emotion predictions into a dominant emotion label.
        return self._fallback.dominant_emotion(timeline=timeline)
