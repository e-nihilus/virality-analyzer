"""Retention prediction providers.

The production contract is intentionally model-friendly: callers provide one
feature row per sampled second and receive one normalized retention estimate per
row. Until a trained regression model is available, the heuristic provider uses
all signals already extracted by the AI pipeline instead of the old linear
motion-only decay.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging
import os
import pickle
from pathlib import Path

from .provider_exceptions import ProviderDependencyError

logger = logging.getLogger(__name__)


class RetentionPredictor(ABC):
    provider_name = "heuristic"

    def validate_dependencies(self) -> None:
        """Validate optional provider dependencies."""

    @abstractmethod
    def predict(self, features_per_second: list[dict]) -> list[float]:
        """Return one retention score in [0, 1] per feature row."""


class HeuristicRetentionPredictor(RetentionPredictor):
    """AI-signal fusion estimator used until a trained retention model exists."""

    provider_name = "heuristic"

    def predict(self, features_per_second: list[dict]) -> list[float]:
        if not features_per_second:
            return []

        n = len(features_per_second)
        predictions: list[float] = []
        previous = 0.88

        for i, features in enumerate(features_per_second):
            progress = i / max(n - 1, 1)
            motion = _as_float(features.get("motion"), default=0.0)
            face_arousal = _as_float(features.get("face_arousal"), default=0.0)
            face_valence = _as_float(features.get("face_valence"), default=0.5)
            detection_density = _as_float(features.get("detection_density"), default=0.0)
            audio_energy = _as_float(features.get("audio_energy"), default=0.0)
            is_silent = bool(features.get("is_silent", False))

            # Non-linear baseline: strongest pressure is in the first seconds,
            # then decay stabilizes instead of dropping linearly forever.
            baseline = 0.86 - 0.12 * (progress ** 0.75)

            score = baseline
            score += 0.14 * motion
            score += 0.08 * audio_energy
            score += 0.14 * detection_density
            score += 0.10 * face_arousal
            score += 0.04 * max(face_valence - 0.5, 0.0)

            if is_silent and motion < 0.25:
                score -= 0.18
            elif is_silent:
                score -= 0.08

            if detection_density <= 0.05 and motion < 0.2:
                score -= 0.12

            if detection_density >= 0.45:
                score += 0.08

            # Avoid one-frame cliffs unless all engagement signals are weak.
            score = 0.7 * score + 0.3 * previous
            score = _clamp(score, 0.25, 1.0)
            predictions.append(round(score, 3))
            previous = score

        return predictions


class MLRetentionPredictor(RetentionPredictor):
    """Serialized ML retention model provider.

    Configure with ``RETENTION_MODEL_PATH`` or ``AUREA_RETENTION_MODEL_PATH``.
    The model object must expose ``predict(matrix)`` and return one numeric
    retention estimate per input row. Supported file formats:

    - ``.joblib`` / ``.pkl`` / ``.pickle`` via joblib when installed
    - any other extension via Python pickle
    """

    provider_name = "ml"
    feature_columns = [
        "motion",
        "face_arousal",
        "face_valence",
        "detection_density",
        "audio_energy",
        "is_silent",
    ]

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or os.environ.get("RETENTION_MODEL_PATH") or os.environ.get("AUREA_RETENTION_MODEL_PATH")
        self._model = None

    def validate_dependencies(self) -> None:
        if not self.model_path:
            raise ProviderDependencyError(
                "ML retention provider requested but RETENTION_MODEL_PATH is not configured"
            )
        if not Path(self.model_path).exists():
            raise ProviderDependencyError(
                f"ML retention provider requested but model file does not exist: {self.model_path}"
            )

        suffix = Path(self.model_path).suffix.lower()
        if suffix in {".joblib", ".pkl", ".pickle"}:
            try:
                import joblib  # noqa: F401
            except ImportError as exc:
                if suffix == ".joblib":
                    raise ProviderDependencyError(
                        "ML retention provider requested a joblib model but 'joblib' is not installed"
                    ) from exc

    def _load_model(self):
        if self._model is not None:
            return self._model

        self.validate_dependencies()
        assert self.model_path is not None
        path = Path(self.model_path)

        if path.suffix.lower() in {".joblib", ".pkl", ".pickle"}:
            try:
                import joblib

                self._model = joblib.load(path)
                return self._model
            except ImportError:
                # Pickle fallback for .pkl/.pickle when joblib is not installed.
                if path.suffix.lower() == ".joblib":
                    raise

        with path.open("rb") as f:
            self._model = pickle.load(f)
        return self._model

    def predict(self, features_per_second: list[dict]) -> list[float]:
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
                "Configured retention model does not expose a predict(matrix) method"
            ) from exc

        predictions = _flatten_predictions(raw_predictions)
        if len(predictions) != len(features_per_second):
            raise ValueError(
                f"Retention model returned {len(predictions)} predictions for {len(features_per_second)} feature rows"
            )
        return [round(_clamp(float(value), 0.0, 1.0), 3) for value in predictions]


def _as_float(value: object, *, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return min(hi, max(lo, value))


def _feature_value(row: dict, column: str) -> float:
    if column == "is_silent":
        return 1.0 if bool(row.get(column, False)) else 0.0
    default = 0.5 if column == "face_valence" else 0.0
    return _as_float(row.get(column), default=default)


def _flatten_predictions(predictions: object) -> list[float]:
    if hasattr(predictions, "tolist"):
        predictions = predictions.tolist()
    if isinstance(predictions, (tuple, list)):
        flattened: list[float] = []
        for item in predictions:
            if isinstance(item, (tuple, list)):
                if not item:
                    continue
                flattened.append(float(item[0]))
            else:
                flattened.append(float(item))
        return flattened
    return [float(predictions)]
