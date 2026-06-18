import { useCallback, useRef, useState } from "react";
import { createAnalysis, fetchAnalysis } from "../api/analysisApi";
import type { AnalysisResult } from "../types/analysis";
import type { AnalysisSource } from "../stores/analysisStore";
import { useAnalysisStore } from "../stores/analysisStore";

function setVideoUrl(url: string | null) {
  useAnalysisStore.setState({ videoUrl: url });
}

type UploadStatus = "idle" | "uploading" | "processing" | "done" | "error";

// Polling uses backoff: starts fast, then slows down for long analyses to cut
// down on request noise while a video is still processing.
const POLL_INTERVAL_START_MS = 1500;
const POLL_INTERVAL_MAX_MS = 5000;
const POLL_BACKOFF_FACTOR = 1.4;

function sourceFromResult(result: AnalysisResult): AnalysisSource {
  if (result.status === "failed" || result.analysis_source === "failed") {
    return "failed";
  }
  if (result.analysis_source === "uploaded_partial") {
    return "uploaded-partial";
  }
  return "uploaded-real";
}

export function useVideoUpload() {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const videoUrl = useAnalysisStore((s) => s.videoUrl);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const pollAnalysis = useCallback(
    (analysisId: string) => {
      setStatus("processing");
      setProgress(30);

      let delay = POLL_INTERVAL_START_MS;

      const scheduleNext = () => {
        pollingRef.current = setTimeout(tick, delay);
        delay = Math.min(Math.round(delay * POLL_BACKOFF_FACTOR), POLL_INTERVAL_MAX_MS);
      };

      const tick = async () => {
        try {
          const result = await fetchAnalysis(analysisId);
          const serverProgress = result.progress ?? 0;

          // Map server progress (0-1) to UI progress (30-95 during processing)
          setProgress(Math.round(30 + serverProgress * 65));

          if (result.status === "completed") {
            stopPolling();
            setProgress(100);
            useAnalysisStore.setState({
              analysis: result,
              source: sourceFromResult(result),
              error: null,
              uploading: false,
            });
            setStatus("done");
            return;
          } else if (result.status === "failed") {
            stopPolling();
            useAnalysisStore.setState({
              analysis: result,
              source: "failed",
              uploading: false,
            });
            setError("Analysis failed. Please try a different video.");
            setStatus("error");
            return;
          }
        } catch {
          // Network error during poll — keep trying
        }
        scheduleNext();
      };

      scheduleNext();
    },
    [stopPolling],
  );

  const upload = useCallback(
    async (file: File) => {
      setStatus("uploading");
      setProgress(0);
      setError(null);
      stopPolling();

      // Validate client-side
      const ext = file.name.split(".").pop()?.toLowerCase();
      const allowed = ["mp4", "mov", "webm", "avi", "mkv"];
      if (!ext || !allowed.includes(ext)) {
        setError(
          `Unsupported file type .${ext}. Allowed: ${allowed.join(", ")}`,
        );
        setStatus("error");
        return;
      }

      if (file.size > 1024 * 1024 * 1024) {
        setError("File too large. Max 1 GB.");
        setStatus("error");
        return;
      }

      try {
        // Clear previous analysis and mark upload in progress
        useAnalysisStore.setState({
          analysis: null,
          source: "uploaded-real",
          error: null,
          uploading: true,
        });

        // Create a local preview URL for the video
        const localUrl = URL.createObjectURL(file);
        setVideoUrl(localUrl);

        setProgress(10);
        const { id, status: serverStatus } = await createAnalysis(file);
        setProgress(25);

        if (serverStatus === "completed") {
          // Synchronous analysis (shouldn't happen now, but handles edge case)
          const result = await fetchAnalysis(id);
          setProgress(100);
          useAnalysisStore.setState({
            analysis: result,
            source: sourceFromResult(result),
            error: null,
            uploading: false,
          });
          setStatus(result.status === "failed" ? "error" : "done");
        } else {
          // Background processing — start polling
          pollAnalysis(id);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Upload failed";
        useAnalysisStore.setState({
          source: "failed",
          uploading: false,
          error: message,
        });
        setError(message);
        setStatus("error");
      }
    },
    [stopPolling, pollAnalysis],
  );

  const reset = useCallback(() => {
    stopPolling();
    const currentUrl = useAnalysisStore.getState().videoUrl;
    if (currentUrl) URL.revokeObjectURL(currentUrl);
    setVideoUrl(null);
    useAnalysisStore.setState({ analysis: null, source: "demo-mock" });
    setStatus("idle");
    setProgress(0);
    setError(null);
  }, [stopPolling]);

  return { status, progress, error, videoUrl, upload, reset };
}
