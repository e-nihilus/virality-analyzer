import clsx from "clsx";

interface ViralityScoreProps {
  score?: number | null;
  emotion?: string;
  timestamp?: string;
  sourceType?: "ai" | "derived" | "heuristic" | "mock" | "unavailable";
  sourceMessage?: string;
}

export default function ViralityScore({
  score,
  emotion = "Emotional Intelligence",
  timestamp,
  sourceType,
  sourceMessage,
}: ViralityScoreProps) {
  const percentage = score == null ? null : Math.round(score * 100);
  const badgeLabel = sourceType === "ai" ? "AI score" : sourceType === "mock" ? "Demo mock" : "Composite score";

  return (
    <section className="flex flex-col gap-1 lg:flex-row lg:justify-between lg:items-start">
      {/* Left: Active analysis label + headline */}
      <div className="flex flex-col">
        <span className="text-label-sm text-primary uppercase tracking-widest">
          Active Analysis
        </span>
        <h2 className="text-headline-md mt-1">{emotion}</h2>
        {timestamp && (
          <span className="text-on-surface-variant/60 text-label-sm uppercase tracking-widest mt-0.5 lg:hidden">
            Real-time sync: {timestamp}
          </span>
        )}
      </div>

      {/* Right: Virality score */}
      <div className="flex items-center gap-2 lg:flex-col lg:items-end lg:gap-0 mt-2 lg:mt-0">
        <div className="flex items-center gap-2 lg:flex-col lg:items-end">
          {/* Mobile: pulsing amber dot + secondary color */}
          <span className="lg:hidden flex items-center gap-2">
            <span className="w-2 h-2 bg-secondary rounded-full pulse-dot" />
            <span className="text-display-lg-mobile text-secondary font-bold">
              {percentage == null ? "—" : `${percentage}%`}
            </span>
          </span>

          {/* Desktop: primary color, no dot */}
          <span className="hidden lg:block text-right">
            <span className="text-on-surface-variant text-label-sm block">
              Virality Score
            </span>
            <span className="text-primary text-display-lg leading-none">
              {percentage == null ? "—" : `${percentage}%`}
            </span>
          </span>
          {sourceType && (
            <span
              className={clsx(
                "rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest",
                sourceType === "ai"
                  ? "border-primary/40 text-primary"
                  : "border-outline-variant/40 text-on-surface-variant",
              )}
              title={sourceMessage}
            >
              {badgeLabel}
            </span>
          )}
        </div>

        {/* Mobile label below */}
        <span
          className={clsx(
            "text-label-sm lg:hidden",
            "text-secondary/80",
          )}
        >
          VIRALITY SCORE
        </span>
      </div>
    </section>
  );
}
