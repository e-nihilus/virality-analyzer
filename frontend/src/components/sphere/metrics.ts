/**
 * Metric definitions shared by the shader sphere (MetricsCanvas).
 * Values in MetricState are expressed on a 0–100 scale.
 */

export interface MetricState {
  valence: number;
  virality: number;
  arousal: number;
  pacing: number;
  retention: number;
  emotion: number;
  hook: number;
}

export interface MetricDefinition {
  key: keyof MetricState;
  name: string;
  color: string;
  hex: string;
}

export const METRICS_LIST: MetricDefinition[] = [
  { key: "valence", name: "Valence", color: "cyan", hex: "#00F2FF" },
  { key: "virality", name: "Virality", color: "pink", hex: "#FF00E5" },
  { key: "arousal", name: "Arousal", color: "orange", hex: "#FF3D00" },
  { key: "pacing", name: "Pacing", color: "indigo", hex: "#AD00FF" },
  { key: "retention", name: "Retention", color: "blue", hex: "#0066FF" },
  { key: "emotion", name: "Emotion", color: "lime", hex: "#14FF00" },
  { key: "hook", name: "Hook", color: "amber", hex: "#FFD600" },
];
