"""Speech transcription via faster-whisper — optional, returns None when unavailable."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel

    _WHISPER_IMPORTABLE = True
except ImportError:
    _WHISPER_IMPORTABLE = False

# Process-wide Whisper model cache, keyed by model size. Loaded once and reused
# across analyses instead of being rebuilt on every request.
_WHISPER_CACHE: dict[str, object] = {}
_WHISPER_LOCK = threading.Lock()


def _load_whisper_model(model_size: str):
    """Return a cached WhisperModel, preferring GPU with a CPU fallback."""
    cached = _WHISPER_CACHE.get(model_size)
    if cached is not None:
        return cached
    with _WHISPER_LOCK:
        cached = _WHISPER_CACHE.get(model_size)
        if cached is None:
            use_cuda = False
            try:
                import torch

                use_cuda = torch.cuda.is_available()
            except Exception:
                use_cuda = False

            if use_cuda:
                try:
                    logger.info("Loading Whisper '%s' on CUDA (cached) …", model_size)
                    cached = WhisperModel(model_size, device="cuda", compute_type="float16")
                except Exception:
                    logger.warning(
                        "Whisper CUDA init failed; falling back to CPU int8", exc_info=True
                    )
                    cached = None
            if cached is None:
                logger.info("Loading Whisper '%s' on CPU int8 (cached) …", model_size)
                cached = WhisperModel(model_size, device="cpu", compute_type="int8")
            _WHISPER_CACHE[model_size] = cached
    return cached


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class TranscriptResult:
    segments: list[TranscriptSegment] = field(default_factory=list)
    full_text: str = ""


def whisper_available() -> bool:
    """Return True when faster-whisper is importable AND the feature flag is on."""
    enabled = os.environ.get("AUREA_WHISPER_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    return _WHISPER_IMPORTABLE and enabled


def video_has_audio(video_path: str) -> bool:
    """Return True when the video appears to contain an audio stream."""
    return _video_has_audio(video_path)


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


def _extract_audio(video_path: str, output_dir: str) -> str | None:
    """Extract mono 16 kHz WAV from *video_path* using ffmpeg."""
    if shutil.which("ffmpeg") is None:
        logger.warning("ffmpeg not found in PATH — cannot extract audio")
        return None

    if not _video_has_audio(video_path):
        logger.info("Video has no audio stream — skipping speech extraction: %s", video_path)
        return None

    wav_path = str(Path(output_dir) / "audio.wav")
    cmd = [
        "ffmpeg",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
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

    return wav_path


def transcribe_video(video_path: str, output_dir: str) -> TranscriptResult | None:
    """Transcribe speech from a video file.

    Returns None when whisper is unavailable, disabled, or on any error.
    """
    if not whisper_available():
        logger.debug("Whisper not available or disabled — skipping transcription")
        return None

    wav_path = _extract_audio(video_path, output_dir)
    if wav_path is None:
        return None

    try:
        model_size = os.environ.get("AUREA_WHISPER_MODEL", "small")
        model = _load_whisper_model(model_size)

        segments_iter, _info = model.transcribe(wav_path)
        segments: list[TranscriptSegment] = []
        for seg in segments_iter:
            segments.append(
                TranscriptSegment(
                    start=round(seg.start, 3),
                    end=round(seg.end, 3),
                    text=seg.text.strip(),
                )
            )

        full_text = " ".join(s.text for s in segments)
        return TranscriptResult(segments=segments, full_text=full_text)
    except Exception:
        logger.exception("Whisper transcription error for %s", video_path)
        return None
