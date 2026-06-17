from __future__ import annotations

from app.ai_services.emotion_analyzer import DeepFaceEmotionAnalyzer, HeuristicEmotionAnalyzer
from app.ai_services.explanation_generator import CachedExplanationGenerator, HeuristicExplanationGenerator, QwenExplanationGenerator
from app.ai_services.memorability_scorer import ClipMemorabilityScorer, HeuristicMemorabilityScorer
from app.ai_services.provider_factory import (
    get_emotion_analyzer,
    get_explanation_generator,
    get_memorability_scorer,
    get_retention_predictor,
    get_temporal_analyzer,
    get_virality_predictor,
    get_visual_analyzer,
    scene_detection_enabled,
    temporal_analysis_enabled,
)
from app.ai_services.provider_exceptions import ProviderDependencyError
from app.ai_services.retention_predictor import HeuristicRetentionPredictor, MLRetentionPredictor
from app.ai_services.temporal_analyzer import HeuristicTemporalAnalyzer
from app.ai_services.visual_analyzer import HeuristicVisualAnalyzer, YoloVisualAnalyzer
from app.ai_services.virality_predictor import DerivedViralityPredictor, MLViralityPredictor


def test_visual_provider_defaults_to_heuristic(monkeypatch):
    monkeypatch.delenv("VISUAL_ANALYZER_PROVIDER", raising=False)
    monkeypatch.delenv("AUREA_VISUAL_ANALYZER_PROVIDER", raising=False)

    provider = get_visual_analyzer()
    assert isinstance(provider, HeuristicVisualAnalyzer)


def test_visual_provider_falls_back_when_yolo_dependency_missing(monkeypatch):
    monkeypatch.setenv("VISUAL_ANALYZER_PROVIDER", "yolo")
    monkeypatch.setattr(
        YoloVisualAnalyzer,
        "validate_dependencies",
        lambda self: (_ for _ in ()).throw(ProviderDependencyError("missing yolo")),
    )

    provider = get_visual_analyzer()
    assert isinstance(provider, HeuristicVisualAnalyzer)


def test_emotion_provider_falls_back_when_deepface_dependency_missing(monkeypatch):
    monkeypatch.setenv("EMOTION_ANALYZER_PROVIDER", "deepface")

    monkeypatch.setattr(
        DeepFaceEmotionAnalyzer,
        "validate_dependencies",
        lambda self: (_ for _ in ()).throw(ProviderDependencyError("missing deepface")),
    )

    provider = get_emotion_analyzer()
    assert isinstance(provider, HeuristicEmotionAnalyzer)


def test_emotion_provider_defaults_to_deepface(monkeypatch):
    monkeypatch.delenv("EMOTION_ANALYZER_PROVIDER", raising=False)
    monkeypatch.delenv("AUREA_EMOTION_ANALYZER_PROVIDER", raising=False)
    monkeypatch.setattr(DeepFaceEmotionAnalyzer, "validate_dependencies", lambda self: None)

    provider = get_emotion_analyzer()
    assert isinstance(provider, DeepFaceEmotionAnalyzer)


def test_temporal_provider_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_TEMPORAL_ANALYSIS", raising=False)
    monkeypatch.delenv("AUREA_ENABLE_TEMPORAL_ANALYSIS", raising=False)

    assert temporal_analysis_enabled() is False


def test_temporal_provider_flag_true(monkeypatch):
    monkeypatch.setenv("ENABLE_TEMPORAL_ANALYSIS", "true")

    assert temporal_analysis_enabled() is True


def test_temporal_provider_falls_back_when_videomae_dependencies_missing(monkeypatch):
    monkeypatch.setenv("TEMPORAL_ANALYZER_PROVIDER", "videomae")
    from app.ai_services.temporal_analyzer import VideoMAETemporalAnalyzer

    monkeypatch.setattr(
        VideoMAETemporalAnalyzer,
        "validate_dependencies",
        lambda self: (_ for _ in ()).throw(ProviderDependencyError("missing videomae")),
    )

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
    monkeypatch.setattr(
        QwenExplanationGenerator,
        "validate_dependencies",
        lambda self: (_ for _ in ()).throw(ProviderDependencyError("missing qwen")),
    )

    provider = get_explanation_generator()
    assert isinstance(provider, HeuristicExplanationGenerator)


