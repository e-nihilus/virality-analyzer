"""Frame extractor — samples frames from video using OpenCV."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: str,
    output_dir: str,
    interval_seconds: float = 1.0,
) -> list[Path]:
    """Extract frames at fixed intervals and save as JPEG.

    Returns list of saved frame paths.
    """
    frames_dir = Path(output_dir) / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = int(fps * interval_seconds)
    saved: list[Path] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            filename = f"{frame_idx:06d}.jpg"
            path = frames_dir / filename
            cv2.imwrite(str(path), frame)
            saved.append(path)

        frame_idx += 1

    cap.release()
    logger.info("Extracted %d frames from %s", len(saved), video_path)
    return saved


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
