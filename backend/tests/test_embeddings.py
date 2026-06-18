from __future__ import annotations

import json

from app.ai_services.feature_store import FeatureStore, build_and_persist_multimodal_features
from app.processing.window_builder import build_windows
from app.schemas.analysis import TranscriptSegment


def test_build_windows_uses_three_second_stride_one_windows():
    windows = build_windows(6.0)

    assert [(w.start_seconds, w.end_seconds) for w in windows] == [
        (0.0, 3.0),
        (1.0, 4.0),
        (2.0, 5.0),
        (3.0, 6.0),
    ]


def test_multimodal_feature_store_persists_window_tensor(tmp_path):
    feature_set = build_and_persist_multimodal_features(
        analysis_id="ana_test_features",
        output_dir=tmp_path,
        duration_seconds=6.0,
        frame_diffs=[0.0, 10.0, 20.0, 5.0, 1.0, 0.5],
        brightness=[100.0, 120.0, 150.0, 130.0, 110.0, 90.0],
        detection_density=[0.0, 0.5, 1.0, 0.25, 0.0, 0.0],
        face_valence=[0.4, 0.5, 0.8, 0.7, 0.6, 0.5],
        face_arousal=[0.2, 0.4, 0.9, 0.6, 0.3, 0.2],
        audio_energy=[0.1, 0.5, 0.9, 0.3, 0.1, 0.0],
        audio_silence=[False, False, False, False, False, True],
        audio_energy_change=[0.0, 0.4, 0.4, 0.6, 0.2, 0.1],
        audio_pitch_hz=[0.0, 180.0, 260.0, 210.0, 160.0, 0.0],
        audio_pitch_variance=[0.0, 10.0, 200.0, 50.0, 5.0, 0.0],
        audio_speech_rate=[0.0, 0.5, 1.0, 0.4, 0.2, 0.0],
        audio_beat_drop=[0.0, 0.0, 0.75, 0.0, 0.0, 0.0],
        audio_laughter_scream=[0.0, 0.0, 0.7, 0.0, 0.0, 0.0],
        audio_voice_intensity=[0.1, 0.5, 0.9, 0.4, 0.2, 0.0],
        transcript_segments=[
            TranscriptSegment(start=0.0, end=2.0, text="Mira esto ahora"),
            TranscriptSegment(start=3.0, end=5.0, text="final inesperado"),
        ],
    )

    assert feature_set.shape == (4, 60)
    assert feature_set.dimensions == {"video": 12, "audio": 16, "text": 32, "total": 60}
    assert feature_set.matrix_path.exists()
    assert feature_set.metadata_path.exists()

    metadata = json.loads(feature_set.metadata_path.read_text(encoding="utf-8"))
    assert metadata["analysis_id"] == "ana_test_features"
    assert metadata["shape"] == [4, 60]
    assert metadata["windows"][0]["start_seconds"] == 0.0

    loaded = FeatureStore(tmp_path).load()
    assert loaded is not None
    matrix, loaded_metadata = loaded
    assert matrix.shape == (4, 60)
    assert loaded_metadata["dimensions"]["total"] == 60

    # Text hashing occupies the last 32 dimensions and should be non-zero for
    # windows overlapping transcript segments.
    assert matrix[0, -32:].any()
