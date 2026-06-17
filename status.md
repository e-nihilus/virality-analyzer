# Estado de datos IA vs heurística en el frontend

Fecha de revisión: 2026-06-16

## Resumen ejecutivo

No: **no todos los datos que muestra el frontend son análisis reales de IA del vídeo subido**.

La aplicación mezcla cuatro tipos de datos:

1. **IA real sobre el vídeo**: YOLO, DeepFace, VideoMAE, Qwen, Whisper, CLIP cuando sus providers/flags están activados y sus dependencias funcionan.
2. **Señales reales no-IA**: OpenCV/FFmpeg/librosa calculan movimiento, brillo, audio, silencios, duración, etc. Son reales del vídeo, pero no modelos IA.
3. **Fusión heurística de señales IA/no-IA**: muchas métricas finales no son una predicción aprendida, sino fórmulas que combinan señales reales.
4. **Mock/hardcoded/fallback frontend**: todavía hay datos de desarrollo o valores por defecto visibles si falta información o antes de subir un vídeo.

Con la configuración observada en el entorno actual:

```text
VISUAL_ANALYZER_PROVIDER=yolo
EMOTION_ANALYZER_PROVIDER=deepface
ENABLE_TEMPORAL_ANALYSIS=true
TEMPORAL_ANALYZER_PROVIDER=videomae
EXPLANATION_PROVIDER=qwen
EXPLANATION_CACHE_ENABLED=true
```

Sí se intentan usar YOLO, DeepFace, VideoMAE y Qwen. Pero otros módulos siguen en default:

```text
RETENTION_PREDICTOR_PROVIDER=heuristic        # default
MEMORABILITY_SCORER=heuristic                 # default
TEXT_HOOK_ANALYZER=regex                      # default
CLIP_RANKER_ENABLED=false                     # default
SCENE_DETECTION_ENABLED=false                 # default
AUREA_WHISPER_ENABLED=false                   # default, si no se define
```

## Flujo real de datos mostrado por el frontend

### Pantalla inicial

El hook `useAnalysis()` carga datos iniciales llamando a:

- `GET /api/viral-intelligence/analysis/mock`
- archivo: `frontend/src/stores/analysisStore.ts`
- función API: `frontend/src/api/analysisApi.ts` → `fetchMockAnalysis()`

Si el backend no responde, usa además `frontend/src/data/mockAnalysis.ts`.

**Conclusión:** antes de subir un vídeo, la UI muestra mock, no análisis real de un vídeo.

### Después de subir un vídeo

`useVideoUpload()` sí sube el archivo, hace polling a `/analysis/{id}` y reemplaza el estado por el resultado real del backend.

**Conclusión:** después de un upload completado, la mayor parte de la UI usa el resultado persistido del análisis del vídeo. Pero ese resultado puede contener métricas heurísticas/fallbacks, y el worker aún cae a mock si hay una excepción no controlada.

## Estado por elemento visible del frontend

