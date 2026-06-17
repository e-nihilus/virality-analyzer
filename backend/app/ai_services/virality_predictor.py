"""Virality score providers.

The default provider is intentionally named ``derived_formula`` to avoid
presenting the current composite formula as an AI-trained virality predictor.
Configure ``VIRALITY_PREDICTOR_PROVIDER=ml`` and ``VIRALITY_MODEL_PATH`` to use a
serialized model that predicts one virality score per sampled second.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
import pickle
from pathlib import Path

from .provider_exceptions import ProviderDependencyError


class ViralityPredictor(ABC):
    provider_name = "derived_formula"

    def validate_dependencies(self) -> None:
        """Validate optional provider dependencies."""

    def predict_video(self, features: dict) -> float | None:
        """Return one aggregate score, or None to keep derived aggregate."""
        return None

    @abstractmethod
    def predict_timeline(self, features_per_second: list[dict]) -> list[float] | None:
        """Return one score per feature row, or None to keep existing formula."""


class DerivedViralityPredictor(ViralityPredictor):
    """Keeps timeline_builder's composite formula and labels it as derived."""

    provider_name = "derived_formula"

    def predict_timeline(self, features_per_second: list[dict]) -> list[float] | None:
        return None


class MLViralityPredictor(ViralityPredictor):
    """Serialized ML virality model provider.

    The model must expose ``predict(matrix)``. Input feature columns are fixed so
    training/export can match runtime order.
    """

    provider_name = "ml"
    feature_columns = [
        "current_virality",
        "motion",
        "brightness",
        "audio_energy",
        "audio_energy_change",
        "face_arousal",
        "face_valence",
        "detection_density",
        "retention",
    ]

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or os.environ.get("VIRALITY_MODEL_PATH") or os.environ.get("AUREA_VIRALITY_MODEL_PATH")
        self._model = None

    def validate_dependencies(self) -> None:
        if not self.model_path:
            raise ProviderDependencyError(
                "ML virality provider requested but VIRALITY_MODEL_PATH is not configured"
            )
        if not Path(self.model_path).exists():
            raise ProviderDependencyError(
                f"ML virality provider requested but model file does not exist: {self.model_path}"
            )

        suffix = Path(self.model_path).suffix.lower()
        if suffix == ".joblib":
            try:
                import joblib  # noqa: F401
            except ImportError as exc:
                raise ProviderDependencyError(
                    "ML virality provider requested a joblib model but 'joblib' is not installed"
                ) from exc

    def _load_model(self):
        if self._model is not None:
            return self._model

        self.validate_dependencies()
        assert self.model_path is not None
        path = Path(self.model_path)

        if path.suffix.lower() == ".joblib":
            import joblib

            self._model = joblib.load(path)
            return self._model

        with path.open("rb") as f:
            self._model = pickle.load(f)
        return self._model

    def predict_video(self, features: dict) -> float | None:
        predictions = self.predict_timeline([features])
        if predictions is None:
            return None
        return predictions[0] if predictions else None

    def predict_timeline(self, features_per_second: list[dict]) -> list[float] | None:
        if not features_per_second:
            return []

        model = self._load_model()
        matrix = [
            [_feature_value(row, column) for column in self.feature_columns]
            for row in features_per_second
        ]
        try:
            raw_predictions = model.predict(matrix)
        except AttributeError as exc:
            raise ProviderDependencyError(
                "Configured virality model does not expose a predict(matrix) method"
            ) from exc

        predictions = _flatten_predictions(raw_predictions)
        if len(predictions) != len(features_per_second):
            raise ValueError(
                f"Virality model returned {len(predictions)} predictions for {len(features_per_second)} feature rows"
            )
        return [round(_clamp(float(value), 0.0, 1.0), 3) for value in predictions]


def _feature_value(row: dict, column: str) -> float:
    default = 0.5 if column in {"brightness", "face_valence", "current_virality", "retention"} else 0.0
    try:
        value = row.get(column, default)
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _flatten_predictions(predictions: object) -> list[float]:
    if hasattr(predictions, "tolist"):
        predictions = predictions.tolist()
    if isinstance(predictions, (tuple, list)):
        flattened: list[float] = []
        for item in predictions:
            if isinstance(item, (tuple, list)):
                if item:
                    flattened.append(float(item[0]))
            else:
                flattened.append(float(item))
        return flattened
    return [float(predictions)]


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, value))
