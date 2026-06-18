"""Visual analyzer adapters for heuristic and YOLO providers."""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import logging

from .provider_exceptions import ProviderDependencyError

if TYPE_CHECKING:
    from ..processing.frame_extractor import SampledFrame

logger = logging.getLogger(__name__)

# Process-wide YOLO model cache. Loading the model is expensive, so it is loaded
# once and reused across analyses instead of being rebuilt on every request.
_YOLO_MODEL = None
_YOLO_LOCK = threading.Lock()


def _load_yolo_model():
    """Return a cached YOLOv8 model, loading it on first use."""
    global _YOLO_MODEL
    if _YOLO_MODEL is None:
        with _YOLO_LOCK:
            if _YOLO_MODEL is None:
                from ultralytics import YOLO

                logger.info("Loading YOLOv8 model (cached for reuse) …")
                _YOLO_MODEL = YOLO("yolov8n.pt")
    return _YOLO_MODEL


@dataclass
class VisualAnalysis:
    """Container with visual signals used by the timeline builder."""

    frame_diffs: list[float]
    brightness: list[float]
    provider: str = "heuristic"
    detections: list[dict[str, object]] = field(default_factory=list)
    samples: list["SampledFrame"] = field(default_factory=list)


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
        from ..processing.frame_extractor import extract_sampled_frames

        # Single decode pass: saves frames + computes diffs + brightness together.
        sampled = extract_sampled_frames(
            video_path, output_dir, interval_seconds=interval_seconds
        )
        return VisualAnalysis(
            frame_diffs=sampled.frame_diffs,
            brightness=sampled.brightness,
            provider=self.provider_name,
            samples=sampled.samples,
        )


class YoloVisualAnalyzer(VisualAnalyzerAdapter):
    """YOLOv8 provider that combines heuristic signals with object detection."""

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

    def _run_yolo_on_samples(
        self,
        samples: list["SampledFrame"],
    ) -> list[dict[str, object]]:
        """Run YOLOv8 detection on already-sampled frame JPEGs.

        Reuses the frames decoded once by the heuristic extractor instead of
        re-decoding the entire video.
        """
        import cv2

        model = _load_yolo_model()

        detections: list[dict[str, object]] = []
        for sample in samples:
            frame = cv2.imread(str(sample.path))
            if frame is None:
                logger.warning("Could not read sampled frame for YOLO: %s", sample.path)
                continue

            results = model(frame, verbose=False)
            for result in results:
                for box in result.boxes:
                    conf = float(box.conf[0])
                    if conf < 0.4:
                        continue
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0])
                    class_name = result.names.get(cls_id, str(cls_id))
                    detections.append(
                        {
                            "frame_index": sample.frame_index,
                            "sample_index": sample.sample_index,
                            "time_seconds": round(sample.time_seconds, 2),
                            "class_name": class_name,
                            "confidence": round(conf, 4),
                            "bbox": [x1, y1, x2, y2],
                        }
                    )

        return detections

    def analyze(
        self,
        *,
        video_path: str,
        output_dir: str,
        interval_seconds: float,
    ) -> VisualAnalysis:
        self.validate_dependencies()

        fallback_analysis = self._fallback.analyze(
            video_path=video_path,
            output_dir=output_dir,
            interval_seconds=interval_seconds,
        )

        try:
            detections = self._run_yolo_on_samples(fallback_analysis.samples)
            fallback_analysis.provider = self.provider_name
            fallback_analysis.detections = detections
        except Exception:
            logger.warning(
                "YOLOv8 inference failed; returning heuristic-only result",
                exc_info=True,
            )

        return fallback_analysis
