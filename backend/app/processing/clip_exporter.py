"""FFmpeg wrapper — exports clip segments from a source video."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    output_path: Path
    duration_seconds: float
    size_bytes: int


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def export_clip(source: Path, output: Path, start: float, end: float) -> ExportResult:
    """Cut a segment from *source* and write it to *output* as mp4."""
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not found in PATH")

    output.parent.mkdir(parents=True, exist_ok=True)

    duration = end - start
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-i", str(source),
        "-to", str(duration),
        "-c", "copy",
        "-y",
        str(output),
    ]

    logger.info("Exporting clip: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    return ExportResult(
        output_path=output,
        duration_seconds=round(duration, 3),
        size_bytes=output.stat().st_size,
    )
