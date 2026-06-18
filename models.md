# Modelos de IA — Qué datos manda cada modelo a la interfaz

Fecha de revisión: 2026-06-18

Este documento explica, para cada elemento visible de la web, **de dónde sale su
valor**: qué modelo o fórmula lo produce y por qué campo del `AnalysisResult`
viaja hasta la UI. Ejemplos que se responden aquí: de dónde saca la esfera el
valor de `retention`, cómo se miden las emociones del Engagement Graph, etc.

Conceptos de procedencia que usa la app (`metric_sources[].source_type`):

- **ai** — predicción de un modelo de IA real (DeepFace, CLIP, Qwen, Whisper, VideoMAE).
- **derived** — fórmula compuesta sobre señales reales (no un modelo entrenado).
- **heuristic** — reglas simples sin IA.
- **unavailable** — no se pudo calcular; la UI lo oculta o muestra "No disponible".

En **modo demo** (`source = "demo-mock"`) se permiten valores de relleno. En
**modo uploaded** los valores son reales o se ocultan; nunca se inventan.

---

## Resumen visual del flujo

```
Video subido
  │
  ├─ OpenCV ─────── frame_diffs, brightness (1 frame/seg) ─────┐
  ├─ librosa ────── rms_energy, silence, energy_change ────────┤
  ├─ YOLOv8n ────── detection_density (objetos/personas) ──────┤
  ├─ DeepFace ───── valence/arousal por frame + dominante ─────┤
  │                                                             ▼
  │                                            build_timeline()  →  timeline[]
  │                                            RetentionPredictor →  retention
  │                                                             │
  │   ┌─────────────────────────────────────────────────────────┘
  │   ▼
  │  timeline[] (virality, arousal, valence, retention por segundo)
  │   ├──► Esfera 3D (virality/arousal/valence/retention)
  │   ├──► Engagement Graph (curva de arousal + retención)
  │   ├──► Emotion Quadrant (valence/arousal + emoción)
  │   └──► Virality Score (promedio de virality)
  │
  ├─ CLIP ───────── memorability por segundo ──► rewatch_factor + ranking Top Clips
  ├─ Qwen2.5 ────── insights + razones de clips + clasificación de hooks
  ├─ Whisper ────── transcripción + segmentos ──► Transcript Panel
  └─ VideoMAE ───── action_recognition_score (opcional) ──► MetricCard
```

---

# PARTE A — Qué produce cada modelo

## 1. OpenCV — Señales visuales base (no IA)

| | |
|---|---|
| **Librería** | OpenCV (`cv2`) |
| **Qué analiza** | 1 frame muestreado por segundo (decodifica el vídeo **una sola vez** y reutiliza esos frames para YOLO/DeepFace). |
| **Qué produce** | `frame_diffs` (movimiento entre frames muestreados) y `brightness` (brillo medio). |
| **A dónde va** | Entra en `build_timeline()` y en el `RetentionPredictor`. Es la base de `virality`, `arousal`, `valence` y `retention`. |
| **Procedencia** | No-IA (señal real del vídeo). |
| **Archivos** | `backend/app/processing/frame_extractor.py`, `visual_analyzer.py` → `HeuristicVisualAnalyzer` |

## 2. librosa — Señales de audio (no IA)

| | |
|---|---|
| **Librería** | `librosa` |
| **Qué analiza** | El audio extraído del vídeo (WAV), por intervalos de 1s. |
| **Qué produce** | `rms_energy` (energía sonora), `silence_mask` (silencios), `energy_change` (cambios bruscos de volumen). |
| **A dónde va** | Se fusiona en `build_timeline()` (sube `arousal`/`virality` en picos, baja `retention` en silencios) y es feature del `RetentionPredictor`. |
| **Procedencia** | No-IA (señal real). Activo por defecto (`AUREA_AUDIO_ENABLED=true`). |
| **Archivos** | `backend/app/ai_services/audio_analyzer.py` |

## 3. YOLOv8n — Detección de objetos

