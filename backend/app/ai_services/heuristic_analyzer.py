"""Heuristic analyzer with model-adapter factory integration."""

from __future__ import annotations

import logging
from pathlib import Path

from ..processing.audio_extractor import extract_audio_wav
from ..processing.clip_ranker import build_clip_context, rank_clips, structured_reasons_from_context
from ..processing.ffmpeg_probe import probe_video
from ..processing.scene_detector import detect_scene_cuts, pacing_score_from_cuts
from ..processing.timeline_builder import build_timeline
from ..schemas.analysis import (
    AnalysisResult,
    AnalysisSource,
    AnalysisStatus,
    HookEvidence,
    MetricSource,
    MetricSourceType,
    ProviderExecutionStatus,
    ProviderStatus,
    TextHook as TextHookSchema,
    Transcript,
    TranscriptSegment as TranscriptSegmentSchema,
    VideoMeta,
)
from .audio_analyzer import analyze_audio, librosa_available
from .emotion_analyzer import analyze_frames_deepface
from .explanation_generator import HeuristicExplanationGenerator, QwenExplanationGenerator
from .provider_factory import (
    _env_flag,
    get_emotion_analyzer,
    get_explanation_generator,
    get_memorability_scorer,
    get_retention_predictor,
    get_temporal_analyzer,
    get_virality_predictor,
    get_visual_analyzer,
    scene_detection_enabled,
    temporal_analysis_enabled,
)
from .speech_analyzer import transcribe_video, video_has_audio, whisper_available
from .temporal_analyzer import HeuristicTemporalAnalyzer
from .text_hook_analyzer import detect_hooks, generate_hook_insights
from .visual_analyzer import HeuristicVisualAnalyzer

logger = logging.getLogger(__name__)

SAMPLE_INTERVAL = 1.0  # seconds between sampled frames

_AI_PROVIDERS = {"yolo", "deepface", "videomae", "qwen", "clip", "whisper", "ml"}


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    lo, hi = min(values), max(values)
    spread = hi - lo
    if spread < 1e-9:
        return [0.5] * len(values)
    return [(v - lo) / spread for v in values]


def _at(values: list[float] | None, index: int, default: float) -> float:
    if values and index < len(values):
        return values[index]
    return default


