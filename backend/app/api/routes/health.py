from fastapi import APIRouter

from ...core.config import settings

router = APIRouter()


@router.get("/api/viral-intelligence/health")
def health_check():
    return {"status": "ok", "version": settings.version}
