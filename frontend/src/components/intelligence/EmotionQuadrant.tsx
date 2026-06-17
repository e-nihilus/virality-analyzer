import clsx from "clsx";

interface EmotionQuadrantProps {
  valence?: number;
  arousal?: number;
  emotion?: string;
  intensity?: number | null;
  timestamp?: string;
  isPlaying?: boolean;
  allowDemoFallback?: boolean;
}

export default function EmotionQuadrant({
  valence,
  arousal,
  emotion,
  intensity,
  timestamp,
  isPlaying = true,
  allowDemoFallback = false,
}: EmotionQuadrantProps) {
  const displayValence = valence ?? (allowDemoFallback ? 0.72 : null);
  const displayArousal = arousal ?? (allowDemoFallback ? 0.78 : null);
  const displayEmotion = emotion ?? (allowDemoFallback ? "Surprise" : "No disponible");
  const displayIntensity = intensity ?? (allowDemoFallback ? displayArousal : null);

  if (displayValence == null || displayArousal == null || displayIntensity == null) {
    return (
      <div className="relative w-full aspect-square rounded-xl overflow-hidden bg-surface-container-low border border-outline-variant/10 flex items-center justify-center text-label-sm text-on-surface-variant">
        Emotion data no disponible
      </div>
    );
  }

  // Map 0-1 values to percentage positions with padding (10% inset)
  const padding = 10;
  const range = 100 - padding * 2;
  const left = padding + displayValence * range;
  const bottom = padding + displayArousal * range;

  return (
    <div
      className={clsx(
        "relative w-full aspect-square rounded-xl overflow-hidden",
        "bg-surface-container-low border border-outline-variant/10",
      )}
    >
      {/* Grid background */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: [
            "linear-gradient(rgba(141,144,160,0.1) 1px, transparent 1px)",
            "linear-gradient(90deg, rgba(141,144,160,0.1) 1px, transparent 1px)",
          ].join(", "),
          backgroundSize: "20% 20%",
        }}
      />

      {/* Center crosshair */}
      <div className="absolute top-1/2 left-0 w-full h-px bg-outline-variant/30" />
      <div className="absolute left-1/2 top-0 h-full w-px bg-outline-variant/30" />

      {/* Axis labels */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 text-label-sm text-on-surface-variant opacity-50">
        HIGH AROUSAL
      </div>
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-label-sm text-on-surface-variant opacity-50">
        LOW AROUSAL
      </div>
      <div className="absolute left-4 top-1/2 -translate-y-1/2 -rotate-90 text-label-sm text-on-surface-variant opacity-50">
        NEGATIVE VALENCE
      </div>
      <div className="absolute right-4 top-1/2 -translate-y-1/2 rotate-90 text-label-sm text-on-surface-variant opacity-50">
        POSITIVE VALENCE
      </div>

      {/* Quadrant corner labels */}
      <div className="absolute top-[15%] right-[15%] text-center">
        <span className="text-primary font-bold text-label-sm block">
          Exhilaration
        </span>
        <div className="w-24 h-24 bg-primary/10 rounded-full blur-2xl absolute -top-4 -left-4" />
      </div>
      <div className="absolute top-[20%] left-[20%] text-center opacity-40">
        <span className="text-on-surface-variant text-label-sm block">
          Anger
        </span>
      </div>
      <div className="absolute bottom-[15%] left-[20%] text-center opacity-40">
        <span className="text-on-surface-variant text-label-sm block">
          Depression
        </span>
      </div>
      <div className="absolute bottom-[15%] right-[15%] text-center opacity-40">
        <span className="text-on-surface-variant text-label-sm block">
          Calm
        </span>
      </div>

      {/* Active data point */}
      <div
        className="absolute z-10"
        style={{
          left: `${left}%`,
          bottom: `${bottom}%`,
          transform: "translate(-50%, 50%)",
        }}
      >
        <div className="relative">
          {/* Glowing dot */}
          <div className="w-4 h-4 bg-primary rounded-full shadow-[0_0_20px_rgba(180,197,255,0.8)]" />

          {/* Pulsing ring */}
          <div
            className="absolute -inset-4 bg-primary/20 rounded-full"
            style={{
              animation: isPlaying ? "pulse-ring 3s cubic-bezier(0.4,0,0.6,1) infinite" : "none",
            }}
          />

          {/* Tooltip */}
          <div className="absolute top-6 left-6 glass-panel p-3 rounded-lg border border-primary/30 w-40">
            <span className="block font-bold text-primary">{displayEmotion}</span>
            <span className="block text-label-sm text-on-surface-variant">
              Intensity: {displayIntensity.toFixed(2)}
            </span>
            {timestamp && (
              <span className="block text-label-sm text-on-surface-variant">
                {timestamp}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
