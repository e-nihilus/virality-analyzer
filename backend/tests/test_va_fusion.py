from __future__ import annotations

from app.ai_services.emotion.va_fusion import (
    dominant_emotion_from_points,
    fuse_timeline_valence_arousal,
)
from app.schemas.analysis import TextHook, TimelineEntry, TranscriptSegment


def test_multimodal_va_fusion_updates_timeline_with_confidence():
    timeline = [
        TimelineEntry(time_seconds=0.0, valence=0.5, arousal=0.45),
        TimelineEntry(time_seconds=1.0, valence=0.5, arousal=0.45),
    ]

    points = fuse_timeline_valence_arousal(
        timeline=timeline,
        face_valence=[0.7, 0.3],
        face_arousal=[0.6, 0.7],
        face_dominant_emotions=["Joy", "Tension"],
        audio_voice_intensity=[0.2, 0.9],
        audio_beat_drop=[0.0, 0.8],
        audio_laughter_scream=[0.0, 0.0],
        transcript_segments=[
            TranscriptSegment(start=0.0, end=1.0, text="esto es increíble"),
            TranscriptSegment(start=1.0, end=2.0, text="problema urgente ahora"),
        ],
        text_hooks=[
            TextHook(text="problema urgente ahora", hook_type="urgency", timestamp=1.0, confidence=0.8),
        ],
    )

    assert len(points) == 2
    assert timeline[0].emotion is not None
    assert timeline[0].emotion_confidence is not None
    assert timeline[1].arousal > timeline[0].arousal
    assert timeline[1].emotion_confidence >= 0.4
    assert "audio_prosody" in points[1].providers
    assert "text_lexicon" in points[1].providers


def test_dominant_emotion_prefers_confident_fused_points():
    timeline = [
        TimelineEntry(time_seconds=0.0, valence=0.7, arousal=0.75),
        TimelineEntry(time_seconds=1.0, valence=0.72, arousal=0.78),
    ]
    points = fuse_timeline_valence_arousal(timeline=timeline)

    assert dominant_emotion_from_points(points) == "Excitement"