| | |
|---|---|
| **Modelo** | `yolov8n.pt` (YOLOv8-nano, ~6 MB) |
| **Qué analiza** | Cada frame muestreado. Detecta personas, animales, coches, comida, etc. |
| **Qué produce** | Detecciones por frame: `class_name`, `confidence` (≥0.4), `bbox`, `frame_index`, `sample_index`, `time_seconds`. De ahí se agrega `detection_density` por segundo. |
| **A dónde va** | `detection_density` sube `virality` (+12% × densidad) y `retention` en `build_timeline()`/`RetentionPredictor`; genera **labels** del timeline ("Person enters scene", "Scene change"…); alimenta el `hook_score` y el ranking de Top Clips. |
| **Procedencia** | IA. Solo activo con `VISUAL_ANALYZER_PROVIDER=yolo` (si no, el visual es heurístico sin detecciones). |
| **Archivos** | `backend/app/ai_services/visual_analyzer.py` → `YoloVisualAnalyzer` |

## 4. DeepFace — Emoción facial (valence / arousal / dominante)

| | |
|---|---|
| **Modelo** | DeepFace (clasificador de emoción facial) |
| **Qué analiza** | Los frames muestreados (1/seg). En cada frame obtiene la distribución de emociones. |
| **Qué produce** | Por frame: `valence` y `arousal` continuos (modelo circumplejo de Russell sobre las probabilidades) + la emoción dominante del frame. De ahí se derivan: **timeline.valence/arousal**, **`dominant_emotion`** (la más frecuente, submuestreada cada 2s) y **`emotion_intensity`** (promedio de arousal). |
| **Mapa de emociones** | `happy`→Joy · `sad`→Sadness · `angry`/`fear`/`disgust`→Tension · `surprise`→Surprise · `neutral`→Neutral |
| **A dónde va** | Esfera (regiones arousal/valence/emotion), **Emotion Quadrant**, **curva del Engagement Graph** (la curva es principalmente arousal), tarjeta **Dominant Emotion**, e insights. |
| **Procedencia** | IA. Activo por defecto (`EMOTION_ANALYZER_PROVIDER=deepface`). Si falla, fusión heurística marcada en `provider_status`. La emoción dominante se deriva de los resultados por-frame (sin segunda pasada de vídeo). |
| **Archivos** | `backend/app/ai_services/emotion_analyzer.py` |

## 5. RetentionPredictor — Curva de retención

| | |
|---|---|
| **Tipo** | Fusión de señales (default) o modelo ML serializado (opcional). |
| **Qué analiza** | Una fila de features por segundo: `motion` (OpenCV), `face_arousal`/`face_valence` (DeepFace), `detection_density` (YOLO), `audio_energy`/`is_silent` (librosa). |
| **Qué produce** | `retention` por segundo (0-1). `retention_score` = promedio del timeline. |
| **Fórmula (heurístico)** | Baseline no lineal que cae más al principio, + 0.14·motion + 0.14·detección + 0.10·arousal facial + 0.08·audio − penalización por silencio/escena vacía, suavizado contra el segundo anterior. |
| **A dónde va** | Esfera (región **retention**), Engagement Graph (cabecera "Retention %"), cálculo de `attention_duration_seconds`. |
| **Procedencia** | **derived** por defecto. `ai` solo si `RETENTION_PREDICTOR_PROVIDER=ml` con un modelo en `RETENTION_MODEL_PATH`. |
| **Archivos** | `backend/app/ai_services/retention_predictor.py` |

## 6. CLIP — Memorabilidad (rewatch + ranking de clips)

