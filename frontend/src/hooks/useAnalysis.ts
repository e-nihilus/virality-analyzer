import { useEffect } from "react";
import { useAnalysisStore } from "../stores/analysisStore";

export function useAnalysis() {
  const { analysis, loading, error, source, loadAnalysis } =
    useAnalysisStore();

  useEffect(() => {
    if (!analysis && !loading) {
      loadAnalysis();
    }
  }, [analysis, loading, loadAnalysis]);

  return { analysis, loading, error, source };
}