| Elemento UI | Fuente actual | ¿IA real? | Observaciones |
|---|---|---:|---|
| Virality Score | `data.overall_virality_score` | Parcial | Es promedio de `timeline.virality`. La virality se calcula con fórmula sobre movimiento/brillo/audio/YOLO density. No es un modelo entrenado de viralidad. |
| Brain Sphere: Virality | `timeline[].virality` | Parcial | Usa señales reales del vídeo; YOLO puede influir si está activo. Sigue siendo fórmula. |
| Brain Sphere: Arousal/Valence | `timeline[].arousal` / `timeline[].valence` | Sí si DeepFace; si no, heurística | DeepFace alimenta estas señales si `EMOTION_ANALYZER_PROVIDER=deepface` y dependencias OK. Si falla, usa movimiento/brillo/audio. |
| Brain Sphere: Retention | `timeline[].retention` / `retention_score` | No modelo ML | `RetentionPredictor` default es heurístico mejorado. Usa señales IA/no-IA, pero no curva real aprendida. |
| Brain Sphere: Hook | `data.hook_score` o fallback frontend | Parcial | Backend calcula `hook_score` por fórmula con YOLO person, DeepFace arousal, text hooks y virality inicial. Si falta, frontend usa promedio de virality primeros 5s. |
| Brain Sphere: Pacing | `data.pacing_score` o fallback frontend | No por defecto | `SCENE_DETECTION_ENABLED=false` por defecto; entonces frontend usa densidad de labels, una heurística. |
| Brain Sphere: Emotion intensity | tabla fija `EMOTION_INTENSITY` | No | Convierte el nombre de emoción a intensidad con valores hardcodeados. |
| Emotion Quadrant | `closestEntry.valence/arousal` + `dominant_emotion` | Parcial | Puede venir de DeepFace; si no, heurística. El layout/cuadrantes son visualización fija. |
| Dominant Emotion card | `data.dominant_emotion` | Sí si DeepFace; si no, heurística | El valor puede ser real DeepFace. Pero la descripción debajo está hardcodeada. |
| Attention Duration card | hardcoded `8.4s` | No | No existe campo backend para esta métrica. Es un valor fijo. |
| Engagement Graph curva | `timeline`, preferentemente `arousal` | Parcial | Curva real del timeline, pero si falta timeline usa `DEFAULT_PATH` hardcoded. Además prioriza arousal antes que retention/virality. |
| Engagement Graph Retention | `data.retention_score` con fallback `0.884` | Parcial | El valor real backend es heurístico mejorado; si falta, el frontend muestra 88.4% hardcoded. |
| Engagement Graph Rewatches | `data.rewatch_factor` con fallback `3.2` | Parcial | Por defecto `MEMORABILITY_SCORER=heuristic`; CLIP no está activo salvo `MEMORABILITY_SCORER=clip`. Si falta, muestra 3.2 hardcoded. |
| Engagement Graph eje X | `TIME_LABELS` fijo `0:00..0:50` | No | No se adapta al duration real. |
| Top Clips | `data.top_clips` | Parcial | Ranking por picos de virality y ventana deslizante. Reasons pueden incluir YOLO detections; ranking CLIP solo si se activa `CLIP_RANKER_ENABLED=true` y `MEMORABILITY_SCORER=clip`. |
| Top Clip export/download | corte con FFmpeg | Real, no IA | Exporta físicamente el segmento del vídeo fuente. |
| Insights | `data.insights` | Sí si Qwen; si no, heurística | Con `EXPLANATION_PROVIDER=qwen`, Qwen genera texto. Si falla, usa reglas del `explanation_engine`. No modifica scoring. |
| Transcript | `data.transcript` | Sí si Whisper activo | Solo aparece si `AUREA_WHISPER_ENABLED=true` y hay audio/transcripción. |
| Transcript hook badges | `data.transcript.hooks` | Regex por defecto | `TEXT_HOOK_ANALYZER=regex` por defecto. Qwen solo si `TEXT_HOOK_ANALYZER=qwen`. |
| Video mostrado | `videoUrl` de upload o `/videos/default.mp4` | N/A | Si no hay upload, muestra vídeo default. |
| “Analyze Variations” button | UI hardcoded | No | Botón visual sin conexión a datos/análisis. |

## Elementos que siguen usando heurística o fallback en vez de IA

### En frontend

1. **Carga inicial mock**
   - `frontend/src/stores/analysisStore.ts` llama a `fetchMockAnalysis()`.
   - Si falla backend usa `frontend/src/data/mockAnalysis.ts`.

2. **Attention Duration = `8.4s`**
   - En `frontend/src/App.tsx`.
   - No viene del backend.

3. **Descripción de Dominant Emotion**
   - Texto fijo: `Triggered by abrupt scene transition at 0:12.`
   - No viene del análisis.

4. **Fallbacks numéricos en EngagementGraph**
   - `retention_score ?? 0.884`
   - `rewatch_factor ?? 3.2`
   - `EngagementGraph` también tiene defaults `88.4` y `3.2`.

5. **Curva default del EngagementGraph**
   - `DEFAULT_PATH` hardcoded si no hay timeline.

6. **Eje temporal fijo del EngagementGraph**
   - `TIME_LABELS = ["0:00", "0:10", ... "0:50"]`.
   - No escala con vídeos más cortos/largos.

7. **Pacing fallback de esfera**
   - Si `data.pacing_score` no existe, usa conteo de labels por duración.
   - Como `SCENE_DETECTION_ENABLED` no aparece activado, actualmente lo normal es que use este fallback.

8. **Hook fallback de esfera**
   - Si `data.hook_score` no existe, usa promedio de virality primeros 5s.
   - En el flujo actual backend sí intenta calcular `hook_score`, pero el fallback sigue presente.

9. **Emotion intensity de esfera**
   - Tabla fija por etiqueta (`Surprise=0.85`, `Joy=0.75`, etc.).

### En backend

1. **Provider defaults son heurísticos**
   - En `provider_factory.py`, si no se define env var, casi todo cae a `heuristic`.

2. **Virality del timeline**
   - Fórmula en `timeline_builder.py`.
   - Usa señales reales y YOLO density si existe, pero no un modelo de viralidad entrenado.

3. **Retention predictor**
   - `HeuristicRetentionPredictor` por defecto.
   - Usa motion, audio, YOLO density, DeepFace valence/arousal, silencios.
   - Es fusión heurística, no ML entrenado con curvas reales.

4. **Rewatch factor**
   - Por defecto usa `HeuristicMemorabilityScorer`.
   - CLIP solo si `MEMORABILITY_SCORER=clip`.

5. **Top clips**
   - Ranking base por picos locales de virality.
   - YOLO mejora reasons y score, pero no hay LLM/Qwen generando reasons específicas todavía.

6. **Text hooks**
   - Regex por defecto.
   - Qwen solo si `TEXT_HOOK_ANALYZER=qwen`.

7. **Pacing score**
   - Solo se calcula con PySceneDetect si `SCENE_DETECTION_ENABLED=true`.
   - Si no, el frontend cae a heurística por labels.

