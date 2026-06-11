from __future__ import annotations

from app.ai_services.emotion_analyzer import HeuristicEmotionAnalyzer
from app.ai_services.explanation_generator import CachedExplanationGenerator, HeuristicExplanationGenerator
from app.ai_services.provider_factory import (
    get_emotion_analyzer,
    get_explanation_generator,
    get_temporal_analyzer,
    get_visual_analyzer,
    temporal_analysis_enabled,
)
from app.ai_services.temporal_analyzer import HeuristicTemporalAnalyzer
from app.ai_services.visual_analyzer import HeuristicVisualAnalyzer


def test_visual_provider_defaults_to_heuristic(monkeypatch):
    monkeypatch.delenv("VISUAL_ANALYZER_PROVIDER", raising=False)
    monkeypatch.delenv("AUREA_VISUAL_ANALYZER_PROVIDER", raising=False)

    provider = get_visual_analyzer()
    assert isinstance(provider, HeuristicVisualAnalyzer)


def test_visual_provider_falls_back_when_yolo_dependency_missing(monkeypatch):
    monkeypatch.setenv("VISUAL_ANALYZER_PROVIDER", "yolo")

    provider = get_visual_analyzer()
    assert isinstance(provider, HeuristicVisualAnalyzer)


def test_emotion_provider_falls_back_when_deepface_dependency_missing(monkeypatch):
    monkeypatch.setenv("EMOTION_ANALYZER_PROVIDER", "deepface")

    provider = get_emotion_analyzer()
    assert isinstance(provider, HeuristicEmotionAnalyzer)


def test_temporal_provider_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_TEMPORAL_ANALYSIS", raising=False)
    monkeypatch.delenv("AUREA_ENABLE_TEMPORAL_ANALYSIS", raising=False)

    assert temporal_analysis_enabled() is False


def test_temporal_provider_flag_true(monkeypatch):
    monkeypatch.setenv("ENABLE_TEMPORAL_ANALYSIS", "true")

    assert temporal_analysis_enabled() is True


def test_temporal_provider_falls_back_when_videomae_dependencies_missing(monkeypatch):
    monkeypatch.setenv("TEMPORAL_ANALYZER_PROVIDER", "videomae")

    provider = get_temporal_analyzer()
    assert isinstance(provider, HeuristicTemporalAnalyzer)


def test_explanation_provider_defaults_to_cached_heuristic(monkeypatch):
    monkeypatch.delenv("EXPLANATION_PROVIDER", raising=False)
    monkeypatch.delenv("AUREA_EXPLANATION_PROVIDER", raising=False)
    monkeypatch.setenv("EXPLANATION_CACHE_ENABLED", "true")

    provider = get_explanation_generator()
    assert isinstance(provider, CachedExplanationGenerator)
    assert isinstance(provider.inner, HeuristicExplanationGenerator)


def test_explanation_provider_cache_can_be_disabled(monkeypatch):
    monkeypatch.setenv("EXPLANATION_PROVIDER", "heuristic")
    monkeypatch.setenv("EXPLANATION_CACHE_ENABLED", "false")

    provider = get_explanation_generator()
    assert isinstance(provider, HeuristicExplanationGenerator)


def test_explanation_provider_falls_back_when_qwen_dependencies_missing(monkeypatch):
    monkeypatch.setenv("EXPLANATION_PROVIDER", "qwen")
    monkeypatch.setenv("EXPLANATION_CACHE_ENABLED", "false")

    provider = get_explanation_generator()
    assert isinstance(provider, HeuristicExplanationGenerator)


def test_factory_supports_aurea_prefixed_env(monkeypatch):
    monkeypatch.delenv("VISUAL_ANALYZER_PROVIDER", raising=False)
    monkeypatch.setenv("AUREA_VISUAL_ANALYZER_PROVIDER", "heuristic")

    provider = get_visual_analyzer()
    assert isinstance(provider, HeuristicVisualAnalyzer)
