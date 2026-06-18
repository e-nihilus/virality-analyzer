# Comparativa: Especificación vs. Implementación actual

Fecha: 2026-06-18

Este documento contrasta lo que pide el spec [`Predicción de viralidad.md`](./Predicción%20de%20viralidad.md)
con lo que el proyecto tiene implementado hoy. Responde a la pregunta:
**¿cuánto se parece el proyecto actual a lo que se pide?**

## Veredicto rápido

- **Amplitud de features y arquitectura de outputs:** alto parecido (~60-70% del "MVP realista" descrito).
- **Núcleo predictivo (modelos entrenados + fusion transformer + dataset etiquetado):** prácticamente no implementado.

> Está bien montado todo el andamiaje multimodal y la capa de explicación/clips,
> pero la "predicción de viralidad" sigue siendo una **estimación compuesta
> (`derived`)**, no un modelo entrenado como pide el documento (que marca esto
> como "lo más importante").

---

## Tabla de cumplimiento por sección del spec

| Sección del spec | Estado | Implementación actual | Hueco principal |
|---|---|---|---|
| 1. Input pipeline (MP4, decoding) | ✅ Cumple | FFmpeg + OpenCV (decode único, frames reutilizados) | decord/PyAV/moviepy no usados (no críticos) |
| A. Visual analysis | 🟡 Parcial | YOLOv8 (objetos/personas), DeepFace (emoción facial), motion, brillo, scene cuts (PySceneDetect), CLIP (attention) | Sin eye contact, zoom/camera shake, GroundingDINO, EMOCA/OpenFace, SlowFast/TimeSformer |
| B. Audio analysis | 🟡 Parcial | librosa: energía RMS, silencios, cambios de energía | Sin pitch variance, speech speed, beat drops, risas/gritos, wav2vec2/openSMILE/pyannote |
| C. Speech + NLP | ✅ Cumple | Whisper (transcripción) + hooks con Qwen (curiosity_gap, urgency, conflict, question, command, surprise) | Sin clasificadores entrenados (ragebait, meme), DeBERTa/RoBERTa |
| 3. Valence/Arousal modeling | 🟡 Parcial | DeepFace por-frame → valence/arousal (modelo circumplejo de Russell); output con timestamp/valence/arousal | Solo facial; no fusión estilo Hume (audio + texto + prosodia) |
| 4. Detección de momentos virales | ✅ Cumple | Sliding window + peak detection en `clip_ranker` | — |
| 5. Virality Prediction Engine | ❌ No cumple | Fórmula compuesta `derived` (motion+audio+brillo+YOLO density) | **Sin modelo entrenado, sin dataset (watch time/shares/saves/rewatch)** |
| 6. Explanation engine | ✅ Cumple | Qwen2.5 sobre features estructuradas (+ fallback de reglas) | — |
| 7. Generación automática de clips | ✅ Cumple | Peak detect + expandir contexto + ranking + export FFmpeg | — |
| 8/10. Modelos recomendados | 🟡 Parcial | YOLOv8, VideoMAE (opcional), Qwen, Whisper, CLIP, DeepFace | Sin Qwen2.5-VL, InternVideo2/Video-LLaMA, EMOCA, openSMILE |
| 9. Output JSON final | ✅ Cumple | `overall_virality_score`, `top_clips` con start/end/score/emotion/explanation | Muy alineado con el ejemplo del spec |
| Fusion Transformer / Temporal Transformer | ❌ No cumple | Fusión **heurística** en `build_timeline` | **No hay fusión multimodal aprendida** |
| Retention estimation | 🟡 Parcial | `RetentionPredictor` heurístico (fusión de señales) | No entrenado sobre curvas de retención reales |
| 11/13. Señales sociales/contexto | ❌ No cumple | No modeladas | Sin timing, plataforma, trend alignment |

Leyenda: ✅ cumple · 🟡 parcial · ❌ no cumple

---

## Lo que SÍ coincide con el spec

- **Estructura general del pipeline** y el conjunto de **outputs** (viral score, top clips, curva de emoción, hooks, retención, valence/arousal).
- **Cobertura multimodal de extracción:** visual + audio + speech/NLP + emoción + temporal.
- **Capa de explicación con LLM** (Qwen) sobre features estructuradas.
- **Generación y ranking de clips** con export real (FFmpeg).
- **Timeline de valence/arousal** con formato casi idéntico al pedido.
- **Detección de hooks verbales** multilingüe vía LLM.
- **Filosofía "Potential Virality Score"** (no "Guaranteed"): las métricas se etiquetan como `derived`/`ai`/`unavailable`, sin prometer viralidad garantizada.

## Lo que NO coincide (huecos grandes)

1. **Virality Prediction Engine entrenado.** El spec pide entrenar con watch time, shares, saves, rewatch rate y un dataset real (TikTok/Reels/Shorts). Hoy es una fórmula `derived`, sin entrenamiento ni dataset. *Es justo lo que el documento marca como "lo más importante".*
2. **Fusion Transformer / Temporal Transformer propio.** Pieza central del diagrama del spec. No existe; la "fusión" es heurística.
3. **Retention model entrenado** sobre curvas reales — es heurístico.
4. **Audio superficial** — falta prosodia, pitch, speech speed, beat drops, risas/gritos y modelos de emoción de audio.
5. **Modelos recomendados ausentes:** EMOCA/OpenFace, Qwen2.5-VL, InternVideo2/Video-LLaMA, SlowFast/TimeSformer, clasificadores entrenados (ragebait, meme).
6. **Señales sociales/contexto** (timing, plataforma, trend) no modeladas.

---

## Resumen en una frase

El proyecto implementa fielmente **el andamiaje multimodal, la capa de
explicación y la generación de clips** del spec, pero **el corazón predictivo
—modelos entrenados de viralidad/retención y la fusión multimodal aprendida con
un dataset etiquetado— está pendiente**, sustituido por fórmulas compuestas
marcadas como `derived`.

## Próximos pasos para cerrar la brecha (si se quisiera)

1. Construir/etiquetar un **dataset** (segmento → retención/shares/saves/rewatch).
2. Entrenar un **`MLViralityPredictor`** y un **`MLRetentionPredictor`** reales
   (el código ya deja los puntos de extensión `VIRALITY_PREDICTOR_PROVIDER=ml` /
   `RETENTION_PREDICTOR_PROVIDER=ml`).
3. Añadir un **encoder/fusión temporal multimodal** (p. ej. Qwen2.5-VL o
   InternVideo2 + transformer de fusión) en lugar de la fusión heurística.
4. Enriquecer el **análisis de audio** (prosodia/pitch/beat drops con openSMILE/wav2vec2).
5. Incorporar **señales de contexto/plataforma** si se busca un score más realista.
