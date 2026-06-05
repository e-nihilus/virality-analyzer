"""Audio extractor — extracts WAV audio from video via FFmpeg."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _video_has_audio(video_path: str) -> bool:
    """Use ffprobe to check whether the video file contains an audio stream."""
    if shutil.which("ffprobe") is None:
        return True  # assume yes if we can't check

    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return bool(result.stdout.strip())
    except Exception:
        return True  # assume yes on error


def extract_audio_wav(video_path: str, output_dir: str) -> str | None:
    """Extract mono 22050 Hz WAV from *video_path* for librosa analysis.

    Returns the path to the WAV file or None on failure.
    """
    if not ffmpeg_available():
        logger.warning("ffmpeg not found in PATH — cannot extract audio")
        return None

    if not _video_has_audio(video_path):
        logger.info("Video has no audio stream — skipping audio extraction: %s", video_path)
        return None

    wav_path = str(Path(output_dir) / "audio_analysis.wav")
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "22050",
        "-ac", "1",
        wav_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            logger.error("ffmpeg audio extraction failed: %s", result.stderr)
            return None
    except Exception:
        logger.exception("ffmpeg audio extraction error for %s", video_path)
        return None

    if not Path(wav_path).exists():
        logger.error("WAV file not created: %s", wav_path)
        return None

    return wav_path
