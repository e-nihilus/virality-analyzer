# Estado de datos IA vs heurística en el frontend

Fecha de revisión: 2026-06-18

> Revisión anterior: 2026-06-16. Este documento se ha reescrito para reflejar el
> estado actual tras implementar el plan de `ToDo.txt` (separación demo/upload,
> procedencia de providers, eliminación del fallback a mock, activación de IA por
> defecto, eliminación de hardcoded en modo uploaded) y la optimización de
> rendimiento del pipeline de análisis.

## Resumen ejecutivo

Estado actual: **tras subir un vídeo, el frontend muestra solo datos reales del
vídeo o los oculta**. Ya no se sustituyen métricas por mock ni por valores
hardcoded en modo uploaded. Cada métrica viaja con su procedencia
(`metric_sources`) y cada provider informa si se usó, hizo fallback o falló
(`provider_status`).

La aplicación sigue distinguiendo cuatro tipos de datos, pero ahora están
claramente separados y etiquetados:

1. **IA real sobre el vídeo**: YOLO, DeepFace, CLIP, Qwen, Whisper, VideoMAE
   cuando sus providers/flags están activos y sus dependencias funcionan.
2. **Señales reales no-IA**: OpenCV/FFmpeg/librosa calculan movimiento, brillo,
   audio, silencios, duración, etc. Reales del vídeo, pero no modelos IA.
3. **Fusión derivada de señales IA/no-IA**: algunas métricas finales son fórmulas
   compuestas, no predicciones aprendidas. Se etiquetan como `derived`.
4. **Demo mock**: solo en la pantalla inicial (`source === "demo-mock"`). En modo
   uploaded el mock está prohibido por diseño.

### Cambios clave desde la revisión anterior

- **Sin fallback a mock**: `analysis_worker.py` ya no genera mock si el análisis
  falla; persiste un resultado `status=failed` / `analysis_source=failed`.
- **Procedencia en el contrato**: `AnalysisResult` incluye `analysis_source`,
  `provider_status` y `metric_sources`.
- **Modo demo vs uploaded en frontend**: `source` =
  `demo-mock | uploaded-real | uploaded-partial | failed`.
- **Hardcoded solo en demo**: `8.4s`, `0.884`, `3.2`, `DEFAULT_PATH`, intensidad
  de emoción por tabla y fallbacks de hook/pacing solo se usan si `isDemo`.
- **Eje X dinámico**: las etiquetas de tiempo se derivan del `duration` real.
- **IA activada por defecto**: emotion=deepface, memorability=clip,
  clip_ranker=true, scene_detection=true, whisper=true, audio=true,
  text_hooks=qwen (ver matiz de defaults abajo).
- **Métricas nuevas reales**: `attention_duration_seconds`, `emotion_intensity`,
  `hook_score` + `hook_evidence`, `pacing_score`.
- **Rendimiento**: el pipeline decodifica el vídeo una sola vez y reutiliza los
  frames muestreados en YOLO/DeepFace; la emoción dominante se deriva de los
  resultados por-frame de DeepFace (misma procedencia, sin segunda pasada).

## Defaults efectivos de providers

Importante: la selección de providers en tiempo de ejecución usa `_env_flag()`
(lee `os.environ` directamente en `provider_factory.py` y `heuristic_analyzer.py`),
**no** el objeto `Settings` de `app/core/config.py`. Los defaults de `config.py`
existen pero no gobiernan el pipeline; los valores efectivos sin definir ninguna
env var son:

```text
EMOTION_ANALYZER_PROVIDER=deepface     # IA por defecto
MEMORABILITY_SCORER=clip               # CLIP por defecto
CLIP_RANKER_ENABLED=true               # ranking semántico por defecto
SCENE_DETECTION_ENABLED=true           # pacing por defecto
TEXT_HOOK_ANALYZER=qwen                # hooks por LLM por defecto
AUREA_WHISPER_ENABLED=true             # transcript por defecto
AUREA_AUDIO_ENABLED=true               # audio por defecto
EXPLANATION_CACHE_ENABLED=true
```

Siguen en no-IA / derived por defecto:

