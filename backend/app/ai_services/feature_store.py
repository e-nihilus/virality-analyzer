"""Feature store for V2 multimodal window embeddings."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from ..processing.window_builder import TimeWindow, build_windows
from ..schemas.analysis import TranscriptSegment
from .embeddings.audio_embedder import AudioEmbeddingInput, ScalarAudioEmbedder
from .embeddings.text_embedder import HashingTextEmbedder, TextSegmentInput
from .embeddings.video_embedder import ScalarVideoEmbedder, VideoEmbeddingInput


FEATURES_DIRNAME = "features"
FEATURE_MATRIX_FILENAME = "multimodal_windows.npz"
FEATURE_METADATA_FILENAME = "multimodal_windows.json"


@dataclass(frozen=True)
class MultimodalFeatureSet:
    analysis_id: str
    matrix: np.ndarray
    windows: list[TimeWindow]
    dimensions: dict[str, int]
    providers: dict[str, str]
    matrix_path: Path
    metadata_path: Path

    @property
    def shape(self) -> tuple[int, int]:
        return tuple(self.matrix.shape)  # type: ignore[return-value]


class FeatureStore:
    """Persist and load feature tensors by analysis id."""

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.features_dir = self.output_dir / FEATURES_DIRNAME

    @property
    def matrix_path(self) -> Path:
        return self.features_dir / FEATURE_MATRIX_FILENAME

    @property
    def metadata_path(self) -> Path:
        return self.features_dir / FEATURE_METADATA_FILENAME

    def save(self, feature_set: MultimodalFeatureSet) -> MultimodalFeatureSet:
        self.features_dir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            self.matrix_path,
            embeddings=feature_set.matrix.astype(np.float32, copy=False),
            window_start=np.array([window.start_seconds for window in feature_set.windows], dtype=np.float32),
            window_end=np.array([window.end_seconds for window in feature_set.windows], dtype=np.float32),
        )
        metadata = {
            "analysis_id": feature_set.analysis_id,
            "shape": list(feature_set.matrix.shape),
            "dimensions": feature_set.dimensions,
            "providers": feature_set.providers,
            "windows": [
                {
                    "index": window.index,
                    "start_seconds": window.start_seconds,
                    "end_seconds": window.end_seconds,
                    "center_seconds": window.center_seconds,
                }
                for window in feature_set.windows
            ],
        }
        self.metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return MultimodalFeatureSet(
            analysis_id=feature_set.analysis_id,
            matrix=feature_set.matrix,
            windows=feature_set.windows,
            dimensions=feature_set.dimensions,
            providers=feature_set.providers,
            matrix_path=self.matrix_path,
            metadata_path=self.metadata_path,
        )

    def load(self) -> tuple[np.ndarray, dict] | None:
        if not self.matrix_path.exists() or not self.metadata_path.exists():
            return None
        with np.load(self.matrix_path) as data:
            matrix = data["embeddings"]
        metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        return matrix, metadata


def build_and_persist_multimodal_features(
    *,
    analysis_id: str,
    output_dir: str | Path,
    duration_seconds: float,
    frame_diffs: list[float],
    brightness: list[float],
    detection_density: list[float] | None = None,
    face_valence: list[float] | None = None,
    face_arousal: list[float] | None = None,
    audio_energy: list[float] | None = None,
    audio_silence: list[bool] | None = None,
    audio_energy_change: list[float] | None = None,
    audio_pitch_hz: list[float] | None = None,
    audio_pitch_variance: list[float] | None = None,
    audio_speech_rate: list[float] | None = None,
    audio_beat_drop: list[float] | None = None,
    audio_laughter_scream: list[float] | None = None,
    audio_voice_intensity: list[float] | None = None,
    transcript_segments: list[TranscriptSegment] | None = None,
    sample_interval_seconds: float = 1.0,
    window_seconds: float = 3.0,
    stride_seconds: float = 1.0,
) -> MultimodalFeatureSet:
    """Build ``(n_windows, dim_video + dim_audio + dim_text)`` and persist it."""
    windows = build_windows(
        duration_seconds,
        window_seconds=window_seconds,
        stride_seconds=stride_seconds,
    )

    video_embedder = ScalarVideoEmbedder()
    audio_embedder = ScalarAudioEmbedder()
    text_embedder = HashingTextEmbedder()

    video_matrix = np.array(
        video_embedder.embed_windows(
            windows=windows,
            inputs=VideoEmbeddingInput(
                frame_diffs=frame_diffs,
                brightness=brightness,
                detection_density=detection_density,
                face_valence=face_valence,
                face_arousal=face_arousal,
                sample_interval_seconds=sample_interval_seconds,
            ),
        ),
        dtype=np.float32,
    )
    audio_matrix = np.array(
        audio_embedder.embed_windows(
            windows=windows,
            inputs=AudioEmbeddingInput(
                rms_energy=audio_energy,
                silence_mask=audio_silence,
                energy_change=audio_energy_change,
                pitch_hz=audio_pitch_hz,
                pitch_variance=audio_pitch_variance,
                speech_rate=audio_speech_rate,
                beat_drop=audio_beat_drop,
                laughter_scream=audio_laughter_scream,
                voice_intensity=audio_voice_intensity,
                sample_interval_seconds=sample_interval_seconds,
            ),
        ),
        dtype=np.float32,
    )
    text_matrix = np.array(
        text_embedder.embed_windows(
            windows=windows,
            segments=[
                TextSegmentInput(start=segment.start, end=segment.end, text=segment.text)
                for segment in transcript_segments or []
            ],
        ),
        dtype=np.float32,
    )

    matrix = np.concatenate([video_matrix, audio_matrix, text_matrix], axis=1)
    feature_set = MultimodalFeatureSet(
        analysis_id=analysis_id,
        matrix=matrix,
        windows=windows,
        dimensions={
            "video": int(video_matrix.shape[1]),
            "audio": int(audio_matrix.shape[1]),
            "text": int(text_matrix.shape[1]),
            "total": int(matrix.shape[1]),
        },
        providers={
            "video": video_embedder.provider_name,
            "audio": audio_embedder.provider_name,
            "text": text_embedder.provider_name,
        },
        matrix_path=Path(output_dir) / FEATURES_DIRNAME / FEATURE_MATRIX_FILENAME,
        metadata_path=Path(output_dir) / FEATURES_DIRNAME / FEATURE_METADATA_FILENAME,
    )
    return FeatureStore(output_dir).save(feature_set)
