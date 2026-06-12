"""Factory functions for model-adapter provider selection and fallbacks."""

from __future__ import annotations

import logging
import os

from .emotion_analyzer import (
    DeepFaceEmotionAnalyzer,
    EmotionAnalyzerAdapter,
    HeuristicEmotionAnalyzer,
)
from .explanation_generator import (
    CachedExplanationGenerator,
    ExplanationGenerator,
    HeuristicExplanationGenerator,
    QwenExplanationGenerator,
)
from .provider_exceptions import ProviderDependencyError
from .temporal_analyzer import (
    HeuristicTemporalAnalyzer,
    TemporalAnalyzerAdapter,
    VideoMAETemporalAnalyzer,
)
from .visual_analyzer import (
    HeuristicVisualAnalyzer,
    VisualAnalyzerAdapter,
    YoloVisualAnalyzer,
)

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: str) -> str:
    return (
        os.environ.get(name)
        or os.environ.get(f"AUREA_{name}")
        or default
    ).strip().lower()


def _validate_or_fallback(provider: object, fallback: object) -> object:
    try:
        validate = getattr(provider, "validate_dependencies", None)
        if callable(validate):
            validate()
        return provider
    except ProviderDependencyError as exc:
        logger.warning(
            "%s. Falling back to %s provider.",
            exc,
            getattr(fallback, "provider_name", "heuristic"),
        )
        return fallback


def get_visual_analyzer() -> VisualAnalyzerAdapter:
    provider = _env_flag("VISUAL_ANALYZER_PROVIDER", "heuristic")
    heuristic = HeuristicVisualAnalyzer()

    if provider == "heuristic":
        return heuristic
    if provider == "yolo":
        return _validate_or_fallback(YoloVisualAnalyzer(fallback=heuristic), heuristic)

    logger.warning("Unknown VISUAL_ANALYZER_PROVIDER=%s. Falling back to heuristic.", provider)
    return heuristic


def get_emotion_analyzer(*, video_path: str | None = None) -> EmotionAnalyzerAdapter:
    provider = _env_flag("EMOTION_ANALYZER_PROVIDER", "heuristic")
    heuristic = HeuristicEmotionAnalyzer()

    if provider == "heuristic":
        return heuristic
    if provider == "deepface":
        return _validate_or_fallback(
            DeepFaceEmotionAnalyzer(fallback=heuristic, video_path=video_path),
            heuristic,
        )

    logger.warning("Unknown EMOTION_ANALYZER_PROVIDER=%s. Falling back to heuristic.", provider)
    return heuristic


def temporal_analysis_enabled() -> bool:
    return _env_flag("ENABLE_TEMPORAL_ANALYSIS", "false") in {"1", "true", "yes"}


def get_temporal_analyzer(*, video_path: str | None = None) -> TemporalAnalyzerAdapter:
    provider = _env_flag("TEMPORAL_ANALYZER_PROVIDER", "heuristic")
    heuristic = HeuristicTemporalAnalyzer()

    if provider == "heuristic":
        return heuristic
    if provider == "videomae":
        return _validate_or_fallback(
            VideoMAETemporalAnalyzer(fallback=heuristic, video_path=video_path),
            heuristic,
        )

    logger.warning("Unknown TEMPORAL_ANALYZER_PROVIDER=%s. Falling back to heuristic.", provider)
    return heuristic


def get_explanation_generator() -> ExplanationGenerator:
    provider = _env_flag("EXPLANATION_PROVIDER", "heuristic")
    use_cache = _env_flag("EXPLANATION_CACHE_ENABLED", "true") in {"1", "true", "yes"}
    heuristic = HeuristicExplanationGenerator()

    selected: ExplanationGenerator
    if provider == "heuristic":
        selected = heuristic
    elif provider == "qwen":
        selected = _validate_or_fallback(QwenExplanationGenerator(fallback=heuristic), heuristic)
    else:
        logger.warning("Unknown EXPLANATION_PROVIDER=%s. Falling back to heuristic.", provider)
        selected = heuristic

    if use_cache:
        return CachedExplanationGenerator(selected)
    return selected
