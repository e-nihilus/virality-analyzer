from __future__ import annotations

from app.processing.clip_ranker import rank_clips
from app.schemas.analysis import TimelineEntry


def _timeline() -> list[TimelineEntry]:
    return [
        TimelineEntry(time_seconds=0, virality=0.2, arousal=0.2, retention=0.5),
        TimelineEntry(time_seconds=1, virality=0.3, arousal=0.4, retention=0.6),
        TimelineEntry(time_seconds=2, virality=0.7, arousal=0.8, retention=0.8),
        TimelineEntry(time_seconds=3, virality=0.4, arousal=0.5, retention=0.7),
        TimelineEntry(time_seconds=4, virality=0.3, arousal=0.3, retention=0.6),
        TimelineEntry(time_seconds=5, virality=0.2, arousal=0.2, retention=0.5),
    ]


def test_rank_clips_requires_semantic_scores_for_uploaded_mode():
    clips = rank_clips(_timeline(), require_semantic_scores=True)

    assert clips == []


def test_rank_clips_uses_clip_scores_and_evidence_reasons():
    detections = [
        {"time_seconds": 2.0, "class_name": "person"},
        {"time_seconds": 2.0, "class_name": "phone"},
        {"time_seconds": 3.0, "class_name": "person"},
    ]
    clips = rank_clips(
        _timeline(),
        semantic_scores=[0.1, 0.2, 0.95, 0.4, 0.2, 0.1],
        detections=detections,
        audio_energy_change=[0.0, 0.1, 0.35, 0.05, 0.0, 0.0],
        require_semantic_scores=True,
    )

    assert clips
    assert clips[0].score > 0.7
    reasons = " ".join(clips[0].reasons or [])
    assert "CLIP memorability peak" in reasons
    assert any(marker in reasons for marker in ["person", "Audio energy spike", "arousal"])
