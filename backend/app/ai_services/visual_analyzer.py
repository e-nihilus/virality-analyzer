"""Visual analyzer adapters for heuristic and YOLO providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import logging

from .provider_exceptions import ProviderDependencyError

logger = logging.getLogger(__name__)


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

    def _run_yolo_on_frames(
        self,
        video_path: str,
        interval_seconds: float,
    ) -> list[dict[str, object]]:
        """Sample frames from *video_path* and run YOLOv8 detection."""
        import cv2
        from ultralytics import YOLO

        model = YOLO("yolov8n.pt")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("Could not open video for YOLO inference: %s", video_path)
            return []

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_step = max(1, int(fps * interval_seconds))
        detections: list[dict[str, object]] = []
        frame_idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
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
                                "frame_index": frame_idx,
                                "class_name": class_name,
                                "confidence": round(conf, 4),
                                "bbox": [x1, y1, x2, y2],
                            }
                        )

            frame_idx += 1

        cap.release()
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
        fallback_analysis.provider = self.provider_name

        try:
            detections = self._run_yolo_on_frames(video_path, interval_seconds)
            fallback_analysis.detections = detections
        except Exception:
            logger.warning(
                "YOLOv8 inference failed; returning heuristic-only result",
                exc_info=True,
            )

        return fallback_analysis
