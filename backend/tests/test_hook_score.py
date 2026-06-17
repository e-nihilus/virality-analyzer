from __future__ import annotations

from app.ai_services.heuristic_analyzer import _compute_hook_score
from app.ai_services.text_hook_analyzer import TextHook
from app.schemas.analysis import TimelineEntry


def test_hook_score_returns_structured_evidence():
    score, evidence = _compute_hook_score(
        timeline=[
            TimelineEntry(time_seconds=0, virality=0.5),
            TimelineEntry(time_seconds=1, virality=0.6),
            TimelineEntry(time_seconds=6, virality=0.9),
        ],
        detections=[{"time_seconds": 1.0, "class_name": "person"}],
        face_arousal=[0.7, 0.8],
        audio_energy=[0.6, 0.5],
        hooks=[TextHook(text="wait for it", hook_type="command", timestamp=1.0, confidence=0.8)],
    )

    assert score is not None and score > 0.8
    assert evidence is not None
    assert evidence.person_detected_first_5s is True
    assert evidence.face_arousal_avg_first_5s == 0.75
    assert evidence.audio_energy_first_5s == 0.55
    assert evidence.text_hook_first_5s is not None
    assert evidence.text_hook_first_5s.hook_type == "command"
