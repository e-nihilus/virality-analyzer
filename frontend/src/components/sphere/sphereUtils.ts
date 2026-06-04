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

function findClosestEntry(
  timeline: TimelineEntry[],
  time: number,
): TimelineEntry | undefined {
  if (!timeline.length) return undefined;
  let closest = timeline[0];
  let minDist = Math.abs(timeline[0].time_seconds - time);
  for (let i = 1; i < timeline.length; i++) {
    const dist = Math.abs(timeline[i].time_seconds - time);
    if (dist < minDist) {
      minDist = dist;
      closest = timeline[i];
    }
  }
  return closest;
}

export function analysisToSphereData(
  data: AnalysisResult,
  currentTime: number,
): SphereData {
  const timeline = data.timeline ?? [];
  const entry = findClosestEntry(timeline, currentTime);

  const virality = entry?.virality ?? data.overall_virality_score ?? 0.5;
  const arousal = entry?.arousal ?? 0.5;
  const valence = entry?.valence ?? 0.5;
  const retention = entry?.retention ?? data.retention_score ?? 0.5;
  const emotionIntensity =
    EMOTION_INTENSITY[data.dominant_emotion ?? "Neutral"] ?? 0.5;

  // Hook strength: average virality in first 5 seconds
  const hookEntries = timeline.filter((e) => e.time_seconds <= 5);
  const hook =
    hookEntries.length > 0
      ? hookEntries.reduce((sum, e) => sum + (e.virality ?? 0.5), 0) /
        hookEntries.length
      : 0.5;

  // Pacing: count labeled events as density proxy
  const labelCount = timeline.filter((e) => e.label).length;
  const duration = data.video?.duration_seconds ?? 45;
  const pacing = Math.min(1, (labelCount / (duration / 10)) * 0.6);

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
    { id: "emotion", name: "Emotion", intensity: emotionIntensity, position: REGION_POSITIONS.emotion },
    { id: "hook", name: "Hook", intensity: hook, position: REGION_POSITIONS.hook },
    { id: "pacing", name: "Pacing", intensity: pacing, position: REGION_POSITIONS.pacing },
  ];

  return { regions, engagement, cognitiveLoad, emotion: emotionIntensity };
}

export function intensityToColor(intensity: number): THREE.Color {
  const hue = (1 - intensity) * 0.66; // blue (cold) → red (hot)
  const color = new THREE.Color();
  color.setHSL(hue, 1, 0.5);
  return color;
}
