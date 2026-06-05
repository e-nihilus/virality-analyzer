# Plan de desarrollo ejecutable — Aurea Viral Intelligence

## 0. Resumen ejecutivo

Este proyecto es una plataforma local-first de análisis de vídeo para estimar **potencial de viralidad**, detectar momentos con alta probabilidad de retención, visualizar emoción temporal y generar recomendaciones/clip candidates. La especificación original describe una arquitectura multimodal avanzada; el plan recomendado la aterriza en un MVP incremental que funcione rápido en local, use mocks cuando sea necesario y permita sustituir piezas heurísticas por modelos reales sin rehacer toda la aplicación.

El producto inicial debe priorizar:

1. Interfaz React/Vite/Tailwind inspirada en los HTML de Stitch.
2. Backend FastAPI con contrato estable y datos mock/heurísticos.
3. Upload de MP4 y análisis básico local con FFmpeg/OpenCV cuando esté disponible.
4. Timeline unificado de scores: virality, arousal, valence, retention, hooks y clips sugeridos.
5. Preparación para IA avanzada, pero sin bloquear el MVP con GPU, datasets o modelos pesados.

## 1. Análisis del proyecto

### Tipo de plataforma

Plataforma web de inteligencia audiovisual para creadores/equipos de contenido. Combina:

- análisis de vídeo y audio;
- visualización temporal tipo dashboard/lab cinematográfico;
- predicción heurística/modelada de viralidad potencial;
- extracción y ranking de clips;
- explicación textual accionable.

### Arquitectura recomendada

Arquitectura monorepo simple, con frontend y backend separados pero compartiendo tipos/contratos:

```txt
virality-analizer/
├─ frontend/                React + Vite + TailwindCSS + TypeScript
├─ backend/                 FastAPI + pipeline local + workers in-process al inicio
├─ ai_services/             módulos de análisis multimodal desacoplados
├─ processing/              utilidades FFmpeg/OpenCV, timelines, clip detection
├─ workers/                 jobs async; fase inicial in-process, luego cola real
├─ uploads/                 vídeos subidos y artefactos generados localmente
├─ shared/                  esquemas JSON/OpenAPI/types generados o compartidos
└─ docs/                    documentación técnica incremental
```

Flujo objetivo:

```diagram
╭──────────────╮     ╭──────────────╮     ╭────────────────╮
│ React/Vite UI│────▶│ FastAPI API  │────▶│ Analysis Job   │
│ Upload + Lab │◀────│ REST + status│◀────│ in-process MVP │
╰──────┬───────╯     ╰──────┬───────╯     ╰──────┬─────────╯
       │                    │                    │
       │                    ▼                    ▼
       │             ╭────────────╮       ╭───────────────╮
       ╰────────────▶│ JSON result│◀──────│ processing/AI │
                     │ timeline   │       │ heuristics    │
                     ╰────────────╯       ╰───────────────╯
```

### Complejidad

- **Frontend:** media/alta por visualizaciones, responsive desktop/mobile, reproductor de vídeo y timeline sincronizado.
- **Backend:** media en MVP; alta cuando entren modelos, colas, GPU, datasets y clipping real.
- **IA multimodal:** alta/muy alta. Debe incorporarse por capas: heurísticas → modelos ligeros → modelos pesados opcionales.
- **Infraestructura:** baja en MVP local; media/alta al introducir Redis/Celery/GPU/storage cloud.

### Riesgos técnicos principales

1. **Sobredimensionamiento temprano:** usar Qwen/VideoMAE/EMOCA desde el inicio puede bloquear el proyecto por GPU, instalación y latencia.
2. **Contratos inestables:** si la UI se acopla a mocks sin esquema claro, habrá refactors grandes.
3. **Procesamiento de vídeo lento:** extracción frame-by-frame completa no escala; MVP debe muestrear por intervalos.
4. **Predicción engañosa:** el sistema debe decir “Potential Virality Score”, no garantizar viralidad.
5. **Dependencias de sistema:** FFmpeg, CUDA y modelos externos requieren pasos humanos o instalación fuera del workspace.

### MVP recomendado

Un MVP realista debe entregar una demo funcional local:

- UI profesional desktop/mobile con datos mock y estado de análisis.
- Upload de MP4 al backend.
- Job de análisis con progreso simulado o real básico.
- Si FFmpeg está disponible: metadata, duración, FPS aproximado, thumbnails/frames muestreados.
- Timeline heurístico: picos sintéticos o calculados por cambios visuales simples.
- Resultado JSON estable con score global, clips sugeridos, emotion timeline e insights.
- Sin modelos pesados por defecto.

## 2. Decisiones técnicas base

### Frontend

- **React + Vite + TypeScript** por velocidad, DX y compatibilidad con componentes visuales.
- **TailwindCSS** con tokens extraídos de Stitch (`Cinematic Intelligence Lab`).
- **React Router** solo si se necesitan múltiples vistas; si no, una página dashboard inicial.
- **Zustand** para estado ligero de analysis/upload si hace falta; evitar Redux.
- **Recharts o SVG custom** para timeline; al inicio SVG custom permite replicar Stitch con menos dependencias.
- **fetch nativo** con una capa `api/client.ts` pequeña.

### Backend

- **FastAPI** con endpoints REST simples.
- **Pydantic** como fuente de verdad de esquemas.
- **BackgroundTasks/in-process jobs** en MVP para evitar Redis/Celery temprano.
- **SQLite opcional en fase posterior**; al inicio JSON files en `uploads/<analysis_id>/result.json` para mínima fricción.
- **FFmpeg vía subprocess** para metadata y frames. OpenCV opcional para heurísticas visuales.

### IA y procesamiento

- Fase inicial: `MockAnalyzer` + `HeuristicVideoAnalyzer`.
- Fase intermedia: Whisper opcional para transcript, análisis de audio con librosa opcional.
- Fase avanzada: adapters para VideoMAE/Qwen/CLIP/EMOCA sin cambiar el contrato de salida.

