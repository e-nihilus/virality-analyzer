<div align="center">

# 🎬 Aurea Viral Intelligence

### Análisis de vídeo *local-first* para estimar el potencial de viralidad

Detecta momentos de alta retención · visualiza la emoción temporal · genera recomendaciones accionables con clips candidatos.

<br/>

[![Status](https://img.shields.io/badge/status-MVP%20funcional-success?style=for-the-badge)](#-estado-actual)
[![Phases](https://img.shields.io/badge/fases-13%2F15-blue?style=for-the-badge)](#-estado-actual)
[![License](https://img.shields.io/badge/license-privada-lightgrey?style=for-the-badge)](#-licencia)

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind-4-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?logo=ffmpeg&logoColor=white)](https://ffmpeg.org/)

<br/>

Forma parte de **[AureaSuite](https://www.aureasuite.ai/)** — diseñado para integrarse como módulo *microservice*.

</div>

---

## 📑 Tabla de contenidos

- [✨ Estado actual](#-estado-actual)
- [🚀 Características](#-características)
- [🏗️ Arquitectura](#️-arquitectura)
- [📦 Requisitos](#-requisitos)
- [⚡ Quick Start](#-quick-start)
- [🔌 API Endpoints](#-api-endpoints)
- [🧠 Pipeline de análisis](#-pipeline-de-análisis)
- [⚙️ Variables de entorno](#️-variables-de-entorno)
- [🛠️ Comandos clave](#️-comandos-clave)
- [🧭 Filosofía de desarrollo](#-filosofía-de-desarrollo)
- [📄 Licencia](#-licencia)

---

## ✨ Estado actual

> **Fases completadas: 1–13** de 15. El proyecto es un MVP funcional con análisis real de vídeo, inteligencia opcional de voz/audio y procesamiento basado en colas.

| Fase | Descripción | Estado |
|:---:|-------------|:---:|
| 1 | Estructura monorepo & docs | ✅ |
| 2 | Frontend Vite + Tailwind + tokens Stitch | ✅ |
| 3 | HTML Stitch → componentes React | ✅ |
| 4 | Backend FastAPI + contrato mock | ✅ |
| 5 | Conexión Frontend ↔ Backend | ✅ |
| 6 | Subida MP4 + persistencia local | ✅ |
| 7 | Pipeline real de vídeo (FFmpeg + OpenCV) | ✅ |
| 8 | Ciclo de vida de jobs + polling | ✅ |
| 9 | Motor de explicación + insights accionables | ✅ |
| 10 | Exportación de clips con FFmpeg | ✅ |
| 11 | Voz/NLP opcional (Whisper) | ✅ |
| 12 | Features de audio opcionales (librosa) | ✅ |
| 13 | Cola real & workers externos (RQ/Redis) | ✅ |
| 14 | Adaptadores multimodales avanzados de IA | ⬚ |
| 15 | Tests, calidad & empaquetado local | ⬚ |

---

## 🚀 Características

- 🎨 **UI profesional** — dashboard React/Vite/Tailwind en modo oscuro inspirado en Stitch *Cinematic Intelligence Lab*, responsive escritorio y móvil
- 📤 **Subida de vídeo** — arrastrar y soltar MP4/MOV/WebM/AVI/MKV (máx. 200 MB), validado en cliente y servidor
- 🎞️ **Análisis real de vídeo** — muestreo de frames con OpenCV, detección de movimiento, análisis de brillo, scoring heurístico
- 🔧 **Integración FFmpeg** — extracción de metadatos opcional vía `ffprobe` (cae a OpenCV si no está disponible)
- 🔊 **Análisis de audio** *(opcional)* — energía RMS, detección de silencios y cambios de energía vía librosa; fusionado en el timeline para mejor precisión de arousal/retención
- 🗣️ **Transcripción de voz** *(opcional)* — integración faster-whisper para transcripción automática y detección de hooks verbales (curiosity gap, urgencia, conflicto, preguntas, órdenes, sorpresa)
- ⚙️ **Procesamiento en segundo plano** — análisis despachado vía cola RQ/Redis o fallback a hilo en proceso; la API responde al instante y el frontend hace polling del progreso
- 📈 **Timeline unificado** — scores por segundo de viralidad, arousal, valencia y retención con etiquetas auto-detectadas (hook, ruptura de patrón, caída de retención, pico de movimiento, silencio, pico de audio)
- ✂️ **Ranking de clips** — detección automática de los mejores clips candidatos a partir de los picos de viralidad
- 💡 **Motor de explicación** — 8+ generadores de insights basados en reglas, con recomendaciones accionables y marcas de tiempo, ampliado con insights de hooks verbales cuando hay transcripción
- 📝 **Panel de transcripción** — componente frontend con segmentos de transcripción marcados en el tiempo, badges de hook y sincronizados con la reproducción
- 🧩 **Fallback mock** — la UI completa funciona offline con datos sintéticos cuando el backend no está disponible
- 🔐 **AureaSuite-ready** — placeholders de auth, rutas API con namespace, backends de almacenamiento y cola configurables

---

## 🏗️ Arquitectura

```
virality-analizer/
├─ frontend/          React 19 + Vite 8 + Tailwind 4 + TypeScript
├─ backend/           FastAPI + OpenCV + pipeline FFmpeg
│  └─ app/
│     ├─ api/routes/  Endpoints REST
│     ├─ schemas/     Modelos Pydantic (fuente de verdad)
│     ├─ services/    Orquestación, almacenamiento, dispatch de cola
│     ├─ processing/  Probe FFmpeg, extracción de frames/audio, timeline, ranking de clips
│     ├─ ai_services/ Heurística, voz (Whisper), audio (librosa), hook de texto, motor de explicación
│     ├─ workers/     Jobs de análisis en background
│     └─ core/        Config, paths, placeholder de auth
├─ shared/            JSON schemas + tipos TypeScript
├─ uploads/           Vídeos + resultados de análisis (gitignored)
└─ docs/              Docs de arquitectura & contrato de API
```

```diagram
╭──────────╮   upload    ╭──────────╮   dispatch   ╭──────────╮
│ Frontend │────────────▶│ FastAPI  │─────────────▶│  Worker  │
│  React   │◀────────────│   API    │◀─────────────│ RQ/Hilo  │
╰──────────╯   polling   ╰────┬─────╯   resultado  ╰────┬─────╯
                              │                          │
                              ▼                          ▼
                        ╭──────────╮              ╭──────────────╮
                        │ uploads/ │              │ FFmpeg·OpenCV │
                        │ + JSON   │              │ librosa·Whisper│
                        ╰──────────╯              ╰──────────────╯
```

---

## 📦 Requisitos

| Herramienta | Versión | Notas |
|-------------|---------|-------|
| **Node.js** | 20+ | Frontend |
| **Python** | 3.11+ | Backend |
| **FFmpeg** | — | Recomendado, para metadatos y audio precisos |
| **Git** | — | — |
| **Redis** | — | *Opcional*, para workers de cola RQ |

---

## ⚡ Quick Start

### 1️⃣ Clonar & preparar

```bash
git clone <repo-url>
cd virality-analizer
```

### 2️⃣ Backend

```bash
# Crear y activar entorno virtual
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows Git Bash
source .venv/Scripts/activate
# macOS/Linux
source .venv/bin/activate

# Instalar dependencias core
pip install -e backend

# Extras opcionales (instala cualquier combinación)
pip install -e "backend[audio]"       # librosa + soundfile (análisis de audio)
pip install -e "backend[speech]"      # faster-whisper (transcripción)
pip install -e "backend[queue]"       # redis + rq (workers de cola)
pip install -e "backend[all]"         # todo lo anterior

# Arrancar el servidor (auto-reload)
uvicorn app.main:app --reload --app-dir backend
```

> 🌐 La API estará disponible en `http://127.0.0.1:8000`. Docs interactivas en `/docs`.

### 3️⃣ Frontend

```bash
cd frontend
npm install
npm run dev
```

> 🖥️ La UI estará disponible en `http://localhost:5173`.

### 4️⃣ Verificar

```bash
# Health check del backend
curl http://127.0.0.1:8000/api/viral-intelligence/health

# Análisis mock (sin vídeo)
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/mock

# Subir un vídeo para análisis real
curl -F "file=@sample.mp4" http://127.0.0.1:8000/api/viral-intelligence/analysis

# Consultar estado/resultado del análisis
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/<analysis_id>
```

---

## 🔌 API Endpoints

Todas las rutas bajo `/api/viral-intelligence/`:

| Método | Ruta | Descripción |
|:---:|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/analysis/mock` | Análisis mock completo para desarrollo de UI |
| `POST` | `/analysis` | Subir vídeo → inicia análisis en background |
| `GET` | `/analysis/{id}` | Obtener estado & resultados del análisis |
| `GET` | `/analysis` | Listar todos los análisis |

### 🔄 Ciclo de vida del análisis

```
POST /analysis (upload) → status: "processing", progress: 0.0
GET  /analysis/{id}     → status: "processing", progress: 0.1–0.9
GET  /analysis/{id}     → status: "completed",  progress: 1.0, resultados completos
```

> ⏱️ El frontend hace polling cada 1.5 segundos hasta `completed` o `failed`.

---

## 🧠 Pipeline de análisis

Cuando se sube un vídeo, el backend despacha un job (vía RQ o fallback a hilo):

1. **🔍 Probe** — `ffprobe` extrae duración, FPS, resolución, códecs (cae a OpenCV)
2. **🎞️ Extracción de frames** — muestrea un frame por segundo, guardado como JPEG en `uploads/<id>/frames/`
3. **👁️ Señales visuales** — calcula diferencias inter-frame (movimiento) y brillo por muestra
4. **🔊 Extracción de audio** *(opcional)* — FFmpeg exporta WAV mono; librosa calcula energía RMS, silencios y cambios de energía por segundo
5. **📈 Timeline** — normaliza y suaviza señales visuales + audio en scores por segundo de viralidad/arousal/valencia/retención
6. **✂️ Ranking de clips** — detecta picos de viralidad, expande ventanas, rankea top 3 candidatos
7. **🗣️ Transcripción de voz** *(opcional)* — faster-whisper transcribe el audio; el analizador de hooks de texto detecta hooks verbales (curiosity gap, urgencia, conflicto, etc.)
8. **💡 Motor de explicación** — genera insights desde 8+ categorías de reglas con marcas de tiempo y recomendaciones accionables

### 📋 Categorías de insights

| Regla | Detecta |
|-------|---------|
| Análisis de hook | Fuerza de apertura (primeros 3 segundos) |
| Ruptura de patrón | Picos de viralidad por cambios de escena |
| Caídas de retención | Puntos de riesgo de abandono |
| Arco emocional | Dinámicas de arousal/valencia |
| Ritmo | Cadencia visual rápida/lenta |
| Razonamiento de clips | Por qué se seleccionó cada clip |
| Score global | Explicación del score general |
| Fuerza del final | Potencial de loop & impacto de cierre |
| Hooks verbales *(opcional)* | Curiosity gap, urgencia, conflicto, preguntas en el habla |

---

## ⚙️ Variables de entorno

Todas con prefijo `AUREA_`:

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `AUREA_ENVIRONMENT` | `local` | `local` / `staging` / `production` |
| `AUREA_CORS_ORIGINS` | `localhost:5173` | Orígenes CORS permitidos |
| `AUREA_AUTH_ENABLED` | `false` | Habilitar validación JWT de Clerk |
| `AUREA_STORAGE_BACKEND` | `local` | `local` / `s3` |
| `AUREA_QUEUE_BACKEND` | `thread` | `thread` (en proceso) / `redis` (workers RQ) |
| `AUREA_REDIS_URL` | `redis://localhost:6379/0` | URL de conexión a Redis |
| `AUREA_WHISPER_ENABLED` | `false` | Habilitar transcripción de voz vía faster-whisper |
| `AUREA_WHISPER_MODEL` | `small` | Tamaño del modelo Whisper (`tiny` / `base` / `small` / `medium` / `large`) |
| `AUREA_AUDIO_ENABLED` | `true` | Habilitar análisis de features de audio vía librosa |
| `AUREA_VISUAL_ANALYZER_PROVIDER` | `heuristic` | `heuristic` / `yolo` (YOLO cae a heurística si falta la dependencia) |
| `AUREA_EMOTION_ANALYZER_PROVIDER` | `heuristic` | `heuristic` / `deepface` (DeepFace cae a heurística si falta la dependencia) |
| `AUREA_ENABLE_TEMPORAL_ANALYSIS` | `false` | Habilitar etapa de análisis temporal (deshabilitada por defecto) |
| `AUREA_TEMPORAL_ANALYZER_PROVIDER` | `heuristic` | `heuristic` / `videomae` (VideoMAE cae a heurística si falta la dependencia) |
| `AUREA_EXPLANATION_PROVIDER` | `heuristic` | `heuristic` / `qwen` (Qwen solo para explicaciones, nunca scoring) |
| `AUREA_EXPLANATION_CACHE_ENABLED` | `true` | Habilitar caché de explicaciones en memoria |
| `VITE_API_BASE_URL` | (vacío) | URL del backend para el frontend |

---

## 🛠️ Comandos clave

```bash
# ── Frontend ──
cd frontend
npm run dev          # Dev server con HMR
npm run build        # Build de producción (TypeScript + Vite)
npm run preview      # Preview del build de producción
npm run lint         # ESLint

# ── Backend ──
uvicorn app.main:app --reload --app-dir backend   # Dev server
python -m pytest backend/tests                      # Tests (cuando estén disponibles)

# ── Quick start (ambos) ──
bash start.sh                                       # Lanza backend + frontend juntos

# ── Cola Redis (opcional) ──
docker compose up redis                             # Arranca Redis vía Docker
AUREA_QUEUE_BACKEND=redis python -m backend.run_worker  # Arranca worker RQ

# ── FFmpeg ──
ffmpeg -version                                     # Verificar instalación
ffprobe -v quiet -print_format json -show_format -show_streams video.mp4  # Probe manual
```

---

## 🧭 Filosofía de desarrollo

1. **📜 Contract first** — UI y backend conectan vía un JSON schema estable
2. **🧩 Mock before block** — si falta FFmpeg/modelo/GPU, usa mock con aviso explícito
3. **💻 MVP local-first** — nada requiere cloud, login o API keys para funcionar
4. **🔌 Adaptadores, no refactors gigantes** — cada modelo de IA conecta tras una interfaz existente
5. **✅ Validación continua** — cada fase termina con un check mínimo build/test/curl
6. **📊 Siempre "Potential Virality Score"** — nunca garantizar viralidad
7. **🔗 Integration-ready** — todas las decisiones contemplan el futuro embebido en AureaSuite

---

## 📄 Licencia

Privada — Todos los derechos reservados.

<div align="center">
<br/>
Hecho con 🎬 por el equipo de <a href="https://www.aureasuite.ai/">AureaSuite</a>
</div>
