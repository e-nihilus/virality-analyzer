"""Emotion analyzer adapters for heuristic and DeepFace providers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass
from importlib import metadata, util

from .provider_exceptions import ProviderDependencyError

logger = logging.getLogger(__name__)


def _tf_keras_required_but_missing() -> bool:
    """Return True for TensorFlow/Keras setups known to break RetinaFace imports."""
    if util.find_spec("tf_keras") is not None:
        return False
    try:
        version = metadata.version("tensorflow")
    except metadata.PackageNotFoundError:
        return False
    parts = version.split(".")
    try:
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        return False
    return (major, minor) >= (2, 16)


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
        self._video_path = video_path
        self._interval_seconds = interval_seconds

    def validate_dependencies(self) -> None:
        if _tf_keras_required_but_missing():
            raise ProviderDependencyError(
                "DeepFace provider requested but TensorFlow >= 2.16 requires the 'tf-keras' package"
            )
        try:
            from deepface import DeepFace  # noqa: F401
        except Exception as exc:
            raise ProviderDependencyError(
                "DeepFace provider requested but DeepFace dependencies are not available"
            ) from exc

    def dominant_emotion(self, *, timeline: list[object]) -> str:
        if self._precomputed is not None:
            return self._precomputed
        if self._video_path is not None:
            try:
                self._precomputed = self._analyze_video(self._video_path, self._interval_seconds)
            except Exception:
                logger.warning("DeepFace dominant-emotion analysis failed — using heuristic", exc_info=True)
                self._precomputed = None
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

        if _tf_keras_required_but_missing():
            logger.warning("DeepFace requires tf-keras with this TensorFlow version – falling back to heuristic")
            return None

        try:
            from deepface import DeepFace
        except Exception:
            logger.warning("DeepFace dependencies are unavailable – falling back to heuristic")
            return None

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


@dataclass
class FrameEmotionSignals:
    """Per-frame valence/arousal derived from DeepFace emotion probabilities."""
    valence: list[float]
    arousal: list[float]


# Russell's circumplex model weights for mapping discrete emotions → continuous V/A
_VALENCE_WEIGHTS: dict[str, float] = {
    "happy": 1.0,
    "surprise": 0.2,
    "neutral": 0.0,
    "sad": -0.8,
    "angry": -0.6,
    "fear": -0.7,
    "disgust": -0.8,
}

_AROUSAL_WEIGHTS: dict[str, float] = {
    "angry": 0.8,
    "fear": 0.7,
    "surprise": 0.8,
    "happy": 0.5,
    "disgust": 0.3,
    "neutral": -0.3,
    "sad": -0.5,
}


def analyze_frames_deepface(
    video_path: str,
    interval_seconds: float = 1.0,
) -> FrameEmotionSignals | None:
    """Run DeepFace per-frame and return continuous valence/arousal arrays.

    Uses Russell's circumplex model to convert DeepFace emotion probability
    distributions into continuous valence (negative→positive) and arousal
    (calm→excited) values in the [0, 1] range.

    Returns ``None`` if deepface/cv2 are unavailable or all frames fail.
    """
    if _tf_keras_required_but_missing():
        logger.debug("DeepFace per-frame skipped because tf-keras is missing")
        return None

    try:
        from deepface import DeepFace
        import cv2
    except Exception:
        logger.debug("deepface or cv2 not available for per-frame analysis", exc_info=True)
        return None

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.warning("Cannot open video for per-frame emotion: %s", video_path)
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, int(fps * interval_seconds))

    valence_list: list[float] = []
    arousal_list: list[float] = []
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_step == 0:
                try:
                    results = DeepFace.analyze(
                        img_path=frame,
                        actions=["emotion"],
                        enforce_detection=False,
                    )
                    result = results[0] if isinstance(results, list) else results
                    emotions: dict[str, float] = result.get("emotion", {})

                    # Normalize emotion probabilities to sum to 1
                    total = sum(emotions.values()) or 1.0

                    # Weighted sum → raw valence/arousal in [-1, +1]
                    raw_valence = sum(
                        (prob / total) * _VALENCE_WEIGHTS.get(emo, 0.0)
                        for emo, prob in emotions.items()
                    )
                    raw_arousal = sum(
                        (prob / total) * _AROUSAL_WEIGHTS.get(emo, 0.0)
                        for emo, prob in emotions.items()
                    )

                    # Remap [-1, +1] → [0, 1]
                    valence_list.append(max(0.0, min(1.0, (raw_valence + 1.0) / 2.0)))
                    arousal_list.append(max(0.0, min(1.0, (raw_arousal + 1.0) / 2.0)))
                except Exception:
                    logger.debug("DeepFace per-frame failed at frame %d – using neutral", frame_idx)
                    valence_list.append(0.5)
                    arousal_list.append(0.5)
            frame_idx += 1
    finally:
        cap.release()

    if not valence_list:
        logger.warning("No frames analysed for per-frame emotion")
        return None

    logger.info("DeepFace per-frame emotion: %d frames analysed", len(valence_list))
    return FrameEmotionSignals(valence=valence_list, arousal=arousal_list)
