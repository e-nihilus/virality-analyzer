"""Model warm-up — pre-loads heavy models at server startup.

Each model is loaded once and cached process-wide (see the ``_load_*`` helpers in
the individual provider modules). Warming them up at startup means the *first*
uploaded video does not pay the model-load cost during analysis.

Warm-up is best-effort: any failure (missing dependency, no GPU, download error)
is logged and skipped — it must never crash the server. Only the models enabled
by the current provider configuration are loaded.
"""

from __future__ import annotations

import logging
import os
import threading

from .provider_factory import (
    _env_flag,
    scene_detection_enabled,
    temporal_analysis_enabled,
)

logger = logging.getLogger(__name__)

_QWEN_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

_warmup_started = False
_warmup_lock = threading.Lock()


def warmup_enabled() -> bool:
    return _env_flag("AUREA_WARMUP_MODELS", "true") in {"1", "true", "yes"}


def _warm(name: str, fn) -> None:
    """Run a single warm-up step, logging failures without raising."""
    try:
        logger.info("Warming up %s …", name)
        fn()
        logger.info("Warm-up complete: %s", name)
    except Exception:
        logger.warning("Warm-up skipped for %s (unavailable or failed)", name, exc_info=True)


def _warm_yolo() -> None:
    from .visual_analyzer import _load_yolo_model

    _load_yolo_model()


def _warm_clip() -> None:
    from .memorability_scorer import ClipMemorabilityScorer, _load_clip_model

    _load_clip_model(ClipMemorabilityScorer._MODEL_ID)


def _warm_qwen() -> None:
    from .explanation_generator import _load_qwen_model

    _load_qwen_model(_QWEN_MODEL_ID)


def _warm_whisper() -> None:
    from .speech_analyzer import _load_whisper_model, whisper_available

    if not whisper_available():
        return
    _load_whisper_model(os.environ.get("AUREA_WHISPER_MODEL", "small"))


def _warm_videomae() -> None:
    from .temporal_analyzer import VideoMAETemporalAnalyzer, _load_videomae_model

    _load_videomae_model(VideoMAETemporalAnalyzer._MODEL_NAME)


def _warm_deepface() -> None:
    import numpy as np
    from deepface import DeepFace

    # Analysing a tiny blank frame forces DeepFace to build and cache its
    # emotion model so per-frame analysis is fast on the first real video.
    blank = np.zeros((48, 48, 3), dtype=np.uint8)
    DeepFace.analyze(img_path=blank, actions=["emotion"], enforce_detection=False)


def _run_warmup() -> None:
    """Load every model enabled by the current configuration."""
    logger.info("Starting model warm-up …")

    if _env_flag("VISUAL_ANALYZER_PROVIDER", "heuristic") == "yolo":
        _warm("YOLO", _warm_yolo)

    if _env_flag("EMOTION_ANALYZER_PROVIDER", "deepface") == "deepface":
        _warm("DeepFace", _warm_deepface)

    if _env_flag("MEMORABILITY_SCORER", "clip") == "clip":
        _warm("CLIP", _warm_clip)

    if (
        _env_flag("EXPLANATION_PROVIDER", "heuristic") == "qwen"
        or _env_flag("TEXT_HOOK_ANALYZER", "qwen") == "qwen"
    ):
        _warm("Qwen", _warm_qwen)

    _warm("Whisper", _warm_whisper)

    if (
        temporal_analysis_enabled()
        and _env_flag("TEMPORAL_ANALYZER_PROVIDER", "heuristic") == "videomae"
    ):
        _warm("VideoMAE", _warm_videomae)

    if scene_detection_enabled():
        logger.debug("Scene detection enabled (no persistent model to warm up)")

    logger.info("Model warm-up finished.")


def start_warmup_in_background() -> None:
    """Kick off model warm-up in a daemon thread (idempotent, non-blocking).

    Runs in the background so the server becomes ready immediately; the demo
    screen and health checks work while models load. If an upload arrives before
    warm-up finishes, the per-model locks ensure the model is loaded only once.
    """
    global _warmup_started
    if not warmup_enabled():
        logger.info("Model warm-up disabled via AUREA_WARMUP_MODELS")
        return
    with _warmup_lock:
        if _warmup_started:
            return
        _warmup_started = True
    threading.Thread(target=_run_warmup, name="model-warmup", daemon=True).start()
