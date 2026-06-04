import { useCallback, useRef, useState } from "react";
import { createAnalysis, fetchAnalysis } from "../api/analysisApi";
import { useAnalysisStore } from "../stores/analysisStore";

function setVideoUrl(url: string | null) {
  useAnalysisStore.setState({ videoUrl: url });
}

type UploadStatus = "idle" | "uploading" | "processing" | "done" | "error";

const POLL_INTERVAL_MS = 1500;

export function useVideoUpload() {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const videoUrl = useAnalysisStore((s) => s.videoUrl);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const pollAnalysis = useCallback(
    (analysisId: string) => {
      setStatus("processing");
      setProgress(30);

      pollingRef.current = setInterval(async () => {
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
              source: "backend",
              error: null,
            });
            setStatus("done");
          } else if (result.status === "failed") {
            stopPolling();
            setError("Analysis failed. Please try a different video.");
            setStatus("error");
          }
        } catch {
          // Network error during poll — keep trying
        }
      }, POLL_INTERVAL_MS);
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
        // Clear previous analysis so the UI shows loading
        useAnalysisStore.setState({
          analysis: null,
          source: "backend",
          error: null,
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
            source: "backend",
            error: null,
          });
          setStatus("done");
        } else {
          // Background processing — start polling
          pollAnalysis(id);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : "Upload failed";
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
    setStatus("idle");
    setProgress(0);
    setError(null);
  }, [stopPolling]);

  return { status, progress, error, videoUrl, upload, reset };
}
