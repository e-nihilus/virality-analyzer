"""Clip ranker — identifies top clip candidates from timeline data."""

from __future__ import annotations

from ..schemas.analysis import TimelineEntry, TopClip

# Default clip duration bounds (seconds)
MIN_CLIP_DURATION = 5.0
MAX_CLIP_DURATION = 15.0


def rank_clips(
    timeline: list[TimelineEntry],
    max_clips: int = 3,
    min_clip_duration: float = MIN_CLIP_DURATION,
    max_clip_duration: float = MAX_CLIP_DURATION,
) -> list[TopClip]:
    """Find top clip candidates by detecting virality peaks and expanding windows."""
    if len(timeline) < 3:
        return []

    # Find local peaks in virality
    peaks: list[tuple[int, float]] = []
    for i in range(1, len(timeline) - 1):
        v = timeline[i].virality or 0.0
        prev_v = timeline[i - 1].virality or 0.0
        next_v = timeline[i + 1].virality or 0.0
        if v >= prev_v and v >= next_v and v > 0.4:
            peaks.append((i, v))

    # Sort by score descending
    peaks.sort(key=lambda x: x[1], reverse=True)

    clips: list[TopClip] = []
    used_indices: set[int] = set()

    for peak_idx, peak_score in peaks:
        if len(clips) >= max_clips:
            break
        if peak_idx in used_indices:
            continue

        peak_time = timeline[peak_idx].time_seconds

        # Expand window around peak
        half_dur = max_clip_duration / 2
        start = max(0.0, peak_time - half_dur)
        end = min(timeline[-1].time_seconds, peak_time + half_dur)

        # Ensure minimum duration
        if end - start < min_clip_duration:
            end = min(timeline[-1].time_seconds, start + min_clip_duration)

        # Compute average retention in window
        window_retentions = [
            e.retention or 0.5
            for e in timeline
            if start <= e.time_seconds <= end
        ]
        avg_retention = (
            sum(window_retentions) / len(window_retentions) if window_retentions else 0.5
        )

        # Generate reasons from signals
        reasons: list[str] = []
        if peak_score > 0.7:
            reasons.append(f"High virality peak ({peak_score:.2f}) at T+{peak_time:.0f}s")
        if peak_time < 5.0:
            reasons.append("Strong opening hook")
        if avg_retention > 0.75:
            reasons.append(f"High predicted retention ({avg_retention:.2f})")

        # Check for motion spike
        virality_values = [
            e.virality or 0.0
            for e in timeline
            if start <= e.time_seconds <= end
        ]
        if virality_values:
            max_v = max(virality_values)
            min_v = min(virality_values)
            if max_v - min_v > 0.3:
                reasons.append("Visual pattern disruption detected")

        if not reasons:
            reasons.append("Elevated engagement signals")

        clips.append(
            TopClip(
                start_seconds=round(start, 2),
                end_seconds=round(end, 2),
                score=round(peak_score, 3),
                predicted_retention=round(avg_retention, 3),
                reasons=reasons,
            )
        )

        # Mark nearby indices as used to avoid overlapping clips
        for j in range(max(0, peak_idx - 5), min(len(timeline), peak_idx + 6)):
            used_indices.add(j)

    return clips
