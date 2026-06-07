/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { MetricState, METRICS_LIST, MetricDefinition } from "../types";
import { 
  Smile, 
  Share2, 
  Flame, 
  Activity, 
  Hourglass, 
  Heart, 
  Magnet, 
  Sparkles, 
  Shuffle, 
  Volume2, 
  VolumeX,
} from "lucide-react";

interface ControlPanelProps {
  metrics: MetricState;
  onMetricChange: (key: keyof MetricState, value: number) => void;
  onHoverMetric: (key: keyof MetricState | null) => void;
  autoPlayBeat: boolean;
  onToggleBeat: () => void;
  onRandomize: () => void;
}

// Icon mapper for key metrics
const getMetricIcon = (key: keyof MetricState, className: string) => {
  switch (key) {
    case "valence":
      return <Smile className={className} />;
    case "virality":
      return <Share2 className={className} />;
    case "arousal":
      return <Flame className={className} />;
    case "pacing":
      return <Activity className={className} />;
    case "retention":
      return <Hourglass className={className} />;
    case "emotion":
      return <Heart className={className} />;
    case "hook":
      return <Magnet className={className} />;
    default:
      return <Sparkles className={className} />;
  }
};

// Color style mapping for custom glowing sliders match Immersive UI specification
const getMetricColorStyles = (key: keyof MetricState) => {
  switch (key) {
    case "valence":
      return {
        accent: "text-[#00F2FF]",
        bg: "bg-[#00F2FF]",
        border: "border-[#00F2FF]/20",
        shadow: "shadow-[0_0_15px_rgba(0,242,255,0.4)]",
        rail: "bg-[#00F2FF]/10",
        hex: "#00F2FF"
      };
    case "virality":
      return {
        accent: "text-[#FF00E5]",
        bg: "bg-[#FF00E5]",
        border: "border-[#FF00E5]/20",
        shadow: "shadow-[0_0_15px_rgba(255,0,229,0.4)]",
        rail: "bg-[#FF00E5]/10",
        hex: "#FF00E5"
      };
    case "arousal":
      return {
        accent: "text-[#FF3D00]",
        bg: "bg-[#FF3D00]",
        border: "border-[#FF3D00]/20",
        shadow: "shadow-[0_0_15px_rgba(255,61,0,0.4)]",
        rail: "bg-[#FF3D00]/10",
        hex: "#FF3D00"
      };
    case "pacing":
      return {
        accent: "text-[#FFD600]",
        bg: "bg-[#FFD600]",
        border: "border-[#FFD600]/20",
        shadow: "shadow-[0_0_15px_rgba(255,214,0,0.4)]",
        rail: "bg-[#FFD600]/10",
        hex: "#FFD600"
      };
    case "retention":
      return {
        accent: "text-[#AD00FF]",
        bg: "bg-[#AD00FF]",
        border: "border-[#AD00FF]/25",
        shadow: "shadow-[0_0_15px_rgba(173,0,255,0.4)]",
        rail: "bg-[#AD00FF]/15",
        hex: "#AD00FF"
      };
    case "emotion":
      return {
        accent: "text-[#14FF00]",
        bg: "bg-[#14FF00]",
        border: "border-[#14FF00]/20",
        shadow: "shadow-[0_0_15px_rgba(20,255,0,0.4)]",
        rail: "bg-[#14FF00]/10",
        hex: "#14FF00"
      };
    case "hook":
      return {
        accent: "text-[#0057FF]",
        bg: "bg-[#0057FF]",
        border: "border-[#0057FF]/20",
        shadow: "shadow-[0_0_15px_rgba(0,87,255,0.4)]",
        rail: "bg-[#0057FF]/10",
        hex: "#0057FF"
      };
    default:
      return {
        accent: "text-zinc-400",
        bg: "bg-zinc-500",
        border: "border-zinc-500/20",
        shadow: "shadow-none",
        rail: "bg-zinc-950/40",
        hex: "#71717a"
      };
  }
};

