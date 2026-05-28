import { useCallback, useRef, useState } from "react";
import clsx from "clsx";

interface TimelineMarker {
  position: number;
  color?: string;
  label?: string;
}

interface TimelineScrubberProps {
  progress: number;
  markers?: TimelineMarker[];
  onSeek?: (progress: number) => void;
  className?: string;
}

export default function TimelineScrubber({
  progress,
  markers,
  onSeek,
  className,
}: TimelineScrubberProps) {
  const barRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const [dragProgress, setDragProgress] = useState(0);

  const getProgress = useCallback(
    (clientX: number) => {
      if (!barRef.current) return 0;
      const rect = barRef.current.getBoundingClientRect();
      return Math.min(Math.max((clientX - rect.left) / rect.width, 0), 1);
    },
    [],
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!onSeek) return;
      e.preventDefault();
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      const pos = getProgress(e.clientX);
      setDragging(true);
      setDragProgress(pos);
      onSeek(pos);
    },
    [onSeek, getProgress],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!dragging || !onSeek) return;
      const pos = getProgress(e.clientX);
      setDragProgress(pos);
      onSeek(pos);
    },
    [dragging, onSeek, getProgress],
  );

  const handlePointerUp = useCallback(() => {
    setDragging(false);
  }, []);

  const displayProgress = dragging ? dragProgress : progress;
  const pct = Math.min(Math.max(displayProgress, 0), 1) * 100;

  return (
    <div
      ref={barRef}
      className={clsx(
        "relative h-2 bg-white/20 rounded-full cursor-pointer group/scrubber touch-none",
        className,
      )}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      {/* Progress fill */}
      <div
        className="absolute inset-y-0 left-0 bg-primary rounded-full"
        style={{ width: `${pct}%` }}
      />

      {/* Markers */}
      {markers?.map((marker, i) => (
        <div
          key={i}
          className="absolute top-1/2 -translate-y-1/2 w-2 h-2 rounded-full"
          style={{
            left: `${marker.position * 100}%`,
            backgroundColor: marker.color ?? "var(--color-secondary)",
          }}
          title={marker.label}
        />
      ))}

      {/* Draggable handle */}
      <div
        className={clsx(
          "absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 rounded-full bg-white shadow-md transition-opacity",
          dragging ? "opacity-100 scale-110" : "opacity-0 group-hover/scrubber:opacity-100",
        )}
        style={{ left: `${pct}%` }}
      />
    </div>
  );
}
