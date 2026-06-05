"""Queue service — enqueues analysis jobs via RQ/Redis or in-process fallback.

When ``AUREA_QUEUE_BACKEND=redis`` and RQ is installed, jobs are pushed to a
Redis-backed queue and processed by an external ``rq worker``.  Otherwise the
job runs in a background thread (the original MVP behaviour).
"""

from __future__ import annotations

import logging
import threading

from ..core.config import settings

logger = logging.getLogger(__name__)

# ── Try importing RQ ────────────────────────────────────────────────

try:
    from redis import Redis
    from rq import Queue

    _RQ_IMPORTABLE = True
except ImportError:
    _RQ_IMPORTABLE = False


# ── Public helpers ──────────────────────────────────────────────────


def redis_available() -> bool:
    """Return True when RQ is importable, the backend is configured, and Redis responds."""
    if not _RQ_IMPORTABLE:
        return False
    if settings.queue_backend != "redis":
        return False
    try:
        conn = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        return conn.ping()
    except Exception:
        return False


def _get_queue() -> "Queue":
    """Return an RQ Queue connected to the configured Redis."""
    conn = Redis.from_url(settings.redis_url)
    return Queue("aurea-analysis", connection=conn, default_timeout=600)


# ── Enqueue / dispatch ──────────────────────────────────────────────


def enqueue_analysis(analysis_id: str, *, user_id: str | None = None) -> str:
    """Dispatch an analysis job.

    Returns a descriptor string: ``"rq:<job_id>"`` or ``"thread:<analysis_id>"``.
    """
    if settings.queue_backend == "redis" and _RQ_IMPORTABLE:
        return _enqueue_redis(analysis_id, user_id=user_id)

    return _enqueue_thread(analysis_id, user_id=user_id)


def _enqueue_redis(analysis_id: str, *, user_id: str | None = None) -> str:
    """Push job to RQ."""
    from ..workers.analysis_worker import run_analysis

    q = _get_queue()
    job = q.enqueue(
        run_analysis,
        analysis_id,
        user_id=user_id,
        job_id=f"analysis-{analysis_id}",
        result_ttl=3600,
    )
    logger.info("Enqueued RQ job %s for analysis %s", job.id, analysis_id)
    return f"rq:{job.id}"


def _enqueue_thread(analysis_id: str, *, user_id: str | None = None) -> str:
    """Fallback: run analysis in a daemon thread (MVP behaviour)."""
    from ..workers.analysis_worker import run_analysis
    from . import storage_service
    from ..schemas.analysis import AnalysisResult, AnalysisStatus

    def _worker() -> None:
        try:
            run_analysis(analysis_id, user_id=user_id)
        except Exception:
            logger.exception("Background analysis failed for %s", analysis_id)
            failed = AnalysisResult(
                id=analysis_id,
                user_id=user_id,
                status=AnalysisStatus.failed,
                progress=0.0,
            )
            storage_service.save_result(analysis_id, failed)

    thread = threading.Thread(
        target=_worker, daemon=True, name=f"analysis-{analysis_id}",
    )
    thread.start()
    logger.info("Started thread worker for analysis %s", analysis_id)
    return f"thread:{analysis_id}"
