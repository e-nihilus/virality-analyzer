import type { AnalysisResult, TimelineEntry } from "../../types/analysis";
import * as THREE from "three";

export interface SphereRegion {
  id: string;
  name: string;
  intensity: number;
  position: [number, number, number];
}

export interface SphereData {
  regions: SphereRegion[];
  engagement: number;
  cognitiveLoad: number;
  emotion: number;
}

const REGION_POSITIONS: Record<string, [number, number, number]> = {
  virality: [0.0, 1.85, 0.2],
  arousal: [1.4, 1.2, 0.4],
  valence: [-1.4, 1.2, 0.4],
  retention: [0.0, -0.2, -1.95],
  emotion: [0.0, -0.4, 0.4],
  hook: [-1.5, 0.4, 1.0],
  pacing: [1.5, 0.4, 1.0],
};

const EMOTION_INTENSITY: Record<string, number> = {
  Surprise: 0.85,
  Joy: 0.75,
  Anger: 0.9,
  Fear: 0.8,
  Sadness: 0.6,
  Disgust: 0.7,
  Neutral: 0.3,
};

/**
 * Linearly interpolate a numeric timeline field at an arbitrary time.
 *
 * Real analysis timelines are sampled once per second and can jump sharply
 * between consecutive samples (e.g. valence can change by 0.5 in 1s). Snapping
 * to the closest sample produces a step function that looks abrupt as playback
 * advances. Interpolating between the two bracketing samples yields a smooth,
 * continuous signal regardless of how jumpy the underlying data is — matching
 * the fluidity of the smooth demo timeline.
 */
function interpolateField(
  timeline: TimelineEntry[],
  time: number,
  key: "virality" | "valence" | "arousal" | "retention",
): number | undefined {
  const points: Array<{ t: number; v: number }> = [];
  for (const e of timeline) {
    const v = e[key];
    if (typeof v === "number") points.push({ t: e.time_seconds, v });
  }
  if (!points.length) return undefined;
  points.sort((a, b) => a.t - b.t);

  if (time <= points[0].t) return points[0].v;
  const last = points[points.length - 1];
  if (time >= last.t) return last.v;

  for (let i = 1; i < points.length; i++) {
    if (time <= points[i].t) {
      const a = points[i - 1];
      const b = points[i];
      const span = b.t - a.t;
      const f = span > 0 ? (time - a.t) / span : 0;
      return a.v + (b.v - a.v) * f;
    }
  }
  return last.v;
}

export function analysisToSphereData(
  data: AnalysisResult,
  currentTime: number,
): SphereData {
  const isDemo = data.analysis_source === "demo_mock";
  const timeline = data.timeline ?? [];

  // Numeric per-time metrics are interpolated between samples so the sphere
  // transitions smoothly even when the underlying analysis data jumps sharply
  // from one second to the next.
  const virality =
    interpolateField(timeline, currentTime, "virality") ??
    data.overall_virality_score ??
    (isDemo ? 0.5 : 0);
  const arousal =
    interpolateField(timeline, currentTime, "arousal") ?? (isDemo ? 0.5 : 0);
  const valence =
    interpolateField(timeline, currentTime, "valence") ?? (isDemo ? 0.5 : 0);
  const retention =
    interpolateField(timeline, currentTime, "retention") ??
    data.retention_score ??
    (isDemo ? 0.5 : 0);
  const emotionIntensity = isDemo
    ? EMOTION_INTENSITY[data.dominant_emotion ?? "Neutral"] ?? 0.5
    : data.emotion_intensity ?? null;

  // Hook strength: backend score when present. The average-virality fallback is
  // allowed only for demo/mock data, never for uploaded videos.
  const hookEntries = timeline.filter((e) => e.time_seconds <= 5);
  const hookFallback = isDemo ? (
    hookEntries.length > 0
      ? hookEntries.reduce((sum, e) => sum + (e.virality ?? 0.5), 0) /
        hookEntries.length
      : 0.5
  ) : null;
  const hook = data.hook_score ?? hookFallback;

  // Pacing: backend scene-cut score when present. The label-density fallback is
  // allowed only for demo/mock data, never for uploaded videos.
  const labelCount = timeline.filter((e) => e.label).length;
  const duration = data.video?.duration_seconds ?? 45;
  const pacing = data.pacing_score ?? (isDemo ? Math.min(1, (labelCount / (duration / 10)) * 0.6) : null);

  const engagement = (arousal + retention) / 2;

  // Cognitive load: variance of virality around current time
  const window = timeline.filter(
    (e) => Math.abs(e.time_seconds - currentTime) <= 5,
  );
  let cognitiveLoad = 0.4;
  if (window.length > 1) {
    const mean =
      window.reduce((s, e) => s + (e.virality ?? 0.5), 0) / window.length;
    const variance =
      window.reduce((s, e) => s + Math.pow((e.virality ?? 0.5) - mean, 2), 0) /
      window.length;
    cognitiveLoad = Math.min(1, variance * 20);
  }

  const regions: SphereRegion[] = [
    { id: "virality", name: "Virality", intensity: virality, position: REGION_POSITIONS.virality },
    { id: "arousal", name: "Arousal", intensity: arousal, position: REGION_POSITIONS.arousal },
    { id: "valence", name: "Valence", intensity: valence, position: REGION_POSITIONS.valence },
    { id: "retention", name: "Retention", intensity: retention, position: REGION_POSITIONS.retention },
  ];
  if (emotionIntensity != null) {
    regions.push({ id: "emotion", name: "Emotion", intensity: emotionIntensity, position: REGION_POSITIONS.emotion });
  }
  if (hook != null) {
    regions.push({ id: "hook", name: "Hook", intensity: hook, position: REGION_POSITIONS.hook });
  }
  if (pacing != null) {
    regions.push({ id: "pacing", name: "Pacing", intensity: pacing, position: REGION_POSITIONS.pacing });
  }

  return { regions, engagement, cognitiveLoad, emotion: emotionIntensity ?? 0 };
}

export function intensityToColor(intensity: number): THREE.Color {
  const hue = (1 - intensity) * 0.66; // blue (cold) → red (hot)
  const color = new THREE.Color();
  color.setHSL(hue, 1, 0.5);
  return color;
}