## 3. Análisis del diseño Stitch

### Elementos reutilizables detectados

- Layout desktop split-view:
  - sidebar fija izquierda;
  - top app bar;
  - columna izquierda de “Emotional Intelligence”;
  - columna derecha con player + engagement graph;
  - floating action.
- Layout mobile:
  - top app bar compacta;
  - cards verticales;
  - bottom nav;
  - visual “Neural Lens/Core Presence”.
- Tokens visuales:
  - dark mode default;
  - `surface`, `surface-container`, `primary`, `secondary`, `tertiary`;
  - Geist como fuente;
  - labels pequeñas uppercase;
  - glass panels con blur;
  - pulsing dots para IA/virality;
  - timelines finos con playhead.

### Problemas del HTML exportado que deben corregirse al convertir a React

- Usa CDN de Tailwind; en Vite debe migrarse a `tailwind.config.ts` y CSS local.
- Atributos SVG/HTML incompatibles con JSX: `viewbox` → `viewBox`, `lineargradient` → `linearGradient`, `stop-color` → `stopColor`, `stroke-width` → `strokeWidth`, `preserveaspectratio` → `preserveAspectRatio`, etc.
- Duplicación de fuentes Material Symbols.
- Scripts DOM imperativos; en React deben convertirse a estado/event handlers o eliminarse en MVP.
- Algunas clases/typos de Stitch requieren normalización: `text-headline-md-mobile` no existe si no se define, `bottom--6` debe revisarse.
- Imágenes remotas de Google exportadas por Stitch deben sustituirse por placeholders locales, gradientes o estados de vídeo subido.

## 4. Estructura profesional propuesta

```txt
virality-analizer/
├─ frontend/
│  ├─ index.html
│  ├─ package.json
│  ├─ vite.config.ts
│  ├─ tailwind.config.ts
│  ├─ postcss.config.js
│  └─ src/
│     ├─ main.tsx
│     ├─ App.tsx
│     ├─ styles.css
│     ├─ api/
│     │  ├─ client.ts
│     │  └─ analysisApi.ts
│     ├─ components/
│     │  ├─ layout/
│     │  │  ├─ SideNav.tsx
│     │  │  ├─ TopAppBar.tsx
│     │  │  └─ BottomNav.tsx
│     │  ├─ upload/
│     │  │  └─ VideoUploadPanel.tsx
│     │  ├─ video/
│     │  │  ├─ VideoPlayer.tsx
│     │  │  └─ TimelineScrubber.tsx
│     │  ├─ intelligence/
│     │  │  ├─ ViralityScore.tsx
│     │  │  ├─ EmotionQuadrant.tsx
│     │  │  ├─ EngagementGraph.tsx
│     │  │  └─ InsightsPanel.tsx
│     │  └─ ui/
│     │     ├─ GlassPanel.tsx
│     │     └─ MetricCard.tsx
│     ├─ hooks/
│     │  ├─ useAnalysis.ts
│     │  └─ useVideoUpload.ts
│     ├─ stores/
│     │  └─ analysisStore.ts
│     ├─ types/
│     │  └─ analysis.ts
│     └─ data/
│        └─ mockAnalysis.ts
├─ backend/
│  ├─ pyproject.toml
│  ├─ README.md
│  └─ app/
│     ├─ main.py
│     ├─ core/
│     │  ├─ config.py
│     │  └─ paths.py
│     ├─ api/
│     │  └─ routes/
│     │     ├─ health.py
│     │     └─ analysis.py
│     ├─ schemas/
│     │  └─ analysis.py
│     ├─ services/
│     │  ├─ analysis_service.py
│     │  └─ storage_service.py
│     ├─ processing/
│     │  ├─ ffmpeg_probe.py
│     │  ├─ frame_extractor.py
│     │  ├─ timeline_builder.py
│     │  └─ clip_ranker.py
│     ├─ ai_services/
│     │  ├─ mock_analyzer.py
│     │  ├─ heuristic_analyzer.py
│     │  ├─ speech_analyzer.py
│     │  ├─ visual_analyzer.py
│     │  └─ explanation_engine.py
│     └─ workers/
│        └─ analysis_worker.py
├─ shared/
│  ├─ schemas/
│  │  └─ analysis.schema.json
│  └─ types/
│     └─ analysis.ts
├─ uploads/
│  └─ .gitkeep
└─ docs/
   ├─ architecture.md
   └─ api-contract.md
```

## 5. Contrato de datos MVP

El contrato debe existir antes de conectar UI y backend.

```json
{
  "id": "analysis_123",
  "status": "completed",
  "video": {
    "filename": "video.mp4",
    "duration_seconds": 45.0,
    "fps": 30,
    "width": 1080,
    "height": 1920
  },
  "overall_virality_score": 0.92,
  "retention_score": 0.884,
  "rewatch_factor": 3.2,
  "dominant_emotion": "Surprise",
  "timeline": [
    {
      "time_seconds": 12.04,
      "virality": 0.92,
      "valence": 0.74,
      "arousal": 0.88,
      "retention": 0.89,
      "label": "Pattern disruption"
    }
  ],
  "top_clips": [
    {
      "start_seconds": 7.0,
      "end_seconds": 22.0,
      "score": 0.92,
      "predicted_retention": 0.81,
      "reasons": ["strong hook", "high emotional intensity"]
    }
  ],
  "insights": [
    {
      "title": "Pattern Disruption Hook",
      "description": "Frame change at T+12s correlates with a retention spike.",
      "severity": "high"
    }
  ]
}
```

## 6. Instalación y setup propuestos

### Requisitos base

- Node.js LTS 20+.
- Python 3.11+.
- Git.
- FFmpeg para análisis real básico.

