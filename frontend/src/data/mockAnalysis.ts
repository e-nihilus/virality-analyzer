import type { AnalysisResult, TimelineEntry } from "../types/analysis";

function generateTimeline(): TimelineEntry[] {
  const entries: TimelineEntry[] = [];

  for (let t = 0; t <= 44; t++) {
    // Virality: peaks sharply around T+12s, moderate elsewhere
    const viralityBase =
      0.55 +
      0.4 * Math.exp(-Math.pow((t - 12) / 3, 2)) +
      0.15 * Math.exp(-Math.pow((t - 32) / 5, 2));
    const virality = Math.min(
      1,
      Math.max(0, viralityBase + (Math.sin(t * 1.7) * 0.03))
    );

    // Arousal: builds up in first 15s, stays elevated, slight dip mid-video
    const arousalBase =
      0.3 +
      0.5 * (1 - Math.exp(-t / 6)) -
      0.12 * Math.exp(-Math.pow((t - 25) / 6, 2));
    const arousal = Math.min(
      1,
      Math.max(0, arousalBase + (Math.cos(t * 2.1) * 0.025))
    );

    // Valence: generally positive, spikes with virality peak
    const valenceBase =
      0.6 +
      0.25 * Math.exp(-Math.pow((t - 12) / 4, 2)) +
      0.1 * Math.sin(t * 0.3);
    const valence = Math.min(
      1,
      Math.max(0, valenceBase + (Math.sin(t * 1.3) * 0.02))
    );

    // Retention: starts high, dips slightly in the middle (20-30s), recovers at end
    const retentionBase =
      0.92 -
      0.1 * Math.exp(-Math.pow((t - 26) / 7, 2)) +
      0.05 * Math.exp(-Math.pow((t - 40) / 4, 2));
    const retention = Math.min(
      1,
      Math.max(0, retentionBase + (Math.sin(t * 0.9) * 0.015))
    );

    const entry: TimelineEntry = {
      time_seconds: t,
      virality: Math.round(virality * 1000) / 1000,
      valence: Math.round(valence * 1000) / 1000,
      arousal: Math.round(arousal * 1000) / 1000,
      retention: Math.round(retention * 1000) / 1000,
    };

    // Add labels at notable points
    if (t === 0) entry.label = "Hook open";
    if (t === 12) entry.label = "Pattern disruption";
    if (t === 25) entry.label = "Mid-roll dip";
    if (t === 38) entry.label = "CTA build-up";
    if (t === 44) entry.label = "End frame";

    entries.push(entry);
  }

  return entries;
}

export const mockAnalysis: AnalysisResult = {
  id: "ana_7f3a9b2e-01d4-4c8a-b5e6-9d1f0a3c7e42",
  status: "completed",
  analysis_source: "demo_mock",
  progress: 100,
  video: {
    filename: "neural_core_analysis.mp4",
    duration_seconds: 45,
    fps: 30,
    width: 1080,
    height: 1920,
  },
  overall_virality_score: 0.92,
  retention_score: 0.884,
  rewatch_factor: 3.2,
  dominant_emotion: "Surprise",
  emotion_intensity: 0.85,
  attention_duration_seconds: 8.4,
  timeline: generateTimeline(),
  top_clips: [
    {
      start_seconds: 10,
      end_seconds: 16,
      score: 0.97,
      predicted_retention: 0.95,
      reasons: [
        "Pattern disruption at T+12s triggers dopamine response",
        "Frame change velocity 3.2× above baseline",
        "Audio-visual sync score 0.94",
      ],
    },
    {
      start_seconds: 35,
      end_seconds: 43,
      score: 0.88,
      predicted_retention: 0.91,
      reasons: [
        "Strong CTA framing with motion convergence",
        "Emotional valence peaks before resolution",
        "End-screen retention recovery pattern detected",
      ],
    },
  ],
  insights: [
    {
      title: "Pattern Disruption Hook",
      description:
        "Frame change at T+12s correlates with a 34% retention spike. The abrupt visual shift triggers an orienting response, keeping viewers locked in during the critical first-scroll window.",
      severity: "high",
      icon: "zap",
    },
    {
      title: "Synthesized Subtitles",
      description:
        "Neural analysis suggests dynamic font scaling tied to speech cadence would increase accessibility retention by ~12%. Current static overlay underperforms on muted autoplay scenarios.",
      severity: "medium",
      icon: "type",
    },
    {
      title: "Deep Transition Synthesis",
      description:
        "Analyze full sequence for complex motion mapping across scene boundaries. Unlock advanced temporal coherence scoring to identify hidden re-share triggers.",
      severity: "low",
      icon: "lock",
    },
  ],
};