| | |
|---|---|
| **Modelo** | `openai/clip-vit-base-patch32` |
| **Qué analiza** | El frame de cada segundo, comparándolo con prompts ("a memorable viral moment", "a surprising reveal", "an emotional reaction" vs "a boring static shot"). |
| **Qué produce** | Un `memorability_score` por segundo. De ahí: **`rewatch_factor`** = proporción de segundos con score > 0.62; y los **scores semánticos** que rankean los Top Clips. |
| **A dónde va** | Engagement Graph (cabecera "Rewatches"), **Top Clips** (ranking). |
| **Procedencia** | IA. Activo por defecto (`MEMORABILITY_SCORER=clip`, `CLIP_RANKER_ENABLED=true`). Si CLIP falla, `rewatch_factor=null` y la UI lo oculta (nada de `3.2x` en uploaded). |
| **Archivos** | `backend/app/ai_services/memorability_scorer.py`, `processing/clip_ranker.py` |

## 7. Qwen2.5-1.5B-Instruct — Texto (insights, razones, hooks)

| | |
|---|---|
| **Modelo** | `Qwen/Qwen2.5-1.5B-Instruct` |
| **Qué analiza** | No analiza el vídeo. Recibe métricas/evidencias ya calculadas y genera texto. Tres usos: (a) insights, (b) razones de cada Top Clip, (c) clasificación de hooks del transcript. |
| **Qué produce** | Insights `{title, description, action, severity}`; `reasons` por clip; tipo de hook (`curiosity_gap`, `urgency`, `conflict`, `question`, `command`, `surprise`). |
| **A dónde va** | **Insights Panel**, razones en **Top Clips**, badges de hook en **Transcript Panel**. |
| **IMPORTANTE** | Qwen **nunca** modifica los scores numéricos; solo produce texto. |
| **Procedencia** | Insights: `ai` solo si `EXPLANATION_PROVIDER=qwen` (default heurístico). Hooks: `ai` con `TEXT_HOOK_ANALYZER=qwen` (default). El mismo modelo se carga una sola vez y se comparte. |
| **Archivos** | `explanation_generator.py`, `text_hook_analyzer.py` |

## 8. Whisper — Transcripción de voz

| | |
|---|---|
| **Modelo** | faster-whisper (`small` por defecto), en GPU si está disponible. |
| **Qué analiza** | El audio del vídeo (speech-to-text). |
| **Qué produce** | `segments[]` (`start`, `end`, `text`), `full_text`, y los `hooks[]` (clasificados por Qwen). |
| **A dónde va** | **Transcript Panel** (segmentos sincronizados con el playback + badges de hook). Los hooks también suman insights. |
| **Procedencia** | IA. Activo por defecto (`AUREA_WHISPER_ENABLED=true`). Sin audio → `transcript=null` y el panel se oculta. |
| **Archivos** | `speech_analyzer.py`, `text_hook_analyzer.py` |

## 9. VideoMAE — Reconocimiento de acciones (opcional)

| | |
|---|---|
| **Modelo** | `MCG-NJU/videomae-base-finetuned-kinetics` |
| **Qué analiza** | 16 frames repartidos por el vídeo; clasifica la acción (Kinetics-400). |
| **Qué produce** | `action_recognition_score` (0-1) + etiqueta de acción. |
| **A dónde va** | Campo `action_recognition_score` del JSON / MetricCard. |
| **Procedencia** | IA. **Desactivado por defecto**; requiere `ENABLE_TEMPORAL_ANALYSIS=true` + `TEMPORAL_ANALYZER_PROVIDER=videomae`. |
| **Archivos** | `temporal_analyzer.py` → `VideoMAETemporalAnalyzer` |

## 10. PySceneDetect — Pacing (opcional)

| | |
|---|---|
| **Librería** | `scenedetect` |
| **Qué analiza** | Frecuencia de cortes de escena del vídeo. |
| **Qué produce** | `pacing_score` (0-1) derivado de la densidad de cortes. |
| **A dónde va** | Esfera (región **pacing**). |
| **Procedencia** | derived. Activo por defecto (`SCENE_DETECTION_ENABLED=true`). Si no hay cortes/falla → `pacing_score=null` y la región se oculta. |
| **Archivos** | `processing/scene_detector.py` |

---

# PARTE B — De dónde saca su valor cada elemento de la UI