8. **Action recognition**
   - Con tu entorno actual se intenta VideoMAE porque `ENABLE_TEMPORAL_ANALYSIS=true` y `TEMPORAL_ANALYZER_PROVIDER=videomae`.
   - Pero `action_recognition_score` no se muestra claramente en la UI principal actual.

9. **Fallback a mock si explota el análisis**
   - `backend/app/workers/analysis_worker.py` captura cualquier excepción del análisis y genera mock.
   - El resultado queda como `completed`, sin un campo visible que indique `mock` o `fallback`.
   - Esto puede hacer que el frontend muestre datos que parecen reales pero son mock si hubo una excepción grave.

## ¿Son reales los datos del vídeo subido?

### Sí, para estos datos cuando el análisis termina sin fallback a mock

- Duración, fps, ancho, alto: probe/metadata real.
- Frames/motion/brightness: OpenCV sobre el vídeo real.
- Audio energy/silence: audio real si `librosa` y `AUREA_AUDIO_ENABLED`.
- YOLO detections: IA real si `VISUAL_ANALYZER_PROVIDER=yolo`.
- DeepFace emotion/arousal/valence: IA real si `EMOTION_ANALYZER_PROVIDER=deepface` y dependencias OK.
- VideoMAE action score: IA real si temporal está activo y carga correctamente.
- Qwen insights: IA generativa real si `EXPLANATION_PROVIDER=qwen` y carga correctamente.
- Whisper transcript: IA real si `AUREA_WHISPER_ENABLED=true`.
- Export de clips: vídeo real cortado del original.

### No completamente, para estos datos

- `overall_virality_score`: derivado por fórmula; no es predicción IA entrenada.
- `retention_score`: promedio de retention heurística/fusión; no curva real aprendida.
- `rewatch_factor`: heurístico salvo CLIP activo.
- `top_clips`: algoritmo heurístico con señales IA opcionales.
- `hook_score`: fórmula compuesta, no modelo.
- `pacing_score`: ausente por defecto; fallback frontend heurístico.
- `insights`: pueden ser Qwen, pero si Qwen falla son reglas.
- `transcript.hooks`: regex por defecto.
- varias etiquetas/descripciones/valores UI siguen hardcoded.

## Riesgos actuales para interpretación de datos

1. **La UI no distingue real vs mock vs fallback.**
   - El usuario puede ver un resultado `completed` generado por mock si el worker tuvo una excepción.

2. **La palabra “AI” en la UI es demasiado amplia.**
   - Algunas métricas son IA real, otras son fórmulas sobre señales reales.

3. **Hay valores hardcoded visibles.**
   - Especialmente `Attention Duration 8.4s`, descripción de emoción, fallbacks 88.4/3.2 y eje X fijo.

4. **Los defaults de backend son heurísticos.**
   - En producción conviene definir explícitamente los providers deseados.

## Recomendaciones para que el frontend muestre solo análisis real del vídeo

1. **Eliminar la carga inicial de `/analysis/mock` en producción.**
   - Mostrar estado vacío: “Sube un vídeo para analizar”.

2. **Añadir campo backend `analysis_source` o `provider_status`.**
   - Ejemplo: `real`, `mock`, `partial_fallback`.
   - Incluir qué providers se usaron: YOLO/DeepFace/Qwen/VideoMAE/Whisper/CLIP.

3. **No marcar como `completed` un fallback mock tras una excepción.**
   - Mejor `failed` o `completed_with_fallback`.

4. **Quitar hardcoded UI values.**
   - `Attention Duration 8.4s` debe venir del backend o no mostrarse.
   - La descripción de dominant emotion debe venir de insight/backend.
   - Quitar defaults `0.884`, `3.2` si se quiere evitar datos inventados.

5. **Activar explícitamente providers IA restantes si se desean.**
   - `MEMORABILITY_SCORER=clip`
   - `CLIP_RANKER_ENABLED=true`
   - `TEXT_HOOK_ANALYZER=qwen`
   - `SCENE_DETECTION_ENABLED=true`
   - `AUREA_WHISPER_ENABLED=true`

6. **Exponer métricas de confianza/procedencia en el frontend.**
   - Por ejemplo: “Retention: heuristic fusion”, “Emotion: DeepFace”, “Insights: Qwen”.

## Conclusión

La app ya usa IA real en partes importantes del pipeline cuando los providers están activados, especialmente YOLO, DeepFace, VideoMAE y Qwen. Sin embargo, **el frontend todavía muestra varios valores heurísticos, fallback o hardcoded**, y la pantalla inicial usa mock. Por tanto, actualmente no se puede afirmar que “todos los datos del frontend son análisis reales de IA del vídeo enviado”.

La descripción más correcta del estado actual es:

> El frontend muestra resultados reales del vídeo tras un upload completado, enriquecidos por IA cuando los providers están activos, pero varias métricas finales siguen siendo fórmulas heurísticas o tienen fallbacks/hardcoded de UI. Además, existe un fallback a mock si el análisis falla.
