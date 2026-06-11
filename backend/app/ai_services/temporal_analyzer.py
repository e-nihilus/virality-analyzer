"""Temporal analyzer adapters for heuristic and VideoMAE providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .provider_exceptions import ProviderDependencyError


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
    """VideoMAE provider placeholder.

    The adapter keeps current behavior while exposing a stable integration point
    for real action recognition in a future phase.
    """

    provider_name = "videomae"

    def __init__(self, fallback: TemporalAnalyzerAdapter | None = None) -> None:
        self._fallback = fallback or HeuristicTemporalAnalyzer()

    def validate_dependencies(self) -> None:
        try:
            import transformers  # noqa: F401
            import torch  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "VideoMAE provider requested but required 'torch/transformers' dependencies are not installed"
            ) from exc

    def analyze(self, *, timeline: list[object]) -> TemporalAnalysis:
        self.validate_dependencies()

        # TODO(phase-14): run VideoMAE on frame windows and map logits into
        # per-video action recognition confidence.
        fallback_analysis = self._fallback.analyze(timeline=timeline)
        fallback_analysis.provider = self.provider_name
        return fallback_analysis