export default function ControlPanel({
  metrics,
  onMetricChange,
  onHoverMetric,
  autoPlayBeat,
  onToggleBeat,
  onRandomize,
}: ControlPanelProps) {
  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col gap-6 shadow-2xl">
      {/* Title & Fast controls */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4">
        <div>
          <span className="value-tag text-[#00F2FF] block mb-0.5 tracking-widest font-semibold">NEURAL CONTROLS</span>
          <h2 className="text-white text-base font-light tracking-tight">PANEL DE PARÁMETROS</h2>
        </div>

        <div className="flex items-center gap-2">
          {/* Audio reactive pulse button */}
          <button
            onClick={onToggleBeat}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-mono tracking-wider transition border ${
              autoPlayBeat 
                ? "bg-cyan-500/10 text-[#00F2FF] border-[#00F2FF]/20 shadow-[0_0_15px_rgba(0,242,255,0.2)]" 
                : "bg-white/5 text-zinc-500 border-white/5 hover:text-zinc-400"
            }`}
            title="Activa modulaciones periódicas simulando ritmos acústicos"
          >
            {autoPlayBeat ? (
              <>
                <Volume2 className="w-3.5 h-3.5 animate-pulse text-[#00F2FF]" />
                <span className="text-[10px] uppercase font-mono tracking-widest font-semibold header-text">PULSO ACTIVO</span>
              </>
            ) : (
              <>
                <VolumeX className="w-3.5 h-3.5 text-zinc-600" />
                <span className="text-[10px] uppercase font-mono tracking-widest font-semibold">PULSO APAGADO</span>
              </>
            )}
          </button>

          {/* Randomizer */}
          <button
            onClick={onRandomize}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-mono tracking-wider uppercase font-semibold text-zinc-400 hover:text-white bg-white/5 hover:bg-white/10 border border-white/5 transition"
            title="Genera métricas aleatorias consistentes"
          >
            <Shuffle className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">MUTAR</span>
          </button>
        </div>
      </div>

      {/* Sliders Container */}
      <div className="flex flex-col gap-5">
        {METRICS_LIST.map((metric: MetricDefinition) => {
          const value = metrics[metric.key];
          const styles = getMetricColorStyles(metric.key);

          // Build elegant linear gradient background style for active track representation
          const backgroundGradient = `linear-gradient(to right, ${styles.hex} ${value}%, rgba(255, 255, 255, 0.08) ${value}%)`;

          return (
            <div
              key={metric.key}
              className="group flex flex-col gap-2 p-2 rounded-xl transition hover:bg-white/[0.015] border border-transparent hover:border-white/5"
              onMouseEnter={() => onHoverMetric(metric.key)}
              onMouseLeave={() => onHoverMetric(null)}
            >
              {/* Slider Header */}
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded-lg bg-white/5 border border-white/5 group-hover:${styles.border} transition-colors`}>
                    {getMetricIcon(metric.key, `w-3.5 h-3.5 ${styles.accent}`)}
                  </div>
                  <div>
                    <span className="text-xs font-light text-zinc-300 group-hover:text-white tracking-wide transition-colors">
                      {metric.name}
                    </span>
                    <span className="font-mono text-[9px] text-zinc-600 ml-1.5 uppercase tracking-widest hidden sm:inline">
                      [{metric.shortLabel}]
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* Percentage bubble styled as Apple monospace value tag */}
                  <span className={`font-mono text-[11px] font-medium tracking-widest ${styles.accent} bg-white/5 px-2 py-0.5 rounded border border-white/5 group-hover:${styles.border} transition-colors`}>
                    {value}%
                  </span>
                </div>
              </div>

              {/* Slider Body with customized custom-slider logic */}
              <div className="relative w-full h-4 flex items-center">
                <input
                  type="range"
                  min="1"
                  max="100"
                  value={value}
                  onChange={(e) => onMetricChange(metric.key, parseInt(e.target.value))}
                  className="custom-slider cursor-pointer"
                  style={{ background: backgroundGradient }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
