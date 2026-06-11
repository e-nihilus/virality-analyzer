"""Explanation generator adapters for heuristic and Qwen providers."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod

from ..schemas.analysis import Insight, TimelineEntry, TopClip
from .explanation_engine import generate_insights
from .provider_exceptions import ProviderDependencyError


class ExplanationGenerator(ABC):
    """Abstraction for generating natural-language analysis insights."""

    provider_name = "heuristic"

    def validate_dependencies(self) -> None:
        """Validate optional provider dependencies."""

    @abstractmethod
    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        """Generate insights for the analysis result."""


class HeuristicExplanationGenerator(ExplanationGenerator):
    """Current rule-based explanation generator."""

    provider_name = "heuristic"

    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        return generate_insights(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion,
        )


class CachedExplanationGenerator(ExplanationGenerator):
    """Simple in-memory cache wrapper for explanation generation."""

    _GLOBAL_CACHE: dict[str, list[Insight]] = {}

    def __init__(self, inner: ExplanationGenerator) -> None:
        self.inner = inner
        self.provider_name = inner.provider_name
        self._cache = self._GLOBAL_CACHE

    def _cache_key(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> str:
        payload = (
            self.provider_name,
            round(duration, 3),
            round(overall_virality, 3),
            round(retention_score, 3),
            dominant_emotion,
            tuple((e.time_seconds, e.virality, e.valence, e.arousal, e.retention, e.label) for e in timeline),
            tuple((c.start_seconds, c.end_seconds, c.score, c.predicted_retention, tuple(c.reasons or [])) for c in top_clips),
        )
        return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()

    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        key = self._cache_key(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion,
        )
        if key not in self._cache:
            self._cache[key] = self.inner.generate(
                timeline=timeline,
                top_clips=top_clips,
                duration=duration,
                overall_virality=overall_virality,
                retention_score=retention_score,
                dominant_emotion=dominant_emotion,
            )
        return list(self._cache[key])


class QwenExplanationGenerator(ExplanationGenerator):
    """Qwen2.5-VL explanation provider placeholder.

    This provider is restricted to explanation generation only. Viral scores are
    still calculated by heuristic modules in the analysis pipeline.
    """

    provider_name = "qwen"

    def __init__(self, fallback: ExplanationGenerator | None = None) -> None:
        self._fallback = fallback or HeuristicExplanationGenerator()

    def validate_dependencies(self) -> None:
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "Qwen provider requested but required 'torch/transformers' dependencies are not installed"
            ) from exc

    def generate(
        self,
        *,
        timeline: list[TimelineEntry],
        top_clips: list[TopClip],
        duration: float,
        overall_virality: float,
        retention_score: float,
        dominant_emotion: str,
    ) -> list[Insight]:
        self.validate_dependencies()

        # TODO(phase-14): call Qwen2.5-VL to generate richer explanations from
        # temporal signals and transcript context. Keep score computation outside
        # this generator to preserve deterministic virality scoring.
        return self._fallback.generate(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion,
        )