## 🔮 Esfera 3D (`BrainSphere` / `sphereUtils.ts`)

Cada segundo busca la `TimelineEntry` más cercana a `currentTime` y enciende las
regiones. En modo uploaded, las regiones cuyo dato es `null` **no se dibujan**.

| Región | Campo que consume | Producido por |
|---|---|---|
| **Virality** | `timeline[t].virality` | Fórmula `build_timeline` (OpenCV motion + audio + brillo + densidad YOLO) → *derived* |
| **Arousal** | `timeline[t].arousal` | DeepFace (60%) + motion/audio (40%) → *ai/derived* |
| **Valence** | `timeline[t].valence` | DeepFace (70%) + brillo (30%) → *ai/derived* |
| **Retention** | `timeline[t].retention` | **RetentionPredictor** (fusión motion+DeepFace+YOLO+audio) → *derived* |
| **Emotion** | `data.emotion_intensity` | DeepFace (promedio de arousal). *En demo* usa una tabla fija por emoción. |
| **Hook** | `data.hook_score` | Backend `_compute_hook_score` (persona YOLO + arousal DeepFace + hook de texto + audio en los primeros 5s). *En demo* cae a promedio de virality 5s. |
| **Pacing** | `data.pacing_score` | PySceneDetect. *En demo* cae a densidad de labels. |

> **¿De dónde saca la esfera la retention?** De `timeline[t].retention`, que produce
> el **RetentionPredictor** combinando movimiento (OpenCV), arousal/valence facial
> (DeepFace), densidad de objetos (YOLO) y energía/silencio de audio (librosa).

## 📊 Engagement Graph (`EngagementGraph.tsx`)

| Elemento | Campo que consume | Producido por |
|---|---|---|
| **Curva** | `timeline[t].arousal` (cae a virality/retention si falta) | DeepFace + motion/audio → la curva es básicamente la **curva de arousal** |
| **Pico** | máximo de arousal de la curva | igual que la curva |
| **Retention %** | `retention_score × 100` | RetentionPredictor (promedio) |
| **Rewatches (x)** | `rewatch_factor` | CLIP (proporción de segundos memorables) |
| **Playhead / eje X** | `currentTime` y `duration` reales | metadata del vídeo (eje X dinámico) |

> **¿Cómo se miden las emociones del Engagement Graph?** La curva representa el
> **arousal** (activación emocional) por segundo. Ese arousal se mide con DeepFace
> sobre las caras (probabilidades de emoción → arousal vía modelo circumplejo de
> Russell), mezclado con el movimiento (OpenCV) y la energía de audio (librosa).
> La cabecera correlaciona esa curva de arousal con los picos de retención.

## 🎯 Emotion Quadrant (`EmotionQuadrant.tsx`)

| Elemento | Campo | Producido por |
|---|---|---|
| **Eje X (Valence)** | `closestEntry.valence` | DeepFace |
| **Eje Y (Arousal)** | `closestEntry.arousal` | DeepFace |
| **Punto luminoso** | (valence, arousal) del segundo actual | DeepFace |
| **Label de emoción** | `data.dominant_emotion` | DeepFace (emoción más frecuente) |
| **Intensidad** | `data.emotion_intensity` | DeepFace (promedio de arousal) |
| **Cuadrantes** | Exhilaration ↗ · Anger ↖ · Depression ↙ · Calm ↘ | etiquetas fijas del grid |

## 🏆 Virality Score (`ViralityScore.tsx`)

| Elemento | Campo | Producido por |
|---|---|---|
| **Porcentaje grande** | `overall_virality_score × 100` | promedio de `timeline.virality` (fórmula derived) |
| **Badge de procedencia** | `metric_sources` de virality | "AI score" / "Composite score" / "Demo mock" |

## 💡 Insights Panel (`InsightsPanel.tsx`)