### HUMAN ACTION REQUIRED — instalaciones fuera del workspace

Instalar o verificar en el sistema operativo:

```bash
node --version
npm --version
python --version
ffmpeg -version
```

Si falta FFmpeg en Windows, instalarlo con una de estas opciones:

```bash
winget install Gyan.FFmpeg
```

o instalar manualmente desde https://www.gyan.dev/ffmpeg/builds/ y añadir `ffmpeg` al `PATH`.

### Setup frontend

Comandos que Amp puede ejecutar cuando toque la fase correspondiente:

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer prettier eslint
npm install @vitejs/plugin-react zustand clsx lucide-react
npx tailwindcss init -p
npm run dev
```

### Setup backend

### HUMAN ACTION REQUIRED — entorno virtual si prefieres control manual

Crear y activar `.venv` puede hacerlo Amp si se autoriza, pero se marca como acción humana porque modifica el entorno local y depende de políticas de cada máquina:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Git Bash
source .venv/Scripts/activate
```

Luego Amp puede instalar dependencias dentro del workspace:

```bash
pip install fastapi uvicorn[standard] pydantic-settings python-multipart opencv-python numpy
pip freeze > backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

Para mayor reproducibilidad, se recomienda `pyproject.toml` en backend:

```bash
pip install -e backend
```

### Dependencias backend por etapas

- MVP mínimo: `fastapi`, `uvicorn[standard]`, `pydantic-settings`, `python-multipart`, `numpy`.
- Vídeo básico: `opencv-python` y FFmpeg del sistema.
- Audio opcional: `librosa`, `soundfile`.
- Whisper opcional: `openai-whisper` o `faster-whisper`.
- Colas opcionales: `redis`, `rq` o `celery` solo después de validar jobs in-process.

## 7. Roadmap ejecutable por fases

Las fases están pensadas para ejecutarse con instrucciones como “ejecuta fase 1”, “ejecuta fase 2”, etc. Cada fase debe dejar el proyecto en un estado verificable.

---

## Fase 1 — Bootstrap del monorepo y documentación base

### Objetivo

Crear estructura profesional mínima, preparar archivos base y documentar contratos iniciales sin instalar dependencias pesadas.

### Archivos a crear/modificar

- `frontend/` estructura inicial si se decide crear Vite ya en esta fase.
- `backend/` estructura inicial.
- `shared/`, `uploads/`, `docs/`.
- `docs/architecture.md`.
- `docs/api-contract.md`.
- `.gitignore`.
- `README.md`.

### Dependencias necesarias

- Ninguna obligatoria si solo se crea estructura y docs.
- Node/Python solo si se inicializan proyectos ejecutables en esta fase.

### Amp puede hacer automáticamente

- Crear carpetas y `.gitkeep`.
- Crear `.gitignore` para Node, Python, uploads y caches.
- Crear docs iniciales copiando decisiones de este plan.
- Crear contratos JSON/TypeScript preliminares.

### HUMAN ACTION REQUIRED

- Confirmar que Node.js 20+ y Python 3.11+ existen si se quiere ejecutar instalación inmediata:

```bash
node --version
python --version
```

### Criterios de finalización

- Estructura de carpetas existe.
- `uploads/` está ignorada por Git salvo `.gitkeep`.
- Existe contrato MVP documentado.

### Validaciones/tests mínimos

```bash
find . -maxdepth 3 -type d
```

En Windows PowerShell equivalente:

```powershell
Get-ChildItem -Directory -Recurse -Depth 2
```

---

## Fase 2 — Frontend Vite + Tailwind + tokens de Stitch

### Objetivo

Inicializar React/Vite/TypeScript y migrar el diseño system de Stitch a Tailwind local reproducible.

### Archivos a crear/modificar

- `frontend/package.json`.
- `frontend/vite.config.ts`.
- `frontend/tailwind.config.ts`.
- `frontend/postcss.config.js`.
- `frontend/src/main.tsx`.
- `frontend/src/App.tsx`.
- `frontend/src/styles.css`.

### Dependencias necesarias

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install -D tailwindcss postcss autoprefixer eslint prettier
npm install zustand clsx lucide-react
npx tailwindcss init -p
```

### Amp puede hacer automáticamente

- Inicializar el proyecto Vite.
- Instalar dependencias npm.
- Configurar Tailwind con colores, spacing, border radius y tipografías de `DESIGN.md`.
- Definir CSS global para dark background, Geist y utilidades `glass-panel`, `pulse-*`, `scrim-bottom`.

### HUMAN ACTION REQUIRED

- Si Node/npm no está instalado, instalar Node.js LTS 20+ desde https://nodejs.org/ o con:

```bash
winget install OpenJS.NodeJS.LTS
```

### Criterios de finalización

- `npm run dev` levanta Vite.
- Tailwind compila clases custom del tema.
- La pantalla inicial renderiza sin errores.

### Validaciones/tests mínimos

```bash
cd frontend
npm run build
```

---

## Fase 3 — Conversión del HTML Stitch a componentes React

### Objetivo

Convertir los diseños web/mobile exportados por Stitch en componentes React compatibles con JSX, Tailwind local y datos mock.

### Archivos a crear/modificar

- `frontend/src/components/layout/SideNav.tsx`.
- `frontend/src/components/layout/TopAppBar.tsx`.
- `frontend/src/components/layout/BottomNav.tsx`.
- `frontend/src/components/video/VideoPlayer.tsx`.
- `frontend/src/components/video/TimelineScrubber.tsx`.
- `frontend/src/components/intelligence/EmotionQuadrant.tsx`.
- `frontend/src/components/intelligence/EngagementGraph.tsx`.
- `frontend/src/components/intelligence/ViralityScore.tsx`.
- `frontend/src/components/intelligence/InsightsPanel.tsx`.
- `frontend/src/components/ui/GlassPanel.tsx`.
- `frontend/src/data/mockAnalysis.ts`.
- `frontend/src/types/analysis.ts`.
- `frontend/src/App.tsx`.

