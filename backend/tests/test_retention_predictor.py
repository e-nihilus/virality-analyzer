from __future__ import annotations

import pickle

from app.ai_services.retention_predictor import MLRetentionPredictor


class DummyRetentionModel:
    def predict(self, matrix):
        return [row[0] + row[3] - row[5] * 0.2 for row in matrix]


class BadCountRetentionModel:
    def predict(self, matrix):
        return [0.5]


def test_ml_retention_predictor_loads_pickle_model(tmp_path):
    model_path = tmp_path / "retention.model"
    model_path.write_bytes(pickle.dumps(DummyRetentionModel()))

    predictor = MLRetentionPredictor(model_path=str(model_path))

    predictions = predictor.predict([
        {
            "motion": 0.2,
            "face_arousal": 0.4,
            "face_valence": 0.6,
            "detection_density": 0.3,
            "audio_energy": 0.1,
            "is_silent": False,
        },
        {
            "motion": 0.9,
            "face_arousal": 0.4,
            "face_valence": 0.6,
            "detection_density": 0.4,
            "audio_energy": 0.1,
            "is_silent": True,
        },
    ])

    assert predictions == [0.5, 1.0]


def test_ml_retention_predictor_validates_prediction_count(tmp_path):
    model_path = tmp_path / "retention.model"
    model_path.write_bytes(pickle.dumps(BadCountRetentionModel()))

    predictor = MLRetentionPredictor(model_path=str(model_path))

    try:
        predictor.predict([{"motion": 0.1}, {"motion": 0.2}])
    except ValueError as exc:
        assert "returned 1 predictions for 2 feature rows" in str(exc)
    else:
        raise AssertionError("Expected invalid prediction count to raise ValueError")
