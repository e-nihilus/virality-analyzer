from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from app.ai_services import heuristic_analyzer
from app.ai_services.visual_analyzer import VisualAnalysis
from app.schemas.analysis import AnalysisSource, AnalysisStatus, MetricSourceType, ProviderExecutionStatus


class _FakeVisualAnalyzer:
    provider_name = "yolo"

    def analyze(self, *, video_path: str, output_dir: str, interval_seconds: float) -> VisualAnalysis:
        return VisualAnalysis(
            frame_diffs=[0.1, 0.4, 0.2, 0.3, 0.2, 0.1],
            brightness=[0.5, 0.55, 0.58, 0.52, 0.5, 0.48],
            provider="yolo",
            detections=[],
        )


class _FailingMemorabilityScorer:
    provider_name = "clip"

    def score_timeline(self, *, video_path: str, timeline: list) -> list[float]:
        raise RuntimeError("clip failed")


class _EmptyMemorabilityScorer:
    provider_name = "clip"

    def score_timeline(self, *, video_path: str, timeline: list) -> list[float]:
        return []


def _metric(result, name: str):
    return next(source for source in result.metric_sources if source.metric == name)


def _provider(result, name: str):
    return next(status for status in result.provider_status if status.name == name)


def _setup_lightweight_analysis(monkeypatch, *, memorability_scorer=None) -> None:
    monkeypatch.setenv("EMOTION_ANALYZER_PROVIDER", "heuristic")
    monkeypatch.setenv("EXPLANATION_PROVIDER", "heuristic")
    monkeypatch.setenv("EXPLANATION_CACHE_ENABLED", "false")
    monkeypatch.setenv("ENABLE_TEMPORAL_ANALYSIS", "false")
    monkeypatch.setenv("AUREA_WHISPER_ENABLED", "false")

    monkeypatch.setattr(
        heuristic_analyzer,
        "probe_video",
        lambda _path: SimpleNamespace(
            duration_seconds=6.0,
            fps=30,
            width=1080,
            height=1920,
        ),
    )
    monkeypatch.setattr(heuristic_analyzer, "get_visual_analyzer", lambda: _FakeVisualAnalyzer())
    monkeypatch.setattr(heuristic_analyzer, "librosa_available", lambda: False)
    monkeypatch.setattr(heuristic_analyzer, "video_has_audio", lambda _path: True)

    if memorability_scorer is not None:
        monkeypatch.setattr(
            heuristic_analyzer,
            "get_memorability_scorer",
            lambda: memorability_scorer,
        )


def test_mock_analyzer_marks_demo_source():
    from app.ai_services.mock_analyzer import generate_mock_analysis

    result = generate_mock_analysis("ana_demo", "demo.mp4")

    assert result.analysis_source == AnalysisSource.demo_mock
    assert result.provider_status
    assert all(source.source_type == MetricSourceType.mock for source in result.metric_sources)


def test_real_analysis_result_contains_provenance(monkeypatch, tmp_path):
    _setup_lightweight_analysis(monkeypatch, memorability_scorer=_EmptyMemorabilityScorer())
    monkeypatch.setenv("SCENE_DETECTION_ENABLED", "false")
    video_path = tmp_path / "upload.mp4"
    video_path.write_bytes(b"placeholder")

    result = heuristic_analyzer.analyze_video(
        analysis_id="ana_provenance",
        video_path=str(video_path),
        output_dir=str(tmp_path),
    )

    assert result.status == AnalysisStatus.completed
    assert result.analysis_source != AnalysisSource.demo_mock
    assert result.provider_status
    assert result.metric_sources
    assert _metric(result, "overall_virality_score")


def test_clip_failure_makes_rewatch_unavailable(monkeypatch, tmp_path):
    _setup_lightweight_analysis(monkeypatch, memorability_scorer=_FailingMemorabilityScorer())
    monkeypatch.setenv("SCENE_DETECTION_ENABLED", "false")
    video_path = tmp_path / "upload.mp4"
    video_path.write_bytes(b"placeholder")

    result = heuristic_analyzer.analyze_video(
        analysis_id="ana_clip_fail",
        video_path=str(video_path),
        output_dir=str(tmp_path),
    )

    assert result.rewatch_factor is None
    assert _metric(result, "rewatch_factor").source_type == MetricSourceType.unavailable
    assert _provider(result, "memorability").status == ProviderExecutionStatus.fallback


def test_scene_detection_disabled_makes_pacing_unavailable(monkeypatch, tmp_path):
    _setup_lightweight_analysis(monkeypatch, memorability_scorer=_EmptyMemorabilityScorer())
    monkeypatch.setenv("SCENE_DETECTION_ENABLED", "false")
    video_path = tmp_path / "upload.mp4"
    video_path.write_bytes(b"placeholder")

    result = heuristic_analyzer.analyze_video(
        analysis_id="ana_scene_disabled",
        video_path=str(video_path),
        output_dir=str(tmp_path),
    )

    assert result.pacing_score is None
    assert _metric(result, "pacing_score").source_type == MetricSourceType.unavailable
    assert _provider(result, "pacing").status == ProviderExecutionStatus.disabled


def test_whisper_disabled_makes_transcript_unavailable(monkeypatch, tmp_path):
    _setup_lightweight_analysis(monkeypatch, memorability_scorer=_EmptyMemorabilityScorer())
    monkeypatch.setenv("SCENE_DETECTION_ENABLED", "false")
    monkeypatch.setenv("AUREA_WHISPER_ENABLED", "false")
    video_path = tmp_path / "upload.mp4"
    video_path.write_bytes(b"placeholder")

    result = heuristic_analyzer.analyze_video(
        analysis_id="ana_whisper_disabled",
        video_path=str(video_path),
        output_dir=str(tmp_path),
    )

    assert result.transcript is None
    assert _metric(result, "transcript").source_type == MetricSourceType.unavailable
    assert _provider(result, "transcript").status == ProviderExecutionStatus.disabled