| Elemento | Campo | Producido por |
|---|---|---|
| **Lista de insights** | `data.insights[]` | Qwen (si `EXPLANATION_PROVIDER=qwen`) o motor de reglas heurístico |
| **Severidad / icono** | `insight.severity` | high → púrpura ✨ · medium → 🧠 · low → 🔒 |
| **Acción / timestamp** | `insight.action`, `insight.timestamp` | el mismo generador |

## 🎬 Top Clips (`ClipList.tsx`)

| Elemento | Campo | Producido por |
|---|---|---|
| **Segmento** | `clip.start_seconds` – `clip.end_seconds` | `rank_clips()` sobre el timeline |
| **Score %** | `clip.score × 100` | ranking con scores semánticos de **CLIP** |
| **Razones** | `clip.reasons[]` | Qwen (si activo) o razones estructuradas por evidencia (YOLO/DeepFace/audio/hooks) |
| **Export/Download** | recorte físico | FFmpeg sobre el vídeo original |

Si CLIP no genera candidatos → `top_clips` vacío y la UI muestra "No disponible".

## 📝 Transcript Panel (`TranscriptPanel.tsx`)

| Elemento | Campo | Producido por |
|---|---|---|
| **Segmentos** | `transcript.segments[]` | Whisper (sincronizados con el playback) |
| **Hook badges** | `transcript.hooks[]` | Qwen (tipo + confianza) |

## 📐 MetricCards (`App.tsx`)

| Tarjeta | Campo | Producido por |
|---|---|---|
| **Dominant Emotion** | `data.dominant_emotion` | DeepFace |
| **Attention Duration** | `data.attention_duration_seconds` | Backend `_compute_attention_duration_seconds`: intervalo continuo más largo con retención alta + ≥2 señales reales (persona/cara, audio/hook, CLIP) → *derived*. En uploaded solo se muestra si existe. |

---

## Rendimiento (modelos)

Los modelos pesados (YOLO, DeepFace, CLIP, Qwen, Whisper, VideoMAE) se **cargan
una sola vez** (caché a nivel de proceso) y se **precargan al arrancar el
servidor** (warm-up en segundo plano), por lo que no se recargan en cada análisis.
Whisper y VideoMAE corren en **GPU** cuando hay CUDA. El vídeo se decodifica una
sola vez y los frames muestreados se reutilizan entre OpenCV, YOLO y DeepFace.

Esto no cambia la procedencia de los datos: solo acelera el análisis.

---

## Variables de entorno por modelo

```bash
# Detección de objetos (YOLO) — por defecto heurístico, actívalo:
VISUAL_ANALYZER_PROVIDER=yolo

# Emoción facial (DeepFace) — activo por defecto
EMOTION_ANALYZER_PROVIDER=deepface

# Memorabilidad / rewatch / ranking de clips (CLIP) — activo por defecto
MEMORABILITY_SCORER=clip
CLIP_RANKER_ENABLED=true

# Insights y hooks (Qwen) — hooks por defecto; insights opcional
TEXT_HOOK_ANALYZER=qwen
EXPLANATION_PROVIDER=qwen

# Transcripción (Whisper) — activo por defecto
AUREA_WHISPER_ENABLED=true
AUREA_WHISPER_MODEL=small

# Audio (librosa) — activo por defecto
AUREA_AUDIO_ENABLED=true

# Pacing (PySceneDetect) — activo por defecto
SCENE_DETECTION_ENABLED=true

# Reconocimiento de acciones (VideoMAE) — desactivado por defecto
ENABLE_TEMPORAL_ANALYSIS=true
TEMPORAL_ANALYZER_PROVIDER=videomae

# Retención por modelo ML (opcional; por defecto fórmula derived)
RETENTION_PREDICTOR_PROVIDER=ml
RETENTION_MODEL_PATH=/ruta/al/modelo.joblib

# Warm-up de modelos al arrancar (activo por defecto)
AUREA_WARMUP_MODELS=true
```

Sin estas variables, las métricas que dependen de un modelo ausente se calculan
de forma `derived`/heurística o se marcan `unavailable` (y la UI las oculta);
nunca se sustituyen por valores inventados en modo uploaded.
