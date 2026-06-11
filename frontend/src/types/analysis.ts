export type AnalysisStatus = "pending" | "processing" | "completed" | "failed";

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
  icon?: string;
  timestamp?: number;
  action?: string;
}

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

export interface TextHook {
  text: string;
  hook_type: string;
  timestamp: number;
  confidence: number;
}

export interface Transcript {
  segments: TranscriptSegment[];
  full_text: string;
  hooks: TextHook[];
}

export interface AnalysisResult {
  id: string;
  user_id?: string;
  status: AnalysisStatus;
  progress?: number;
  video?: VideoMeta;
  overall_virality_score?: number;
  retention_score?: number;
  rewatch_factor?: number;
  action_recognition_score?: number;
  dominant_emotion?: string;
  timeline?: TimelineEntry[];
  top_clips?: TopClip[];
  insights?: Insight[];
  transcript?: Transcript;
}
