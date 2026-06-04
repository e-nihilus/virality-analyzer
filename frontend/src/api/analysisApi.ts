import type { AnalysisResult } from "../types/analysis";
import { apiFetch, buildUrl, getAuthHeaders } from "./client";

const API_PREFIX = "/api/viral-intelligence/analysis";

export function fetchMockAnalysis(): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>(`${API_PREFIX}/mock`);
}

export function fetchAnalysis(id: string): Promise<AnalysisResult> {
  return apiFetch<AnalysisResult>(`${API_PREFIX}/${id}`);
}

export function exportClip(analysisId: string, clipIndex: number): Promise<void> {
  return apiFetch(`${API_PREFIX}/${analysisId}/clips/${clipIndex}/export`, {
    method: "POST",
  });
}

export function downloadClipUrl(analysisId: string, clipIndex: number): string {
  return buildUrl(`${API_PREFIX}/${analysisId}/clips/${clipIndex}/download`);
}

export async function createAnalysis(file: File): Promise<{ id: string; status: string }> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(buildUrl(API_PREFIX), {
    method: "POST",
    body: form,
    headers: getAuthHeaders(),
  });

  if (!res.ok) {
    throw new Error(`Upload failed: ${res.status}`);
  }

  return res.json();
}