### Dependencias necesarias

- Las de fase 2.

### Amp puede hacer automáticamente

- Extraer estructura del `code.html` web y mobile.
- Convertir atributos HTML/SVG a JSX.
- Sustituir scripts DOM por props/estado React o CSS.
- Separar responsive behavior con Tailwind (`hidden md:flex`, `md:hidden`, etc.).
- Mantener estética “Cinematic Intelligence Lab”.
- Reemplazar imágenes remotas por gradientes/placeholders y futuro vídeo subido.

### HUMAN ACTION REQUIRED

- Ninguna, salvo validar visualmente el resultado en navegador.

### Criterios de finalización

- La UI se parece razonablemente a Stitch en desktop y mobile.
- No depende del CDN de Tailwind.
- No contiene scripts inline de manipulación DOM.
- Datos vienen de `mockAnalysis.ts` tipado.

### Validaciones/tests mínimos

```bash
cd frontend
npm run build
```

Validación visual manual recomendada:

### HUMAN ACTION REQUIRED

Abrir `http://localhost:5173`, revisar desktop y mobile con DevTools responsive, y confirmar que la estética es aceptable.

---

## Fase 4 — Backend FastAPI mínimo con contrato mock

### Objetivo

Crear API FastAPI con endpoints de salud y análisis mock compatible con la UI.

### Archivos a crear/modificar

- `backend/pyproject.toml` o `backend/requirements.txt`.
- `backend/app/main.py`.
- `backend/app/core/config.py`.
- `backend/app/api/routes/health.py`.
- `backend/app/api/routes/analysis.py`.
- `backend/app/schemas/analysis.py`.
- `backend/app/ai_services/mock_analyzer.py`.
- `backend/app/services/analysis_service.py`.

### Dependencias necesarias

```bash
pip install fastapi uvicorn[standard] pydantic-settings python-multipart
```

### Amp puede hacer automáticamente

- Crear app FastAPI con CORS para Vite.
- Crear modelos Pydantic del contrato MVP.
- Crear endpoints:

```txt
GET  /api/viral-intelligence/health
GET  /api/viral-intelligence/analysis/mock
POST /api/viral-intelligence/analysis
GET  /api/viral-intelligence/analysis/{analysis_id}
```

- Implementar almacenamiento temporal en memoria o JSON local.

### HUMAN ACTION REQUIRED

- Crear/activar `.venv` si aún no existe:

```bash
python -m venv .venv
source .venv/Scripts/activate
```

En PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### Criterios de finalización

- `GET /api/viral-intelligence/health` responde OK.
- `GET /api/viral-intelligence/analysis/mock` devuelve JSON validado por Pydantic.
- La API arranca sin modelos IA pesados.

### Validaciones/tests mínimos

```bash
uvicorn app.main:app --reload --app-dir backend
curl http://127.0.0.1:8000/api/viral-intelligence/health
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/mock
```

---

## Fase 5 — Conexión frontend-backend y estados reales de UI

### Objetivo

Conectar la UI con FastAPI, manteniendo fallback a mocks si el backend no está activo.

### Archivos a crear/modificar

- `frontend/src/api/client.ts`.
- `frontend/src/api/analysisApi.ts`.
- `frontend/src/hooks/useAnalysis.ts`.
- `frontend/src/stores/analysisStore.ts`.
- `frontend/src/App.tsx`.
- Componentes de score/timeline/insights.

### Dependencias necesarias

- `zustand` si se usa store global.

### Amp puede hacer automáticamente

- Crear cliente API con `VITE_API_BASE_URL`.
- Implementar loading/error/empty states.
- Mostrar datos de `/api/viral-intelligence/analysis/mock`.
- Añadir fallback local `mockAnalysis` cuando la API falla en modo desarrollo.

### HUMAN ACTION REQUIRED

- Ninguna obligatoria.

### Criterios de finalización

- Frontend renderiza datos del backend cuando está disponible.
- Frontend no queda roto si backend está apagado.
- Tipos frontend reflejan contrato backend.

### Validaciones/tests mínimos

```bash
cd frontend
npm run build
```

Con backend activo:

```bash
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/mock
```

---

## Fase 6 — Upload de MP4 y persistencia local simple

### Objetivo

Permitir subir un `.mp4`, guardarlo en `uploads/` y crear un `analysis_id` consultable.

### Archivos a crear/modificar

- `frontend/src/components/upload/VideoUploadPanel.tsx`.
- `frontend/src/hooks/useVideoUpload.ts`.
- `backend/app/services/storage_service.py`.
- `backend/app/api/routes/analysis.py`.
- `backend/app/core/paths.py`.
- `uploads/.gitkeep`.

### Dependencias necesarias

- Backend: `python-multipart`.

### Amp puede hacer automáticamente

- Crear dropzone/input de archivo.
- Validar extensión `.mp4` y tamaño máximo configurable.
- Endpoint `POST /api/viral-intelligence/analysis` con `UploadFile`.
- Guardar archivo en `uploads/<analysis_id>/input.mp4`.
- Crear `result.json` inicial con status `queued` o `processing`.

### HUMAN ACTION REQUIRED

- Proveer un vídeo MP4 de prueba local.
- Confirmar límite de tamaño deseado si el default no sirve; sugerencia MVP: 200 MB.

### Criterios de finalización

- Se puede subir un MP4 desde la UI.
- Backend crea carpeta por análisis.
- UI muestra estado del análisis creado.

### Validaciones/tests mínimos

```bash
curl -F "file=@sample.mp4" http://127.0.0.1:8000/api/viral-intelligence/analysis
```

---

## Fase 7 — Pipeline local básico de vídeo con FFmpeg/OpenCV opcional

