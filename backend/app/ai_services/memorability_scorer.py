"""Memorability scorers used for rewatch-factor estimation."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
import logging
from pathlib import Path

from ..schemas.analysis import TimelineEntry
from .provider_exceptions import ProviderDependencyError

logger = logging.getLogger(__name__)

# Process-wide CLIP model cache, keyed by model id. Loaded once and reused across
# analyses instead of being rebuilt on every request.
_CLIP_CACHE: dict[str, tuple[object, object]] = {}
_CLIP_LOCK = threading.Lock()


def _load_clip_model(model_id: str) -> tuple[object, object]:
    """Return a cached (model, processor) pair for *model_id*."""
    cached = _CLIP_CACHE.get(model_id)
    if cached is not None:
        return cached
    with _CLIP_LOCK:
        cached = _CLIP_CACHE.get(model_id)
        if cached is None:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            logger.info("Loading CLIP model %s (cached for reuse) …", model_id)
            processor = CLIPProcessor.from_pretrained(model_id)
            model = CLIPModel.from_pretrained(model_id)
            model = model.to("cuda" if torch.cuda.is_available() else "cpu")
            model.eval()
            cached = (model, processor)
            _CLIP_CACHE[model_id] = cached
    return cached


class MemorabilityScorer(ABC):
    provider_name = "heuristic"

    def validate_dependencies(self) -> None:
        """Validate optional provider dependencies."""

    @abstractmethod
    def score_timeline(self, *, video_path: str, timeline: list[TimelineEntry]) -> list[float]:
        """Return one memorability score in [0, 1] per timeline entry."""


class HeuristicMemorabilityScorer(MemorabilityScorer):
    provider_name = "heuristic"

    def score_timeline(self, *, video_path: str, timeline: list[TimelineEntry]) -> list[float]:
        if not timeline:
            return []
        scores: list[float] = []
        for i, entry in enumerate(timeline):
            virality = entry.virality or 0.0
            arousal = entry.arousal or 0.0
            prev_v = timeline[i - 1].virality if i > 0 else virality
            novelty = abs(virality - (prev_v or 0.0))
            scores.append(min(1.0, 0.55 * virality + 0.30 * arousal + 0.15 * novelty))
        return scores


class ClipMemorabilityScorer(MemorabilityScorer):
    """CLIP prompt-similarity scorer for sampled video frames."""

    provider_name = "clip"

    _MODEL_ID = "openai/clip-vit-base-patch32"
    _POSITIVE_PROMPTS = [
        "a memorable viral moment",
        "a surprising reveal",
        "an emotional reaction",
    ]
    _NEGATIVE_PROMPTS = ["a boring static shot"]

    def __init__(self, fallback: MemorabilityScorer | None = None) -> None:
        # Keep the argument for compatibility with the factory, but do not use a
        # heuristic runtime fallback: callers must know when CLIP failed so
        # rewatch_factor can be marked unavailable instead of looking like AI.
        self._model = None
        self._processor = None

    def validate_dependencies(self) -> None:
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
            import PIL  # noqa: F401
            import cv2  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "CLIP memorability scorer requested but required dependencies are not installed"
            ) from exc

    def _load_model(self) -> None:
        if self._model is not None:
            return
        self._model, self._processor = _load_clip_model(self._MODEL_ID)

    def score_timeline(self, *, video_path: str, timeline: list[TimelineEntry]) -> list[float]:
        self.validate_dependencies()
        if not timeline or not Path(video_path).exists():
            return []

        try:
            import cv2
            import torch
            from PIL import Image

            self._load_model()
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            prompts = self._POSITIVE_PROMPTS + self._NEGATIVE_PROMPTS

            # Per-frame CLIP "memorability margin": how much more the frame looks
            # like a memorable/viral/emotional moment than a boring static shot.
            # CLIP assigns most real footage a high absolute similarity to "a
            # boring static shot", so the raw margin is almost always negative.
            # The signal that matters is the *relative* variation across the
            # video, so margins are min-max normalized below to surface the most
            # memorable moments. (The old absolute `positive - negative + 0.5`
            # mapping floored every score to 0.0, which meant no top clips ever.)
            margins: list[float | None] = []
            for entry in timeline:
                frame_no = int((entry.time_seconds or 0.0) * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
                ok, frame = cap.read()
                if not ok:
                    margins.append(None)
                    continue
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(rgb)
                inputs = self._processor(
                    text=prompts,
                    images=image,
                    return_tensors="pt",
                    padding=True,
                )
                inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
                with torch.no_grad():
                    outputs = self._model(**inputs)
                    probs = outputs.logits_per_image.softmax(dim=1)[0].detach().cpu().tolist()
                positive = max(probs[: len(self._POSITIVE_PROMPTS)])
                negative = probs[-1]
                margins.append(positive - negative)

            cap.release()
            return self._normalize_margins(margins)
        except Exception:
            logger.warning("CLIP memorability scoring failed", exc_info=True)
            raise

    @staticmethod
    def _normalize_margins(margins: list[float | None]) -> list[float]:
        """Min-max normalize per-frame margins into [0, 1] memorability scores.

        Frames that could not be read (``None``) score 0.0. When every frame has
        essentially the same margin (a flat, uniform video) there is no
        meaningful peak to surface, so all frames get a neutral 0.5.
        """
        valid = [m for m in margins if m is not None]
        if not valid:
            return [0.0 for _ in margins]

        lo = min(valid)
        hi = max(valid)
        spread = hi - lo

        scores: list[float] = []
        for margin in margins:
            if margin is None:
                scores.append(0.0)
            elif spread < 1e-6:
                scores.append(0.5)
            else:
                scores.append(round((margin - lo) / spread, 3))
        return scores
