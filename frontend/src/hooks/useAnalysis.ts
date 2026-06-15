import { useEffect } from "react";
import { useAnalysisStore } from "../stores/analysisStore";

export function useAnalysis() {
  const { analysis, loading, error, source, uploading, loadAnalysis } =
    useAnalysisStore();

  useEffect(() => {
    if (!analysis && !loading && !uploading) {
      loadAnalysis();
    }
  }, [analysis, loading, uploading, loadAnalysis]);

  return { analysis, loading, error, source };
}