```text
VISUAL_ANALYZER_PROVIDER=heuristic     # YOLO solo si =yolo
RETENTION_PREDICTOR_PROVIDER=heuristic # fusión derivada, no ML entrenado
VIRALITY_PREDICTOR_PROVIDER=derived    # fórmula compuesta, no ML entrenado
ENABLE_TEMPORAL_ANALYSIS=false         # VideoMAE desactivado salvo que se active
TEMPORAL_ANALYZER_PROVIDER=heuristic
EXPLANATION_PROVIDER=heuristic         # Qwen solo si =qwen
```

Todos los providers degradan con seguridad: si falta una dependencia o falla la
validación, se hace fallback (heurística o métrica `unavailable`) y queda
registrado en `provider_status`. Nunca se inventa un número en modo uploaded.

## Flujo real de datos mostrado por el frontend

### Pantalla inicial (demo)

- `useAnalysis()` carga datos demo vía `fetchMockAnalysis()` →
  `GET /api/viral-intelligence/analysis/mock`, con `frontend/src/data/mockAnalysis.ts`
  como respaldo si el backend no responde.
- El estado queda como `source = "demo-mock"`.

**Conclusión:** antes de subir un vídeo, la UI muestra mock, **marcado
explícitamente como demo** (badge de "demo data"). Todos los fallbacks hardcoded
solo aplican en este modo.

### Después de subir un vídeo

- `useVideoUpload()` sube el archivo, hace polling a `/analysis/{id}` y reemplaza
  el estado por el resultado real del backend.
- Según la procedencia del resultado, `source` pasa a `uploaded-real`,
  `uploaded-partial` (si hubo algún fallback/failed en providers) o `failed`.

**Conclusión:** tras un upload, la UI usa el resultado persistido del análisis
real. Si el análisis falla, se muestra un estado de error explícito; **no** se
muestran métricas mock como si fueran reales.

## Estado por elemento visible del frontend

| Elemento UI | Fuente actual | ¿IA real? | Observaciones |
|---|---|---:|---|
| Virality Score | `data.overall_virality_score` | Derived | Promedio de `timeline.virality`. Fórmula sobre movimiento/brillo/audio/(YOLO si activo). Etiquetado `derived` (badge "Composite score"). |
| Brain Sphere: Virality | `timeline[].virality` | Derived | Señales reales del vídeo; YOLO influye si está activo. Sigue siendo fórmula. |
| Brain Sphere: Arousal/Valence | `timeline[].arousal` / `valence` | Sí si DeepFace | DeepFace por defecto. Si falla, fallback heurístico marcado en `provider_status`. |
| Brain Sphere: Retention | `timeline[].retention` / `retention_score` | Derived | `RetentionPredictor` por defecto heurístico de fusión; etiquetado `derived`. ML solo si `RETENTION_PREDICTOR_PROVIDER=ml` con modelo. |
| Brain Sphere: Hook | `data.hook_score` (+ `hook_evidence`) | Derived | Calculado en backend desde person YOLO, arousal DeepFace, text hooks y audio en los primeros 5s. En uploaded no hay fallback frontend (solo en demo). Si es null, la región se oculta. |
| Brain Sphere: Pacing | `data.pacing_score` | Sí si PySceneDetect | `SCENE_DETECTION_ENABLED=true` por defecto. Derivado de frecuencia de cortes. Si falla/null, la región se oculta (en demo usa densidad de labels). |
| Brain Sphere: Emotion intensity | `data.emotion_intensity` | Sí si DeepFace | Promedio de arousal de DeepFace. En demo usa tabla fija; en uploaded usa el valor real o null. |
| Emotion Quadrant | `closestEntry.valence/arousal` + `dominant_emotion` | Sí si DeepFace | El layout/cuadrantes son visualización fija; los valores vienen de DeepFace. |
| Dominant Emotion card | `data.dominant_emotion` | Sí si DeepFace | Derivado de los resultados por-frame de DeepFace. La descripción solo aparece en modo demo. |
| Attention Duration card | `data.attention_duration_seconds` | Derived | Métrica real backend: intervalo continuo con retención alta + múltiples señales (face/person, audio/hooks, CLIP). En uploaded solo se muestra si existe; ya no hay `8.4s` fijo (solo demo). |
| Engagement Graph curva | `timeline` | Real | Curva del timeline real. `DEFAULT_PATH` solo si `isDemo`. |
| Engagement Graph Retention | `data.retention_score` | Derived | Sin fallback `0.884` en uploaded; si falta, muestra no disponible. |
| Engagement Graph Rewatches | `data.rewatch_factor` | Sí si CLIP | `MEMORABILITY_SCORER=clip` por defecto. Si CLIP falla, `rewatch_factor=null` y se oculta (sin `3.2` en uploaded). |
| Engagement Graph eje X | `timeLabels(duration)` | Real | Etiquetas derivadas del `duration` real (0, 25%, 50%, 75%, 100%). |
| Top Clips | `data.top_clips` | Sí si CLIP | Ranking con scores semánticos CLIP (`CLIP_RANKER_ENABLED=true`). Reasons estructuradas por evidencia; Qwen si `CLIP_REASON_PROVIDER/EXPLANATION_PROVIDER=qwen`. Si no hay candidatos CLIP, `unavailable`. |
| Top Clip export/download | corte con FFmpeg | Real, no IA | Exporta físicamente el segmento del vídeo fuente. |
| Insights | `data.insights` | Sí si Qwen | `EXPLANATION_PROVIDER=heuristic` por defecto → reglas. Qwen solo si se activa. No modifica scoring. |
| Transcript | `data.transcript` | Sí si Whisper | Whisper activo por defecto. Solo aparece si hay audio y segmentos. Sin audio → `unavailable`. |
| Transcript hook badges | `data.transcript.hooks` | Sí si Qwen | `TEXT_HOOK_ANALYZER=qwen` por defecto. Si Qwen falla, hooks vacíos/`unavailable` (sin regex salvo configuración explícita). |
| Video mostrado | `videoUrl` de upload o vídeo demo | N/A | Si no hay upload, muestra vídeo demo. |
| Data source / badges | `source` + `metric_sources` | N/A | Muestra badge de demo, de parcial y de procedencia por métrica (AI / derived / unavailable). |