### Objetivo

Extraer metadata y señales básicas sin IA pesada: duración, resolución, frames muestreados, cambios visuales aproximados y timeline heurístico.

### Archivos a crear/modificar

- `backend/app/processing/ffmpeg_probe.py`.
- `backend/app/processing/frame_extractor.py`.
- `backend/app/processing/timeline_builder.py`.
- `backend/app/processing/clip_ranker.py`.
- `backend/app/ai_services/heuristic_analyzer.py`.
- `backend/app/workers/analysis_worker.py`.
- `backend/app/services/analysis_service.py`.

### Dependencias necesarias

```bash
pip install opencv-python numpy
```

FFmpeg del sistema para metadata/frames robustos.

### Amp puede hacer automáticamente

- Implementar `ffprobe` vía subprocess.
- Implementar fallback si FFmpeg no está disponible: análisis mock con warning.
- Muestrear frames cada 1s o 2s, no frame-by-frame completo.
- Calcular heurísticas simples:
  - diferencia promedio entre frames como proxy de motion/cuts;
  - brillo/contraste;
  - score de novelty por cambios bruscos;
  - picos para clips candidatos.
- Generar `timeline` y `top_clips` en contrato MVP.

### HUMAN ACTION REQUIRED

- Instalar FFmpeg si no existe:

```bash
ffmpeg -version
winget install Gyan.FFmpeg
```

### Criterios de finalización

- Un MP4 real produce metadata y timeline.
- Si FFmpeg falla, el sistema sigue funcionando con mock y mensaje claro.
- No requiere GPU.

### Validaciones/tests mínimos

```bash
python -m backend.app.processing.ffmpeg_probe uploads/<analysis_id>/input.mp4
```

O validación API:

```bash
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/<analysis_id>
```

---

## Fase 8 — Job lifecycle y progreso de análisis

### Objetivo

Hacer que la UI refleje estados reales: queued, processing, completed, failed; con polling desde frontend.

### Archivos a crear/modificar

- `backend/app/schemas/analysis.py`.
- `backend/app/workers/analysis_worker.py`.
- `backend/app/services/analysis_service.py`.
- `frontend/src/hooks/useAnalysis.ts`.
- `frontend/src/components/upload/VideoUploadPanel.tsx`.
- `frontend/src/components/intelligence/*`.

### Dependencias necesarias

- Ninguna nueva.

### Amp puede hacer automáticamente

- Ejecutar análisis en `BackgroundTasks` o thread simple.
- Persistir status/progress en `result.json`.
- Polling cada 1-2 segundos desde frontend hasta completed/failed.
- Mostrar estado “AI Thinking” con visual de Stitch.

### HUMAN ACTION REQUIRED

- Ninguna.

### Criterios de finalización

- Upload inicia job.
- UI muestra progreso.
- Resultado se actualiza automáticamente al completar.

### Validaciones/tests mínimos

```bash
cd frontend && npm run build
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/<analysis_id>
```

---

## Fase 9 — Explanation engine heurístico y recomendaciones accionables

### Objetivo

Convertir features estructuradas en explicaciones comprensibles sin LLM externo.

### Archivos a crear/modificar

- `backend/app/ai_services/explanation_engine.py`.
- `backend/app/processing/timeline_builder.py`.
- `backend/app/schemas/analysis.py`.
- `frontend/src/components/intelligence/InsightsPanel.tsx`.

### Dependencias necesarias

- Ninguna nueva.

### Amp puede hacer automáticamente

- Crear reglas explicables:
  - motion spike → “Pattern disruption hook”;
  - alta densidad de cortes → “Fast pacing”;
  - pico temprano → “Strong opening hook”;
  - arousal alto + contraste → “High emotional intensity”.
- Añadir severidad y timestamps a insights.
- Mostrar insights vinculados al playhead/timeline.

### HUMAN ACTION REQUIRED

- Ninguna.

### Criterios de finalización

- Cada clip recomendado tiene razones.
- El score global tiene explicación breve.
- UI muestra recomendaciones accionables.

### Validaciones/tests mínimos

```bash
python -m pytest backend/tests
```

Si aún no hay tests, crear prueba mínima del explanation engine en esta fase.

---

## Fase 10 — Exportación básica de clips con FFmpeg

### Objetivo

Permitir generar archivos clip MP4 para los top clips sugeridos.

### Archivos a crear/modificar

- `backend/app/processing/clip_exporter.py`.
- `backend/app/api/routes/analysis.py`.
- `frontend/src/components/intelligence/ClipList.tsx`.
- `frontend/src/api/analysisApi.ts`.

### Dependencias necesarias

- FFmpeg del sistema.

### Amp puede hacer automáticamente

- Endpoint:

```txt
POST /api/viral-intelligence/analysis/{analysis_id}/clips/{clip_index}/export
GET  /api/viral-intelligence/analysis/{analysis_id}/clips/{clip_index}/download
```

- Ejecutar FFmpeg con `-ss`, `-to`, copia rápida o re-encode básico.
- Guardar clips en `uploads/<analysis_id>/clips/`.
- Añadir botón “Export Clip” en UI.

### HUMAN ACTION REQUIRED

- FFmpeg instalado y accesible en `PATH`.

### Criterios de finalización

- Un clip recomendado puede exportarse y descargarse.
- Errores de FFmpeg aparecen en UI/API de forma clara.

### Validaciones/tests mínimos

```bash
ffmpeg -version
curl -X POST http://127.0.0.1:8000/api/viral-intelligence/analysis/<analysis_id>/clips/0/export
```

---

## Fase 11 — Speech/NLP opcional con Whisper ligero

### Objetivo

Añadir transcripción opcional para detectar hooks textuales sin bloquear el MVP.

### Archivos a crear/modificar

