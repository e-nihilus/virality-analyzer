"""Visual analyzer adapters for heuristic and YOLO providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .provider_exceptions import ProviderDependencyError


@dataclass
class VisualAnalysis:
    """Container with visual signals used by the timeline builder."""

    frame_diffs: list[float]
    brightness: list[float]
    provider: str = "heuristic"
    detections: list[dict[str, object]] = field(default_factory=list)


class VisualAnalyzerAdapter(ABC):
    """Abstraction for visual signal extraction providers."""

    provider_name = "heuristic"

    def validate_dependencies(self) -> None:
        """Validate optional runtime dependencies.

        Concrete adapters can override this to raise
        :class:`ProviderDependencyError` when optional libraries are missing.
        """

    @abstractmethod
    def analyze(
        self,
        *,
        video_path: str,
        output_dir: str,
        interval_seconds: float,
    ) -> VisualAnalysis:
        """Extract visual signals from a video source."""


class HeuristicVisualAnalyzer(VisualAnalyzerAdapter):
    """Current production visual analyzer based on OpenCV heuristics."""

    provider_name = "heuristic"

    def analyze(
        self,
        *,
        video_path: str,
        output_dir: str,
        interval_seconds: float,
    ) -> VisualAnalysis:
        # Local import keeps startup lightweight for tests that do not touch OpenCV.
        from ..processing.frame_extractor import (
            compute_brightness,
            compute_frame_diffs,
            extract_frames,
        )

        extract_frames(video_path, output_dir, interval_seconds=interval_seconds)
        frame_diffs = compute_frame_diffs(video_path, interval_seconds=interval_seconds)
        brightness = compute_brightness(video_path, interval_seconds=interval_seconds)
        return VisualAnalysis(
            frame_diffs=frame_diffs,
            brightness=brightness,
            provider=self.provider_name,
        )


class YoloVisualAnalyzer(VisualAnalyzerAdapter):
    """YOLOv8 provider placeholder.

    The real model integration is intentionally deferred: this adapter checks
    optional dependencies and keeps heuristic outputs so the contract remains
    unchanged until model inference is enabled in a later phase.
    """

    provider_name = "yolo"

    def __init__(self, fallback: VisualAnalyzerAdapter | None = None) -> None:
        self._fallback = fallback or HeuristicVisualAnalyzer()

    def validate_dependencies(self) -> None:
        try:
            import ultralytics  # noqa: F401
        except ImportError as exc:
            raise ProviderDependencyError(
                "YOLO provider requested but 'ultralytics' is not installed"
            ) from exc

    def analyze(
        self,
        *,
        video_path: str,
        output_dir: str,
        interval_seconds: float,
    ) -> VisualAnalysis:
        self.validate_dependencies()

        # TODO(phase-14): load YOLOv8 weights and produce real object/scene
        # detections. For now we preserve current behavior through heuristic
        # signal extraction to keep pipeline compatibility.
        fallback_analysis = self._fallback.analyze(
            video_path=video_path,
            output_dir=output_dir,
            interval_seconds=interval_seconds,
        )
        fallback_analysis.provider = self.provider_name
        return fallback_analysis
