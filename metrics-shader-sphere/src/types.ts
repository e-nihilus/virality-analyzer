/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export interface MetricState {
  valence: number;
  virality: number;
  arousal: number;
  pacing: number;
  retention: number;
  emotion: number;
  hook: number;
}

export interface MetricDefinition {
  key: keyof MetricState;
  name: string;
  color: string; // Tailwind color name or hex
  hex: string;
  description: string;
  visualBehavior: string;
  shortLabel: string;
}

export interface MetricPreset {
  name: string;
  description: string;
  values: MetricState;
  icon: string;
}

export const METRICS_LIST: MetricDefinition[] = [
  {
    key: "valence",
    name: "Valence",
    shortLabel: "Val",
    color: "cyan",
    hex: "#0ea5e9",
    description: "Mide el tono emocional general (positividad vs. negatividad) del contenido y cómo influye en el estado de ánimo de la audiencia.",
    visualBehavior: "Expande un resplandor celeste/cian cristalino en el hemisferio derecho."
  },
  {
    key: "virality",
    name: "Virality",
    shortLabel: "Vir",
    color: "pink",
    hex: "#ec4899",
    description: "El potencial de compartibilidad del video. Representa momentos memorables, memes o ideas altamente contagiosas.",
    visualBehavior: "Genera ráfagas de energía magenta y pulsaciones de partículas rápidas."
  },
  {
    key: "arousal",
    name: "Arousal",
    shortLabel: "Aro",
    color: "orange",
    hex: "#f97316",
    description: "Nivel de activación fisiológica y excitación de la atención. Capta la estimulación, el asombro o el impacto de la escena.",
    visualBehavior: "Aumenta la deformación volumétrica, la turbulencia espacial y el tamaño de onda física de la esfera."
  },
  {
    key: "pacing",
    name: "Pacing",
    shortLabel: "Pac",
    color: "lime",
    hex: "#84cc16",
    description: "El ritmo del montaje, velocidad de los cortes dramáticos y entrega del contenido. Regula la aceleración temporal del pulso.",
    visualBehavior: "Acelera la velocidad de rotación, la oscilación del campo de ruido y la frecuencia de crestas."
  },
  {
    key: "retention",
    name: "Retention",
    shortLabel: "Ret",
    color: "blue",
    hex: "#3b82f6",
    description: "Capacidad de retener a la audiencia segundo a segundo. Un valor alto refleja solidez narrativa y menor tasa de abandono.",
    visualBehavior: "Fortalece un núcleo interno azul profundo, denso, estable, que sostiene el esqueleto de la esfera."
  },
  {
    key: "emotion",
    name: "Emotion",
    shortLabel: "Emo",
    color: "purple",
    hex: "#8b5cf6",
    description: "Profundidad dramática y conexión afectiva. Refleja giros de empatía, nostalgia o melancolía que enganchan emocionalmente.",
    visualBehavior: "Crea ondas magmáticas moradas lentas cruzando desde la base inferior de la estructura."
  },
  {
    key: "hook",
    name: "Hook",
    shortLabel: "Hok",
    color: "red",
    hex: "#ef4444",
    description: "La efectividad de retención en los primeros 3 segundos. Determina si el espectador decide deslizar o quedarse.",
    visualBehavior: "Genera crestas espinosas afiladas e intensos filamentos carmesí centelleantes en los bordes."
  }
];

export const PRESETS: MetricPreset[] = [
  {
    name: "Epic Viral Trend",
    description: "Alto nivel de enganche inicial, ritmo frenético y viralidad explosiva. Ideal para TikToks o Reels de máxima energía.",
    values: {
      valence: 85,
      virality: 95,
      arousal: 90,
      pacing: 88,
      retention: 65,
      emotion: 50,
      hook: 98
    },
    icon: "Zap"
  },
  {
    name: "Deep Narrative Movie",
    description: "Ritmo pausado, alta retención y profunda carga emocional. Perfecto para documentales o historias cinemáticas.",
    values: {
      valence: 45,
      virality: 60,
      arousal: 40,
      pacing: 35,
      retention: 92,
      emotion: 95,
      hook: 70
    },
    icon: "Film"
  },
  {
    name: "Hype Product Launch",
    description: "Alta energía, positividad extrema y gran gancho. Diseñado para un anuncio promocional innovador de Apple.",
    values: {
      valence: 90,
      virality: 80,
      arousal: 85,
      pacing: 70,
      retention: 75,
      emotion: 65,
      hook: 90
    },
    icon: "Sparkles"
  },
  {
    name: "Educational Deep-Dive",
    description: "Retención constante con ritmo medio. Concentración pura y optimización de contenido de alto valor.",
    values: {
      valence: 70,
      virality: 55,
      arousal: 50,
      pacing: 55,
      retention: 88,
      emotion: 42,
      hook: 75
    },
    icon: "BookOpen"
  },
  {
    name: "Emotional Rollercoaster",
    description: "Carga emotiva inestable para provocar empatía y alta tracción narrativa de clímax.",
    values: {
      valence: 60,
      virality: 78,
      arousal: 75,
      pacing: 65,
      retention: 80,
      emotion: 88,
      hook: 82
    },
    icon: "Heart"
  }
];
