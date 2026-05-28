"""Storage service — persists uploaded videos and analysis results as JSON."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import UploadFile

from ..core.paths import analysis_dir, result_path
from ..schemas.analysis import AnalysisResult

MAX_UPLOAD_SIZE_MB = 200
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm", ".avi", ".mkv"}


def validate_upload(filename: str | None, size: int | None) -> str | None:
    """Return an error message if the upload is invalid, or None if OK."""
    if not filename:
        return "No filename provided"

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"

    if size is not None and size > MAX_UPLOAD_SIZE_BYTES:
        return f"File too large ({size / 1024 / 1024:.0f} MB). Max: {MAX_UPLOAD_SIZE_MB} MB"

    return None


async def save_upload(analysis_id: str, file: UploadFile) -> Path:
    """Save the uploaded file to uploads/<analysis_id>/input.mp4."""
    dest_dir = analysis_dir(analysis_id)
    ext = Path(file.filename or "video.mp4").suffix.lower()
    dest = dest_dir / f"input{ext}"

    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunks
            f.write(chunk)

    return dest


def save_result(analysis_id: str, result: AnalysisResult) -> Path:
    """Persist analysis result as JSON."""
    path = result_path(analysis_id)
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_result(analysis_id: str) -> AnalysisResult | None:
    """Load analysis result from JSON, or None if not found."""
    path = result_path(analysis_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return AnalysisResult.model_validate(data)


def input_video_path(analysis_id: str) -> Path | None:
    """Return path to the uploaded video, or None if not found."""
    d = analysis_dir(analysis_id)
    for ext in ALLOWED_EXTENSIONS:
        p = d / f"input{ext}"
        if p.exists():
            return p
    return None
