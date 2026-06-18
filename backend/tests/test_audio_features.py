from __future__ import annotations

from app.ai_services.audio_emotion import estimate_voice_intensity
from app.ai_services.audio_events import detect_beat_drops, detect_laughter_scream
from app.processing.timeline_builder import build_timeline


def test_audio_event_detectors_find_energy_and_voice_spikes():
    beat_drops = detect_beat_drops(
        rms_energy=[0.1, 0.2, 0.85, 0.4],
        energy_change=[0.0, 0.1, 0.65, 0.45],
    )
    laughter_scream = detect_laughter_scream(
        rms_energy=[0.1, 0.2, 0.9, 0.3],
        pitch_hz=[120.0, 140.0, 480.0, 160.0],
        pitch_variance=[5.0, 10.0, 900.0, 20.0],
    )

    assert beat_drops[2] > 0.0
    assert beat_drops[0] == 0.0
    assert laughter_scream[2] > 0.0
    assert laughter_scream[1] == 0.0


def test_voice_intensity_combines_prosody_events_and_speech_rate():
    intensity = estimate_voice_intensity(
        rms_energy=[0.1, 0.8],
        pitch_variance=[1.0, 100.0],
        speech_rate=[0.1, 1.0],
        beat_drop=[0.0, 0.7],
        laughter_scream=[0.0, 0.6],
    )

    assert len(intensity) == 2
    assert intensity[1] > intensity[0]
    assert all(0.0 <= value <= 1.0 for value in intensity)


def test_timeline_arousal_and_labels_use_deep_audio_features():
    baseline = build_timeline(
        4.0,
        frame_diffs=[0.0, 0.1, 0.1, 0.1],
        brightness=[100.0, 100.0, 100.0, 100.0],
        audio_energy=[0.1, 0.1, 0.1, 0.1],
        audio_silence=[False, False, False, False],
        audio_energy_change=[0.0, 0.0, 0.0, 0.0],
    )
    enhanced = build_timeline(
        4.0,
        frame_diffs=[0.0, 0.1, 0.1, 0.1],
        brightness=[100.0, 100.0, 100.0, 100.0],
        audio_energy=[0.1, 0.1, 0.1, 0.1],
        audio_silence=[False, False, False, False],
        audio_energy_change=[0.0, 0.0, 0.0, 0.0],
        audio_voice_intensity=[0.1, 0.9, 0.9, 0.1],
        audio_beat_drop=[0.0, 0.8, 0.0, 0.0],
        audio_laughter_scream=[0.0, 0.0, 0.7, 0.0],
    )

    assert enhanced[1].arousal > baseline[1].arousal
    assert enhanced[1].label == "Beat drop"
    assert enhanced[2].label == "Voice intensity spike"
