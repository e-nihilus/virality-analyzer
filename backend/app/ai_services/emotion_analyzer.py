"""Emotion analyzer adapters for heuristic and DeepFace providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import Counter

from .provider_exceptions import ProviderDependencyError

logger = logging.getLogger(__name__)


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
    """DeepFace provider – analyses sampled video frames for dominant emotion.

    If *video_path* is supplied at construction time, frames are eagerly sampled
    (every *interval_seconds*) and analysed with DeepFace.  The most frequent
    emotion across all frames becomes the pre-computed result returned by
    :meth:`dominant_emotion`.  When no video path is given, or when frame
    analysis fails entirely, the adapter falls back to the heuristic provider.
    """

    provider_name = "deepface"

    _LABEL_MAP: dict[str, str] = {
        "happy": "Joy",
        "sad": "Sadness",
        "angry": "Tension",
        "surprise": "Surprise",
        "fear": "Tension",
        "disgust": "Tension",
        "neutral": "Neutral",
    }

    def __init__(
        self,
        fallback: EmotionAnalyzerAdapter | None = None,
        video_path: str | None = None,
        interval_seconds: float = 2.0,
    ) -> None:
        self._fallback = fallback or HeuristicEmotionAnalyzer()
        self._precomputed: str | None = None

        if video_path is not None:
            self._precomputed = self._analyze_video(video_path, interval_seconds)

    def validate_dependencies(self) -> None:
        try:
            import deepface  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "DeepFace provider requested but 'deepface' is not installed"
            ) from exc

    def dominant_emotion(self, *, timeline: list[object]) -> str:
        if self._precomputed is not None:
            return self._precomputed
        return self._fallback.dominant_emotion(timeline=timeline)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyze_video(self, video_path: str, interval_seconds: float) -> str | None:
        """Sample frames from *video_path* and return the most frequent mapped emotion."""
        self.validate_dependencies()

        try:
            import cv2
        except ImportError:
            logger.warning("opencv-python is not installed – falling back to heuristic")
            return None

        from deepface import DeepFace

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("Could not open video %s – falling back to heuristic", video_path)
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_interval = max(1, int(fps * interval_seconds))
        emotion_counts: Counter[str] = Counter()
        frame_idx = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % frame_interval == 0:
                    try:
                        results = DeepFace.analyze(
                            img_path=frame,
                            actions=["emotion"],
                            enforce_detection=False,
                        )
                        result = results[0] if isinstance(results, list) else results
                        raw_emotion = result.get("dominant_emotion", "neutral")
                        mapped = self._LABEL_MAP.get(raw_emotion, "Neutral")
                        emotion_counts[mapped] += 1
                    except Exception:
                        logger.debug("DeepFace failed on frame %d – skipping", frame_idx)
                frame_idx += 1
        finally:
            cap.release()

        if not emotion_counts:
            logger.warning("All frames failed DeepFace analysis – falling back to heuristic")
            return None

        dominant = emotion_counts.most_common(1)[0][0]
        logger.info(
            "DeepFace emotion distribution: %s → dominant=%s",
            dict(emotion_counts),
            dominant,
        )
        return dominant
