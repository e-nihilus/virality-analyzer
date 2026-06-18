export type AnalysisStatus = "pending" | "processing" | "completed" | "failed";
export type AnalysisSource = "demo_mock" | "uploaded_real" | "uploaded_partial" | "failed";
export type ProviderExecutionStatus = "used" | "fallback" | "disabled" | "failed";
export type MetricSourceType = "ai" | "derived" | "heuristic" | "mock" | "unavailable";

export interface ProviderStatus {
  name: string;
  provider: string;
  status: ProviderExecutionStatus;
  is_ai: boolean;
  message?: string;
}

export interface MetricSource {
  metric: string;
  source_type: MetricSourceType;
  providers: string[];
  message?: string;
}

export interface VideoMeta {
  filename: string;
  duration_seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
}

export interface TimelineEntry {
  time_seconds: number;
  virality?: number;
  valence?: number;
  arousal?: number;
  emotion?: string;
  emotion_confidence?: number;
  retention?: number;
  label?: string;
}

export interface TopClip {
  start_seconds: number;
  end_seconds: number;
  score: number;
  predicted_retention?: number;
  reasons?: string[];
}

export type InsightSeverity = "high" | "medium" | "low";

export interface Insight {
  title: string;
  description: string;
  severity: InsightSeverity;
}

export interface TextHook {
  text: string;
  hook_type: string;
  timestamp: number;
  confidence: number;
}

export interface HookEvidence {
  person_detected_first_5s: boolean;
  face_arousal_avg_first_5s?: number | null;
  text_hook_first_5s?: TextHook | null;
  audio_energy_first_5s?: number | null;
}

export interface AnalysisResult {
  id: string;
  status: AnalysisStatus;
  analysis_source?: AnalysisSource;
  provider_status?: ProviderStatus[];
  metric_sources?: MetricSource[];
  progress?: number;
  video?: VideoMeta;
  overall_virality_score?: number;
  retention_score?: number;
  rewatch_factor?: number | null;
  action_recognition_score?: number;
  hook_score?: number | null;
  hook_evidence?: HookEvidence | null;
  pacing_score?: number | null;
  dominant_emotion?: string;
  emotion_intensity?: number | null;
  attention_duration_seconds?: number | null;
  timeline?: TimelineEntry[];
  top_clips?: TopClip[];
  insights?: Insight[];
}

export interface AnalysisSummary {
  id: string;
  status: AnalysisStatus;
  video?: Pick<VideoMeta, "filename">;
  overall_virality_score?: number;
  created_at?: string;
}
