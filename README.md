# ✨ Aurea Viral Intelligence

**Aurea Viral Intelligence** es una aplicación local-first para analizar vídeos cortos y estimar su potencial de viralidad con una mezcla explícita de:

- modelos IA reales sobre el vídeo/audio/texto,
- señales audiovisuales reales derivadas con OpenCV/FFmpeg/librosa,
- métricas compuestas etiquetadas como `derived`,
- y una demo inicial mock claramente separada del flujo de upload real.

El objetivo actual del proyecto es muy concreto: **si el usuario sube un vídeo manualmente, el frontend no debe mostrar datos inventados, hardcodeados ni mock como si fueran análisis real**.

> Proyecto pensado como módulo/microservicio de [AureaSuite](https://www.aureasuite.ai/).

---

## 🟢 Estado actual del proyecto

**Fecha de estado:** 2026-06-16  
**Estado:** MVP funcional con guardrails contra datos falsos en uploads reales.

### Ya implementado

- ✅ Frontend React/Vite/Tailwind con dashboard visual y esfera 3D.
- ✅ Backend FastAPI con endpoints de análisis, upload, polling y health check.
- ✅ Upload real de vídeo y procesamiento en background.
- ✅ Demo inicial mock separada del modo upload real.
- ✅ Resultado backend con procedencia:
  - `analysis_source`
  - `provider_status`
  - `metric_sources`
- ✅ El worker **ya no convierte errores de uploads reales en mock silencioso**.
- ✅ El frontend ya no usa valores hardcodeados para uploads reales como `8.4s`, `88.4%`, `3.2x` o curvas default si falta información.
- ✅ Métricas no disponibles se muestran como `No disponible` o se ocultan.
- ✅ Tests backend y guardrails frontend añadidos.

### Importante sobre precisión IA

No todas las métricas numéricas son “IA pura”. El sistema distingue explícitamente:

| Tipo | Significado | Ejemplos |
|---|---|---|
| `ai` | Modelo IA real usado para esa señal/métrica | YOLO, DeepFace, VideoMAE, Qwen, Whisper, CLIP |
| `derived` | Fórmula o composición sobre señales reales | virality score, retention score si no hay modelo ML |
| `heuristic` | Regla local explícita | fallback configurable o provider heurístico |
| `mock` | Solo demo inicial | vídeo/datos de muestra |
| `unavailable` | No calculado de forma fiable | se oculta o muestra “No disponible” |

### Estado de providers principales

| Área | Provider actual/recomendado | Estado |
|---|---|---|
| Objetos/visual | YOLO | IA real si dependencias/modelo disponibles |
| Emoción | DeepFace | IA real si dependencias disponibles |
| Temporal/action | VideoMAE | IA real si `ENABLE_TEMPORAL_ANALYSIS=true` |
| Explicaciones | Qwen | IA generativa para texto/razones |
| Transcripción | Whisper/faster-whisper | IA real si `AUREA_WHISPER_ENABLED=true` |
| Memorabilidad/rewatch | CLIP | IA real si está disponible; si falla, no se inventa valor |
| Top clips | CLIP + señales reales | sin CLIP, no se inventa ranking IA |
| Pacing | PySceneDetect | cortes reales; si no está disponible, métrica unavailable |
| Retention | derivado o ML opcional | por defecto `derived`, ML solo con modelo configurado |
| Virality score | derivado o ML opcional | por defecto `derived_formula`, ML solo con modelo configurado |

---

## 🧭 Arquitectura

```text
virality-analyzer/
├─ frontend/                  React 19 + Vite 8 + Tailwind 4 + TypeScript
│  ├─ src/components/          Dashboard, gráficas, esfera 3D, transcript
│  ├─ src/hooks/               Upload, polling y carga de demo
│  ├─ src/stores/              Estado demo/upload/failed
│  └─ scripts/guardrails.mjs   Validación contra fallbacks frontend falsos
│
├─ backend/                   FastAPI + pipeline audiovisual
│  └─ app/
│     ├─ api/routes/           REST API
│     ├─ schemas/              Contrato Pydantic del resultado
│     ├─ services/             Storage, queue y orquestación
│     ├─ workers/              Jobs de análisis
│     ├─ processing/           FFmpeg, frames, audio, clips, escenas, timeline
│     └─ ai_services/          YOLO, DeepFace, VideoMAE, Qwen, Whisper, CLIP,
│                              predictors derived/ML y analyzers heurísticos
│
├─ shared/                    JSON Schema + tipos TypeScript compartidos
├─ uploads/                   Vídeos, frames, resultados y clips generados
├─ status.md                  Auditoría IA/heurística/mock del frontend
├─ ToDo.txt                   Plan de hardening IA para uploads reales
└─ docker-compose.yml         Redis opcional para workers RQ
```

Flujo simplificado:

```text
Upload vídeo
   │
   ▼
FastAPI crea analysis_id y job
   │
   ▼
Worker analiza vídeo real
   │
   ├─ FFmpeg/OpenCV/librosa: señales reales
   ├─ YOLO/DeepFace/VideoMAE/Whisper/CLIP/Qwen: IA si disponible
   ├─ métricas derived cuando corresponde
   └─ provider_status + metric_sources
   │
   ▼
Frontend poll /analysis/{id}
   │
   ├─ muestra datos reales/procedencia
   ├─ marca derived/composite cuando no es IA pura
   └─ oculta o marca unavailable si falta una métrica fiable
```

---

## 🚀 Quick start

### 1. Requisitos

- Node.js 20+
- Python 3.11+
- FFmpeg recomendado
- Redis opcional para cola RQ

### 2. Backend

```bash
cd virality-analyzer

python -m venv .venv
source .venv/bin/activate

# Dependencias base
pip install -e backend

# Recomendado para desarrollo completo local
pip install -e "backend[all,dev]"

# Servidor API
uvicorn app.main:app --reload --app-dir backend
```

API local: `http://127.0.0.1:8000`  
Swagger/OpenAPI: `http://127.0.0.1:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

UI local: `http://localhost:5173`

### 4. Redis opcional

Por defecto el backend puede usar cola en thread local. Para Redis/RQ:

```bash
docker compose up redis
AUREA_QUEUE_BACKEND=redis python -m backend.run_worker
```

---

## 🔌 API principal

Todas las rutas viven bajo `/api/viral-intelligence/`.

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/analysis/mock` | Demo inicial mock para UI |
| `POST` | `/analysis` | Upload de vídeo real |
| `GET` | `/analysis/{id}` | Polling/resultado de análisis |
| `GET` | `/analysis` | Listado de análisis |

Ejemplo rápido:

```bash
curl http://127.0.0.1:8000/api/viral-intelligence/health

curl -F "file=@sample.mp4" \
  http://127.0.0.1:8000/api/viral-intelligence/analysis

curl http://127.0.0.1:8000/api/viral-intelligence/analysis/<analysis_id>
```

---

## 🧠 Qué analiza el pipeline

1. **Probe del vídeo**: duración, fps, resolución y streams con FFmpeg/OpenCV.
2. **Frames**: sampling visual para movimiento, brillo y señales temporales.
3. **Detección visual**: YOLO si está activo/disponible.
4. **Emoción**: DeepFace para emoción dominante, arousal, valence e intensidad.
5. **Audio**: energía, silencios y cambios con librosa.
6. **Transcripción**: Whisper/faster-whisper si está activo.
7. **Hooks de texto**: Qwen por defecto configurable; regex solo si se fuerza.
8. **Pacing**: cortes reales con PySceneDetect si disponible.
9. **Memorabilidad/Rewatch**: CLIP si disponible; si no, no se inventa dato para uploads.
10. **Top clips**: ranking con señales reales e IA; razones descriptivas con Qwen cuando está disponible.
11. **Insights**: explicaciones y recomendaciones accionables.
12. **Provenance**: cada provider y métrica queda marcada como `ai`, `derived`, `heuristic`, `mock` o `unavailable`.

---

## 🏷️ Demo vs upload real

La app soporta dos mundos separados:

### Demo inicial

- Puede usar `/analysis/mock`.
- Puede mostrar datos sintéticos de muestra.
- Se marca como `demo-mock` / `demo_mock`.

### Upload manual real

- Debe usar el vídeo subido por el usuario.
- No puede caer a mock si falla el análisis.
- No puede usar números hardcodeados en frontend.
- Si una métrica no es fiable, se marca `unavailable`.
- Si una métrica es fórmula, se marca `derived` o `composite`, no “IA pura”.

---

## ⚙️ Variables de entorno útiles

La configuración base de `Settings` usa prefijo `AUREA_`. Los providers nuevos aceptan tanto nombre directo como con prefijo `AUREA_` en muchos casos.

### Recomendado para análisis real enriquecido

```bash
VISUAL_ANALYZER_PROVIDER=yolo
EMOTION_ANALYZER_PROVIDER=deepface
ENABLE_TEMPORAL_ANALYSIS=true
TEMPORAL_ANALYZER_PROVIDER=videomae
EXPLANATION_PROVIDER=qwen
TEXT_HOOK_ANALYZER=qwen
MEMORABILITY_SCORER=clip
CLIP_RANKER_ENABLED=true
SCENE_DETECTION_ENABLED=true
AUREA_WHISPER_ENABLED=true
AUREA_AUDIO_ENABLED=true
```

### Modelos ML opcionales para sustituir métricas derived

Por defecto, retention y virality son métricas derivadas/composite. Si se quieren modelos entrenados propios:

```bash
RETENTION_PREDICTOR_PROVIDER=ml
RETENTION_MODEL_PATH=/ruta/al/modelo_retention.joblib

VIRALITY_PREDICTOR_PROVIDER=ml
VIRALITY_MODEL_PATH=/ruta/al/modelo_virality.joblib
```

### Infraestructura

| Variable | Default | Descripción |
|---|---:|---|
| `AUREA_ENVIRONMENT` | `local` | Entorno lógico |
| `AUREA_CORS_ORIGINS` | localhost | Orígenes permitidos |
| `AUREA_AUTH_ENABLED` | `false` | Placeholder de auth/Clerk |
| `AUREA_STORAGE_BACKEND` | `local` | Storage local/S3 futuro |
| `AUREA_QUEUE_BACKEND` | `thread` | `thread` o `redis` |
| `AUREA_REDIS_URL` | `redis://localhost:6379/0` | Redis para RQ |
| `VITE_API_BASE_URL` | vacío | URL backend desde frontend si hace falta |

---

## ✅ Validación y calidad

Comandos principales:

```bash
# Backend
.venv/bin/python -m pytest backend/tests

# Frontend
cd frontend
npm run build
npm run test:guardrails
```

Última validación conocida:

```text
Backend tests:        37 passed
Frontend guardrails:  passed
Frontend build:       passed
```

Los guardrails frontend comprueban que no se reintroduzcan fallbacks falsos en modo upload, por ejemplo:

- attention duration hardcodeado,
- retention/rewatch hardcodeados,
- timeline default para uploads reales,
- transcript inventado,
- top clips inventados,
- pacing/hook derivados en frontend sin datos backend.

---

## 🧪 Comandos de desarrollo

```bash
# Backend dev server
uvicorn app.main:app --reload --app-dir backend

# Backend tests
.venv/bin/python -m pytest backend/tests

# Frontend dev server
cd frontend && npm run dev

# Frontend production build
cd frontend && npm run build

# Frontend anti-regression guardrails
cd frontend && npm run test:guardrails

# Redis opcional
docker compose up redis
```

---

## 📌 Notas de producto

- El score de viralidad debe entenderse como **“Potential Virality Score”**, no como garantía de viralidad.
- Qwen se usa para explicaciones/razones/texto, no para falsear scores numéricos.
- La demo puede ser mock; el upload real no.
- Si un provider IA falla, el resultado debe ser parcial, `unavailable` o `failed`, pero no mock silencioso.
- `status.md` contiene una auditoría detallada del estado IA/heurística/mock.
- `ToDo.txt` contiene el plan operativo de endurecimiento del flujo real.

---

## 🔒 Licencia

Private — All rights reserved.
