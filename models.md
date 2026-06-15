# Modelos de IA — Qué analizan y dónde se reflejan en la web

## Resumen visual rápido

```
Video subido
  │
  ├─► OpenCV ──────────── frame_diffs, brightness ──────────────────► Timeline ──► Engagement Graph
  ├─► YOLOv8n ─────────── detection_density por frame ─────────────► Timeline (virality +12%)
  ├─► DeepFace ────────── valence/arousal per-frame (circumplex) ──► Timeline (arousal 60%, valence 70%)
  │                       + emoción dominante global ──────────────► Emotion Quadrant + Esfera
  ├─► VideoMAE ────────── action recognition ──────────────────────► MetricCard (action score)
  ├─► Qwen2.5 ─────────── insights en lenguaje natural ───────────► Insights Panel
  ├─► librosa (audio) ──── energía, silencios ─────────────────────► Timeline ──► Engagement Graph
  └─► Whisper ─────────── transcripción + hooks ───────────────────► Transcript Panel
```

---

## 1. OpenCV — Señales visuales base

| | |
|---|---|
| **Librería** | OpenCV (`cv2`) |
| **Qué analiza** | Cada frame muestreado del video (1 por segundo) |
| **Qué produce** | `frame_diffs` (movimiento entre frames) y `brightness` (brillo medio) |
| **Dónde se refleja** | Son la base de **todo**. Alimentan `build_timeline()` que genera los valores `virality`, `arousal`, `valence` y `retention` por segundo. Estos datos aparecen en: |
| | • **Engagement Graph** — la curva SVG de arousal/retention |
| | • **Esfera 3D** — regiones virality, arousal, valence, retention |
| | • **Virality Score** — el porcentaje grande (promedio de `virality`) |
| **Archivos** | `backend/app/processing/frame_extractor.py` |
| | `backend/app/ai_services/visual_analyzer.py` → `HeuristicVisualAnalyzer` |

---

## 2. YOLOv8n — Detección de objetos (Fase 14.1)

| | |
|---|---|
| **Modelo** | `yolov8n.pt` (YOLOv8-nano, ~6MB, se descarga en primer uso) |
| **Librería** | `ultralytics` |
| **Qué analiza** | Cada frame muestreado del video. Detecta objetos reales: personas, coches, animales, comida, etc. |
| **Qué produce** | Lista de detecciones por frame: |
| | • `frame_index` — en qué frame se encontró |
| | • `class_name` — tipo de objeto (person, car, dog, cup...) |
| | • `confidence` — confianza del modelo (filtrado ≥ 0.4) |
| | • `bbox` — coordenadas de la caja [x1, y1, x2, y2] |
| **Dónde se refleja** | Las detecciones se almacenan en `VisualAnalysis.detections`. Internamente enriquecen el análisis visual. Los `frame_diffs` y `brightness` que se calculan junto con YOLO siguen alimentando: |
| | • **Esfera 3D** — regiones `virality` y `pacing` reaccionan a la actividad visual |
| | • **Engagement Graph** — la curva refleja la actividad detectada |
| **Env var** | `VISUAL_ANALYZER_PROVIDER=yolo` |
| **Fallback** | Si YOLO falla → solo datos heurísticos (OpenCV) |
| **Archivos** | `backend/app/ai_services/visual_analyzer.py` → `YoloVisualAnalyzer` |

---

## 3. DeepFace — Análisis facial de emociones (Fase 14.2)

| | |
|---|---|
| **Modelo** | DeepFace con backend por defecto (VGG-Face / Facenet según config) |
| **Librería** | `deepface` |
| **Qué analiza** | Frames muestreados cada 2 segundos. Busca caras y clasifica la expresión facial dominante. |
| **Qué produce** | Una emoción dominante para el video completo, mapeada al vocabulario de la app: |
| | • DeepFace `happy` → **Joy** |
| | • DeepFace `sad` → **Sadness** |
| | • DeepFace `angry` / `fear` / `disgust` → **Tension** |
| | • DeepFace `surprise` → **Surprise** |
| | • DeepFace `neutral` → **Neutral** |
| | También puede producir **Excitement** (vía heurístico si arousal + valence altos) |
| **Dónde se refleja** | |
| | • **Emotion Quadrant** — el punto brillante en el grid valence/arousal muestra la emoción. El label (ej. "Surprise") y la posición en el cuadrante (Exhilaration, Anger, Calm, Depression) dependen de la emoción detectada. |
| | • **Esfera 3D** — la región `emotion` (color verde lima) cambia de intensidad según la emoción. Usa un mapa de intensidades: Anger=0.9, Surprise=0.85, Fear=0.8, Joy=0.75, Disgust=0.7, Sadness=0.6, Neutral=0.3. |
| | • **Virality Score header** — el título "Active Analysis" muestra la emoción dominante como subtítulo. |
| | • **Insights Panel** — los insights del explanation engine usan `dominant_emotion` para generar consejos sobre el arco emocional. |
| **Env var** | `EMOTION_ANALYZER_PROVIDER=deepface` |
| **Fallback** | Si no hay caras o DeepFace falla → calcula emoción desde promedios de arousal/valence del timeline |
| **Archivos** | `backend/app/ai_services/emotion_analyzer.py` → `DeepFaceEmotionAnalyzer` |