- `backend/app/ai_services/speech_analyzer.py`.
- `backend/app/ai_services/text_hook_analyzer.py`.
- `backend/app/schemas/analysis.py`.
- `frontend/src/components/intelligence/TranscriptPanel.tsx`.

### Dependencias necesarias

Opción CPU más práctica:

```bash
pip install faster-whisper
```

### Amp puede hacer automáticamente

- Implementar adapter desactivado por defecto con feature flag.
- Añadir transcript al resultado si Whisper está instalado.
- Detectar frases tipo curiosity gap/urgency/conflict con reglas simples.

### HUMAN ACTION REQUIRED

- Instalar dependencias de Whisper y aceptar descarga de modelos.
- Confirmar modelo inicial. Recomendado local: `small`.
- Si se desea GPU, configurar CUDA fuera del workspace.

### Criterios de finalización

- Sin Whisper instalado, el sistema funciona igual.
- Con Whisper instalado, aparece transcript y hooks textuales.

### Validaciones/tests mínimos

```bash
python -c "import faster_whisper; print('ok')"
```

---

## Fase 12 — Audio features opcionales

### Objetivo

Extraer señales de energía, silencios y ritmo para mejorar arousal/retention.

### Archivos a crear/modificar

- `backend/app/ai_services/audio_analyzer.py`.
- `backend/app/processing/audio_extractor.py`.
- `backend/app/processing/timeline_builder.py`.

### Dependencias necesarias

```bash
pip install librosa soundfile
```

### Amp puede hacer automáticamente

- Extraer audio con FFmpeg.
- Calcular RMS energy, silence gaps y cambios de energía.
- Fusionar audio score con motion score.

### HUMAN ACTION REQUIRED

- FFmpeg instalado.
- Aceptar instalación de librerías de audio si pesan demasiado para el entorno actual.

### Criterios de finalización

- Timeline incorpora audio_energy/arousal aproximado.
- Los clips rankean mejor cuando hay picos visuales + audio.

### Validaciones/tests mínimos

```bash
python -c "import librosa; print('ok')"
```

---

## Fase 13 — Cola real y workers externos

### Objetivo

Separar análisis largo del proceso API cuando el MVP ya funcione.

### Archivos a crear/modificar

- `backend/app/workers/analysis_worker.py`.
- `backend/app/core/config.py`.
- `backend/app/services/queue_service.py`.
- `docker-compose.yml` opcional para Redis.

### Dependencias necesarias

Opción simple:

```bash
pip install redis rq
```

Opción más completa:

```bash
pip install celery redis
```

### Amp puede hacer automáticamente

- Integrar RQ/Redis o Celery detrás de una interfaz `queue_service`.
- Mantener fallback in-process para modo local simple.
- Crear scripts `worker`.

### HUMAN ACTION REQUIRED

- Instalar/ejecutar Redis si no se usa Docker.
- Si se usa Docker Desktop, instalarlo y arrancarlo fuera del workspace.

Comando con Docker cuando esté disponible:

```bash
docker compose up redis
```

### Criterios de finalización

- API encola jobs.
- Worker procesa jobs.
- Fallback local sigue disponible.

### Validaciones/tests mínimos

```bash
redis-cli ping
```

---

## Fase 14 — IA multimodal avanzada por adapters

### Objetivo

Incorporar modelos reales sin romper contrato ni UI.

### Archivos a crear/modificar

- `backend/app/ai_services/visual_analyzer.py`.
- `backend/app/ai_services/emotion_analyzer.py`.
- `backend/app/ai_services/multimodal_fusion.py`.
- `backend/app/core/config.py`.

### Dependencias posibles

- `torch`, `transformers`, `opencv-python`, `ultralytics`, modelos de emoción/audio según elección.

### Amp puede hacer automáticamente

- Crear interfaces/adapters y feature flags.
- Integrar modelos ligeros primero.
- Añadir cache de resultados por análisis.

### HUMAN ACTION REQUIRED

- Elegir modelos concretos y aceptar descargas.
- Configurar GPU/CUDA si se requiere.
- Verificar licencias de modelos/datasets.
- Proveer API keys si se decide usar servicios externos.

### Criterios de finalización

- El sistema puede alternar entre `mock`, `heuristic` y `model` analyzers.
- Sin GPU, el MVP sigue funcionando con heurísticas.

### Validaciones/tests mínimos

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

---

## Fase 15 — Tests, calidad y empaquetado local

### Objetivo

Estabilizar el proyecto para desarrollo iterativo continuo.

### Archivos a crear/modificar

- `frontend/src/**/*.test.tsx` opcional.
- `backend/tests/`.
- `package.json` raíz opcional con scripts.
- `Makefile` o `scripts/` opcional si aporta valor.
- `README.md` actualizado.

### Dependencias necesarias

Frontend opcional:

```bash
cd frontend
npm install -D vitest @testing-library/react @testing-library/jest-dom jsdom
```

Backend:

```bash
pip install pytest httpx
```

### Amp puede hacer automáticamente

- Añadir tests unitarios mínimos.
- Añadir scripts de build/test.
- Documentar runbook local.
- Validar build frontend y endpoints backend.

### HUMAN ACTION REQUIRED

- Ninguna obligatoria.

### Criterios de finalización

- `npm run build` pasa.
- Tests backend mínimos pasan.
- README permite levantar el proyecto desde cero.

### Validaciones/tests mínimos

```bash
cd frontend && npm run build
python -m pytest backend/tests
```

## 8. Backend e IA: organización interna recomendada

### FastAPI

- `main.py` solo monta app, CORS y routers.
- `api/routes/` define endpoints, no lógica pesada.
- `services/` coordina storage, jobs y analyzers.
- `schemas/` define contratos Pydantic.

### Pipelines multimodales

Cada analyzer debe producir fragmentos normalizados, no respuestas UI-specific:

```txt
VisualAnalyzer    → motion, cuts, brightness, faces later
AudioAnalyzer     → energy, silence, beat proxies later
SpeechAnalyzer    → transcript, segments, hook phrases
EmotionAnalyzer   → valence/arousal/emotion estimates
Fusion/Timeline   → timeline unified per second/window
ClipRanker        → top clips from peaks + context windows
ExplanationEngine → human-readable reasons
```

### Procesamiento de vídeo

- MVP: muestreo cada 1-2 segundos.
- Evitar procesar todos los frames al inicio.
- Guardar artefactos por `analysis_id`:

```txt
uploads/<analysis_id>/
├─ input.mp4
├─ result.json
├─ frames/
│  ├─ 000001.jpg
│  └─ ...
└─ clips/
   └─ clip_0.mp4
```

### Colas y workers

- Fases 4-8: `BackgroundTasks` o thread in-process.
- Fase 13: Redis/RQ cuando haya análisis lentos o múltiples jobs concurrentes.
- Mantener interfaz común para no reescribir endpoints:

```python
queue_service.enqueue_analysis(analysis_id)
```

### Timelines y análisis temporal

- Usar ventanas iniciales de 3s con stride 1s cuando el procesamiento lo permita.
- En MVP, si solo hay frames cada 1s, interpolar scores por segundo.
- Score compuesto inicial:

```txt
virality = 0.35 * hook_score
         + 0.25 * arousal_score
         + 0.20 * novelty_score
         + 0.10 * pacing_score
         + 0.10 * retention_proxy
```

Los pesos deben vivir en configuración para ajustarlos sin tocar UI.

## 9. Filosofía de desarrollo

1. **Contrato primero:** UI y backend se conectan por un JSON estable.
2. **Mock antes que bloqueo:** si falta FFmpeg/modelo/GPU, usar mock o heurística con warning explícito.
3. **MVP local-first:** nada debe requerir cloud, login ni API keys para funcionar inicialmente.
4. **Adapters, no refactors gigantes:** cada modelo IA se conecta detrás de una interfaz ya existente.
5. **Validación continua:** cada fase termina con build/test/curl mínimo.
6. **Diseño preservado, implementación limpia:** Stitch es referencia visual, no código final literal.
7. **No prometer viralidad garantizada:** siempre hablar de “Potential Virality Score”.
8. **Integración-ready:** toda decisión debe considerar que este módulo se integrará en AureaSuite como feature.

## 10. Integración con AureaSuite — decisiones y preparación

Este módulo se integrará en https://www.aureasuite.ai/ como funcionalidad. Las siguientes decisiones ya están implementadas o deben respetarse en todas las fases futuras:

### Decisiones ya implementadas (fases 1-6)

1. **API namespace:** todas las rutas usan prefijo `/api/viral-intelligence/` para evitar colisiones con las rutas existentes de AureaSuite (`/api/clips/*`, `/api/projects/*`, `/api/chat/*`, etc.).
2. **user_id opcional:** los schemas `AnalysisResult` y `AnalysisSummary` incluyen `user_id: Optional[str]`. Se pobla automáticamente cuando auth está activa.
3. **Auth dependency placeholder:** `backend/app/core/auth.py` define `get_current_user_id()` que retorna `None` en modo local y validará JWT de Clerk en producción. Se inyecta con `Depends()` en rutas que lo necesiten.
4. **Config por entorno:** `config.py` incluye `environment` (local/staging/production), `storage_backend` (local/s3), `auth_enabled` (bool), y CORS configurable via env vars con prefijo `AUREA_`.
5. **Frontend auth-ready:** `api/client.ts` expone `setAuthTokenProvider()` para que AureaSuite inyecte `getToken()` de Clerk. Las llamadas `apiFetch` adjuntan `Authorization: Bearer <token>` automáticamente cuando hay provider.

### Reglas para fases futuras

Cada fase futura (7-15+) debe respetar:

- **Rutas API:** siempre bajo `/api/viral-intelligence/`. Nunca `/api/analysis/` genérico.
- **user_id en escritura:** todo endpoint POST/PUT/DELETE debe usar `Depends(get_current_user_id)` y asociar el resultado al usuario.
- **Storage abstracto:** el `storage_service` actual usa filesystem. No hardcodear `Path` ni `open()` en código nuevo fuera de `storage_service.py`. En integración se sustituirá por S3.
- **Sin layout propio en embebido:** los componentes `SideNav`, `TopAppBar`, `BottomNav` solo se usan en modo standalone. Cuando se embeba en AureaSuite, el shell lo provee AureaSuite. Los componentes de contenido (`ViralityScore`, `EmotionQuadrant`, `EngagementGraph`, `InsightsPanel`, `VideoPlayer`, `VideoUploadPanel`) deben ser independientes del layout.
- **Sin hardcodear URLs:** usar siempre `buildUrl()` del client y `BASE_URL` de env. En AureaSuite, el microservicio FastAPI estará detrás de un proxy/gateway.
- **IDs:** mantener formato `ana_<uuid>`. Compatible con AureaSuite.
- **Progreso real-time:** cuando se implemente polling (fase 8), diseñarlo para que pueda migrarse a WebSocket/SSE sin cambiar la interfaz del componente.
- **Mantener FastAPI como microservicio Python.** No migrar a Node. El ecosistema de IA/ML de Python (OpenCV, Whisper, librosa, torch, transformers) no tiene equivalente viable en Node. AureaSuite llamará a este microservicio vía proxy reverso.

### Stack de AureaSuite (referencia)

- Frontend: React SPA, Clerk auth, Stripe billing, dark mode, Vite build
- Backend: API routes bajo `/api/*`, S3 para media, Stripe para pagos
- Auth: Clerk (JWT, `useAuth()`, `getToken()`)
- Media: S3 + proxy URLs (`/api/s3-proxy/*`)
- Proyectos: `/api/projects/*` con concepto de proyecto por usuario

