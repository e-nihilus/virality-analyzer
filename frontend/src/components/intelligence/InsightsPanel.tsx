import clsx from "clsx";
import {
  BrainCircuit,
  Clock,
  Lightbulb,
  Lock,
  Sparkles,
} from "lucide-react";
import type { Insight, InsightSeverity } from "../../types/analysis";

interface InsightsPanelProps {
  insights: Insight[];
}

const severityBarColor: Record<InsightSeverity, string> = {
  high: "bg-primary",
  medium: "bg-secondary",
  low: "bg-outline-variant",
};

const severityIconBg: Record<InsightSeverity, string> = {
  high: "bg-primary-container/20",
  medium: "bg-tertiary-container/20",
  low: "bg-surface-container-highest",
};

const severityIconColor: Record<InsightSeverity, string> = {
  high: "text-primary",
  medium: "text-tertiary",
  low: "text-on-surface-variant/40",
};

function InsightIcon({ severity }: { severity: InsightSeverity }) {
  const iconClass = clsx("w-5 h-5", severityIconColor[severity]);

  if (severity === "low") return <Lock className={iconClass} />;
  if (severity === "medium") return <BrainCircuit className={iconClass} />;
  return <Sparkles className={iconClass} />;
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function InsightsPanel({ insights }: InsightsPanelProps) {
  return (
    <>
      {/* Desktop: single card with bar indicators */}
      <div className="hidden lg:block bg-surface-container p-6 rounded-xl border border-outline-variant/20 relative overflow-hidden">
        {/* Corner icon */}
        <div className="absolute top-0 right-0 p-4">
          <BrainCircuit className="w-9 h-9 text-primary/40" />
        </div>

        <h3 className="text-headline-md mb-4 text-on-surface">
          AI Insights &amp; Hooks
        </h3>

        <div className="space-y-5">
          {insights.map((insight, i) => (
            <div key={i} className="flex gap-4">
              <div
                className={clsx(
                  "w-1 rounded-full shrink-0",
                  severityBarColor[insight.severity],
                )}
              />
              <div className="min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h4 className="font-bold text-on-surface">{insight.title}</h4>
                  {insight.timestamp != null && (
                    <span className="inline-flex items-center gap-1 text-mono-metric text-on-surface-variant/50">
                      <Clock size={10} />
                      T+{formatTimestamp(insight.timestamp)}
                    </span>
                  )}
                </div>
                <p className="text-on-surface-variant text-body-md mt-0.5">
                  {insight.description}
                </p>
                {insight.action && (
                  <p className="flex items-start gap-1.5 mt-1.5 text-body-md text-tertiary/80">
                    <Lightbulb size={14} className="shrink-0 mt-0.5" />
                    {insight.action}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Mobile: separate cards with icon boxes */}
      <div className="flex flex-col gap-3 lg:hidden">
        <h3 className="text-label-sm text-on-surface-variant uppercase tracking-widest px-1">
          AI Hooks &amp; Recommendations
        </h3>

        {insights.map((insight, i) => (
          <div
            key={i}
            className={clsx(
              "glass-panel rounded-xl p-4 flex gap-4 items-start",
              "active:scale-[0.98] transition-transform",
              insight.severity === "low" && "opacity-60",
            )}
          >
            <div
              className={clsx(
                "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
                severityIconBg[insight.severity],
              )}
            >
              <InsightIcon severity={insight.severity} />
            </div>

            <div className="flex flex-col gap-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h4 className="text-body-lg text-on-surface leading-tight">
                  {insight.title}
                </h4>
                {insight.timestamp != null && (
                  <span className="inline-flex items-center gap-1 text-mono-metric text-on-surface-variant/50">
                    <Clock size={10} />
                    T+{formatTimestamp(insight.timestamp)}
                  </span>
                )}
              </div>
              <p className="text-on-surface-variant/60 text-body-md leading-relaxed">
                {insight.description}
              </p>
              {insight.action && (
                <p className="flex items-start gap-1.5 mt-1 text-body-md text-tertiary/70">
                  <Lightbulb size={14} className="shrink-0 mt-0.5" />
                  {insight.action}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
