"""Analysis service — orchestrates upload, storage, and analysis."""

from __future__ import annotations

import logging

from ..ai_services.mock_analyzer import generate_mock_analysis
from ..schemas.analysis import AnalysisResult, AnalysisStatus, VideoMeta
from ..workers.analysis_worker import run_analysis
from . import storage_service
from .queue_service import enqueue_analysis

logger = logging.getLogger(__name__)

# In-memory store keyed by analysis_id (hot cache; JSON on disk is source of truth)
_store: dict[str, AnalysisResult] = {}


def get_analysis(analysis_id: str) -> AnalysisResult | None:
    """Lookup from memory first, then disk."""
    # Always re-read from disk to pick up background worker updates
    result = storage_service.load_result(analysis_id)
    if result:
        _store[analysis_id] = result
        return result

    return _store.get(analysis_id)


def list_analyses() -> list[AnalysisResult]:
    return list(_store.values())


def create_pending(
    analysis_id: str, filename: str, *, user_id: str | None = None,
) -> AnalysisResult:
    """Register a new analysis in pending state."""
    result = AnalysisResult(
        id=analysis_id,
        user_id=user_id,
        status=AnalysisStatus.pending,
        progress=0.0,
        video=VideoMeta(filename=filename),
    )
    _store[analysis_id] = result
    storage_service.save_result(analysis_id, result)
    return result


def start_analysis_background(analysis_id: str, *, user_id: str | None = None) -> None:
    """Dispatch analysis via the configured queue backend (RQ or thread)."""
    job_ref = enqueue_analysis(analysis_id, user_id=user_id)
    logger.info("Dispatched analysis %s → %s", analysis_id, job_ref)


def run_real_analysis(analysis_id: str, *, user_id: str | None = None) -> AnalysisResult:
    """Run heuristic video analysis synchronously (legacy)."""
    result = run_analysis(analysis_id, user_id=user_id)
    _store[analysis_id] = result
    storage_service.save_result(analysis_id, result)
    return result


def complete_with_mock(
    analysis_id: str, filename: str = "video.mp4", *, user_id: str | None = None,
) -> AnalysisResult:
    """Run mock analysis and persist the result."""
    result = generate_mock_analysis(analysis_id=analysis_id, filename=filename)
    result.user_id = user_id
    _store[analysis_id] = result
    storage_service.save_result(analysis_id, result)
    return result