---

## 4. VideoMAE — Reconocimiento de acciones (Fase 14.3)

| | |
|---|---|
| **Modelo** | `MCG-NJU/videomae-base-finetuned-kinetics` (~350MB, HuggingFace) |
| **Librería** | `torch` + `transformers` |
| **Qué analiza** | 16 frames uniformemente distribuidos del video completo. Clasifica qué tipo de acción humana ocurre usando 400 clases de Kinetics-400 (bailar, cocinar, saltar, hablar, etc.). |
| **Qué produce** | |
| | • `action_score` — confianza (0-1) de la predicción top |
| | • `label` — nombre de la acción reconocida (ej. "playing basketball") |
| **Dónde se refleja** | |
| | • **`action_recognition_score`** en el JSON — campo dedicado en `AnalysisResult`. Solo aparece si temporal está habilitado. |
| | • **MetricCard** — se puede mostrar como tarjeta con el score de acción. |
| | • **Esfera 3D** — indirectamente contribuye al pacing y actividad general del video. |
| **Env vars** | `ENABLE_TEMPORAL_ANALYSIS=true` + `TEMPORAL_ANALYZER_PROVIDER=videomae` |
| **Fallback** | Si VideoMAE falla → calcula score como ratio de frames con virality > 0.55 |
| **Archivos** | `backend/app/ai_services/temporal_analyzer.py` → `VideoMAETemporalAnalyzer` |

---

## 5. Qwen2.5-1.5B-Instruct — Explicaciones con LLM (Fase 14.4)

| | |
|---|---|
| **Modelo** | `Qwen/Qwen2.5-1.5B-Instruct` (~3GB, HuggingFace) |
| **Librería** | `torch` + `transformers` |
| **Qué analiza** | No analiza el video directamente. Recibe un resumen estructurado de métricas: virality score, retention, duración, emoción dominante, y top clips. Con eso genera texto. |
| **Qué produce** | 3 insights accionables en lenguaje natural, cada uno con: |
| | • `title` — título corto (ej. "Weak Opening Hook") |
| | • `description` — explicación detallada del hallazgo |
| | • `action` — recomendación concreta para mejorar |
| | • `severity` — high / medium / low |
| **Dónde se refleja** | |
| | • **Insights Panel (desktop)** — tarjeta "AI Insights & Hooks" con barras de color por severidad: |
| |   - 🟣 `high` → barra primaria (púrpura) + icono ✨ |
| |   - 🟠 `medium` → barra secundaria + icono 🧠 |
| |   - ⚪ `low` → barra gris + icono 🔒 |
| | • **Insights Panel (mobile)** — tarjetas individuales con iconos de severidad |
| | • Cada insight muestra opcionalmente un timestamp (`T+0:12`) y una acción recomendada con icono 💡 |
| **IMPORTANTE** | Qwen **nunca** modifica los scores de viralidad. Solo genera texto explicativo. Los números siempre vienen de los módulos heurísticos. |
| **Env var** | `EXPLANATION_PROVIDER=qwen` |
| **Fallback** | Si el LLM genera texto no parseable → usa el motor de reglas heurístico (`explanation_engine.py`) |
| **Archivos** | `backend/app/ai_services/explanation_generator.py` → `QwenExplanationGenerator` |

---

## 6. librosa — Análisis de audio (opcional)

| | |
|---|---|
| **Librería** | `librosa` |
| **Qué analiza** | El audio extraído del video (WAV) |
| **Qué produce** | |
| | • `rms_energy` — energía sonora por intervalo |
| | • `silence_mask` — dónde hay silencios |
| | • `energy_change` — cambios bruscos de volumen |
| **Dónde se refleja** | Se fusiona en el **Timeline**. Los cambios de energía y silencios afectan los valores de `arousal` y `virality` de cada `TimelineEntry`. Esto impacta: |
| | • **Engagement Graph** — la curva refleja picos de audio |
| | • **Esfera 3D** — la región `arousal` reacciona al audio |
| **Archivos** | `backend/app/ai_services/audio_analyzer.py` |

---

## 7. Whisper — Transcripción de voz (opcional)

