# Plan de desarrollo V2 — Núcleo predictivo de viralidad (Aurea Viral Intelligence)

## 0. Resumen ejecutivo

`plan.md` (Fases 1-15) entrega un **producto integrable** que orquesta modelos
preentrenados (YOLO, DeepFace, CLIP, Qwen, Whisper, VideoMAE) y combina sus
señales con **fórmulas compuestas (`derived`)**. Lo que NO entrega —y que
[`Predicción de viralidad.md`](./Predicción%20de%20viralidad.md) marca como "lo más
importante"— es el **corazón predictivo entrenado**:

- un **dataset etiquetado** (watch time / shares / saves / rewatch / retención),
- una **fusión multimodal temporal aprendida** (Fusion/Temporal Transformer),
- modelos **entrenados** de retención y de viralidad,
- audio/emoción profundos y clasificadores de texto entrenados,
- evaluación cuantitativa contra ground-truth.

Este `planV2.md` define las fases para construir eso **a partir del estado
actual**, reutilizando los puntos de extensión que el código ya tiene
(`provider_factory.py`, `MLViralityPredictor`, `MLRetentionPredictor`,
`VIRALITY_PREDICTOR_PROVIDER=ml`, `RETENTION_PREDICTOR_PROVIDER=ml`).

> **Expectativa realista:** completar este plan acerca el proyecto a un sistema
> predictivo de viralidad real y validado. NO lo convierte en un foundation model
> tipo Meta/TRIBE (eso requiere datos y cómputo a escala de laboratorio). El
> objetivo es "lo más parecido posible" al spec, con un **Potential Virality
> Score** calibrado y explicable, no viralidad garantizada.

---

## 1. Punto de partida (estado actual)

Ya implementado y reutilizable:

- Pipeline multimodal por adapters: visual (YOLO/heurístico), emoción (DeepFace),
  memorabilidad (CLIP), temporal (VideoMAE), explicación (Qwen), voz (Whisper),
  audio (librosa), pacing (PySceneDetect).
- `timeline[]` por segundo con `virality/arousal/valence/retention` + labels.
- Ranking de clips, hooks de texto, valence/arousal, explanation engine.
- Contrato estable (`AnalysisResult`, `metric_sources`, `provider_status`).
- Caché de modelos + warm-up + GPU; decodificación única del vídeo.
- Puntos de extensión ML ya presentes pero **sin modelo**:
  `MLViralityPredictor`, `MLRetentionPredictor` (cargan `*.joblib/.pkl`).

Brechas que cubre este plan: dataset, embeddings multimodales ricos, audio/emoción
profundos, clasificadores entrenados, fusion transformer, modelos de
retención/viralidad entrenados, evaluación y MLOps.

---

## 2. Decisiones técnicas base (V2)

### Featurización
- Pasar de "señales escalares heurísticas" a **embeddings por ventana** (3s, stride 1s).
- Persistir features por `analysis_id` para reentrenar sin recomputar.

### Modelado
- Targets entrenables, no solo views: **watch time, shares, saves, rewatch, curva de retención**.
- Salida siempre como **probabilidad/score calibrado** ("Potential Virality").
- Mantener fallback `derived` cuando no haya modelo (no romper el contrato actual).

### Infra
- Entrenamiento offline (PyTorch/Lightning) separado del serving (FastAPI).
- Versionado de modelos y features; serving por adapter (mismo patrón actual).

### Compatibilidad
- Todo modelo nuevo entra detrás del `provider_factory` con su feature flag.
- Sin GPU o sin modelo → el sistema sigue funcionando en modo `derived`.

---

## 3. Roadmap ejecutable por fases

---

## Fase 1 — Featurización multimodal por ventanas (embeddings)

### Objetivo
Reemplazar las señales escalares por **embeddings ricos** por ventana temporal,
base de cualquier modelo aprendido.

