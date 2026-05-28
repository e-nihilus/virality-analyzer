"""FFmpeg/ffprobe wrapper — extracts video metadata via subprocess."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProbeResult:
    duration_seconds: float
    fps: int
    width: int
    height: int
    codec: str | None = None
    audio_codec: str | None = None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def probe_video(path: str) -> ProbeResult | None:
    """Run ffprobe and return structured metadata, or None if unavailable."""
    if not ffprobe_available():
        logger.warning("ffprobe not found in PATH — skipping probe")
        return None

    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.error("ffprobe failed: %s", result.stderr)
            return None

        data = json.loads(result.stdout)
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            None,
        )
        if video_stream is None:
            logger.error("No video stream found in %s", path)
            return None

        # Parse FPS from r_frame_rate (e.g. "30/1" or "30000/1001")
        fps_str = video_stream.get("r_frame_rate", "30/1")
        num, den = fps_str.split("/")
        fps = round(int(num) / int(den))

        duration = float(
            data.get("format", {}).get("duration", 0)
            or video_stream.get("duration", 0)
        )

        audio_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
            None,
        )

        return ProbeResult(
            duration_seconds=round(duration, 3),
            fps=fps,
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            codec=video_stream.get("codec_name"),
            audio_codec=audio_stream.get("codec_name") if audio_stream else None,
        )
    except Exception:
        logger.exception("ffprobe error for %s", path)
        return None
