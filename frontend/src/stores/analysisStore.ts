import { create } from "zustand";
import type { AnalysisResult } from "../types/analysis";
import { fetchMockAnalysis } from "../api/analysisApi";
import { mockAnalysis } from "../data/mockAnalysis";

interface AnalysisState {
  analysis: AnalysisResult | null;
  loading: boolean;
  error: string | null;
  source: "backend" | "local-mock";
  videoUrl: string | null;
  playbackTime: number;
  isPlaying: boolean;
  setPlaybackTime: (t: number) => void;
  setIsPlaying: (playing: boolean) => void;
  loadAnalysis: () => Promise<void>;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  analysis: null,
  loading: false,
  error: null,
  source: "local-mock",
  videoUrl: null,
  playbackTime: 0,
  isPlaying: false,
  setPlaybackTime: (t) => set({ playbackTime: t }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),

  loadAnalysis: async () => {
    set({ loading: true, error: null });
    try {
      const data = await fetchMockAnalysis();
      set({ analysis: data, loading: false, source: "backend" });
    } catch {
      // Fallback to local mock data when backend is unavailable
      console.warn("[Aurea] Backend unavailable — using local mock data");
      set({
        analysis: mockAnalysis,
        loading: false,
        source: "local-mock",
        error: null,
      });
    }
  },
}));
