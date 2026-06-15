"""Heuristic analyzer with model-adapter factory integration."""

from __future__ import annotations

import logging
from pathlib import Path

from ..processing.audio_extractor import extract_audio_wav
from ..processing.clip_ranker import rank_clips
from ..processing.ffmpeg_probe import probe_video
from ..processing.timeline_builder import build_timeline
from ..schemas.analysis import (
    AnalysisResult,
    AnalysisStatus,
    TextHook as TextHookSchema,
    Transcript,
    TranscriptSegment as TranscriptSegmentSchema,
    VideoMeta,
)
from .audio_analyzer import analyze_audio, librosa_available
from .emotion_analyzer import HeuristicEmotionAnalyzer, analyze_frames_deepface
from .explanation_generator import HeuristicExplanationGenerator
from .provider_factory import (
    get_emotion_analyzer,
    get_explanation_generator,
    get_temporal_analyzer,
    get_visual_analyzer,
    temporal_analysis_enabled,
)
from .speech_analyzer import transcribe_video, whisper_available
from .temporal_analyzer import HeuristicTemporalAnalyzer
from .text_hook_analyzer import detect_hooks, generate_hook_insights
from .visual_analyzer import HeuristicVisualAnalyzer

logger = logging.getLogger(__name__)

SAMPLE_INTERVAL = 1.0  # seconds between sampled frames


def analyze_video(
    analysis_id: str,
    video_path: str,
    output_dir: str,
) -> AnalysisResult:
    """Run analysis while preserving the existing response contract."""
    video_file = Path(video_path)
    filename = video_file.name

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

    if not visual.frame_diffs:
        logger.warning("No frame data extracted - returning failed result")
        return AnalysisResult(
            id=analysis_id,
            status=AnalysisStatus.failed,
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
    else:
        logger.debug("librosa not available - skipping audio analysis")

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
        max_count = max(counts) if counts else 1
        detection_density = [c / max(max_count, 1) for c in counts]
        logger.info("YOLO detection density: max=%d detections/frame", max_count)

    # Step 2d: DeepFace per-frame emotion for timeline enrichment
    face_valence: list[float] | None = None
    face_arousal: list[float] | None = None
    from .provider_factory import _env_flag
    if _env_flag("EMOTION_ANALYZER_PROVIDER", "heuristic") == "deepface":
        logger.info("Running DeepFace per-frame analysis for timeline enrichment")
        try:
            face_signals = analyze_frames_deepface(video_path, interval_seconds=SAMPLE_INTERVAL)
            if face_signals:
                face_valence = face_signals.valence
                face_arousal = face_signals.arousal
                logger.info("DeepFace per-frame: %d valence/arousal pairs", len(face_valence))
        except Exception:
            logger.warning("DeepFace per-frame analysis failed — using heuristic", exc_info=True)

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
    )

    # Step 4: Rank clips
    top_clips = rank_clips(timeline, max_clips=3)

    # Step 5: Compute aggregate scores
    virality_values = [e.virality or 0.0 for e in timeline]
    retention_values = [e.retention or 0.0 for e in timeline]

    overall_virality = sum(virality_values) / len(virality_values) if virality_values else 0.0
    retention_score = sum(retention_values) / len(retention_values) if retention_values else 0.0

    # Rewatch factor: ratio of peak virality to average (higher = more rewatchable moments)
    peak_v = max(virality_values) if virality_values else 0.0
    rewatch_factor = round(peak_v / max(overall_virality, 0.01), 1)

    # Step 6: Dominant emotion (provider + fallback)
    emotion_adapter = get_emotion_analyzer(video_path=video_path)
    try:
        dominant_emotion = emotion_adapter.dominant_emotion(timeline=timeline)
    except Exception:
        logger.exception(
            "Emotion provider '%s' failed. Falling back to heuristic.",
            getattr(emotion_adapter, "provider_name", "unknown"),
        )
        dominant_emotion = HeuristicEmotionAnalyzer().dominant_emotion(timeline=timeline)

    # Step 6b: Optional temporal action score (disabled by default)
    action_recognition_score: float | None = None
    if temporal_analysis_enabled():
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

    # Step 6c: Explanation generation (provider + fallback)
    explanation_generator = get_explanation_generator()
    try:
        insights = explanation_generator.generate(
            timeline=timeline,
            top_clips=top_clips,
            duration=duration,
            overall_virality=overall_virality,
            retention_score=retention_score,
            dominant_emotion=dominant_emotion,
        )
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
            dominant_emotion=dominant_emotion,
        )

    # Step 7: Optional speech transcription + text hook detection
    transcript_data: Transcript | None = None
    if whisper_available():
        logger.info("Whisper available - transcribing audio for %s", analysis_id)
        tr = transcribe_video(str(video_file), output_dir)
        if tr and tr.segments:
            hooks = detect_hooks(tr.segments)
            hook_insights = generate_hook_insights(hooks, duration)
            insights.extend(hook_insights)

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
        logger.debug("Whisper not available - skipping transcription")

    return AnalysisResult(
        id=analysis_id,
        status=AnalysisStatus.completed,
        progress=1.0,
        video=video_meta,
        overall_virality_score=round(overall_virality, 3),
        retention_score=round(retention_score, 3),
        rewatch_factor=rewatch_factor,
        action_recognition_score=action_recognition_score,
        dominant_emotion=dominant_emotion,
        timeline=timeline,
        top_clips=top_clips,
        insights=insights,
        transcript=transcript_data,
    )