def _safe_float(value: object, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _is_ai_provider(provider: str) -> bool:
    return provider.lower() in _AI_PROVIDERS


def _provider_status(
    *,
    name: str,
    provider: str,
    status: ProviderExecutionStatus,
    message: str | None = None,
) -> ProviderStatus:
    return ProviderStatus(
        name=name,
        provider=provider,
        status=status,
        is_ai=_is_ai_provider(provider),
        message=message,
    )


def _metric_source(
    *,
    metric: str,
    source_type: MetricSourceType,
    providers: list[str] | None = None,
    message: str | None = None,
) -> MetricSource:
    return MetricSource(
        metric=metric,
        source_type=source_type,
        providers=providers or [],
        message=message,
    )


def _status_from_requested(requested: str, actual: str) -> ProviderExecutionStatus:
    return ProviderExecutionStatus.used if requested == actual else ProviderExecutionStatus.fallback


def _build_retention_features(
    *,
    frame_diffs: list[float],
    audio_energy: list[float] | None,
    audio_silence: list[bool] | None,
    face_valence: list[float] | None,
    face_arousal: list[float] | None,
    detection_density: list[float] | None,
) -> list[dict]:
    motion_values = _normalize(frame_diffs)
    features: list[dict] = []
    for i, motion in enumerate(motion_values):
        features.append({
            "motion": motion,
            "face_arousal": _at(face_arousal, i, 0.0),
            "face_valence": _at(face_valence, i, 0.5),
            "detection_density": _at(detection_density, i, 0.0),
            "audio_energy": _at(audio_energy, i, 0.0),
            "is_silent": audio_silence[i] if audio_silence and i < len(audio_silence) else False,
        })
    return features


def _build_virality_features(
    *,
    timeline: list,
    frame_diffs: list[float],
    brightness: list[float],
    audio_energy: list[float] | None,
    audio_energy_change: list[float] | None,
    face_valence: list[float] | None,
    face_arousal: list[float] | None,
    detection_density: list[float] | None,
) -> list[dict]:
    motion_values = _normalize(frame_diffs)
    brightness_values = _normalize(brightness)
    features: list[dict] = []
    for i, entry in enumerate(timeline):
        features.append({
            "current_virality": _safe_float(getattr(entry, "virality", None), 0.5),
            "motion": _at(motion_values, i, 0.0),
            "brightness": _at(brightness_values, i, 0.5),
            "audio_energy": _at(audio_energy, i, 0.0),
            "audio_energy_change": _at(audio_energy_change, i, 0.0),
            "face_arousal": _at(face_arousal, i, 0.0),
            "face_valence": _at(face_valence, i, 0.5),
            "detection_density": _at(detection_density, i, 0.0),
            "retention": _safe_float(getattr(entry, "retention", None), 0.5),
        })
    return features


def _compute_hook_score(
    *,
    timeline: list,
    detections: list[dict] | None,
    face_arousal: list[float] | None,
    audio_energy: list[float] | None,
    hooks: list,
) -> tuple[float | None, HookEvidence | None]:
    if not timeline:
        return None, None

    early_entries = [e for e in timeline if e.time_seconds <= 5.0]
    if not early_entries:
        return None, None

    avg_virality = sum(e.virality or 0.0 for e in early_entries) / len(early_entries)
    score = avg_virality * 0.2

    early_detections = [
        det for det in (detections or [])
        if _safe_float(det.get("time_seconds"), 999.0) <= 5.0
    ]
    person_detected = any(str(det.get("class_name", "")).lower() == "person" for det in early_detections)
    if person_detected:
        score += 0.3

    early_face_arousal = (face_arousal or [])[:5]
    face_arousal_avg = (sum(early_face_arousal) / len(early_face_arousal)) if early_face_arousal else None
    if face_arousal_avg is not None and face_arousal_avg > 0.6:
        score += 0.2

    text_hook_first_5s = next((hook for hook in hooks if getattr(hook, "timestamp", 999.0) <= 5.0), None)
    if text_hook_first_5s is not None:
        score += 0.3

    early_audio = (audio_energy or [])[:5]
    audio_energy_first_5s = (sum(early_audio) / len(early_audio)) if early_audio else None
    if audio_energy_first_5s is not None and audio_energy_first_5s > 0.45:
        score += 0.1

    evidence = HookEvidence(
        person_detected_first_5s=person_detected,
        face_arousal_avg_first_5s=round(face_arousal_avg, 3) if face_arousal_avg is not None else None,
        text_hook_first_5s=(
            TextHookSchema(
                text=text_hook_first_5s.text,
                hook_type=text_hook_first_5s.hook_type,
                timestamp=text_hook_first_5s.timestamp,
                confidence=text_hook_first_5s.confidence,
            )
            if text_hook_first_5s is not None
            else None
        ),
        audio_energy_first_5s=round(audio_energy_first_5s, 3) if audio_energy_first_5s is not None else None,
    )
    return round(min(1.0, score), 3), evidence


def _compute_attention_duration_seconds(
    *,
    timeline: list,
    detections: list[dict] | None,
    face_arousal: list[float] | None,
    audio_energy: list[float] | None,
    audio_silence: list[bool] | None,
    hooks: list,
    memorability_scores: list[float],
    sample_interval: float,
) -> float | None:
    """Longest continuous attention interval from real content signals."""
    if not timeline:
        return None

    person_samples = {
        int(det.get("sample_index"))
        for det in detections or []
        if str(det.get("class_name", "")).lower() == "person" and det.get("sample_index") is not None
    }
    hook_times = [_safe_float(getattr(hook, "timestamp", None), -999.0) for hook in hooks]
    has_any_signal_source = bool(person_samples or face_arousal or audio_energy or hooks or memorability_scores)
    if not has_any_signal_source:
        return None

    best_run = 0
    current_run = 0
    for i, entry in enumerate(timeline):
        retention = _safe_float(getattr(entry, "retention", None), 0.0)
        time_seconds = _safe_float(getattr(entry, "time_seconds", None), i * sample_interval)
        signal_count = 0

        if i in person_samples:
            signal_count += 1
        if face_arousal is not None and i < len(face_arousal):
            signal_count += 1
        if audio_energy is not None and i < len(audio_energy):
            is_silent = audio_silence[i] if audio_silence and i < len(audio_silence) else False
            if not is_silent and audio_energy[i] > 0.03:
                signal_count += 1
        if any(time_seconds <= hook_time < time_seconds + sample_interval for hook_time in hook_times):
            signal_count += 1
        if i < len(memorability_scores) and memorability_scores[i] >= 0.62:
            signal_count += 1

        if retention >= 0.65 and signal_count >= 2:
            current_run += 1
            best_run = max(best_run, current_run)
        else:
            current_run = 0

    if best_run == 0:
        return None
    return round(best_run * sample_interval, 2)


def analyze_video(
    analysis_id: str,
    video_path: str,
    output_dir: str,
) -> AnalysisResult:
    """Run analysis while preserving the existing response contract."""
    video_file = Path(video_path)
    filename = video_file.name
    provider_status: list[ProviderStatus] = []
    metric_sources: list[MetricSource] = []

    # Step 1: Probe metadata (FFmpeg optional)
    probe = probe_video(video_path)
    if probe:
        duration = probe.duration_seconds
        fps = probe.fps
        width = probe.width
        height = probe.height
    else:
        # Fallback: use OpenCV for basic metadata
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error("Cannot open video: %s", video_path)
            return AnalysisResult(
                id=analysis_id,
                status=AnalysisStatus.failed,
                analysis_source=AnalysisSource.failed,
                provider_status=provider_status,
                metric_sources=metric_sources,
                video=VideoMeta(filename=filename),
            )
        fps = int(cap.get(cv2.CAP_PROP_FPS) or 30)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frame_count / fps if fps > 0 else 0.0
        cap.release()

    video_meta = VideoMeta(
        filename=filename,
        duration_seconds=round(duration, 3),
        fps=fps,
        width=width,
        height=height,
    )

    # Step 2: Extract visual signals (provider + fallback)
    requested_visual_provider = _env_flag("VISUAL_ANALYZER_PROVIDER", "heuristic")
    visual_adapter = get_visual_analyzer()
    try:
        visual = visual_adapter.analyze(
            video_path=video_path,
            output_dir=output_dir,
            interval_seconds=SAMPLE_INTERVAL,
        )
    except Exception:
        logger.exception(
            "Visual provider '%s' failed. Falling back to heuristic.",
            getattr(visual_adapter, "provider_name", "unknown"),
        )
        visual = HeuristicVisualAnalyzer().analyze(
            video_path=video_path,
            output_dir=output_dir,
            interval_seconds=SAMPLE_INTERVAL,
        )
        provider_status.append(_provider_status(
            name="visual",
            provider="heuristic",
            status=ProviderExecutionStatus.fallback,
            message=f"{getattr(visual_adapter, 'provider_name', 'unknown')} failed during visual analysis",
        ))
    else:
        provider_status.append(_provider_status(
            name="visual",
            provider=visual.provider,
            status=_status_from_requested(requested_visual_provider, visual.provider),
        ))

    if not visual.frame_diffs:
        logger.warning("No frame data extracted - returning failed result")
        return AnalysisResult(
            id=analysis_id,
            status=AnalysisStatus.failed,
            analysis_source=AnalysisSource.failed,
            provider_status=provider_status,
            metric_sources=metric_sources,
            video=video_meta,
        )

    # Step 2b: Optional audio feature extraction
    audio_energy = None
    audio_silence = None
    audio_energy_change = None
    if librosa_available():
        logger.info("librosa available - extracting audio features for %s", analysis_id)
        wav_path = extract_audio_wav(video_path, output_dir)
        if wav_path:
            audio_features = analyze_audio(wav_path, interval_seconds=SAMPLE_INTERVAL)
            if audio_features:
                audio_energy = audio_features.rms_energy
                audio_silence = audio_features.silence_mask
                audio_energy_change = audio_features.energy_change
                logger.info("Audio features extracted: %d frames", len(audio_energy))
                provider_status.append(_provider_status(
                    name="audio",
                    provider="librosa",
                    status=ProviderExecutionStatus.used,
                ))
        if audio_energy is None:
            provider_status.append(_provider_status(
                name="audio",
                provider="librosa",
                status=ProviderExecutionStatus.failed,
                message="Audio extraction or analysis returned no features",
            ))
    else:
        logger.debug("librosa not available - skipping audio analysis")
        provider_status.append(_provider_status(
            name="audio",
            provider="librosa",
            status=ProviderExecutionStatus.disabled,
        ))

    # Step 2c: Aggregate YOLO detections into per-second density for timeline
    detection_density: list[float] | None = None
    if visual.detections:
        import cv2 as _cv2

        _cap = _cv2.VideoCapture(video_path)
        _fps = _cap.get(_cv2.CAP_PROP_FPS) or 30.0
        _cap.release()
        frame_step = max(1, int(_fps * SAMPLE_INTERVAL))

        n_frames = len(visual.frame_diffs)
        counts = [0] * n_frames
        for det in visual.detections:
            idx = int(det["frame_index"]) // frame_step
            if 0 <= idx < n_frames:
                counts[idx] += 1
                det["sample_index"] = idx
                det["time_seconds"] = round(idx * SAMPLE_INTERVAL, 2)
        max_count = max(counts) if counts else 1
        detection_density = [c / max(max_count, 1) for c in counts]
        logger.info("YOLO detection density: max=%d detections/frame", max_count)

    # Step 2d: DeepFace per-frame emotion for timeline enrichment
    face_valence: list[float] | None = None
    face_arousal: list[float] | None = None
    requested_emotion_provider = _env_flag("EMOTION_ANALYZER_PROVIDER", "deepface")
    if requested_emotion_provider == "deepface":
        logger.info("Running DeepFace per-frame analysis for timeline enrichment")
        try:
            face_signals = analyze_frames_deepface(video_path, interval_seconds=SAMPLE_INTERVAL)
            if face_signals:
                face_valence = face_signals.valence
                face_arousal = face_signals.arousal
                logger.info("DeepFace per-frame: %d valence/arousal pairs", len(face_valence))
                provider_status.append(_provider_status(
                    name="emotion_per_frame",
                    provider="deepface",
                    status=ProviderExecutionStatus.used,
                ))
            else:
                provider_status.append(_provider_status(
                    name="emotion_per_frame",
                    provider="heuristic",
                    status=ProviderExecutionStatus.fallback,
                    message="DeepFace per-frame returned no signals",
                ))
        except Exception:
            logger.warning("DeepFace per-frame analysis failed — using heuristic", exc_info=True)
            provider_status.append(_provider_status(
                name="emotion_per_frame",
                provider="heuristic",
                status=ProviderExecutionStatus.fallback,
                message="DeepFace per-frame failed",
            ))
    else:
        provider_status.append(_provider_status(
            name="emotion_per_frame",
            provider="heuristic",
            status=ProviderExecutionStatus.used,
        ))

    # Step 2e: Predict retention from all available AI/audio/visual signals.
    retention_override: list[float] | None = None
    retention_provider_name = "heuristic"
    requested_retention_provider = _env_flag("RETENTION_PREDICTOR_PROVIDER", "heuristic")
    try:
        retention_features = _build_retention_features(
            frame_diffs=visual.frame_diffs,
            audio_energy=audio_energy,
            audio_silence=audio_silence,
            face_valence=face_valence,
            face_arousal=face_arousal,
            detection_density=detection_density,
        )
        retention_predictor = get_retention_predictor()
        retention_provider_name = getattr(retention_predictor, "provider_name", "heuristic")
        retention_override = retention_predictor.predict(retention_features)
        if len(retention_override) != len(retention_features):
            raise ValueError(
                f"Retention predictor returned {len(retention_override)} values for {len(retention_features)} feature rows"
            )
        provider_status.append(_provider_status(
            name="retention",
            provider=retention_provider_name,
            status=_status_from_requested(requested_retention_provider, retention_provider_name),
        ))
    except Exception:
        logger.warning("Retention predictor failed — using timeline fallback", exc_info=True)
        retention_provider_name = "timeline_fallback"
        provider_status.append(_provider_status(
            name="retention",
            provider="timeline_fallback",
            status=ProviderExecutionStatus.fallback,
            message="Retention predictor failed; timeline fallback used",
        ))

    # Step 3: Build timeline (with optional audio + AI fusion)
    timeline = build_timeline(
        duration,
        visual.frame_diffs,
        visual.brightness,
        SAMPLE_INTERVAL,
        audio_energy=audio_energy,
        audio_silence=audio_silence,
        audio_energy_change=audio_energy_change,
        face_valence=face_valence,
        face_arousal=face_arousal,
        detection_density=detection_density,
        retention_override=retention_override,
        detections=visual.detections,
    )

    # Step 3b: Optional trained virality predictor. Without a configured ML model,
    # keep the timeline_builder composite formula and mark it as derived.
    virality_provider_name = "derived_formula"
    requested_virality_provider = _env_flag("VIRALITY_PREDICTOR_PROVIDER", "derived_formula")
    try:
        virality_predictor = get_virality_predictor()
        virality_provider_name = getattr(virality_predictor, "provider_name", "derived_formula")
        virality_predictions = virality_predictor.predict_timeline(
            _build_virality_features(
                timeline=timeline,
                frame_diffs=visual.frame_diffs,
                brightness=visual.brightness,
                audio_energy=audio_energy,
                audio_energy_change=audio_energy_change,
                face_valence=face_valence,
                face_arousal=face_arousal,
                detection_density=detection_density,
            )
        )
        if virality_predictions is not None:
            if len(virality_predictions) != len(timeline):
                raise ValueError(
                    f"Virality predictor returned {len(virality_predictions)} values for {len(timeline)} timeline rows"
                )
            for entry, predicted_score in zip(timeline, virality_predictions):
                entry.virality = predicted_score
        provider_status.append(_provider_status(
            name="virality",
            provider=virality_provider_name,
            status=(
                ProviderExecutionStatus.used
                if requested_virality_provider in {virality_provider_name, "derived", "heuristic"}
                and virality_provider_name == "derived_formula"
                else _status_from_requested(requested_virality_provider, virality_provider_name)
            ),
        ))
    except Exception:
        logger.warning("Virality predictor failed — keeping derived composite formula", exc_info=True)
        virality_provider_name = "derived_formula"
        provider_status.append(_provider_status(
            name="virality",
            provider="derived_formula",
            status=ProviderExecutionStatus.fallback,
            message="Virality predictor failed; derived composite formula used",
        ))

    # Step 4: Rank clips with YOLO reasons and optional semantic memorability.
    memorability_scores: list[float] = []
    memorability_provider_name = "none"
    requested_memorability_provider = _env_flag("MEMORABILITY_SCORER", "clip")
    try:
        memorability_scorer = get_memorability_scorer()
        memorability_provider_name = getattr(memorability_scorer, "provider_name", "heuristic")
        memorability_scores = memorability_scorer.score_timeline(
            video_path=video_path,
            timeline=timeline,
        )
        provider_status.append(_provider_status(
            name="memorability",
            provider=memorability_provider_name,
            status=_status_from_requested(requested_memorability_provider, memorability_provider_name),
        ))
    except Exception:
        logger.warning("Memorability scorer failed — rewatch_factor unavailable", exc_info=True)
        provider_status.append(_provider_status(
            name="memorability",
            provider="clip",
            status=ProviderExecutionStatus.fallback,
            message="CLIP memorability scoring failed; rewatch_factor unavailable",
        ))

    semantic_scores = (
        memorability_scores
        if memorability_provider_name == "clip"
        and _env_flag("CLIP_RANKER_ENABLED", "true") in {"1", "true", "yes"}
        else None
    )
    top_clips = rank_clips(
        timeline,
        max_clips=3,
        detections=visual.detections,
        semantic_scores=semantic_scores,
        audio_energy=audio_energy,
        audio_energy_change=audio_energy_change,
        require_semantic_scores=True,
    )
    clip_reason_provider_name = "none"
    if top_clips:
        requested_clip_reason_provider = _env_flag(
            "CLIP_REASON_PROVIDER",
            _env_flag("EXPLANATION_PROVIDER", "structured"),
        )
        if requested_clip_reason_provider == "qwen":
            try:
                clip_reason_generator = QwenExplanationGenerator()
                for clip in top_clips:
                    clip.reasons = clip_reason_generator.generate_clip_reasons(build_clip_context(
                        clip=clip,
                        timeline=timeline,
                        detections=visual.detections,
                        semantic_scores=semantic_scores,
                        audio_energy=audio_energy,
                        audio_energy_change=audio_energy_change,
                    ))
                clip_reason_provider_name = "qwen"
                provider_status.append(_provider_status(
                    name="clip_reasons",
                    provider="qwen",
                    status=ProviderExecutionStatus.used,
                ))
            except Exception:
                clip_reason_provider_name = "structured"
                provider_status.append(_provider_status(
                    name="clip_reasons",
                    provider="structured",
                    status=ProviderExecutionStatus.fallback,
                    message="Qwen clip reasons failed; structured evidence reasons used",
                ))
        else:
            clip_reason_provider_name = "structured"
            provider_status.append(_provider_status(
                name="clip_reasons",
                provider="structured",
                status=ProviderExecutionStatus.used,
            ))
    else:
        provider_status.append(_provider_status(
            name="clip_reasons",
            provider="qwen",
            status=ProviderExecutionStatus.disabled,
            message="No CLIP-ranked clip candidates available",
        ))

    # Step 5: Compute aggregate scores
    virality_values = [e.virality or 0.0 for e in timeline]
    retention_values = [e.retention or 0.0 for e in timeline]

    overall_virality = sum(virality_values) / len(virality_values) if virality_values else 0.0
    retention_score = sum(retention_values) / len(retention_values) if retention_values else 0.0

    # Rewatch factor must be CLIP-derived for uploaded videos. If CLIP is not
    # available or fails, leave it unavailable instead of inventing a heuristic x.
    if memorability_provider_name == "clip" and memorability_scores:
        rewatchable_count = sum(1 for score in memorability_scores if score > 0.62)
        rewatch_factor = round(rewatchable_count / max(len(memorability_scores), 1), 2)
    else:
        rewatch_factor = None

    pacing_score: float | None = None
    if scene_detection_enabled():
        scene_cuts = detect_scene_cuts(video_path)
        if scene_cuts is not None:
            pacing_score = pacing_score_from_cuts(scene_cuts, duration)
            provider_status.append(_provider_status(
                name="pacing",
                provider="scenedetect",
                status=ProviderExecutionStatus.used,
            ))
        else:
            provider_status.append(_provider_status(
                name="pacing",
                provider="scenedetect",
                status=ProviderExecutionStatus.failed,
                message="Scene detection failed or dependency unavailable",
            ))
    else:
        provider_status.append(_provider_status(
            name="pacing",
            provider="scenedetect",
            status=ProviderExecutionStatus.disabled,
        ))

    # Step 6: Dominant emotion and intensity from DeepFace only for uploads.
    emotion_intensity = round(sum(face_arousal) / len(face_arousal), 3) if face_arousal else None
    emotion_adapter = get_emotion_analyzer(video_path=video_path)
    dominant_emotion_provider = getattr(emotion_adapter, "provider_name", "unknown")
    dominant_emotion: str | None = None
    if dominant_emotion_provider == "deepface":
        try:
            dominant_emotion = emotion_adapter.dominant_emotion(timeline=timeline)
            provider_status.append(_provider_status(
                name="dominant_emotion",
                provider=dominant_emotion_provider,
                status=_status_from_requested(requested_emotion_provider, dominant_emotion_provider),
            ))
        except Exception:
            logger.exception("DeepFace dominant-emotion provider failed")
            dominant_emotion_provider = "none"
            provider_status.append(_provider_status(
                name="dominant_emotion",
                provider="deepface",
                status=ProviderExecutionStatus.failed,
                message="DeepFace dominant-emotion provider failed",
            ))
    else:
        dominant_emotion_provider = "none"
        provider_status.append(_provider_status(
            name="dominant_emotion",
            provider="deepface",
            status=ProviderExecutionStatus.failed,
            message="DeepFace unavailable; dominant emotion not inferred from heuristic fallback",
        ))

    # Step 6b: Optional temporal action score (disabled by default)
    action_recognition_score: float | None = None
    if temporal_analysis_enabled():
        requested_temporal_provider = _env_flag("TEMPORAL_ANALYZER_PROVIDER", "heuristic")
        temporal_adapter = get_temporal_analyzer(video_path=video_path)
        try:
            temporal_analysis = temporal_adapter.analyze(timeline=timeline)
        except Exception:
            logger.exception(
                "Temporal provider '%s' failed. Falling back to heuristic.",
                getattr(temporal_adapter, "provider_name", "unknown"),
            )
            temporal_analysis = HeuristicTemporalAnalyzer().analyze(timeline=timeline)
        action_recognition_score = temporal_analysis.action_score
        provider_status.append(_provider_status(
            name="temporal",
            provider=temporal_analysis.provider,
            status=_status_from_requested(requested_temporal_provider, temporal_analysis.provider),
        ))
    else:
        provider_status.append(_provider_status(
            name="temporal",
            provider="videomae",
            status=ProviderExecutionStatus.disabled,
        ))

    # Step 6c: Explanation generation (provider + fallback)
    requested_explanation_provider = _env_flag("EXPLANATION_PROVIDER", "heuristic")
    explanation_generator = get_explanation_generator()
    explanation_provider = getattr(explanation_generator, "provider_name", "heuristic")
    try:
        insights = explanation_generator.generate(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion or "Unavailable",
        )
        provider_status.append(_provider_status(
            name="explanation",
            provider=explanation_provider,
            status=_status_from_requested(requested_explanation_provider, explanation_provider),
        ))
    except Exception:
        logger.exception(
            "Explanation provider '%s' failed. Falling back to heuristic.",
            getattr(explanation_generator, "provider_name", "unknown"),
        )
        insights = HeuristicExplanationGenerator().generate(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion or "Unavailable",
        )
        explanation_provider = "heuristic"
        provider_status.append(_provider_status(
            name="explanation",
            provider="heuristic",
            status=ProviderExecutionStatus.fallback,
            message="Explanation provider failed",
        ))

    # Step 7: Optional speech transcription + text hook detection
    transcript_data: Transcript | None = None
    hooks = []
    transcript_metric_message: str | None = None
    text_hooks_provider = _env_flag("TEXT_HOOK_ANALYZER", "qwen")
    text_hooks_source_type = MetricSourceType.unavailable
    if not video_has_audio(str(video_file)):
        transcript_metric_message = "Video has no audio"
        provider_status.append(_provider_status(
            name="transcript",
            provider="whisper",
            status=ProviderExecutionStatus.disabled,
            message=transcript_metric_message,
        ))
        provider_status.append(_provider_status(
            name="text_hooks",
            provider=text_hooks_provider,
            status=ProviderExecutionStatus.disabled,
            message="Video has no audio for hook classification",
        ))
    elif whisper_available():
        logger.info("Whisper available - transcribing audio for %s", analysis_id)
        tr = transcribe_video(str(video_file), output_dir)
        if tr and tr.segments:
            provider_status.append(_provider_status(
                name="transcript",
                provider="whisper",
                status=ProviderExecutionStatus.used,
            ))
            try:
                hooks = detect_hooks(tr.segments)
                text_hooks_source_type = (
                    MetricSourceType.ai if text_hooks_provider == "qwen" else MetricSourceType.heuristic
                )
                provider_status.append(_provider_status(
                    name="text_hooks",
                    provider=text_hooks_provider,
                    status=ProviderExecutionStatus.used,
                ))
                hook_insights = generate_hook_insights(hooks, duration)
                insights.extend(hook_insights)
            except Exception:
                logger.warning("Text hook classification failed — hooks unavailable", exc_info=True)
                hooks = []
                text_hooks_source_type = MetricSourceType.unavailable
                provider_status.append(_provider_status(
                    name="text_hooks",
                    provider=text_hooks_provider,
                    status=ProviderExecutionStatus.failed,
                    message="Text hook classifier failed; no regex fallback used unless explicitly configured",
                ))

            transcript_data = Transcript(
                segments=[
                    TranscriptSegmentSchema(start=s.start, end=s.end, text=s.text)
                    for s in tr.segments
                ],
                full_text=tr.full_text,
                hooks=[
                    TextHookSchema(
                        text=h.text,
                        hook_type=h.hook_type,
                        timestamp=h.timestamp,
                        confidence=h.confidence,
                    )
                    for h in hooks
                ],
            )
            logger.info(
                "Transcription complete: %d segments, %d hooks",
                len(tr.segments),
                len(hooks),
            )
        else:
            transcript_metric_message = "Whisper returned no transcript segments"
            provider_status.append(_provider_status(
                name="transcript",
                provider="whisper",
                status=ProviderExecutionStatus.failed,
                message=transcript_metric_message,
            ))
            provider_status.append(_provider_status(
                name="text_hooks",
                provider=text_hooks_provider,
                status=ProviderExecutionStatus.disabled,
                message="No transcript available for hook classification",
            ))
    else:
        logger.debug("Whisper not available - skipping transcription")
        transcript_metric_message = "Whisper is disabled or faster-whisper is not installed"
        provider_status.append(_provider_status(
            name="transcript",
            provider="whisper",
            status=ProviderExecutionStatus.disabled,
            message=transcript_metric_message,
        ))
        provider_status.append(_provider_status(
            name="text_hooks",
            provider=text_hooks_provider,
            status=ProviderExecutionStatus.disabled,
            message="No transcript available for hook classification",
        ))

    if top_clips and clip_reason_provider_name == "structured" and transcript_data is not None:
        for clip in top_clips:
            clip.reasons = structured_reasons_from_context(build_clip_context(
                clip=clip,
                timeline=timeline,
                detections=visual.detections,
                semantic_scores=semantic_scores,
                audio_energy=audio_energy,
                audio_energy_change=audio_energy_change,
                hooks=transcript_data.hooks,
                transcript_segments=transcript_data.segments,
            ))

    attention_duration_seconds = _compute_attention_duration_seconds(
        timeline=timeline,
        detections=visual.detections,
        face_arousal=face_arousal,
        audio_energy=audio_energy,
        audio_silence=audio_silence,
        hooks=hooks,
        memorability_scores=memorability_scores,
        sample_interval=SAMPLE_INTERVAL,
    )

    hook_score, hook_evidence = _compute_hook_score(
        timeline=timeline,
        detections=visual.detections,
        face_arousal=face_arousal,
        audio_energy=audio_energy,
        hooks=hooks,
    )

    visual_providers = [visual.provider]
    if audio_energy is not None:
        visual_providers.append("librosa")
    if face_valence is not None or face_arousal is not None:
        visual_providers.append("deepface")

    virality_source_type = MetricSourceType.ai if virality_provider_name == "ml" else MetricSourceType.derived
    virality_source_message = (
        "Predicted by configured ML virality model"
        if virality_provider_name == "ml"
        else "Composite score derived from visual/audio/emotion signals; not a trained AI virality prediction"
    )

    metric_sources.extend([
        _metric_source(
            metric="overall_virality_score",
            source_type=virality_source_type,
            providers=[virality_provider_name] if virality_provider_name == "ml" else visual_providers + [virality_provider_name],
            message=virality_source_message,
        ),
        _metric_source(
            metric="timeline.virality",
            source_type=virality_source_type,
            providers=[virality_provider_name] if virality_provider_name == "ml" else visual_providers + [virality_provider_name],
            message=virality_source_message,
        ),
        _metric_source(
            metric="timeline.valence_arousal",
            source_type=MetricSourceType.ai if face_valence is not None or face_arousal is not None else MetricSourceType.derived,
            providers=["deepface"] if face_valence is not None or face_arousal is not None else visual_providers,
        ),
        _metric_source(
            metric="retention_score",
            source_type=MetricSourceType.ai if retention_provider_name == "ml" else MetricSourceType.derived,
            providers=[retention_provider_name],
        ),
        _metric_source(
            metric="timeline.retention",
            source_type=MetricSourceType.ai if retention_provider_name == "ml" else MetricSourceType.derived,
            providers=[retention_provider_name],
        ),
        _metric_source(
            metric="rewatch_factor",
            source_type=MetricSourceType.ai if memorability_provider_name == "clip" and memorability_scores else MetricSourceType.unavailable,
            providers=[memorability_provider_name] if memorability_provider_name == "clip" and memorability_scores else [],
            message=(
                "Estimated from CLIP memorability scores"
                if memorability_provider_name == "clip" and memorability_scores
                else "Unavailable: CLIP memorability analysis did not produce real scores"
            ),
        ),
        _metric_source(
            metric="top_clips",
            source_type=(
                MetricSourceType.ai
                if top_clips and clip_reason_provider_name == "qwen"
                else MetricSourceType.derived if top_clips else MetricSourceType.unavailable
            ),
            providers=(
                ["clip", "clip_ranker", "qwen"]
                if top_clips and clip_reason_provider_name == "qwen"
                else ["clip", "clip_ranker", "structured"] if top_clips else []
            ),
            message=(
                "CLIP-ranked clips with Qwen evidence-grounded reasons"
                if top_clips and clip_reason_provider_name == "qwen"
                else "CLIP-ranked clips with structured evidence reasons" if top_clips
                else "Unavailable: CLIP semantic scores did not produce clip candidates"
            ),
        ),
        _metric_source(
            metric="dominant_emotion",
            source_type=MetricSourceType.ai if dominant_emotion is not None and dominant_emotion_provider == "deepface" else MetricSourceType.unavailable,
            providers=[dominant_emotion_provider] if dominant_emotion is not None and dominant_emotion_provider == "deepface" else [],
            message=(
                "Dominant emotion inferred by DeepFace"
                if dominant_emotion is not None and dominant_emotion_provider == "deepface"
                else "Unavailable: DeepFace did not produce dominant emotion"
            ),
        ),
        _metric_source(
            metric="emotion_intensity",
            source_type=MetricSourceType.ai if emotion_intensity is not None else MetricSourceType.unavailable,
            providers=["deepface"] if emotion_intensity is not None else [],
            message=(
                "Average arousal derived from DeepFace per-frame emotion probabilities"
                if emotion_intensity is not None
                else "Unavailable: DeepFace per-frame emotion signals were not available"
            ),
        ),
        _metric_source(
            metric="attention_duration_seconds",
            source_type=MetricSourceType.derived if attention_duration_seconds is not None else MetricSourceType.unavailable,
            providers=[provider for provider in [visual.provider, "deepface" if face_arousal else None, "librosa" if audio_energy else None, "qwen" if hooks and text_hooks_provider == "qwen" else None, "clip" if memorability_scores else None] if provider],
            message=(
                "Longest continuous interval with high retention and multiple real attention signals"
                if attention_duration_seconds is not None
                else "Unavailable: insufficient real attention evidence across retention/person-face/audio-hook/CLIP signals"
            ),
        ),
        _metric_source(
            metric="action_recognition_score",
            source_type=(MetricSourceType.ai if action_recognition_score is not None else MetricSourceType.unavailable),
            providers=["videomae"] if action_recognition_score is not None else [],
        ),
        _metric_source(
            metric="hook_score",
            source_type=MetricSourceType.derived if hook_score is not None else MetricSourceType.unavailable,
            providers=[visual.provider, "deepface", text_hooks_provider],
            message="Derived from first-5s person/face/audio/text-hook evidence; not a calibrated AI model",
        ),
        _metric_source(
            metric="pacing_score",
            source_type=MetricSourceType.derived if pacing_score is not None else MetricSourceType.unavailable,
            providers=["scenedetect"] if pacing_score is not None else [],
            message=(
                "Derived from PySceneDetect scene-cut frequency"
                if pacing_score is not None
                else "Unavailable: PySceneDetect did not produce scene cuts or is disabled"
            ),
        ),
        _metric_source(
            metric="transcript",
            source_type=MetricSourceType.ai if transcript_data is not None else MetricSourceType.unavailable,
            providers=["whisper"] if transcript_data is not None else [],
            message=transcript_metric_message,
        ),
        _metric_source(
            metric="transcript.hooks",
            source_type=text_hooks_source_type,
            providers=[text_hooks_provider] if transcript_data is not None and text_hooks_source_type != MetricSourceType.unavailable else [],
            message=(
                "Hooks classified by Qwen"
                if text_hooks_source_type == MetricSourceType.ai
                else "Hooks detected by explicit regex fallback" if text_hooks_source_type == MetricSourceType.heuristic
                else "Unavailable: Qwen hook classification failed or transcript was unavailable"
            ),
        ),
        _metric_source(
            metric="insights",
            source_type=MetricSourceType.ai if explanation_provider == "qwen" else MetricSourceType.heuristic,
            providers=[explanation_provider],
        ),
    ])

    analysis_source = (
        AnalysisSource.uploaded_partial
        if any(s.status in {ProviderExecutionStatus.fallback, ProviderExecutionStatus.failed} for s in provider_status)
        else AnalysisSource.uploaded_real
    )

    return AnalysisResult(
        id=analysis_id,
        status=AnalysisStatus.completed,
        analysis_source=analysis_source,
        provider_status=provider_status,
        metric_sources=metric_sources,
        progress=1.0,
        video=video_meta,
        overall_virality_score=round(overall_virality, 3),
        retention_score=round(retention_score, 3),
        rewatch_factor=rewatch_factor,
        action_recognition_score=action_recognition_score,
        hook_score=hook_score,
        hook_evidence=hook_evidence,
        pacing_score=pacing_score,
        dominant_emotion=dominant_emotion,
        emotion_intensity=emotion_intensity,
        attention_duration_seconds=attention_duration_seconds,
        timeline=timeline,
        top_clips=top_clips,
        insights=insights,
        transcript=transcript_data,
    )
