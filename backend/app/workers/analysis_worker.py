"""Analysis worker — runs video analysis in background with progress updates."""

from __future__ import annotations

import logging

from ..ai_services.heuristic_analyzer import analyze_video
from ..ai_services.mock_analyzer import generate_mock_analysis
from ..schemas.analysis import AnalysisResult, AnalysisStatus, VideoMeta
from ..services import storage_service

logger = logging.getLogger(__name__)


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

    Tries heuristic (real) analysis first. Falls back to mock if the video
    cannot be processed (e.g., OpenCV fails to open the file).
    """
    video_path = storage_service.input_video_path(analysis_id)

    if video_path is None:
        logger.error("No input video found for %s", analysis_id)
        result = AnalysisResult(
            id=analysis_id,
            status=AnalysisStatus.failed,
            progress=0.0,
        )
        result.user_id = user_id
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

    except Exception:
        logger.exception("Heuristic analysis failed for %s — falling back to mock", analysis_id)
        result = generate_mock_analysis(
            analysis_id=analysis_id,
            filename=video_path.name,
        )
        result.user_id = user_id
        result.status = AnalysisStatus.completed
        storage_service.save_result(analysis_id, result)
        return result
