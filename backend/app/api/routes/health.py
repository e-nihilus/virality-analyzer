from fastapi import APIRouter

from ...core.config import settings

router = APIRouter()


@router.get("/api/viral-intelligence/health")
def health_check():
    from ...services.queue_service import redis_available

    return {
        "status": "ok",
        "version": settings.version,
        "queue_backend": settings.queue_backend,
        "redis_connected": redis_available() if settings.queue_backend == "redis" else None,
    }
