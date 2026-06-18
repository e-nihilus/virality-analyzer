"""Frame extractor — samples frames from video using OpenCV.

The pipeline only ever needs frames sampled every ``interval_seconds`` (not the
full decoded stream). Decoding the whole video once and reusing the sampled
frames avoids the previous behaviour where each consumer (frame export, diffs,
brightness, YOLO, DeepFace) re-decoded every frame independently — several full
decode passes over the same file.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SampledFrame:
    """A single sampled frame and where it sits in the source video."""

    sample_index: int
    frame_index: int
    time_seconds: float
    path: Path


@dataclass
class SampledFrameSet:
    """Result of a single decode pass: sampled frames + visual signals."""

    fps: float
    frame_step: int
    samples: list[SampledFrame] = field(default_factory=list)
    frame_diffs: list[float] = field(default_factory=list)
    brightness: list[float] = field(default_factory=list)


def extract_sampled_frames(
    video_path: str,
    output_dir: str,
    interval_seconds: float = 1.0,
) -> SampledFrameSet:
    """Decode the video once, sampling every ``interval_seconds``.

    In a single pass this:
      * saves each sampled frame as JPEG (``frames/{frame_idx:06d}.jpg``),
      * computes mean absolute diff between consecutive *sampled* frames,
      * computes mean brightness per sampled frame.

    Signals are computed from the raw decoded frame (before JPEG compression) to
    preserve the previous numeric behaviour.
    """
    frames_dir = Path(output_dir) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    result = SampledFrameSet(fps=30.0, frame_step=1)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return result

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_step = max(1, int(fps * interval_seconds))
    result.fps = fps
    result.frame_step = frame_step

    prev_gray = None
    sample_index = 0
    frame_idx = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # Diff vs previous sampled frame (not consecutive video frames).
                if prev_gray is None:
                    result.frame_diffs.append(0.0)
                else:
                    diff = float(np.mean(np.abs(gray.astype(float) - prev_gray.astype(float))))
                    result.frame_diffs.append(diff)
                prev_gray = gray

                result.brightness.append(float(np.mean(gray)))

                path = frames_dir / f"{frame_idx:06d}.jpg"
                cv2.imwrite(str(path), frame)
                result.samples.append(
                    SampledFrame(
                        sample_index=sample_index,
                        frame_index=frame_idx,
                        time_seconds=round(sample_index * interval_seconds, 3),
                        path=path,
                    )
                )
                sample_index += 1

            frame_idx += 1
    finally:
        cap.release()

    logger.info("Extracted %d sampled frames from %s", len(result.samples), video_path)
    return result


def extract_frames(
    video_path: str,
    output_dir: str,
    interval_seconds: float = 1.0,
) -> list[Path]:
    """Extract frames at fixed intervals and save as JPEG.

    Thin wrapper around :func:`extract_sampled_frames` kept for compatibility.
    """
    return [s.path for s in extract_sampled_frames(video_path, output_dir, interval_seconds).samples]


def compute_frame_diffs(video_path: str, interval_seconds: float = 1.0) -> list[float]:
    """Compute mean absolute difference between consecutive sampled frames.

    Returns a list of diff values (one per sampled frame, first is 0.0).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = int(fps * interval_seconds)
    diffs: list[float] = []
    prev_gray = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is None:
                diffs.append(0.0)
            else:
                diff = float(np.mean(np.abs(gray.astype(float) - prev_gray.astype(float))))
                diffs.append(diff)
            prev_gray = gray

        frame_idx += 1

    cap.release()
    return diffs


def compute_brightness(video_path: str, interval_seconds: float = 1.0) -> list[float]:
    """Compute mean brightness per sampled frame (0-255)."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = int(fps * interval_seconds)
    brightness: list[float] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness.append(float(np.mean(gray)))

        frame_idx += 1

    cap.release()
    return brightness