### Archivos a crear/modificar
- `backend/app/ai_services/embeddings/video_embedder.py` (V-JEPA2 / InternVideo2 / VideoMAE features).
- `backend/app/ai_services/embeddings/audio_embedder.py` (Wav2Vec2 / encoder de Whisper).
- `backend/app/ai_services/embeddings/text_embedder.py` (embeddings de transcript/segmentos).
- `backend/app/processing/window_builder.py` (ventanas 3s / stride 1s).
- `backend/app/ai_services/feature_store.py` (persistencia de features por `analysis_id`).

### Dependencias necesarias
- `torch`, `transformers`, modelos de embeddings (V-JEPA2/InternVideo2/wav2vec2).

### Amp puede hacer automáticamente
- Crear interfaces de embedder y el window builder.
- Persistir vectores por ventana en disco/parquet.
- Integrar caché y reutilización de frames ya decodificados.

### HUMAN ACTION REQUIRED
- Elegir backbones concretos y aceptar descargas/licencias.
- Confirmar GPU/VRAM suficiente para embeddings de vídeo.

### Criterios de finalización
- Cada análisis produce un tensor `(n_ventanas, dim_video+dim_audio+dim_texto)` persistido.
- Sin GPU/modelo → fallback a las señales escalares actuales.

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_embeddings.py
```

---

## Fase 2 — Análisis de audio profundo (prosodia y emoción)

### Objetivo
Cubrir las features de audio del spec: pitch, velocidad de habla, beat drops,
risas/gritos, intensidad y emoción de voz.

### Archivos a crear/modificar
- `backend/app/ai_services/audio_analyzer.py` (ampliar).
- `backend/app/ai_services/audio_emotion.py` (wav2vec2-emotion / openSMILE).
- `backend/app/ai_services/audio_events.py` (beat drops, laughter/scream, silencios).

### Dependencias necesarias
- `openSMILE`, `torchaudio`, `wav2vec2` emotion model, `pyannote.audio` (opcional).

### Amp puede hacer automáticamente
- Extraer prosodia (pitch variance, speech rate) y eventos de audio.
- Integrar features en el feature store y en `timeline.arousal`.

### HUMAN ACTION REQUIRED
- Token de Hugging Face para `pyannote` (si se usa).
- Aceptar licencias de modelos de audio.

### Criterios de finalización
- Por ventana: pitch, speech_rate, beat_drop, laughter/scream, voice_intensity.
- Estas features alimentan emoción y modelos posteriores.

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_audio_features.py
```

---

## Fase 3 — Emoción multimodal Valence/Arousal (estilo Hume)

### Objetivo
Fusionar emoción **facial + audio + texto** en una curva valence/arousal con
confianza, en vez de solo facial (DeepFace).

### Archivos a crear/modificar
- `backend/app/ai_services/emotion_analyzer.py` (ampliar a fusión).
- `backend/app/ai_services/emotion/face_emotion.py` (EMOCA/OpenFace: eye contact, gaze).
- `backend/app/ai_services/emotion/text_emotion.py` (GoEmotions / DeBERTa-emotion).
- `backend/app/ai_services/emotion/va_fusion.py` (fusión → valence/arousal + confidence).

### Dependencias necesarias
- `EMOCA`/`OpenFace` (facial avanzado), `transformers` (GoEmotions/DeBERTa).

### Amp puede hacer automáticamente
- Crear adaptadores de emoción facial/texto y el fusor V/A.
- Emitir `{timestamp, valence, arousal, emotion, confidence}` por ventana.

### HUMAN ACTION REQUIRED
- Instalar/compilar OpenFace o EMOCA (a veces requiere build manual).
- Aceptar licencias (algunas no comerciales).

