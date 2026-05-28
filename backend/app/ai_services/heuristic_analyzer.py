"""Heuristic analyzer — real video analysis using OpenCV + optional FFmpeg."""

from __future__ import annotations

import logging
from pathlib import Path

from ..processing.clip_ranker import rank_clips
from ..processing.ffmpeg_probe import probe_video
from ..processing.frame_extractor import (
    compute_brightness,
    compute_frame_diffs,
    extract_frames,
)
from ..processing.timeline_builder import build_timeline
from .explanation_engine import generate_insights
from ..schemas.analysis import (
    AnalysisResult,
    AnalysisStatus,
    TimelineEntry,
    VideoMeta,
)

logger = logging.getLogger(__name__)

SAMPLE_INTERVAL = 1.0  # seconds between sampled frames


def _compute_dominant_emotion(timeline: list[TimelineEntry]) -> str:
    """Heuristic: pick dominant emotion from average arousal/valence."""
    if not timeline:
        return "Neutral"

    avg_arousal = sum(e.arousal or 0.5 for e in timeline) / len(timeline)
    avg_valence = sum(e.valence or 0.5 for e in timeline) / len(timeline)

    if avg_arousal > 0.65 and avg_valence > 0.6:
        return "Excitement"
    if avg_arousal > 0.65 and avg_valence <= 0.6:
        return "Tension"
    if avg_arousal > 0.5 and avg_valence > 0.5:
        return "Surprise"
    if avg_valence > 0.6:
        return "Joy"
    if avg_valence < 0.4:
        return "Sadness"
    return "Neutral"


def analyze_video(
    analysis_id: str,
    video_path: str,
    output_dir: str,
) -> AnalysisResult:
    """Run heuristic analysis on a real video file.

    Uses OpenCV for frame analysis and optionally FFmpeg for metadata.
    Falls back gracefully if FFmpeg is unavailable.
    """
    video_file = Path(video_path)
    filename = video_file.name

    # Step 1: Probe metadata (FFmpeg optional)
    probe = probe_video(video_path)
    if probe:
        duration = probe.duration_seconds
        fps = probe.fps
        width = probe.width
        height = probe.height
    else:
        # Fallback: use OpenCV for basic metadata
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Cannot open video: %s", video_path)
            return AnalysisResult(
                id=analysis_id,
                status=AnalysisStatus.failed,
                video=VideoMeta(filename=filename),
            )
        fps = int(cap.get(cv2.CAP_PROP_FPS) or 30)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frame_count / fps if fps > 0 else 0.0
        cap.release()

    video_meta = VideoMeta(
        filename=filename,
        duration_seconds=round(duration, 3),
        fps=fps,
        width=width,
        height=height,
    )

    # Step 2: Extract frames and compute visual signals
    extract_frames(video_path, output_dir, interval_seconds=SAMPLE_INTERVAL)
    frame_diffs = compute_frame_diffs(video_path, interval_seconds=SAMPLE_INTERVAL)
    brightness = compute_brightness(video_path, interval_seconds=SAMPLE_INTERVAL)

    if not frame_diffs:
        logger.warning("No frame data extracted — returning failed result")
        return AnalysisResult(
            id=analysis_id,
            status=AnalysisStatus.failed,
            video=video_meta,
        )

    # Step 3: Build timeline
    timeline = build_timeline(duration, frame_diffs, brightness, SAMPLE_INTERVAL)

    # Step 4: Rank clips
    top_clips = rank_clips(timeline, max_clips=3)

    # Step 5: Compute aggregate scores
    virality_values = [e.virality or 0.0 for e in timeline]
    retention_values = [e.retention or 0.0 for e in timeline]

    overall_virality = sum(virality_values) / len(virality_values) if virality_values else 0.0
    retention_score = sum(retention_values) / len(retention_values) if retention_values else 0.0

    # Rewatch factor: ratio of peak virality to average (higher = more rewatchable moments)
    peak_v = max(virality_values) if virality_values else 0.0
    rewatch_factor = round(peak_v / max(overall_virality, 0.01), 1)

    # Step 6: Dominant emotion and explanation engine
    dominant_emotion = _compute_dominant_emotion(timeline)
    insights = generate_insights(
        timeline=timeline,
        top_clips=top_clips,
        duration=duration,
        overall_virality=overall_virality,
        retention_score=retention_score,
        dominant_emotion=dominant_emotion,
    )

    return AnalysisResult(
        id=analysis_id,
        status=AnalysisStatus.completed,
        progress=1.0,
        video=video_meta,
        overall_virality_score=round(overall_virality, 3),
        retention_score=round(retention_score, 3),
        rewatch_factor=rewatch_factor,
        dominant_emotion=dominant_emotion,
        timeline=timeline,
        top_clips=top_clips,
        insights=insights,
    )
