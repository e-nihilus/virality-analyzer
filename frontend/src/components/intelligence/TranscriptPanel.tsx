import clsx from "clsx";
import { Clock, MessageSquareText, Zap } from "lucide-react";
import type { MetricSourceType, Transcript, TextHook } from "../../types/analysis";

interface TranscriptPanelProps {
  transcript: Transcript;
  currentTime?: number;
  hooksSourceType?: MetricSourceType;
  hooksSourceMessage?: string;
}

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

const hookTypeLabel: Record<string, string> = {
  curiosity_gap: "Curiosity Gap",
  urgency: "Urgency",
  conflict: "Conflict",
  question: "Question",
  command: "Command",
  surprise: "Surprise",
};

function HookBadge({ hook, sourceType }: { hook: TextHook; sourceType?: MetricSourceType }) {
  const isAi = sourceType === "ai";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-mono-metric",
        isAi
          ? "bg-primary-container/20 text-primary"
          : "bg-surface-container-highest text-on-surface-variant",
      )}
      title={isAi ? "Qwen-classified verbal hook" : "Explicit regex fallback hook"}
    >
      <Zap size={10} />
      {hookTypeLabel[hook.hook_type] ?? hook.hook_type}
      {!isAi && <span className="opacity-70">Regex</span>}
    </span>
  );
}

export default function TranscriptPanel({
  transcript,
  currentTime = 0,
  hooksSourceType,
  hooksSourceMessage,
}: TranscriptPanelProps) {
  const { segments, hooks } = transcript;

  if (!segments.length) return null;

  const hooksByTime = new Map<number, TextHook[]>();
  for (const hook of hooks) {
    const key = hook.timestamp;
    if (!hooksByTime.has(key)) hooksByTime.set(key, []);
    hooksByTime.get(key)!.push(hook);
  }

  return (
    <div className="bg-surface-container p-6 rounded-xl border border-outline-variant/20 relative overflow-hidden">
      <div className="absolute top-0 right-0 p-4">
        <MessageSquareText className="w-9 h-9 text-primary/40" />
      </div>

      <h3 className="text-headline-md mb-4 text-on-surface">
        Transcript &amp; Verbal Hooks
      </h3>
      {hooks.length > 0 && hooksSourceType && (
        <p className="text-label-sm text-on-surface-variant mb-3">
          Hooks: {hooksSourceType === "ai" ? "Qwen AI" : "explicit fallback"}
          {hooksSourceMessage ? ` — ${hooksSourceMessage}` : ""}
        </p>
      )}

      <div className="space-y-3 max-h-80 overflow-y-auto pr-2">
        {segments.map((seg, i) => {
          const isActive =
            currentTime >= seg.start && currentTime < seg.end;
          const segHooks = hooksByTime.get(seg.start) ?? [];

          return (
            <div
              key={i}
              className={clsx(
                "flex gap-3 rounded-lg px-3 py-2 transition-colors",
                isActive
                  ? "bg-primary-container/15 border border-primary/30"
                  : "hover:bg-surface-container-highest/40",
              )}
            >
              <span className="inline-flex items-center gap-1 text-mono-metric text-on-surface-variant/50 shrink-0 pt-0.5">
                <Clock size={10} />
                {formatTimestamp(seg.start)}
              </span>

              <div className="min-w-0">
                <p className="text-body-md text-on-surface">{seg.text}</p>
                {segHooks.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {segHooks.map((h, j) => (
                      <HookBadge key={j} hook={h} sourceType={hooksSourceType} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
