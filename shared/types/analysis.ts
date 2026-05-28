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
}

export interface AnalysisResult {
  id: string;
  status: AnalysisStatus;
  progress?: number;
  video?: VideoMeta;
  overall_virality_score?: number;
  retention_score?: number;
  rewatch_factor?: number;
  dominant_emotion?: string;
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