| | |
|---|---|
| **Modelo** | OpenAI Whisper |
| **Librería** | `openai-whisper` |
| **Qué analiza** | El audio del video — speech-to-text |
| **Qué produce** | |
| | • `segments[]` — fragmentos de texto con timestamps (start, end, text) |
| | • `full_text` — transcripción completa |
| | • `hooks[]` — text hooks detectados con tipo, timestamp y confianza |
| **Tipos de hooks** | `curiosity_gap`, `urgency`, `conflict`, `question`, `command`, `surprise` |
| **Dónde se refleja** | |
| | • **Transcript Panel** — muestra cada segmento sincronizado con el playback del video, resaltando el segmento activo. Los hooks aparecen como badges con su tipo. |
| | • **Insights Panel** — los hooks detectados generan insights adicionales que se añaden a la lista. |
| **Archivos** | `backend/app/ai_services/speech_analyzer.py` |
| | `backend/app/ai_services/text_hook_analyzer.py` |

---

## Elementos visuales de la web y qué datos consumen

### 🔮 Esfera 3D (`BrainSphere` / `MetricsCanvas`)

La esfera tiene 7 regiones que brillan según las métricas en tiempo real:

| Región | Color | Dato que consume | Fuente |
|---|---|---|---|
| Virality | Rosa (`#FF00E5`) | `timeline[t].virality` | OpenCV + YOLO |
| Arousal | Naranja (`#FF3D00`) | `timeline[t].arousal` | OpenCV + librosa |
| Valence | Cyan (`#00F2FF`) | `timeline[t].valence` | OpenCV + librosa |
| Retention | Rosa (`#FF00E5`) | `timeline[t].retention` | OpenCV + librosa |
| Emotion | Verde (`#14FF00`) | `dominant_emotion` → intensity map | DeepFace |
| Hook | Ámbar (`#FFD600`) | Promedio virality primeros 5s | OpenCV |
| Pacing | Índigo (`#AD00FF`) | Densidad de labels en timeline | OpenCV |

La esfera se actualiza segundo a segundo según `currentTime` del reproductor de video.

### 📊 Engagement Graph (`EngagementGraph`)

- **Curva SVG** — dibuja `arousal` (o `virality`/`retention`) de cada `TimelineEntry`
- **Retention %** — muestra `retention_score` (promedio del timeline)
- **Rewatches** — muestra `rewatch_factor` (peak/avg virality)
- **Playhead** — línea vertical que sigue `currentTime`
- **Peak indicator** — punto en el máximo de la curva
- **Datos fuente**: OpenCV + librosa fusionados en `build_timeline()`

### 🎯 Emotion Quadrant (`EmotionQuadrant`)

- **Eje X** — Valence (negativa ← → positiva)
- **Eje Y** — Arousal (bajo ↓ → alto ↑)
- **Punto luminoso** — posición según valence/arousal del timeline actual
- **Label** — muestra `dominant_emotion` (ej. "Surprise")
- **Cuadrantes** — Exhilaration (↗), Anger (↖), Depression (↙), Calm (↘)
- **Datos fuente**: Timeline (valence, arousal) + DeepFace (dominant_emotion)

### 🏆 Virality Score (`ViralityScore`)

- **Porcentaje grande** — `overall_virality_score × 100` (promedio de virality del timeline)
- **Subtítulo** — muestra la emoción dominante como "Active Analysis"
- **Datos fuente**: Promedio del timeline + DeepFace

### 💡 Insights Panel (`InsightsPanel`)

- **Lista de insights** — cada uno con título, descripción, acción recomendada
- **Severidad visual** — barra de color (high=primario, medium=secundario, low=gris)
- **Timestamps** — `T+0:12` clickeable en cada insight
- **Datos fuente**: Qwen2.5 LLM (o motor de reglas heurístico como fallback)

### 🎬 Top Clips (`ClipList`)

- **3 mejores segmentos** — start/end timestamps, score %, razones
- **Botones Export/Download** — recorta el clip con FFmpeg
- **Score color** — ≥70% primario, ≥50% secundario, <50% gris
- **Datos fuente**: `rank_clips()` sobre el timeline (OpenCV + librosa)

### 📝 Transcript Panel (`TranscriptPanel`)

- **Segmentos de texto** — sincronizados con el playback, se resaltan al reproducir
- **Hook badges** — etiquetas de tipo (Curiosity Gap, Urgency, etc.)
- **Datos fuente**: Whisper (transcripción) + text_hook_analyzer (detección de hooks)

### 📐 MetricCard (genérico)

- Tarjeta reutilizable para mostrar métricas individuales
- Se usa para dominant emotion, attention duration, action score, etc.
- **Datos fuente**: Cualquier campo del `AnalysisResult`

---

## Variables de entorno para activar cada modelo

```bash
# YOLOv8 (detección de objetos)
VISUAL_ANALYZER_PROVIDER=yolo

# DeepFace (emociones faciales)
EMOTION_ANALYZER_PROVIDER=deepface

# VideoMAE (reconocimiento de acciones)
ENABLE_TEMPORAL_ANALYSIS=true
TEMPORAL_ANALYZER_PROVIDER=videomae

# Qwen (insights con LLM)
EXPLANATION_PROVIDER=qwen

# Cache de explicaciones
EXPLANATION_CACHE_ENABLED=true
```

Sin estas variables, todo funciona con heurísticos (OpenCV + reglas).
