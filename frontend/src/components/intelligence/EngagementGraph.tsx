import clsx from "clsx";

interface TimelinePoint {
  time_seconds: number;
  virality?: number;
  arousal?: number;
  retention?: number;
}

interface EngagementGraphProps {
  timeline?: TimelinePoint[];
  retentionScore?: number | null;
  rewatchFactor?: number | null;
  currentTime?: number;
  duration?: number;
  className?: string;
  allowDemoFallback?: boolean;
}

const DEFAULT_PATH = "M0 120 Q 150 110, 250 40 T 450 60 T 650 20 T 850 50 T 1000 30";

interface CurvePoint {
  x: number;
  y: number;
  value: number;
}

function pointValue(p: TimelinePoint): number {
  return p.arousal ?? p.virality ?? p.retention ?? 0;
}

/**
 * Centered Gaussian-weighted moving average. Real analysis timelines are sampled
 * once per second and can jump sharply between consecutive samples, producing a
 * spiky engagement curve. Smoothing the value series suppresses that
 * second-to-second noise while preserving overall trends. The smooth demo
 * timeline is unaffected (its values barely change between neighbours).
 */
function smoothSeries(values: number[], radius = 2): number[] {
  if (values.length <= 2) return values.slice();
  const sigma = radius * 0.75;
  const weights: number[] = [];
  for (let k = -radius; k <= radius; k++) {
    weights.push(Math.exp(-(k * k) / (2 * sigma * sigma)));
  }

  return values.map((_, i) => {
    let sum = 0;
    let wsum = 0;
    for (let k = -radius; k <= radius; k++) {
      const idx = i + k;
      if (idx < 0 || idx >= values.length) continue;
      const w = weights[k + radius];
      sum += values[idx] * w;
      wsum += w;
    }
    return wsum > 0 ? sum / wsum : values[i];
  });
}

function buildSmoothedPoints(timeline: TimelinePoint[], duration: number): CurvePoint[] {
  if (timeline.length === 0) return [];
  const safeDuration = duration > 0 ? duration : Math.max(...timeline.map((p) => p.time_seconds), 1);

  const smoothed = smoothSeries(timeline.map(pointValue));
  return timeline.map((p, i) => ({
    x: (p.time_seconds / safeDuration) * 1000,
    y: 120 - smoothed[i] * 120,
    value: smoothed[i],
  }));
}

function buildPathFromPoints(points: CurvePoint[]): string {
  if (points.length === 0) return "";

  let d = `M${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    d += ` Q ${cpx} ${prev.y}, ${curr.x} ${curr.y}`;
  }

  return d;
}

function findPeak(points: CurvePoint[]): { x: number; y: number } | null {
  if (points.length === 0) return null;

  let peak = points[0];
  for (const p of points) {
    if (p.value > peak.value) peak = p;
  }

  return { x: peak.x, y: peak.y };
}

function formatTime(seconds: number): string {
  const safeSeconds = Math.max(0, seconds);
  const m = Math.floor(safeSeconds / 60);
  const s = Math.floor(safeSeconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function timeLabels(duration: number): string[] {
  const safeDuration = duration > 0 ? duration : 0;
  return [0, 0.25, 0.5, 0.75, 1].map((ratio) => formatTime(safeDuration * ratio));
}

export default function EngagementGraph({
  timeline,
  retentionScore,
  rewatchFactor,
  currentTime = 0,
  duration = 0,
  className,
  allowDemoFallback = false,
}: EngagementGraphProps) {
  const hasData = timeline && timeline.length > 0;
  const points = hasData ? buildSmoothedPoints(timeline, duration) : [];
  const curvePath = hasData ? buildPathFromPoints(points) : allowDemoFallback ? DEFAULT_PATH : "";
  const areaPath = `${curvePath} L1000 120 L0 120 Z`;
  const playheadX = duration > 0 ? (currentTime / duration) * 1000 : 0;

  const peak = hasData ? findPeak(points) : null;
  // Default peak for the hardcoded path (~26.6% at the high point)
  const peakIndicator = peak ?? (allowDemoFallback ? { x: 650, y: 20 } : null);
  const labels = timeLabels(duration || 0);

  return (
    <div className={clsx("glass-panel rounded-xl p-6 space-y-4", className)}>
      {/* Header */}
      <div>
        <h3 className="text-body-lg text-on-surface font-medium">
          Engagement Dynamics
        </h3>
        <p className="text-label-sm text-on-surface-variant mt-1">
          Correlating Arousal Curves with Retention Peaks
        </p>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-label-sm text-on-surface-variant">Retention</span>
          <span className="text-headline-md text-primary">
            {retentionScore == null ? "No disponible" : `${retentionScore.toFixed(1)}%`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-label-sm text-on-surface-variant">Rewatches</span>
          <span className="text-headline-md text-tertiary">
            {rewatchFactor == null ? "No disponible" : `${rewatchFactor.toFixed(1)}x`}
          </span>
        </div>
      </div>

      {/* SVG chart */}
      <div className="relative">
        {curvePath ? (
          <svg
            viewBox="0 0 1000 120"
            className="w-full h-auto"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="engagement-fill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.3" />
                <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0" />
              </linearGradient>
            </defs>

            {/* Area fill */}
            <path d={areaPath} fill="url(#engagement-fill)" />

            {/* Curve line */}
            <path
              d={curvePath}
              fill="none"
              stroke="var(--color-primary)"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Peak indicator */}
            {peakIndicator && (
              <circle
                cx={peakIndicator.x}
                cy={peakIndicator.y}
                r="6"
                fill="var(--color-secondary)"
                stroke="var(--color-surface)"
                strokeWidth="2"
              />
            )}

            {/* Playhead line */}
            <line
              x1={playheadX}
              y1="0"
              x2={playheadX}
              y2="120"
              stroke="var(--color-on-surface)"
              strokeWidth="1.5"
              strokeDasharray="4 3"
              opacity="0.5"
            />
          </svg>
        ) : (
          <div className="h-[120px] flex items-center justify-center rounded-lg border border-outline-variant/20 text-label-sm text-on-surface-variant">
            Timeline no disponible
          </div>
        )}

        {/* X-axis labels */}
        <div className="flex justify-between mt-2">
          {labels.map((label) => (
            <span
              key={label}
              className="text-mono-metric text-on-surface-variant"
            >
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
