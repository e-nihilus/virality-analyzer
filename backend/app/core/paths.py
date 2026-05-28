from pathlib import Path

from .config import settings


def analysis_dir(analysis_id: str) -> Path:
    path = settings.uploads_dir / analysis_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def result_path(analysis_id: str) -> Path:
    return analysis_dir(analysis_id) / "result.json"
