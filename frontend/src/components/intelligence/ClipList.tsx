import { useState } from "react";
import clsx from "clsx";
import {
  Film,
  Download,
  Loader2,
  Clock,
  Star,
  AlertCircle,
} from "lucide-react";
import type { TopClip } from "../../types/analysis";
import { exportClip, downloadClipUrl } from "../../api/analysisApi";

interface ClipListProps {
  clips: TopClip[];
  analysisId: string;
}

type ClipState = "idle" | "exporting" | "exported" | "error";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function scoreColor(score: number): string {
  if (score >= 0.7) return "text-primary";
  if (score >= 0.5) return "text-secondary";
  return "text-on-surface-variant";
}

export default function ClipList({ clips, analysisId }: ClipListProps) {
  const [clipStates, setClipStates] = useState<Map<number, ClipState>>(
    () => new Map(),
  );
  const [clipErrors, setClipErrors] = useState<Map<number, string>>(
    () => new Map(),
  );

  function getState(index: number): ClipState {
    return clipStates.get(index) ?? "idle";
  }

  async function handleExport(index: number) {
    setClipStates((prev) => new Map(prev).set(index, "exporting"));
    setClipErrors((prev) => {
      const next = new Map(prev);
      next.delete(index);
      return next;
    });

    try {
      await exportClip(analysisId, index);
      setClipStates((prev) => new Map(prev).set(index, "exported"));
    } catch (err) {
      setClipStates((prev) => new Map(prev).set(index, "error"));
      setClipErrors((prev) =>
        new Map(prev).set(
          index,
          err instanceof Error ? err.message : "Export failed",
        ),
      );
    }
  }

  function handleDownload(index: number) {
    window.open(downloadClipUrl(analysisId, index), "_blank");
  }

  function renderClipContent(clip: TopClip, index: number) {
    const state = getState(index);

    return (
      <>
        <div className="flex items-center gap-2 flex-wrap">
          <h4 className="font-bold text-on-surface">
            Clip {index + 1}
          </h4>
          <span className="inline-flex items-center gap-1 text-mono-metric text-on-surface-variant/50">
            <Clock size={10} />
            {formatTime(clip.start_seconds)} – {formatTime(clip.end_seconds)}
          </span>
          <span
            className={clsx(
              "inline-flex items-center gap-1 text-mono-metric",
              scoreColor(clip.score),
            )}
          >
            <Star size={10} />
            {Math.round(clip.score * 100)}%
          </span>
        </div>

        {clip.reasons && clip.reasons.length > 0 && (
          <ul className="mt-1 space-y-0.5">
            {clip.reasons.map((reason, ri) => (
              <li
                key={ri}
                className="text-on-surface-variant text-body-md"
              >
                • {reason}
              </li>
            ))}
          </ul>
        )}

        <div className="flex items-center gap-2 mt-2">
          <button
            type="button"
            disabled={state === "exporting"}
            onClick={() => handleExport(index)}
            className={clsx(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-body-md transition-colors",
              state === "exported"
                ? "bg-primary-container/20 text-primary"
                : "bg-surface-container-highest text-on-surface hover:bg-outline-variant/20",
              state === "exporting" && "opacity-60 cursor-wait",
            )}
          >
            {state === "exporting" ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Film size={14} />
            )}
            {state === "exported" ? "Exported" : "Export"}
          </button>

          <button
            type="button"
            disabled={state !== "exported"}
            onClick={() => handleDownload(index)}
            className={clsx(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-body-md transition-colors",
              state === "exported"
                ? "bg-surface-container-highest text-on-surface hover:bg-outline-variant/20"
                : "bg-surface-container-highest text-on-surface/30 cursor-not-allowed",
            )}
          >
            <Download size={14} />
            Download
          </button>
        </div>

        {state === "error" && clipErrors.get(index) && (
          <p className="flex items-start gap-1.5 mt-1.5 text-body-md text-error">
            <AlertCircle size={14} className="shrink-0 mt-0.5" />
            {clipErrors.get(index)}
          </p>
        )}
      </>
    );
  }

  return (
    <>
      {/* Desktop: single card with all clips */}
      <div className="hidden lg:block bg-surface-container p-6 rounded-xl border border-outline-variant/20 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4">
          <Film className="w-9 h-9 text-primary/40" />
        </div>

        <h3 className="text-headline-md mb-4 text-on-surface">
          Top Clips
        </h3>

        <div className="space-y-5">
          {clips.map((clip, i) => (
            <div key={i} className="flex gap-4">
              <div
                className={clsx(
                  "w-1 rounded-full shrink-0",
                  clip.score >= 0.7
                    ? "bg-primary"
                    : clip.score >= 0.5
                      ? "bg-secondary"
                      : "bg-outline-variant",
                )}
              />
              <div className="min-w-0 flex-1">
                {renderClipContent(clip, i)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Mobile: separate cards per clip */}
      <div className="flex flex-col gap-3 lg:hidden">
        <h3 className="text-label-sm text-on-surface-variant uppercase tracking-widest px-1">
          Top Clips
        </h3>

        {clips.map((clip, i) => (
          <div
            key={i}
            className={clsx(
              "glass-panel rounded-xl p-4 flex gap-4 items-start",
              "active:scale-[0.98] transition-transform",
            )}
          >
            <div
              className={clsx(
                "w-10 h-10 rounded-lg flex items-center justify-center shrink-0",
                clip.score >= 0.7
                  ? "bg-primary-container/20"
                  : clip.score >= 0.5
                    ? "bg-tertiary-container/20"
                    : "bg-surface-container-highest",
              )}
            >
              <Film
                className={clsx("w-5 h-5", scoreColor(clip.score))}
              />
            </div>

            <div className="flex flex-col gap-1 min-w-0 flex-1">
              {renderClipContent(clip, i)}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