### Modelo de integración futuro

```txt
AureaSuite React App
├── ClerkProvider (auth)
├── Router
│   ├── /dashboard, /story-creation, /pricing, ...
│   └── /viral-intelligence  ← monta componentes de este módulo
│       └── ViralIntelligencePage
│           ├── VideoUploadPanel
│           ├── ViralityScore, EmotionQuadrant, ...
│           └── EngagementGraph, InsightsPanel
└── API Gateway (Node)
    ├── /api/projects, /api/clips, /api/chat, ...
    └── /api/viral-intelligence/* → proxy → FastAPI microservice
```

## 11. Estado actual — Flujo de análisis y sincronización video-datos (implementado)

### Arquitectura implementada: "Analizar una vez, replay por timestamp"

El flujo actual funciona así:

1. **Carga del video** → el usuario sube un MP4 desde la UI (botón upload en `VideoPlayer`).
2. **Análisis completo** → `useVideoUpload` envía el archivo al backend (`POST /api/viral-intelligence/analysis`), que lo analiza por completo y devuelve un `AnalysisResult` con un `timeline[]` denso (una entry por segundo, con `virality`, `arousal`, `valence`, `retention` y opcionalmente `label`).
3. **Almacenamiento en store** → el resultado se guarda en `analysisStore.ts` (Zustand) como `analysis`. No se recalcula nunca; es inmutable una vez recibido.
4. **Replay por timestamp** → durante la reproducción, el componente `VideoPlayer` emite `onTimeChange(currentTime)` en cada `timeupdate` del `<video>`. App.tsx escribe ese valor en el store como `playbackTime`. Un `useMemo` busca la `closestEntry` del `timeline[]` más cercana al `playbackTime` actual y la pasa como props a todos los componentes de visualización.

### Cómo se sincronizan los componentes con el video

```txt
VideoPlayer (timeupdate / scrub)
    │
    ▼
analysisStore.playbackTime ← setPlaybackTime(t)
    │
    ▼
App.tsx: currentTime = playbackTime
         closestEntry = useMemo(timeline, currentTime)
    │
    ├──▶ BrainSphere(analysis, currentTime)
    │      └── analysisToSphereData(analysis, currentTime)
    │          → busca closestEntry en timeline
    │          → calcula intensities de regiones (virality, arousal, valence, retention, etc.)
    │
    ├──▶ EmotionQuadrant(valence, arousal, intensity) ← de closestEntry
    │
    ├──▶ EngagementGraph(timeline, currentTime) ← playhead line
    │
    └──▶ ViralityScore(score, timestamp)
```

**Regla fundamental:** los datos mostrados dependen **exclusivamente** de `playbackTime`. Si `playbackTime` no cambia, nada cambia. Esto funciona en ambos escenarios:

- **Video reproduciéndose:** `timeupdate` actualiza `playbackTime` → todos los componentes se actualizan al segundo correspondiente.
- **Video pausado + scrub manual:** `handleSeek` actualiza `playbackTime` → los componentes muestran los datos del segundo al que se avanzó.
- **Video pausado sin scrub:** `playbackTime` no cambia → nada se mueve.

### Animaciones de la esfera 3D (BrainSphere)

La esfera tiene animaciones continuas (rotación, pulso, partículas) que son independientes de los datos. Para evitar saltos al pausar/reanudar:

- Cada componente 3D (`BrainCore`, `AnalysisRegion`, `NeuralConnections`, `NeuralParticles`) usa un `localTime` ref que solo avanza con `+= delta` cuando `isPlaying === true`.
- El delta se clampea con `Math.min(rawDelta, 0.1)` para evitar spikes.
- El Canvas usa `frameloop="always"` (no cambia entre `"always"/"demand"`) para que el reloj de THREE.js no acumule tiempo durante la pausa.
- Cuando `isPlaying === false`, los `useFrame` callbacks hacen `return` temprano — las animaciones se congelan en su último estado visual sin salto.

### Fallback local (sin backend)

Si el backend no está disponible, `loadAnalysis()` en el store cae al catch y carga `mockAnalysis` (datos generados proceduralmente en `frontend/src/data/mockAnalysis.ts` con 45 entries, una por segundo). El flujo de replay es idéntico — el video default (`/videos/default.mp4`) se reproduce y los datos mock se consultan por timestamp de la misma forma.

### Archivos clave del flujo

| Archivo | Responsabilidad |
|---|---|
| `stores/analysisStore.ts` | Estado global: `analysis`, `playbackTime`, `isPlaying` |
| `hooks/useVideoUpload.ts` | Upload → POST → polling → guarda resultado en store |
| `hooks/useAnalysis.ts` | Carga inicial (backend o mock fallback) |
| `App.tsx` | Wiring: `currentTime = playbackTime`, `closestEntry = useMemo(...)`, pasa props a componentes |
| `components/video/VideoPlayer.tsx` | Emite `onTimeChange` y `onPlayingChange` |
| `components/sphere/sphereUtils.ts` | `analysisToSphereData()`: convierte analysis + currentTime en datos de esfera |
| `data/mockAnalysis.ts` | Datos mock procedurales (fallback sin backend) |
| `types/analysis.ts` | `AnalysisResult`, `TimelineEntry`, contratos tipados |

---

## 12. Orden recomendado de ejecución

Orden más eficiente para empezar:

1. Fase 1 — estructura y docs.
2. Fase 2 — Vite/Tailwind.
3. Fase 3 — UI Stitch convertida.
4. Fase 4 — API mock.
5. Fase 5 — conexión UI/API.
6. Fase 6 — upload.
7. Fase 7 — análisis básico con FFmpeg/OpenCV.
8. Fase 8 — progreso real.
9. Fase 9 — explanation engine.
10. Fase 10 — export clips.

Las fases 11-14 son incrementos posteriores y no deben bloquear el MVP.
