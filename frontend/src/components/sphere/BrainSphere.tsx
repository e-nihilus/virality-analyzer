import { useMemo } from "react";

import type { AnalysisResult } from "../../types/analysis";
import { analysisToSphereData } from "./sphereUtils";
import type { MetricState } from "./metrics";
import MetricsCanvas from "./MetricsCanvas";

interface BrainSphereProps {
  analysis: AnalysisResult;
  currentTime: number;
  isPlaying?: boolean;
}

/**
 * Data adapter around the shader sphere (MetricsCanvas).
 *
 * Keeps the original BrainSphere API (analysis + currentTime + isPlaying) so the
 * rest of the app is untouched, while feeding the new volumetric shader sphere
 * with live, normalized metric values derived from the analysis timeline.
 */
export default function BrainSphere({
  analysis,
  currentTime,
  isPlaying = true,
}: BrainSphereProps) {
  const metrics = useMemo<MetricState>(() => {
    const { regions } = analysisToSphereData(analysis, currentTime);
    // regions are scored 0..1; the shader sphere expects a 0..100 scale.
    const pct = (id: string) =>
      Math.round((regions.find((r) => r.id === id)?.intensity ?? 0) * 100);

    return {
      valence: pct("valence"),
      virality: pct("virality"),
      arousal: pct("arousal"),
      pacing: pct("pacing"),
      retention: pct("retention"),
      emotion: pct("emotion"),
      hook: pct("hook"),
    };
  }, [analysis, currentTime]);

  return (
    <div className="relative w-full h-full min-h-[300px]">
      <MetricsCanvas metrics={metrics} isPlaying={isPlaying} />
    </div>
  );
}