### Criterios de finalización
- Timeline V/A multimodal con `confidence`; fallback a DeepFace si falta algo.

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_va_fusion.py
```

---

## Fase 4 — Dataset de entrenamiento (recolección + etiquetado)

### Objetivo
Construir el **dataset** que el spec considera imprescindible: segmentos de vídeo
con métricas reales de engagement. Es el cuello de botella del proyecto.

### Archivos a crear/modificar
- `data/collectors/` (scrapers/exportadores por plataforma).
- `data/schema.py` (esquema de labels: hook_strength, shareability, retention_score, novelty, ragebait, memeability).
- `data/build_dataset.py` (featurización + alineación señales↔labels).
- `data/dataset_card.md` (origen, licencias, sesgos).

### Dependencias necesarias
- APIs oficiales (YouTube Data API, etc.) o exportes propios; `pandas`, `pyarrow`.

### Amp puede hacer automáticamente
- Definir esquema, pipeline de featurización y splits train/val/test.
- Generar dataset cards y validaciones de integridad.

### HUMAN ACTION REQUIRED
- **Crítico:** conseguir datos legalmente (ToS de TikTok/IG/YT, derechos, GDPR).
- Acceso a métricas reales (watch time/shares/saves/rewatch/retención).
- Decisiones de etiquetado y, si aplica, anotación humana.

### Criterios de finalización
- Dataset versionado `train/val/test` con features + labels alineados por ventana.
- Documentadas fuentes, licencias y limitaciones.

### Validaciones/tests mínimos
```bash
python data/build_dataset.py --check
```

---

## Fase 5 — Clasificadores de texto/hook entrenados

### Objetivo
Pasar de hooks zero-shot (Qwen) a clasificadores **entrenados/calibrados**:
hook, curiosity gap, conflict, urgency, ragebait, meme.

### Archivos a crear/modificar
- `backend/app/ai_services/text_hook_analyzer.py` (añadir provider entrenado).
- `training/text_classifiers/train.py` (fine-tune DeBERTa/RoBERTa o destilar Qwen).
- `models/text/` (pesos entrenados).

### Dependencias necesarias
- `transformers`, `datasets`, `scikit-learn`.

### Amp puede hacer automáticamente
- Pipeline de entrenamiento, métricas y export.
- Adapter de inferencia detrás de `TEXT_HOOK_ANALYZER=trained`.

### HUMAN ACTION REQUIRED
- Etiquetas de texto del dataset (Fase 4).
- Revisión de calidad/sesgos de los clasificadores.

### Criterios de finalización
- Clasificadores con F1 reportado en test; fallback a Qwen/regex.

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_text_classifiers.py
```

---

## Fase 6 — Fusion Transformer temporal (núcleo multimodal)

### Objetivo
Construir y entrenar la **fusión multimodal temporal** del spec: embeddings
(vídeo+audio+texto+emoción) por ventana → transformer temporal → predicciones por
ventana (engagement/novelty/retención/clipability).

### Archivos a crear/modificar
- `training/fusion/model.py` (transformer temporal multimodal).
- `training/fusion/datamodule.py`, `training/fusion/train.py` (PyTorch Lightning).
- `backend/app/ai_services/multimodal_fusion.py` (adapter de inferencia).

### Dependencias necesarias
- `torch`, `pytorch-lightning`, `einops`.

### Amp puede hacer automáticamente
- Implementar arquitectura, training loop, checkpoints y export.
- Adapter de inferencia que produce scores por ventana.

### HUMAN ACTION REQUIRED
- Dataset (Fase 4) y GPU para entrenar.
- Decisiones de arquitectura/hiperparámetros y presupuesto de cómputo.

### Criterios de finalización
- Modelo entrenado que emite scores por ventana; integrado tras feature flag.
- Métricas de entrenamiento/val registradas.

### Validaciones/tests mínimos
```bash
python -m training.fusion.train --fast-dev-run
```

---

## Fase 7 — Modelo de retención entrenado

### Objetivo
Sustituir la retención heurística por un modelo entrenado sobre **curvas de
retención reales** (predice retención por segundo).

### Archivos a crear/modificar
- `backend/app/ai_services/retention_predictor.py` (usar `MLRetentionPredictor`).
- `training/retention/train.py`; `models/retention/model.joblib`.

### Dependencias necesarias
- `xgboost`/`scikit-learn`/`torch` según arquitectura; `joblib`.

### Amp puede hacer automáticamente
- Entrenamiento, export y wiring vía `RETENTION_PREDICTOR_PROVIDER=ml`.

