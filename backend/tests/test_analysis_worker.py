from __future__ import annotations

from pathlib import Path

from app.schemas.analysis import AnalysisSource, AnalysisStatus, MetricSourceType
from app.workers import analysis_worker


def test_run_analysis_failure_does_not_fall_back_to_mock(monkeypatch, tmp_path):
    analysis_id = "ana_failure_no_mock"
    video_path = tmp_path / "input.mp4"
    video_path.write_bytes(b"not a real video")
    saved_results = []

    monkeypatch.setattr(
        analysis_worker.storage_service,
        "input_video_path",
        lambda _analysis_id: video_path,
    )
    monkeypatch.setattr(
        analysis_worker.storage_service,
        "load_result",
        lambda _analysis_id: None,
    )
    monkeypatch.setattr(
        analysis_worker.storage_service,
        "save_result",
        lambda _analysis_id, result: saved_results.append(result) or Path("result.json"),
    )

    def fail_analysis(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analysis_worker, "analyze_video", fail_analysis)

    result = analysis_worker.run_analysis(analysis_id, user_id="user_1")

    assert result.status == AnalysisStatus.failed
    assert result.analysis_source == AnalysisSource.failed
    assert result.user_id == "user_1"
    assert result.overall_virality_score is None
    assert result.retention_score is None
    assert result.rewatch_factor is None
    assert result.dominant_emotion is None
    assert result.timeline is None
    assert result.top_clips is None
    assert result.provider_status
    assert result.provider_status[0].status == "failed"
    assert result.metric_sources
    assert all(source.source_type == MetricSourceType.unavailable for source in result.metric_sources)
    assert result.insights and result.insights[0].title == "Analysis Failed"
    assert saved_results[-1] is result


def test_run_analysis_missing_input_returns_failed_not_mock(monkeypatch):
    saved_results = []

    monkeypatch.setattr(
        analysis_worker.storage_service,
        "input_video_path",
        lambda _analysis_id: None,
    )
    monkeypatch.setattr(
        analysis_worker.storage_service,
        "save_result",
        lambda _analysis_id, result: saved_results.append(result) or Path("result.json"),
    )

    result = analysis_worker.run_analysis("ana_missing", user_id="user_1")

    assert result.status == AnalysisStatus.failed
    assert result.analysis_source == AnalysisSource.failed
    assert result.user_id == "user_1"
    assert result.overall_virality_score is None
    assert result.metric_sources
    assert all(source.source_type == MetricSourceType.unavailable for source in result.metric_sources)
    assert saved_results[-1] is result
