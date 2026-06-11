/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from "react";
import { MetricState, MetricPreset, PRESETS } from "./types";
import MetricsCanvas from "./components/MetricsCanvas";
import ControlPanel from "./components/ControlPanel";
import PresetsPanel from "./components/PresetsPanel";
import MetricCard from "./components/MetricCard";
import { Info, HelpCircle, Sparkles, Sliders, Play, Settings2, Github } from "lucide-react";

const INITIAL_METRICS: MetricState = {
  valence: 75,
  virality: 70,
  arousal: 60,
  pacing: 50,
  retention: 80,
  emotion: 65,
  hook: 85,
};

export default function App() {
  const [metrics, setMetrics] = useState<MetricState>(INITIAL_METRICS);
  const [activePresetName, setActivePresetName] = useState<string | null>(null);
  const [autoPlayBeat, setAutoPlayBeat] = useState<boolean>(true);
  const [hoveredMetricKey, setHoveredMetricKey] = useState<keyof MetricState | null>(null);

  // Animation controller for sliding sliders transition interpolation
  const animationRef = useRef<number | null>(null);
  const targetMetricsRef = useRef<MetricState | null>(null);

  // Clean up any running transitions on unmount
  useEffect(() => {
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, []);

  // Set metric value individually and clear active preset highlight
  const handleMetricChange = (key: keyof MetricState, value: number) => {
    // If a transition is currently running, cancel it so user takes override control
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    setActivePresetName(null);
    setMetrics((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  // Interpolate state smoothly from current state to target preset state
  const animateToMetrics = (targetValues: MetricState, presetName: string) => {
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    targetMetricsRef.current = targetValues;
    setActivePresetName(presetName);

    const step = () => {
      if (!targetMetricsRef.current) return;

      let allDone = true;
      setMetrics((prev) => {
        const updated = { ...prev };
        const keys = Object.keys(prev) as Array<keyof MetricState>;

        keys.forEach((key) => {
          const current = prev[key];
          const target = targetMetricsRef.current![key];
          const diff = target - current;

          // Smooth exponential ease-out interpolation
          if (Math.abs(diff) > 0.4) {
            updated[key] = Math.round(current + diff * 0.12);
            allDone = false;
          } else {
            updated[key] = target;
          }
        });

        if (allDone) {
          if (animationRef.current) cancelAnimationFrame(animationRef.current);
          animationRef.current = null;
          return targetValues;
        }

        return updated;
      });

      if (!allDone) {
        animationRef.current = requestAnimationFrame(step);
      }
    };

    animationRef.current = requestAnimationFrame(step);
  };

  const handleSelectPreset = (preset: MetricPreset) => {
    animateToMetrics(preset.values, preset.name);
  };

  // Helper code to randomize metrics
  const handleRandomize = () => {
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    setActivePresetName(null);

    const randomized: MetricState = {
      valence: Math.floor(Math.random() * 85) + 15,
      virality: Math.floor(Math.random() * 85) + 15,
      arousal: Math.floor(Math.random() * 85) + 15,
      pacing: Math.floor(Math.random() * 85) + 15,
      retention: Math.floor(Math.random() * 85) + 15,
      emotion: Math.floor(Math.random() * 85) + 15,
      hook: Math.floor(Math.random() * 85) + 15,
    };

    animateToMetrics(randomized, "Mutación Aleatoria");
  };

  return (
    <div className="min-h-screen bg-[#030303] text-[#F5F5F7] flex flex-col font-sans selection:bg-[#00F2FF]/10 selection:text-[#00F2FF]">
      
      {/* Premium Apple-Style Navigation Header */}
      <header className="border-b border-white/5 bg-black/40 backdrop-blur-md sticky top-0 z-50 transition-all">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Hologram aesthetic floating icon */}
            <div className="relative w-7 h-7 rounded-lg overflow-hidden flex items-center justify-center border border-[#00F2FF]/30 bg-black shadow-[0_0_15px_rgba(0,242,255,0.2)]">
              <div className="absolute inset-x-0 bottom-0 top-0 bg-gradient-to-tr from-[#00F2FF] via-[#AD00FF] to-[#FF3D00] animate-[spin_6s_linear_infinite] opacity-60" />
              <div className="w-5 h-5 rounded-md bg-zinc-950 absolute flex items-center justify-center font-mono text-[10px] text-[#00F2FF] font-bold">
                Σ
              </div>
            </div>

            <div>
              <span className="value-tag text-[#00F2FF] text-[9px] font-semibold block uppercase">
                Análisis Espectral WebGL
              </span>
              <h1 className="text-sm font-light tracking-tight text-white uppercase sm:text-base">
                Metrics Shader Orb
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-zinc-400">
            <span className="hidden sm:inline font-mono text-[9px] text-zinc-600 tracking-wider">
              ESTADO // STANDALONE_READY
            </span>
            <div className="w-1.5 h-1.5 rounded-full bg-[#14FF00] animate-pulse" />
            <span className="text-zinc-800 hidden sm:inline">|</span>
            <div className="flex items-center gap-1.5 bg-white/5 px-2.5 py-1 rounded-full border border-white/5">
              <Sparkles className="w-3 h-3 text-[#FFD600]" />
              <span className="font-mono text-[10px] text-zinc-300">Immersive UI Active</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container Layout */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 flex flex-col gap-6">
        
        {/* Upper Grid: 3D Viewport on Left, Parameters Panel on Right */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* WebGL Viewport Container (Col: 7/12) */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            
            <div className="flex items-center justify-between">
              <div>
                <span className="value-tag text-zinc-500 block mb-0.5 font-semibold">
                  Cúpula de Visualización
                </span>
                <h2 className="text-white font-light text-lg tracking-tight">Cruce Dimensional Shaders</h2>
              </div>
              
              {/* Active preset badge status line */}
              {activePresetName && (
                <div className="flex items-center gap-1.5 bg-white/5 px-3 py-1 rounded-full border border-[#00F2FF]/20 text-[9px] font-mono tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#00F2FF] animate-pulse" />
                  <span className="text-[#00F2FF]">PRESET // {activePresetName.toUpperCase()}</span>
                </div>
              )}
            </div>

            {/* Canvas Viewport */}
            <MetricsCanvas
              metrics={metrics}
              autoPlayBeat={autoPlayBeat}
              hoveredMetricKey={hoveredMetricKey}
            />

            {/* Quick Metrics visual specs overlay */}
            <div className="glass-panel border border-white/5 rounded-xl p-4 flex flex-wrap gap-4 items-center justify-between text-xs sm:divide-x sm:divide-white/5 shadow-xl">
              <div className="flex-1 min-w-[120px] flex flex-col gap-0.5">
                <span className="text-zinc-500 font-mono text-[9px] uppercase tracking-widest font-semibold">Potencia de Entrada</span>
                <span className="text-white font-mono font-medium text-sm">
                  {Math.round((metrics.valence + metrics.virality + metrics.arousal + metrics.pacing + metrics.retention + metrics.emotion + metrics.hook) / 7)}%
                </span>
              </div>
              <div className="flex-1 min-w-[120px] sm:pl-4 flex flex-col gap-0.5">
                <span className="text-zinc-500 font-mono text-[9px] uppercase tracking-widest font-semibold">Tasa de Distorsión</span>
                <span className="text-white font-mono font-medium text-sm">
                  {metrics.arousal > 60 || metrics.hook > 60 ? "Turbulencia Alta" : "Flujo Laminar Regular"}
                </span>
              </div>
              <div className="flex-1 min-w-[120px] sm:pl-4 flex flex-col gap-0.5">
                <span className="text-zinc-500 font-mono text-[9px] uppercase tracking-widest font-semibold">Complejidad Cromática</span>
                <span className="text-[#14FF00] font-mono font-medium text-sm">Vibración Activa</span>
              </div>
            </div>

          </div>

          {/* Interactive Parameters Sliders Control Panel (Col: 5/12) */}
          <div className="lg:col-span-5 flex flex-col gap-4 h-full">
            <ControlPanel
              metrics={metrics}
              onMetricChange={handleMetricChange}
              onHoverMetric={setHoveredMetricKey}
              autoPlayBeat={autoPlayBeat}
              onToggleBeat={() => setAutoPlayBeat(!autoPlayBeat)}
              onRandomize={handleRandomize}
            />
          </div>

        </div>

        {/* Middle Section: Storyboarding structure (PresetsPanel) */}
        <div>
          <PresetsPanel
            onSelectPreset={handleSelectPreset}
            activePresetName={activePresetName}
            currentValues={metrics}
          />
        </div>

        {/* Lower Section: Educational optimization dictionary guide (MetricCard) */}
        <div className="mb-4">
          <MetricCard
            currentValues={metrics}
            onHoverMetric={setHoveredMetricKey}
            hoveredMetricKey={hoveredMetricKey}
          />
        </div>

      </main>

      {/* Footer Design Accent */}
      <footer className="border-t border-white/5 bg-[#030303] py-8 text-center text-xs text-zinc-500 mt-auto">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-1 leading-relaxed text-left">
            <span>© 2026 Metrics Shader Orb.</span>
            <span className="text-zinc-800">|</span>
            <span className="text-zinc-600">Unión de matemáticas avanzadas, filtros de ruido tridimensionales y optimización orgánica.</span>
          </div>
          <div className="flex items-center gap-4 text-zinc-600 font-mono text-[9px]">
            <span>TSL / GLSL PIPELINE</span>
            <span>•</span>
            <span>THREEJS REACT CONTEXT</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
