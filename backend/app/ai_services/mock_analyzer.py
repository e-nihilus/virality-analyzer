"""Mock analyzer that returns synthetic analysis data for UI development."""

from __future__ import annotations

import math
import uuid

from ..schemas.analysis import (
    AnalysisResult,
    AnalysisSource,
    AnalysisStatus,
    Insight,
    InsightSeverity,
    MetricSource,
    MetricSourceType,
    ProviderExecutionStatus,
    ProviderStatus,
    TimelineEntry,
    TopClip,
    VideoMeta,
)


def _generate_timeline(duration: float = 45.0) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    for t in range(int(duration)):
        virality_base = (
            0.55
            + 0.4 * math.exp(-((t - 12) / 3) ** 2)
            + 0.15 * math.exp(-((t - 32) / 5) ** 2)
        )
        virality = min(1.0, max(0.0, virality_base + math.sin(t * 1.7) * 0.03))

        arousal_base = (
            0.3
            + 0.5 * (1 - math.exp(-t / 6))
            - 0.12 * math.exp(-((t - 25) / 6) ** 2)
        )
        arousal = min(1.0, max(0.0, arousal_base + math.cos(t * 2.1) * 0.025))

        valence_base = (
            0.6
            + 0.25 * math.exp(-((t - 12) / 4) ** 2)
            + 0.1 * math.sin(t * 0.3)
        )
        valence = min(1.0, max(0.0, valence_base + math.sin(t * 1.3) * 0.02))

        retention_base = (
            0.92
            - 0.1 * math.exp(-((t - 26) / 7) ** 2)
            + 0.05 * math.exp(-((t - 40) / 4) ** 2)
        )
        retention = min(1.0, max(0.0, retention_base + math.sin(t * 0.9) * 0.015))

        label = None
        if t == 0:
            label = "Hook open"
        elif t == 12:
            label = "Pattern disruption"
        elif t == 25:
            label = "Mid-roll dip"
        elif t == 38:
            label = "CTA build-up"
        elif t == int(duration) - 1:
            label = "End frame"

        entries.append(
            TimelineEntry(
                time_seconds=float(t),
                virality=round(virality, 3),
                valence=round(valence, 3),
                arousal=round(arousal, 3),
                retention=round(retention, 3),
                label=label,
            )
        )
    return entries


def generate_mock_analysis(
    analysis_id: str | None = None,
    filename: str = "neural_core_analysis.mp4",
    duration: float = 45.0,
) -> AnalysisResult:
    """Return a complete mock analysis matching the MVP contract."""
    if analysis_id is None:
        analysis_id = f"ana_{uuid.uuid4()}"

    return AnalysisResult(
        id=analysis_id,
        status=AnalysisStatus.completed,
        analysis_source=AnalysisSource.demo_mock,
        provider_status=[
            ProviderStatus(
                name="demo",
                provider="mock",
                status=ProviderExecutionStatus.used,
                is_ai=False,
                message="Synthetic demo data for initial UI preview",
            )
        ],
        metric_sources=[
            MetricSource(metric=name, source_type=MetricSourceType.mock, providers=["mock"])
            for name in [
                "overall_virality_score",
                "retention_score",
                "rewatch_factor",
                "dominant_emotion",
                "emotion_intensity",
                "attention_duration_seconds",
                "timeline",
                "top_clips",
                "insights",
            ]
        ],
        progress=1.0,
        video=VideoMeta(
            filename=filename,
            duration_seconds=duration,
            fps=30,
            width=1080,
            height=1920,
        ),
        overall_virality_score=0.92,
        retention_score=0.884,
        rewatch_factor=3.2,
        dominant_emotion="Surprise",
        emotion_intensity=0.85,
        attention_duration_seconds=8.4,
        timeline=_generate_timeline(duration),
        top_clips=[
            TopClip(
                start_seconds=10,
                end_seconds=16,
                score=0.97,
                predicted_retention=0.95,
                reasons=[
                    "Pattern disruption at T+12s triggers dopamine response",
                    "Frame change velocity 3.2x above baseline",
                    "Audio-visual sync score 0.94",
                ],
            ),
            TopClip(
                start_seconds=35,
                end_seconds=43,
                score=0.88,
                predicted_retention=0.91,
                reasons=[
                    "Strong CTA framing with motion convergence",
                    "Emotional valence peaks before resolution",
                    "End-screen retention recovery pattern detected",
                ],
            ),
        ],
        insights=[
            Insight(
                title="Pattern Disruption Hook",
                description=(
                    "Frame change at T+12s correlates with a 34% retention spike. "
                    "The abrupt visual shift triggers an orienting response, keeping "
                    "viewers locked in during the critical first-scroll window."
                ),
                severity=InsightSeverity.high,
            ),
            Insight(
                title="Synthesized Subtitles",
                description=(
                    "Neural analysis suggests dynamic font scaling tied to speech "
                    "cadence would increase accessibility retention by ~12%. Current "
                    "static overlay underperforms on muted autoplay scenarios."
                ),
                severity=InsightSeverity.medium,
            ),
            Insight(
                title="Deep Transition Synthesis",
                description=(
                    "Analyze full sequence for complex motion mapping across scene "
                    "boundaries. Unlock advanced temporal coherence scoring to identify "
                    "hidden re-share triggers."
                ),
                severity=InsightSeverity.low,
            ),
        ],
    )
