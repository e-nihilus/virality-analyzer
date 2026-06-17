from __future__ import annotations

from app.ai_services.heuristic_analyzer import _compute_attention_duration_seconds
from app.ai_services.text_hook_analyzer import TextHook
from app.schemas.analysis import TimelineEntry


def test_attention_duration_uses_continuous_real_signal_window():
    duration = _compute_attention_duration_seconds(
        timeline=[
            TimelineEntry(time_seconds=0, retention=0.8),
            TimelineEntry(time_seconds=1, retention=0.82),
            TimelineEntry(time_seconds=2, retention=0.83),
            TimelineEntry(time_seconds=3, retention=0.4),
        ],
        detections=[
            {"sample_index": 0, "class_name": "person"},
            {"sample_index": 1, "class_name": "person"},
        ],
        face_arousal=None,
        audio_energy=[0.1, 0.2, 0.0, 0.0],
        audio_silence=[False, False, True, True],
        hooks=[TextHook(text="wait", hook_type="command", timestamp=2.0, confidence=0.8)],
        memorability_scores=[0.2, 0.7, 0.8, 0.1],
        sample_interval=1.0,
    )

    assert duration == 3.0


def test_attention_duration_unavailable_without_real_signals():
    duration = _compute_attention_duration_seconds(
        timeline=[TimelineEntry(time_seconds=0, retention=0.9)],
        detections=[],
        face_arousal=None,
        audio_energy=None,
        audio_silence=None,
        hooks=[],
        memorability_scores=[],
        sample_interval=1.0,
    )

    assert duration is None