## Elementos que siguen siendo heurística / derived (no IA entrenada)

Estos son intencionales y están etiquetados como `derived`, no como IA entrenada:

1. **`overall_virality_score` y `timeline.virality`** — fórmula compuesta en
   `timeline_builder.py` (sin modelo de viralidad entrenado).
2. **`retention_score` / `timeline.retention`** — `HeuristicRetentionPredictor`
   por defecto (fusión de motion/audio/YOLO density/DeepFace/silencios), no ML.
3. **`hook_score`** — fórmula compuesta sobre evidencias de los primeros 5s
   (con `hook_evidence` adjunto), no un modelo calibrado.
4. **`attention_duration_seconds`** — derivado de retención + señales reales.
5. **VideoMAE / action recognition** — desactivado por defecto
   (`ENABLE_TEMPORAL_ANALYSIS=false`); requiere activación explícita.
6. **Insights** — reglas por defecto (`EXPLANATION_PROVIDER=heuristic`); Qwen
   opcional.
7. **Visual / YOLO** — `VISUAL_ANALYZER_PROVIDER=heuristic` por defecto; YOLO
   (object detection) solo si se activa `=yolo`. Sin YOLO, las detecciones que
   alimentan density/hook/clips no están disponibles.

Componentes que ya **no** usan heurística/hardcoded en modo uploaded (resueltos):

- Carga inicial mock → ahora solo en `source === "demo-mock"`.
- `Attention Duration = 8.4s` → métrica real `attention_duration_seconds`.
- Descripción fija de Dominant Emotion → solo en demo.
- Fallbacks `0.884` / `3.2` / `88.4` → solo en demo.
- `DEFAULT_PATH` de la curva → solo en demo (`allowDemoFallback`).
- Eje X fijo `0:00..0:50` → ahora dinámico por `duration`.
- Tabla fija `EMOTION_INTENSITY` → solo en demo; en uploaded usa valor real.
- Fallback de hook/pacing en la esfera → solo en demo; si null, se oculta.

## ¿Son reales los datos del vídeo subido?

### Sí, cuando el análisis termina (real o parcial)

