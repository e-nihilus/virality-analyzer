from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ...ai_services.mock_analyzer import generate_mock_analysis
from ...core.auth import get_current_user_id
from ...core.paths import analysis_dir
from ...processing.clip_exporter import export_clip, ffmpeg_available
from ...schemas.analysis import (
    AnalysisCreateResponse,
    AnalysisResult,
    AnalysisStatus,
    AnalysisSummary,
)
from ...services import analysis_service, storage_service

router = APIRouter(prefix="/api/viral-intelligence/analysis", tags=["viral-intelligence"])


@router.get("/mock", response_model=AnalysisResult)
def get_mock_analysis():
    """Return a complete mock analysis for UI development."""
    return generate_mock_analysis()


@router.post("", response_model=AnalysisCreateResponse, status_code=201)
async def create_analysis(
    file: UploadFile,
    user_id: str | None = Depends(get_current_user_id),
):
    """Upload a video and start analysis."""
    # Validate
    error = storage_service.validate_upload(file.filename, file.size)
    if error:
        raise HTTPException(status_code=400, detail=error)

    analysis_id = f"ana_{uuid.uuid4()}"
    filename = file.filename or "video.mp4"

    # Save video to disk
    await storage_service.save_upload(analysis_id, file)

    # Register as pending and launch background analysis
    analysis_service.create_pending(analysis_id, filename, user_id=user_id)
    analysis_service.start_analysis_background(analysis_id, user_id=user_id)

    return AnalysisCreateResponse(
        id=analysis_id,
        status=AnalysisStatus.processing,
        progress=0.0,
        message="Analysis started",
    )


@router.get("/{analysis_id}", response_model=AnalysisResult)
def get_analysis(analysis_id: str):
    """Get the status and result of an analysis."""
    result = analysis_service.get_analysis(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(user_id: str | None = Depends(get_current_user_id)):
    """List all analyses (summary view)."""
    results = analysis_service.list_analyses()
    return [
        AnalysisSummary(
            id=r.id,
            user_id=r.user_id,
            status=r.status,
            video=r.video,
            overall_virality_score=r.overall_virality_score,
        )
        for r in results
    ]


@router.post("/{analysis_id}/clips/{clip_index}/export")
def export_clip_endpoint(analysis_id: str, clip_index: int):
    """Export a clip from an analysis."""
    result = analysis_service.get_analysis(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if not result.top_clips or clip_index < 0 or clip_index >= len(result.top_clips):
        raise HTTPException(status_code=404, detail="Clip not found")

    source_video = storage_service.input_video_path(analysis_id)
    if source_video is None:
        raise HTTPException(status_code=404, detail="Source video not found")

    clips_dir = analysis_dir(analysis_id) / "clips"
    output = clips_dir / f"clip_{clip_index}.mp4"

    if not ffmpeg_available():
        raise HTTPException(status_code=500, detail="FFmpeg not found on server")

    clip = result.top_clips[clip_index]
    try:
        export_result = export_clip(source_video, output, clip.start_seconds, clip.end_seconds)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "ok",
        "clip_index": clip_index,
        "duration": export_result.duration_seconds,
        "size_bytes": export_result.size_bytes,
    }


@router.get("/{analysis_id}/clips/{clip_index}/download")
def download_clip(analysis_id: str, clip_index: int):
    """Download an exported clip."""
    clip_path = analysis_dir(analysis_id) / "clips" / f"clip_{clip_index}.mp4"
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not exported yet")
    return FileResponse(clip_path, media_type="video/mp4", filename=f"clip_{clip_index}.mp4")