### HUMAN ACTION REQUIRED
- Curvas de retención reales en el dataset.

### Criterios de finalización
- `retention` marcado `source_type=ai`; MAE de la curva reportado en test.

### Validaciones/tests mínimos
```bash
RETENTION_PREDICTOR_PROVIDER=ml RETENTION_MODEL_PATH=models/retention/model.joblib \
  python -m pytest backend/tests/test_retention_predictor.py
```

---

## Fase 8 — Virality Prediction Engine entrenado

### Objetivo
Lo central del spec: un modelo **entrenado** que prediga viralidad (global y por
ventana) desde watch time/shares/saves/rewatch, calibrado como probabilidad.

### Archivos a crear/modificar
- `backend/app/ai_services/virality_predictor.py` (usar `MLViralityPredictor`).
- `training/virality/train.py`; `models/virality/model.*`.
- `backend/app/ai_services/calibration.py` (calibración de probabilidades).

### Dependencias necesarias
- `torch`/`xgboost`, `scikit-learn` (calibración isotónica/Platt).

### Amp puede hacer automáticamente
- Entrenamiento, calibración, export y wiring vía `VIRALITY_PREDICTOR_PROVIDER=ml`.

### HUMAN ACTION REQUIRED
- Dataset con métricas de engagement (Fase 4); GPU.

### Criterios de finalización
- `overall_virality_score` y `timeline.virality` marcados `source_type=ai`.
- Correlación con engagement real reportada; probabilidades calibradas.

### Validaciones/tests mínimos
```bash
VIRALITY_PREDICTOR_PROVIDER=ml python -m pytest backend/tests/test_virality_predictor.py
```

---

## Fase 9 — Detección de momentos virales y clips con el modelo

### Objetivo
Usar los scores **aprendidos** por ventana para detectar hooks/payoff/reveal/
picos emocionales y mejorar el ranking de clips (clipability aprendida).

### Archivos a crear/modificar
- `backend/app/processing/clip_ranker.py` (usar scores del fusion model).
- `backend/app/processing/moment_detector.py` (sliding window + peak detection).

### Dependencias necesarias
- Las de fases anteriores.

### Amp puede hacer automáticamente
- Integrar scores por ventana en detección de picos y ranking.

### HUMAN ACTION REQUIRED
- Ninguna obligatoria (depende de Fase 6/8).

### Criterios de finalización
- Top clips rankeados por score aprendido + razones; metric_source actualizado.

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_clip_ranker.py
```

---

## Fase 10 — Explanation engine sobre predicciones reales

### Objetivo
Que las explicaciones reflejen **por qué el modelo** predice viralidad
(atribuciones de features) en vez de solo describir señales.

### Archivos a crear/modificar
- `backend/app/ai_services/explanation_generator.py` (incluir feature attributions).
- `backend/app/ai_services/attributions.py` (SHAP/importancias del modelo).

### Dependencias necesarias
- `shap` (o importancias nativas), `transformers` (Qwen para redacción).

### Amp puede hacer automáticamente
- Calcular atribuciones y pasarlas como evidencia al LLM.

### HUMAN ACTION REQUIRED
- Ninguna obligatoria.

### Criterios de finalización
- Cada insight cita factores que el modelo realmente ponderó.

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_explanation.py
```

---

## Fase 11 — Señales de contexto/plataforma (Potential Virality)

### Objetivo
Incorporar (cuando haya datos) timing, plataforma y trend alignment, y comunicar
explícitamente "Potential Virality", no garantizada.

### Archivos a crear/modificar
- `backend/app/ai_services/context_signals.py`.
- `backend/app/schemas/analysis.py` (campos de contexto/confianza).

### Dependencias necesarias
- Fuentes de tendencias/plataforma (APIs externas, opcional).

### Amp puede hacer automáticamente
- Añadir features de contexto al modelo y al contrato.

### HUMAN ACTION REQUIRED
- Acceso a datos de tendencias/plataforma si se desean.

