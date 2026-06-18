"""Temporal analyzer adapters for heuristic and VideoMAE providers."""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .provider_exceptions import ProviderDependencyError

logger = logging.getLogger(__name__)

# Process-wide VideoMAE model cache, keyed by model name. Loaded once and reused
# across analyses instead of being rebuilt on every request.
_VIDEOMAE_CACHE: dict[str, tuple[object, object, str]] = {}
_VIDEOMAE_LOCK = threading.Lock()


def _load_videomae_model(model_name: str) -> tuple[object, object, str]:
    """Return a cached (model, processor, device) tuple for *model_name*."""
    cached = _VIDEOMAE_CACHE.get(model_name)
    if cached is not None:
        return cached
    with _VIDEOMAE_LOCK:
        cached = _VIDEOMAE_CACHE.get(model_name)
        if cached is None:
            import torch
            from transformers import VideoMAEForVideoClassification, VideoMAEImageProcessor

            logger.info("Loading VideoMAE model %s (cached for reuse) …", model_name)
            processor = VideoMAEImageProcessor.from_pretrained(model_name)
            model = VideoMAEForVideoClassification.from_pretrained(model_name)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model = model.to(device)
            model.eval()
            cached = (model, processor, device)
            _VIDEOMAE_CACHE[model_name] = cached
    return cached


@dataclass
class TemporalAnalysis:
    """Temporal output attached to clip reasoning and labels."""

    action_score: float
    provider: str = "heuristic"


class TemporalAnalyzerAdapter(ABC):
    """Abstraction for video temporal understanding providers."""

    provider_name = "heuristic"

    def validate_dependencies(self) -> None:
        """Validate optional provider dependencies."""

    @abstractmethod
    def analyze(self, *, timeline: list[object]) -> TemporalAnalysis:
        """Generate temporal action understanding signals."""


class HeuristicTemporalAnalyzer(TemporalAnalyzerAdapter):
    """Lightweight temporal analyzer using timeline dynamics."""

    provider_name = "heuristic"

    def analyze(self, *, timeline: list[object]) -> TemporalAnalysis:
        if not timeline:
            return TemporalAnalysis(action_score=0.0, provider=self.provider_name)

        virality_values = [getattr(entry, "virality", None) or 0.0 for entry in timeline]
        movement_ratio = sum(1 for score in virality_values if score > 0.55) / max(len(virality_values), 1)
        return TemporalAnalysis(action_score=round(movement_ratio, 3), provider=self.provider_name)


class VideoMAETemporalAnalyzer(TemporalAnalyzerAdapter):
    """VideoMAE action-recognition adapter.

    When *video_path* is provided at construction time the adapter eagerly
    samples 16 frames, runs ``VideoMAEForVideoClassification`` inference and
    caches the resulting action score.  At ``analyze`` time the pre-computed
    score is returned directly; if inference was skipped or failed the adapter
    transparently falls back to the heuristic provider.
    """

    provider_name = "videomae"
    _MODEL_NAME = "MCG-NJU/videomae-base-finetuned-kinetics"
    _NUM_FRAMES = 16

    def __init__(
        self,
        fallback: TemporalAnalyzerAdapter | None = None,
        video_path: str | None = None,
    ) -> None:
        self._fallback = fallback or HeuristicTemporalAnalyzer()
        self._precomputed_score: float | None = None
        self._precomputed_label: str | None = None

        if video_path is not None:
            self._run_inference(video_path)

    def validate_dependencies(self) -> None:
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "VideoMAE provider requested but required 'torch/transformers' dependencies are not installed"
            ) from exc

    def _sample_frames(self, video_path: str) -> list:
        """Sample *_NUM_FRAMES* evenly-spaced RGB frames from *video_path*."""
        import cv2
        import numpy as np

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < 1:
            cap.release()
            raise RuntimeError(f"Video has no frames: {video_path}")

        indices = np.linspace(0, total_frames - 1, self._NUM_FRAMES, dtype=int)
        frames: list[np.ndarray] = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ret, frame = cap.read()
            if not ret:
                cap.release()
                raise RuntimeError(f"Failed to read frame {idx} from {video_path}")
            frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        cap.release()
        return frames

    def _run_inference(self, video_path: str) -> None:
        """Run VideoMAE inference and cache the action score."""
        try:
            self.validate_dependencies()
            import torch

            frames = self._sample_frames(video_path)

            model, processor, device = _load_videomae_model(self._MODEL_NAME)

            inputs = processor(frames, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = model(**inputs)

            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)
            top_prob, top_idx = probs.topk(1)

            self._precomputed_score = round(top_prob.item(), 4)
            self._precomputed_label = model.config.id2label[top_idx.item()]
            logger.info(
                "VideoMAE inference complete — label=%s score=%.4f",
                self._precomputed_label,
                self._precomputed_score,
            )
        except ProviderDependencyError:
            logger.warning("VideoMAE dependencies unavailable; falling back to heuristic")
        except Exception:
            logger.warning("VideoMAE inference failed; falling back to heuristic", exc_info=True)

    def analyze(self, *, timeline: list[object]) -> TemporalAnalysis:
        if self._precomputed_score is not None:
            return TemporalAnalysis(
                action_score=self._precomputed_score,
                provider=self.provider_name,
            )

        return self._fallback.analyze(timeline=timeline)
