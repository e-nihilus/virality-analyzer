import clsx from "clsx";

interface TimelinePoint {
  time_seconds: number;
  virality?: number;
  arousal?: number;
  retention?: number;
}

interface EngagementGraphProps {
  timeline?: TimelinePoint[];
  retentionScore?: number;
  rewatchFactor?: number;
  currentTime?: number;
  duration?: number;
  className?: string;
}

const DEFAULT_PATH = "M0 120 Q 150 110, 250 40 T 450 60 T 650 20 T 850 50 T 1000 30";

function buildPathFromTimeline(timeline: TimelinePoint[], duration: number): string {
  if (timeline.length === 0) return DEFAULT_PATH;

  const points = timeline.map((p) => {
    const x = (p.time_seconds / duration) * 1000;
    const value = p.arousal ?? p.virality ?? p.retention ?? 0;
    const y = 120 - value * 120;
    return { x, y };
  });

  let d = `M${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    d += ` Q ${cpx} ${prev.y}, ${curr.x} ${curr.y}`;
  }

  return d;
}

function findPeak(timeline: TimelinePoint[], duration: number): { x: number; y: number } | null {
  if (timeline.length === 0) return null;

  let maxVal = -1;
  let maxPoint: TimelinePoint | null = null;

  for (const p of timeline) {
    const v = p.arousal ?? p.virality ?? p.retention ?? 0;
    if (v > maxVal) {
      maxVal = v;
      maxPoint = p;
    }
  }

  if (!maxPoint) return null;

  return {
    x: (maxPoint.time_seconds / duration) * 1000,
    y: 120 - maxVal * 120,
  };
}

const TIME_LABELS = ["0:00", "0:10", "0:20", "0:30", "0:40", "0:50"];

export default function EngagementGraph({
  timeline,
  retentionScore = 88.4,
  rewatchFactor = 3.2,
  currentTime = 12,
  duration = 50,
  className,
}: EngagementGraphProps) {
  const hasData = timeline && timeline.length > 0;
  const curvePath = hasData ? buildPathFromTimeline(timeline, duration) : DEFAULT_PATH;
  const areaPath = `${curvePath} L1000 120 L0 120 Z`;
  const playheadX = duration > 0 ? (currentTime / duration) * 1000 : 0;

  const peak = hasData ? findPeak(timeline, duration) : null;
  // Default peak for the hardcoded path (~26.6% at the high point)
  const peakIndicator = peak ?? { x: 650, y: 20 };

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
            {retentionScore.toFixed(1)}%
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-label-sm text-on-surface-variant">Rewatches</span>
          <span className="text-headline-md text-tertiary">
            {rewatchFactor.toFixed(1)}x
          </span>
        </div>
      </div>

      {/* SVG chart */}
      <div className="relative">
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
          <circle
            cx={peakIndicator.x}
            cy={peakIndicator.y}
            r="6"
            fill="var(--color-secondary)"
            stroke="var(--color-surface)"
            strokeWidth="2"
          />

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

        {/* X-axis labels */}
        <div className="flex justify-between mt-2">
          {TIME_LABELS.map((label) => (
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
