/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import { METRICS_LIST, MetricDefinition, MetricState } from "../types";
import { ArrowUpRight, HelpCircle, AlertCircle } from "lucide-react";

interface MetricCardProps {
  currentValues: MetricState;
  onHoverMetric: (key: keyof MetricState | null) => void;
  hoveredMetricKey: keyof MetricState | null;
}

// Creative directors advice based on metrics
const getMetricAdvice = (key: keyof MetricState) => {
  switch (key) {
    case "valence":
      return "Para elevar la positividad, introduce transiciones luminosas, colores cálidos, comedia o resoluciones alegres a las preguntas iniciales.";
    case "virality":
      return "Inserta un concepto abstracto de alta discrepancia ('curiosidad mórbida'), memes fácilmente imitables, o llamadas claras a compartir.";
    case "arousal":
      return "Sube el ritmo con cortes sincopados, cambios bruscos de volumen acústico, efectos de sonido de zoom ('whoosh') y clímax dramáticos.";
    case "pacing":
      return "Acelera el compás recortando respiraciones muertas e introduciendo efectos de cambio visual (jumps) cada 1.5 a 2.5 segundos.";
    case "retention":
      return "Diseña un bucle de preguntas infinito: antes de responder a un enigma de video anterior, introduce la premisa del siguiente segmento secundario.";
    case "emotion":
      return "Utiliza pistas musicales melancólicas en piano solo, pausas de habla dramáticas prolongadas o relatos en primera persona sobre vulnerabilidad.";
    case "hook":
      return "Comienza inmediatamente en el medio de la acción extrema ('In Media Res'), evitando introducciones genéricas del tipo 'hola a todos'.";
    default:
      return "";
  }
};

export default function MetricCard({ currentValues, onHoverMetric, hoveredMetricKey }: MetricCardProps) {
  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col gap-6 shadow-2xl">
      <div>
        <span className="value-tag text-[#14FF00] block mb-0.5 tracking-widest font-semibold">ANALYTICS DICTIONARY</span>
        <h2 className="text-white text-base font-light tracking-tight flex items-center gap-1.5">
          <span>GUÍA DE CREACIÓN Y OPTIMIZACIÓN</span>
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {METRICS_LIST.map((metric: MetricDefinition) => {
          const isSelected = hoveredMetricKey === metric.key;
          const value = currentValues[metric.key];
          
          // Immersive color styles hex mapper
          const customHex = 
            metric.key === "valence" ? "#00F2FF" :
            metric.key === "virality" ? "#FF00E5" :
            metric.key === "arousal" ? "#FF3D00" :
            metric.key === "pacing" ? "#FFD600" :
            metric.key === "retention" ? "#AD00FF" :
            metric.key === "emotion" ? "#14FF00" : "#0057FF";

          return (
            <div
              key={metric.key}
              onMouseEnter={() => onHoverMetric(metric.key)}
              onMouseLeave={() => onHoverMetric(null)}
              className={`p-5 rounded-xl border transition-all duration-300 flex flex-col justify-between group ${
                isSelected
                  ? "bg-white/5 border-white/20 shadow-xl scale-[1.01]"
                  : "bg-white/[0.01] hover:bg-white/[0.03] border-white/5 hover:border-white/10"
              }`}
            >
              <div>
                {/* Metric identification row */}
                <div className="flex items-center justify-between w-full mb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-2 h-2 rounded-full block animate-pulse"
                      style={{
                        backgroundColor: customHex,
                        boxShadow: `0 0 10px ${customHex}`
                      }}
                    />
                    <h3 className="text-xs font-medium text-zinc-300 group-hover:text-white transition-colors">
                      {metric.name}
                    </h3>
                  </div>
                  
                  <span className="font-mono text-[9px] tracking-wider text-zinc-400 bg-white/5 px-2 py-0.5 rounded border border-white/5">
                    {value}% cargado
                  </span>
                </div>

                <p className="text-zinc-400 text-[11px] leading-relaxed mb-4">
                  {metric.description}
                </p>
              </div>

              {/* Dynamic recommendation footer */}
              <div className="border-t border-white/5 pt-3.5 mt-2 flex flex-col gap-1">
                <span className="font-mono text-[9px] text-zinc-500 uppercase tracking-widest flex items-center gap-1 font-medium">
                  <AlertCircle className="w-3 h-3 text-zinc-500" />
                  <span>Recomendación Creativa</span>
                </span>
                <p className="text-zinc-300 text-[10px] leading-relaxed">
                  {getMetricAdvice(metric.key)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