- Duración, fps, ancho, alto: probe/metadata real.
- Frames/motion/brightness: OpenCV sobre el vídeo real.
- Audio energy/silence: real (librosa activo por defecto).
- YOLO detections: IA real si `VISUAL_ANALYZER_PROVIDER=yolo`.
- DeepFace emotion/arousal/valence/dominant: IA real (default), con fallback
  marcado si falla.
- CLIP rewatch/top clips: IA real (default), `unavailable` si CLIP falla.
- Whisper transcript: IA real (default) si hay audio.
- Qwen hooks/insights: IA real si los flags están activos.
- VideoMAE action score: IA real solo si temporal está activado y carga.
- Export de clips: vídeo real cortado del original.

### Derived (real, pero fórmula, no IA entrenada)

- `overall_virality_score`, `retention_score`, `hook_score`,
  `attention_duration_seconds`, `pacing_score` (etiquetados `derived`).

### Nunca

- Mock, hardcoded o números inventados en modo uploaded. Si un dato no se puede
  calcular, es `null` y la UI lo oculta o muestra "No disponible".

## Riesgos actuales

Los riesgos críticos de la revisión anterior están mitigados:

1. ~~La UI no distingue real vs mock vs fallback~~ → **resuelto** con `source` y
   `metric_sources`/`provider_status` + badges.
2. ~~"AI" demasiado amplio en la UI~~ → **mitigado**: se muestran badges
   `AI` / `derived` / `unavailable` por métrica.
3. ~~Valores hardcoded visibles tras upload~~ → **resuelto**: solo en demo.
4. ~~Fallback a mock si explota el análisis~~ → **resuelto**: `status=failed`.

Riesgos residuales menores:

- Los defaults de `config.py` (`Settings`) no coinciden con los `_env_flag`
  efectivos; puede confundir a quien lea solo `config.py`. Conviene unificarlos o
  documentarlo en el README.
- Varias métricas siguen siendo `derived`; el usuario debe leer el badge para no
  interpretarlas como IA entrenada.
- Modelos pesados (CLIP/Qwen/DeepFace/Whisper) requieren descarga la primera vez;
  sin GPU el análisis puede ser lento (mitigado en parte por la optimización de
  decodificación única del vídeo).

## Recomendaciones pendientes

1. **Unificar defaults**: hacer que `app/core/config.py` refleje los `_env_flag`
   efectivos (o eliminar los `Settings` que no se usan) para evitar ambigüedad.
2. **Modelos entrenados reales** (Prioridad 3 del `ToDo.txt`): `ViralityPredictor`
   ML y `MLRetentionPredictor` para pasar `virality`/`retention` de `derived` a
   `ai` cuando exista modelo.
3. **Activar YOLO por defecto** si se desea object detection en uploaded
   (`VISUAL_ANALYZER_PROVIDER=yolo`); hoy queda en heurístico salvo configuración.
4. **Exponer procedencia más visible**: ampliar los badges de
   `metric_sources` en todas las tarjetas (no solo virality/clips/hooks).
5. **Pantalla inicial en producción**: opcionalmente sustituir el demo mock por un
   estado vacío "Sube un vídeo para analizar".

## Conclusión

A diferencia de la revisión anterior, la app **ya garantiza que, tras un upload,
los datos mostrados son del vídeo real o se ocultan**. La IA real está activada
por defecto en la mayoría del pipeline (DeepFace, CLIP, Whisper, Qwen hooks,
scene detection), el fallback a mock se eliminó, y todos los hardcoded del
frontend quedaron confinados al modo demo.

La descripción más correcta del estado actual es:

> Tras subir un vídeo, el frontend muestra exclusivamente resultados reales del
> vídeo —IA real cuando el provider está activo y funciona, o métricas `derived`
> etiquetadas como tales—, y oculta o marca como "No disponible" cualquier
> métrica que no se pueda calcular. El mock y los valores hardcoded existen solo
> en la pantalla demo inicial. Si el análisis falla, la UI muestra un error
> explícito en lugar de datos inventados.

Quedan como trabajo opcional los modelos entrenados de virality/retention (para
convertir esas métricas de `derived` a `ai`) y la unificación de los defaults de
configuración.
