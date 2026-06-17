"""Clip ranker — identifies top clip candidates from timeline data."""

from __future__ import annotations

from collections import Counter

from ..schemas.analysis import TextHook, TimelineEntry, TopClip, TranscriptSegment

# Default clip duration bounds (seconds)
MIN_CLIP_DURATION = 5.0
MAX_CLIP_DURATION = 15.0


def _detections_in_window(
    detections: list[dict] | None,
    start: float,
    end: float,
) -> list[dict]:
    if not detections:
        return []
    selected: list[dict] = []
    for det in detections:
        try:
            time_seconds = float(det.get("time_seconds", 0.0))
        except (TypeError, ValueError):
            continue
        if start <= time_seconds <= end:
            selected.append(det)
    return selected


def _detection_reasons(window_detections: list[dict]) -> tuple[list[str], float]:
    if not window_detections:
        return [], 0.0

    classes = [str(det.get("class_name", "")).strip().lower() for det in window_detections]
    classes = [name for name in classes if name]
    unique_classes = sorted(set(classes))

    reasons: list[str] = []
    score_boost = 0.0
    if "person" in unique_classes:
        reasons.append("Person/face visible — high engagement")
        score_boost += 0.06
    if len(unique_classes) >= 2:
        reasons.append(f"Scene variety: {', '.join(unique_classes[:4])}")
        score_boost += min(0.08, 0.02 * len(unique_classes))
    if len(window_detections) >= 6:
        reasons.append("Visually rich segment")
        score_boost += 0.06
    return reasons, score_boost


def _window_entries(timeline: list[TimelineEntry], start: float, end: float) -> list[TimelineEntry]:
    return [entry for entry in timeline if start <= entry.time_seconds <= end]


def _window_values(values: list[float] | None, timeline: list[TimelineEntry], start: float, end: float) -> list[float]:
    if not values:
        return []
    selected: list[float] = []
    for index, entry in enumerate(timeline):
        if start <= entry.time_seconds <= end and index < len(values):
            selected.append(values[index])
    return selected


