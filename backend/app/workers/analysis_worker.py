"""Analysis worker — runs video analysis in background with progress updates."""

from __future__ import annotations

import logging

from ..ai_services.heuristic_analyzer import analyze_video
from ..schemas.analysis import (
    AnalysisResult,
    AnalysisSource,
    AnalysisStatus,
    Insight,
    InsightSeverity,
    MetricSource,
    MetricSourceType,
    ProviderExecutionStatus,
    ProviderStatus,
    VideoMeta,
)
from ..services import storage_service

logger = logging.getLogger(__name__)


def _failed_analysis_result(
    *,
    analysis_id: str,
    filename: str | None = None,
    user_id: str | None = None,
    message: str,
) -> AnalysisResult:
    """Build a failed real-upload result without synthetic/mock metrics."""
    result = AnalysisResult(
        id=analysis_id,
        user_id=user_id,
        status=AnalysisStatus.failed,
        analysis_source=AnalysisSource.failed,
        progress=1.0,
        video=VideoMeta(filename=filename or "video.mp4"),
        provider_status=[
            ProviderStatus(
                name="analysis_worker",
                provider="real_upload_pipeline",
                status=ProviderExecutionStatus.failed,
                is_ai=False,
                message=message,
            )
        ],
        metric_sources=[
            MetricSource(metric=metric, source_type=MetricSourceType.unavailable)
            for metric in [
                "overall_virality_score",
                "retention_score",
                "rewatch_factor",
                "dominant_emotion",
                "emotion_intensity",
                "attention_duration_seconds",
                "timeline",
                "top_clips",
                "insights",
                "transcript",
            ]
        ],
        insights=[
            Insight(
                title="Analysis Failed",
                description=message,
                severity=InsightSeverity.high,
                action="Please try a different video or check the backend logs for provider errors.",
            )
        ],
    )
    return result


def _update_progress(
    analysis_id: str,
    progress: float,
    *,
    status: AnalysisStatus = AnalysisStatus.processing,
    user_id: str | None = None,
) -> None:
    """Persist an intermediate progress update to disk."""
    existing = storage_service.load_result(analysis_id)
    if existing is None:
        existing = AnalysisResult(
            id=analysis_id,
            status=status,
            progress=progress,
        )
    else:
        existing.status = status
        existing.progress = progress
    if user_id:
        existing.user_id = user_id
    storage_service.save_result(analysis_id, existing)


def run_analysis(analysis_id: str, *, user_id: str | None = None) -> AnalysisResult:
    """Execute analysis for a given analysis_id with progress tracking.

    Runs the real upload analysis pipeline. Failures are persisted as failed
    results; uploaded videos must never be silently replaced with mock metrics.
    """
    video_path = storage_service.input_video_path(analysis_id)

    if video_path is None:
        logger.error("No input video found for %s", analysis_id)
        result = _failed_analysis_result(
            analysis_id=analysis_id,
            user_id=user_id,
            message="No input video was found for this analysis.",
        )
        storage_service.save_result(analysis_id, result)
        return result

    output_dir = str(video_path.parent)

    try:
        # Progress: probing metadata
        _update_progress(analysis_id, 0.1, user_id=user_id)
        logger.info("Starting heuristic analysis for %s", analysis_id)

        # Progress: extracting frames
        _update_progress(analysis_id, 0.3, user_id=user_id)

        result = analyze_video(
            analysis_id=analysis_id,
            video_path=str(video_path),
            output_dir=output_dir,
        )
        result.user_id = user_id

        # Progress: finalizing
        _update_progress(analysis_id, 0.9, user_id=user_id)

        storage_service.save_result(analysis_id, result)
        logger.info("Analysis completed for %s — status: %s", analysis_id, result.status)
        return result

    except Exception as exc:
        logger.exception("Real upload analysis failed for %s", analysis_id)
        result = _failed_analysis_result(
            analysis_id=analysis_id,
            filename=video_path.name,
            user_id=user_id,
            message=f"The uploaded video could not be analyzed: {exc}",
        )
        storage_service.save_result(analysis_id, result)
        return result