### Criterios de finalización
- El score expone incertidumbre y contexto; UI muestra "Potential".

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_context_signals.py
```

---

## Fase 12 — Evaluación, calibración y validación cuantitativa

### Objetivo
Demostrar que el sistema **predice** (no solo describe): métricas contra
ground-truth en un holdout.

### Archivos a crear/modificar
- `evaluation/run_eval.py`, `evaluation/report.md`.

### Dependencias necesarias
- `scikit-learn`, `scipy`.

### Amp puede hacer automáticamente
- Métricas: correlación con engagement, MAE de retención, NDCG de clips, calibración (ECE).
- Reporte reproducible sobre test set.

### HUMAN ACTION REQUIRED
- Definir umbrales de aceptación de negocio.

### Criterios de finalización
- Reporte con métricas en test; baseline `derived` vs modelo entrenado.

### Validaciones/tests mínimos
```bash
python evaluation/run_eval.py --split test
```

---

## Fase 13 — Serving a escala y MLOps

### Objetivo
Operar los modelos de forma estable: versionado, batching, reentrenamiento y
monitorización de drift.

### Archivos a crear/modificar
- `backend/app/ai_services/model_registry.py`.
- `serving/` (batching/Triton/vLLM si aplica), `mlops/retrain.py`, `mlops/monitor.py`.

### Dependencias necesarias
- `mlflow`/registry, `triton`/`vllm` (opcional), colas (RQ/Redis ya presente).

### Amp puede hacer automáticamente
- Registry de versiones, carga por versión, batching de inferencia.
- Pipeline de reentrenamiento y métricas de monitorización.

### HUMAN ACTION REQUIRED
- Infra de cómputo/almacenamiento; política de reentrenamiento.

### Criterios de finalización
- Modelos versionados y servidos; reentrenamiento y drift monitor operativos.

### Validaciones/tests mínimos
```bash
python -m pytest backend/tests/test_model_registry.py
```

---

## 4. Orden recomendado de ejecución

El **dataset (Fase 4) es el cuello de botella**: empezar a recolectarlo cuanto
antes, en paralelo a las fases de featurización.

1. **En paralelo desde el día 1:** Fase 4 (dataset) ⟷ Fases 1-3 (embeddings, audio, emoción).
2. Fase 5 — clasificadores de texto (necesita labels de Fase 4).
3. Fase 6 — Fusion Transformer (necesita Fases 1-4).
4. Fase 7 — retención entrenada · Fase 8 — viralidad entrenada (núcleo).
5. Fase 9 — momentos/clips con el modelo · Fase 10 — explicaciones reales.
6. Fase 11 — contexto/plataforma (opcional).
7. Fase 12 — evaluación/calibración (gate de calidad antes de producción).
8. Fase 13 — serving/MLOps.

## 5. Filosofía V2 (extiende la de plan.md)

1. **Datos primero:** sin dataset etiquetado no hay predicción real; es la prioridad.
2. **Adapters, no rupturas:** todo modelo entra tras `provider_factory` con feature flag.
3. **Fallback siempre:** sin modelo/GPU, el sistema sigue en modo `derived`.
4. **Calibración y honestidad:** "Potential Virality Score" con incertidumbre, nunca garantía.
5. **Evaluable:** cada modelo se acepta solo con métricas en holdout.
6. **Reproducible:** features y modelos versionados; entrenamiento separado del serving.

## 6. Qué se logra al terminar este plan

- Núcleo predictivo **entrenado** (viralidad + retención) sobre datos reales.
- **Fusión multimodal temporal aprendida** en lugar de fórmulas heurísticas.
- Emoción V/A y audio profundos; clasificadores de hook entrenados.
- Detección de momentos y clips guiada por el modelo, con explicaciones ancladas.
- **Validación cuantitativa** contra ground-truth.

Esto cubre lo esencial de `Predicción de viralidad.md`. Lo que quedaría fuera de
alcance razonable (y que el propio spec sitúa como "state of the art") es igualar
un foundation model a escala de laboratorio; el límite práctico lo pone la
**cantidad y calidad del dataset** y el **presupuesto de cómputo**.