def _avg(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _hooks_in_window(hooks: list[TextHook] | None, start: float, end: float) -> list[TextHook]:
    return [hook for hook in hooks or [] if start <= hook.timestamp <= end]


def _transcript_in_window(
    transcript_segments: list[TranscriptSegment] | None,
    start: float,
    end: float,
) -> list[TranscriptSegment]:
    return [segment for segment in transcript_segments or [] if segment.start <= end and segment.end >= start]


def build_clip_context(
    *,
    clip: TopClip,
    timeline: list[TimelineEntry],
    detections: list[dict] | None = None,
    semantic_scores: list[float] | None = None,
    audio_energy: list[float] | None = None,
    audio_energy_change: list[float] | None = None,
    hooks: list[TextHook] | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
) -> dict:
    """Build evidence-only context for clip reason generation."""
    start = clip.start_seconds
    end = clip.end_seconds
    entries = _window_entries(timeline, start, end)
    window_detections = _detections_in_window(detections, start, end)
    classes = [str(det.get("class_name", "")).strip().lower() for det in window_detections]
    class_counts = dict(Counter(name for name in classes if name))
    semantic_window = _window_values(semantic_scores, timeline, start, end)
    arousal_values = [entry.arousal or 0.0 for entry in entries]
    valence_values = [entry.valence or 0.5 for entry in entries]
    retention_values = [entry.retention or 0.5 for entry in entries]
    energy_values = _window_values(audio_energy, timeline, start, end)
    energy_change_values = _window_values(audio_energy_change, timeline, start, end)
    hook_window = _hooks_in_window(hooks, start, end)
    transcript_window = _transcript_in_window(transcript_segments, start, end)

    return {
        "start_seconds": start,
        "end_seconds": end,
        "clip_score": clip.score,
        "clip_retention": clip.predicted_retention,
        "clip_score_avg": round(_avg(semantic_window), 3) if semantic_window else None,
        "clip_score_peak": round(max(semantic_window), 3) if semantic_window else None,
        "yolo_class_counts": class_counts,
        "has_person": "person" in class_counts,
        "detection_count": len(window_detections),
        "avg_arousal": round(_avg(arousal_values), 3) if arousal_values else None,
        "avg_valence": round(_avg(valence_values), 3) if valence_values else None,
        "avg_retention": round(_avg(retention_values), 3) if retention_values else None,
        "avg_audio_energy": round(_avg(energy_values), 3) if energy_values else None,
        "max_audio_energy_change": round(max(energy_change_values), 3) if energy_change_values else None,
        "hooks": [hook.text for hook in hook_window[:3]],
        "transcript_excerpt": " ".join(segment.text for segment in transcript_window[:3])[:240],
    }


def structured_reasons_from_context(context: dict) -> list[str]:
    reasons: list[str] = []
    clip_peak = context.get("clip_score_peak")
    clip_avg = context.get("clip_score_avg")
    if isinstance(clip_peak, (int, float)):
        reasons.append(
            f"CLIP memorability peak {clip_peak:.2f}"
            + (f" with {clip_avg:.2f} window average" if isinstance(clip_avg, (int, float)) else "")
        )

    hooks = context.get("hooks") or []
    if hooks:
        reasons.append(f"Transcript hook present: “{hooks[0]}”")

    avg_arousal = context.get("avg_arousal")
    if isinstance(avg_arousal, (int, float)) and avg_arousal >= 0.6:
        reasons.append(f"High facial/emotional arousal in window ({avg_arousal:.2f})")

    class_counts = context.get("yolo_class_counts") or {}
    if class_counts:
        top_classes = sorted(class_counts.items(), key=lambda item: item[1], reverse=True)[:3]
        reasons.append(
            "YOLO detected " + ", ".join(f"{name}×{count}" for name, count in top_classes)
        )

    max_audio_change = context.get("max_audio_energy_change")
    if isinstance(max_audio_change, (int, float)) and max_audio_change >= 0.2:
        reasons.append(f"Audio energy spike detected ({max_audio_change:.2f})")

    return reasons[:2] or ["CLIP-selected segment with elevated video signals"]


def rank_clips(
    timeline: list[TimelineEntry],
    max_clips: int = 3,
    min_clip_duration: float = MIN_CLIP_DURATION,
    max_clip_duration: float = MAX_CLIP_DURATION,
    detections: list[dict] | None = None,
    semantic_scores: list[float] | None = None,
    audio_energy: list[float] | None = None,
    audio_energy_change: list[float] | None = None,
    hooks: list[TextHook] | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    require_semantic_scores: bool = False,
) -> list[TopClip]:
    """Find top clip candidates from content evidence.

    When ``require_semantic_scores`` is true, candidates are ranked only if CLIP
    memorability scores are available. This prevents uploaded-video top clips
    from being presented as AI-selected when they only come from a formula.
    """
    if len(timeline) < 3:
        return []
    if require_semantic_scores and not semantic_scores:
        return []

    # Find local peaks. For upload mode, CLIP memorability is the ranking base;
    # virality/retention can only refine it.
    peaks: list[tuple[int, float]] = []
    for i in range(1, len(timeline) - 1):
        if semantic_scores and i < len(semantic_scores):
            semantic = semantic_scores[i]
            v = min(1.0, 0.70 * semantic + 0.20 * (timeline[i].virality or 0.0) + 0.10 * (timeline[i].retention or 0.5))
            prev_v = semantic_scores[i - 1] if i - 1 < len(semantic_scores) else 0.0
            next_v = semantic_scores[i + 1] if i + 1 < len(semantic_scores) else 0.0
        else:
            v = timeline[i].virality or 0.0
            prev_v = timeline[i - 1].virality or 0.0
            next_v = timeline[i + 1].virality or 0.0
        if v >= prev_v and v >= next_v and v > 0.35:
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

        # Generate reasons from evidence collected inside the exact window.
        window_detections = _detections_in_window(detections, start, end)
        ai_reasons, detection_boost = _detection_reasons(window_detections)
        provisional_clip = TopClip(
            start_seconds=round(start, 2),
            end_seconds=round(end, 2),
            score=round(min(1.0, peak_score + detection_boost), 3),
            predicted_retention=round(avg_retention, 3),
            reasons=ai_reasons,
        )
        context = build_clip_context(
            clip=provisional_clip,
            timeline=timeline,
            detections=detections,
            semantic_scores=semantic_scores,
            audio_energy=audio_energy,
            audio_energy_change=audio_energy_change,
            hooks=hooks,
            transcript_segments=transcript_segments,
        )
        reasons = structured_reasons_from_context(context)

        provisional_clip.reasons = reasons
        clips.append(provisional_clip)

        # Mark nearby indices as used to avoid overlapping clips
        for j in range(max(0, peak_idx - 5), min(len(timeline), peak_idx + 6)):
            used_indices.add(j)

    return clips
