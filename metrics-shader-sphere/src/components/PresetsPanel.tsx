/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { PRESETS, MetricPreset, MetricState } from "../types";
import { Zap, Film, Sparkles, BookOpen, Heart, Eye } from "lucide-react";

interface PresetsPanelProps {
  onSelectPreset: (preset: MetricPreset) => void;
  activePresetName: string | null;
  currentValues: MetricState;
}

// Icon mapper for presets
const getPresetIcon = (iconName: string, className: string) => {
  switch (iconName) {
    case "Zap":
      return <Zap className={className} />;
    case "Film":
      return <Film className={className} />;
    case "Sparkles":
      return <Sparkles className={className} />;
    case "BookOpen":
      return <BookOpen className={className} />;
    case "Heart":
      return <Heart className={className} />;
    default:
      return <Sparkles className={className} />;
  }
};

export default function PresetsPanel({ onSelectPreset, activePresetName, currentValues }: PresetsPanelProps) {
  // Check if currentValues exactly matches a preset, to highlight it (even if tweaked, we might clear it)
  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col gap-4 shadow-2xl">
      <div>
        <span className="value-tag text-[#AD00FF] block mb-0.5 tracking-widest font-semibold">PRESETS DE CONFIGURACIÓN</span>
        <h2 className="text-white text-base font-light tracking-tight">PREAJUSTES DE CONTENIDO</h2>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 mt-2">
        {PRESETS.map((preset: MetricPreset) => {
          const isActive = activePresetName === preset.name;
          
          return (
            <button
              key={preset.name}
              onClick={() => onSelectPreset(preset)}
              className={`flex flex-col text-left p-4 rounded-xl border transition-all relative overflow-hidden group ${
                isActive
                  ? "bg-white/5 border-[#00F2FF]/30 shadow-[0_0_20px_rgba(0,242,255,0.06)] text-white"
                  : "bg-white/[0.015] hover:bg-white/[0.04] border-white/5 hover:border-white/10 text-zinc-300"
              }`}
            >
              {/* Top ambient glow on hover or active */}
              <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#00F2FF]/40 to-transparent transition-opacity ${
                isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"
              }`} />

              <div className="flex items-center justify-between w-full mb-2">
                <div className={`p-1.5 rounded-lg transition ${
                  isActive ? "bg-[#00F2FF]/10 text-[#00F2FF]" : "bg-white/5 text-zinc-400 group-hover:text-white"
                }`}>
                  {getPresetIcon(preset.icon, "w-3.5 h-3.5")}
                </div>
                
                {/* Visual tiny indicator index */}
                <span className="font-mono text-[9px] text-zinc-500 group-hover:text-zinc-400 transition-colors uppercase">
                  profile
                </span>
              </div>

              <h3 className="font-semibold text-xs text-white group-hover:text-[#00F2FF] transition-colors">
                {preset.name}
              </h3>
              
              <p className="text-zinc-400 text-[10px] mt-1 leading-relaxed line-clamp-2">
                {preset.description}
              </p>

              {/* Minimalist values row */}
              <div className="flex items-center gap-1.5 mt-3 border-t border-white/5 pt-2.5 w-full font-mono text-[9px] text-zinc-500 overflow-x-hidden">
                <span title="Hook" className="hover:text-[#0057FF]">HK:{preset.values.hook}%</span>
                <span className="text-zinc-700">•</span>
                <span title="Retention" className="hover:text-[#AD00FF]">RT:{preset.values.retention}%</span>
                <span className="text-zinc-700">•</span>
                <span title="Pacing" className="hover:text-[#FFD600]">PC:{preset.values.pacing}%</span>
              </div>

              {isActive && (
                <div className="absolute top-2 right-2 flex items-center gap-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00F2FF] animate-pulse" />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
