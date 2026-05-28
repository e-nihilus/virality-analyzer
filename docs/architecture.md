# Architecture — Aurea Viral Intelligence

## Overview

Local-first video analysis platform. Monorepo with separate frontend and backend sharing types/contracts.

## High-Level Architecture

```
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

## Frontend

- React + Vite + TypeScript
- TailwindCSS with Stitch design tokens (dark mode, Geist font, glass panels)
- Zustand for lightweight state management
- Custom SVG components for timeline visualization
- Native fetch with thin api/client.ts wrapper

## Backend

- FastAPI with simple REST endpoints
- Pydantic as schema source of truth
- BackgroundTasks/in-process jobs for MVP (no Redis/Celery initially)
- JSON files in uploads/<analysis_id>/result.json (no DB initially)
- FFmpeg via subprocess for metadata and frames

## AI Pipeline Architecture

Layered approach:

1. **MockAnalyzer**: synthetic data for UI development
2. **HeuristicAnalyzer**: basic FFmpeg/OpenCV metrics (motion, cuts, brightness)
3. **Model adapters** (future): VideoMAE, Whisper, CLIP, EMOCA behind same interface

Each analyzer produces normalized fragments:

```
VisualAnalyzer    → motion, cuts, brightness
AudioAnalyzer     → energy, silence, beat proxies
SpeechAnalyzer    → transcript, segments, hook phrases
EmotionAnalyzer   → valence/arousal/emotion estimates
Fusion/Timeline   → unified timeline per second/window
ClipRanker        → top clips from peaks + context windows
ExplanationEngine → human-readable reasons
```

## Data Flow

1. User uploads MP4 via UI
2. Frontend POSTs to /api/analysis
3. Backend creates analysis_id, stores video in uploads/<analysis_id>/
4. Background job runs analysis pipeline
5. Results saved as JSON in uploads/<analysis_id>/result.json
6. Frontend polls /api/analysis/{id} for status and results

## Storage Layout

```
uploads/<analysis_id>/
├─ input.mp4
├─ result.json
├─ frames/
│  ├─ 000001.jpg
│  └─ ...
└─ clips/
   └─ clip_0.mp4
```

## Virality Score Formula (MVP)

```
virality = 0.35 * hook_score
         + 0.25 * arousal_score
         + 0.20 * novelty_score
         + 0.10 * pacing_score
         + 0.10 * retention_proxy
```

Weights live in configuration, adjustable without touching UI.

## Key Design Decisions

1. **Contract-first**: JSON contract must exist before connecting UI and backend
2. **Mock before block**: missing FFmpeg/GPU uses mock/heuristic with explicit warning
3. **Sampling over exhaustive**: MVP samples frames every 1-2 seconds, not every frame
4. **"Potential Virality Score"**: never guarantee virality, always communicate probability
5. **Adapter pattern for AI**: swap analyzers without changing output contract
