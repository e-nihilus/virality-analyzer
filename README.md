# Aurea Viral Intelligence

Local-first video analysis platform to estimate virality potential, detect high-retention moments, visualize temporal emotion, and generate actionable recommendations with clip candidates.

Part of [AureaSuite](https://www.aureasuite.ai/) — designed to integrate as a microservice module.

## Current Status

**Phases completed: 1–9** of 15. The project is a functional MVP with real video analysis.

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Monorepo structure & docs | ✅ |
| 2 | Frontend Vite + Tailwind + Stitch tokens | ✅ |
| 3 | HTML Stitch → React components | ✅ |
| 4 | Backend FastAPI + mock contract | ✅ |
| 5 | Frontend ↔ Backend connection | ✅ |
| 6 | MP4 upload + local persistence | ✅ |
| 7 | Real video pipeline (FFmpeg + OpenCV) | ✅ |
| 8 | Background job lifecycle + polling | ✅ |
| 9 | Explanation engine + actionable insights | ✅ |
| 10 | Clip export with FFmpeg | ⬚ |
| 11–15 | Advanced features, IA multimodal, tests | ⬚ |

## Features

- **Professional UI** — React/Vite/Tailwind dark-mode dashboard inspired by Stitch Cinematic Intelligence Lab, responsive desktop & mobile
- **Video upload** — drag-and-drop MP4/MOV/WebM/AVI/MKV (max 200 MB), validated client and server side
- **Real video analysis** — frame sampling with OpenCV, motion detection, brightness analysis, heuristic scoring
- **FFmpeg integration** — optional metadata extraction via `ffprobe` (falls back to OpenCV if unavailable)
- **Background processing** — analysis runs in a background thread; the API responds immediately and the frontend polls for progress
- **Unified timeline** — per-second scores for virality, arousal, valence, and retention with auto-detected labels (hook, pattern disruption, retention dip, motion spike)
- **Clip ranking** — automatic detection of top clip candidates from virality peaks
- **Explanation engine** — 8 rule-based insight generators producing actionable recommendations with timestamps
- **Mock fallback** — full UI works offline with synthetic data when backend is unavailable
- **AureaSuite-ready** — auth placeholders, namespaced API routes, configurable storage backend

## Architecture

```
virality-analizer/
├─ frontend/          React 19 + Vite 8 + Tailwind 4 + TypeScript
├─ backend/           FastAPI + OpenCV + FFmpeg pipeline
│  └─ app/
│     ├─ api/routes/  REST endpoints
│     ├─ schemas/     Pydantic models (source of truth)
│     ├─ services/    Orchestration layer
│     ├─ processing/  FFmpeg probe, frame extraction, timeline, clip ranking
│     ├─ ai_services/ Mock analyzer, heuristic analyzer, explanation engine
│     ├─ workers/     Background analysis jobs
│     └─ core/        Config, paths, auth placeholder
├─ shared/            JSON schemas + TypeScript types
├─ uploads/           Video files + analysis results (gitignored)
└─ docs/              Architecture & API contract docs
```

## Requirements

- **Node.js** 20+
- **Python** 3.11+
- **FFmpeg** (recommended, for accurate metadata — [download](https://www.gyan.dev/ffmpeg/builds/))
- **Git**

## Quick Start

### 1. Clone & setup

```bash
git clone <repo-url>
cd virality-analizer
```

### 2. Backend

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1
# Windows Git Bash
source .venv/Scripts/activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -e backend

# Start the server (auto-reload)
uvicorn app.main:app --reload --app-dir backend
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

The UI will be available at `http://localhost:5173`.

### 4. Verify

```bash
# Backend health check
curl http://127.0.0.1:8000/api/viral-intelligence/health

# Get mock analysis (no video needed)
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/mock

# Upload a video for real analysis
curl -F "file=@sample.mp4" http://127.0.0.1:8000/api/viral-intelligence/analysis

# Check analysis status/result
curl http://127.0.0.1:8000/api/viral-intelligence/analysis/<analysis_id>
```

## API Endpoints

All routes under `/api/viral-intelligence/`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/analysis/mock` | Full mock analysis for UI dev |
| `POST` | `/analysis` | Upload video → starts background analysis |
| `GET` | `/analysis/{id}` | Get analysis status & results |
| `GET` | `/analysis` | List all analyses |

### Analysis lifecycle

```
POST /analysis (upload) → status: "processing", progress: 0.0
GET  /analysis/{id}     → status: "processing", progress: 0.1–0.9
GET  /analysis/{id}     → status: "completed",  progress: 1.0, full results
```

The frontend polls every 1.5 seconds until `completed` or `failed`.

## Analysis Pipeline

When a video is uploaded, the backend runs this pipeline in a background thread:

1. **Probe** — `ffprobe` extracts duration, FPS, resolution, codecs (falls back to OpenCV)
2. **Frame extraction** — samples one frame per second, saved as JPEG in `uploads/<id>/frames/`
3. **Visual signals** — computes inter-frame differences (motion) and brightness per sample
4. **Timeline** — normalizes and smooths signals into per-second virality/arousal/valence/retention scores
5. **Clip ranking** — detects virality peaks, expands windows, ranks top 3 clip candidates
6. **Explanation engine** — generates insights from 8 rule categories with timestamps and actionable recommendations

### Insight categories

| Rule | Detects |
|------|---------|
| Hook analysis | Opening strength (first 3 seconds) |
| Pattern disruption | Virality spikes from scene changes |
| Retention dips | Drop-off risk points |
| Emotional arc | Arousal/valence dynamics |
| Pacing | Fast/slow visual rhythm |
| Clip reasoning | Why each clip was selected |
| Overall score | Global score explanation |
| Ending strength | Loop potential & closing impact |

## Environment Variables

All prefixed with `AUREA_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUREA_ENVIRONMENT` | `local` | `local` / `staging` / `production` |
| `AUREA_CORS_ORIGINS` | `localhost:5173` | Allowed CORS origins |
| `AUREA_AUTH_ENABLED` | `false` | Enable Clerk JWT validation |
| `AUREA_STORAGE_BACKEND` | `local` | `local` / `s3` |
| `VITE_API_BASE_URL` | (empty) | Backend URL for frontend |

## Key Commands

```bash
# ── Frontend ──
cd frontend
npm run dev          # Dev server with HMR
npm run build        # Production build (TypeScript + Vite)
npm run preview      # Preview production build
npm run lint         # ESLint

# ── Backend ──
uvicorn app.main:app --reload --app-dir backend   # Dev server
python -m pytest backend/tests                      # Run tests (when available)

# ── FFmpeg ──
ffmpeg -version                                     # Verify installation
ffprobe -v quiet -print_format json -show_format -show_streams video.mp4  # Manual probe
```

## Development Philosophy

1. **Contract first** — UI and backend connect via a stable JSON schema
2. **Mock before block** — if FFmpeg/model/GPU is missing, use mock with explicit warning
3. **MVP local-first** — nothing requires cloud, login, or API keys to function
4. **Adapters, not giant refactors** — each AI model connects behind an existing interface
5. **Continuous validation** — each phase ends with a minimal build/test/curl check
6. **Always "Potential Virality Score"** — never guarantee virality
7. **Integration-ready** — all decisions consider future embedding into AureaSuite

## License

Private — All rights reserved.