def test_retention_provider_defaults_to_heuristic(monkeypatch):
    monkeypatch.delenv("RETENTION_PREDICTOR_PROVIDER", raising=False)
    monkeypatch.delenv("AUREA_RETENTION_PREDICTOR_PROVIDER", raising=False)

    provider = get_retention_predictor()
    assert isinstance(provider, HeuristicRetentionPredictor)


def test_retention_provider_ml_falls_back_without_model(monkeypatch):
    monkeypatch.setenv("RETENTION_PREDICTOR_PROVIDER", "ml")
    monkeypatch.delenv("RETENTION_MODEL_PATH", raising=False)
    monkeypatch.delenv("AUREA_RETENTION_MODEL_PATH", raising=False)

    provider = get_retention_predictor()
    assert isinstance(provider, HeuristicRetentionPredictor)


def test_retention_provider_ml_uses_configured_model_path(monkeypatch, tmp_path):
    model_path = tmp_path / "retention.model"
    model_path.write_bytes(b"placeholder")
    monkeypatch.setenv("RETENTION_PREDICTOR_PROVIDER", "ml")
    monkeypatch.setenv("RETENTION_MODEL_PATH", str(model_path))

    provider = get_retention_predictor()
    assert isinstance(provider, MLRetentionPredictor)


def test_virality_provider_defaults_to_derived(monkeypatch):
    monkeypatch.delenv("VIRALITY_PREDICTOR_PROVIDER", raising=False)
    monkeypatch.delenv("AUREA_VIRALITY_PREDICTOR_PROVIDER", raising=False)

    provider = get_virality_predictor()
    assert isinstance(provider, DerivedViralityPredictor)


def test_virality_provider_ml_falls_back_without_model(monkeypatch):
    monkeypatch.setenv("VIRALITY_PREDICTOR_PROVIDER", "ml")
    monkeypatch.delenv("VIRALITY_MODEL_PATH", raising=False)
    monkeypatch.delenv("AUREA_VIRALITY_MODEL_PATH", raising=False)

    provider = get_virality_predictor()
    assert isinstance(provider, DerivedViralityPredictor)


def test_virality_provider_ml_uses_configured_model_path(monkeypatch, tmp_path):
    model_path = tmp_path / "virality.model"
    model_path.write_bytes(b"placeholder")
    monkeypatch.setenv("VIRALITY_PREDICTOR_PROVIDER", "ml")
    monkeypatch.setenv("VIRALITY_MODEL_PATH", str(model_path))

    provider = get_virality_predictor()
    assert isinstance(provider, MLViralityPredictor)


def test_memorability_provider_defaults_to_clip(monkeypatch):
    monkeypatch.delenv("MEMORABILITY_SCORER", raising=False)
    monkeypatch.delenv("AUREA_MEMORABILITY_SCORER", raising=False)
    monkeypatch.setattr(ClipMemorabilityScorer, "validate_dependencies", lambda self: None)

    provider = get_memorability_scorer()
    assert isinstance(provider, ClipMemorabilityScorer)


def test_memorability_provider_clip_falls_back_when_dependencies_missing(monkeypatch):
    monkeypatch.setenv("MEMORABILITY_SCORER", "clip")
    monkeypatch.setattr(
        ClipMemorabilityScorer,
        "validate_dependencies",
        lambda self: (_ for _ in ()).throw(ProviderDependencyError("missing clip")),
    )

    provider = get_memorability_scorer()
    assert isinstance(provider, HeuristicMemorabilityScorer)


def test_scene_detection_enabled_by_default(monkeypatch):
    monkeypatch.delenv("SCENE_DETECTION_ENABLED", raising=False)
    monkeypatch.delenv("AUREA_SCENE_DETECTION_ENABLED", raising=False)

    assert scene_detection_enabled() is True


def test_scene_detection_can_be_disabled(monkeypatch):
    monkeypatch.setenv("SCENE_DETECTION_ENABLED", "false")

    assert scene_detection_enabled() is False


def test_factory_supports_aurea_prefixed_env(monkeypatch):
    monkeypatch.delenv("VISUAL_ANALYZER_PROVIDER", raising=False)
    monkeypatch.setenv("AUREA_VISUAL_ANALYZER_PROVIDER", "heuristic")

    provider = get_visual_analyzer()
    assert isinstance(provider, HeuristicVisualAnalyzer)
