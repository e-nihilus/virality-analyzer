# API Contract — Aurea Viral Intelligence MVP

## Base URL
```
http://localhost:8000/api
```

## Endpoints

### Health Check
```
GET /api/health
```
Response:
```json
{"status": "ok", "version": "0.1.0"}
```

### Create Analysis
```
POST /api/analysis
Content-Type: multipart/form-data
```
Body: `file` (MP4 video file)

Response `201`:
```json
{
  "id": "analysis_abc123",
  "status": "pending"
}
```

### Get Analysis Status / Result
```
GET /api/analysis/{id}
```

Response `200` (pending):
```json
{
  "id": "analysis_abc123",
  "status": "processing",
  "progress": 0.45
}
```

Response `200` (completed):
```json
{
  "id": "analysis_abc123",
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

### List Analyses
```
GET /api/analysis
```
Response `200`:
```json
[
  {
    "id": "analysis_abc123",
    "status": "completed",
    "video": { "filename": "video.mp4" },
    "overall_virality_score": 0.92,
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

## Status Values
| Status | Description |
|--------|-------------|
| `pending` | Analysis created, waiting to start |
| `processing` | Analysis in progress |
| `completed` | Analysis finished successfully |
| `failed` | Analysis encountered an error |

## Data Types

### TimelineEntry
| Field | Type | Description |
|-------|------|-------------|
| time_seconds | float | Timestamp in seconds |
| virality | float (0-1) | Virality score at this moment |
| valence | float (0-1) | Emotional valence |
| arousal | float (0-1) | Emotional arousal |
| retention | float (0-1) | Predicted retention |
| label | string? | Optional label for significant moments |

### TopClip
| Field | Type | Description |
|-------|------|-------------|
| start_seconds | float | Clip start time |
| end_seconds | float | Clip end time |
| score | float (0-1) | Clip quality score |
| predicted_retention | float (0-1) | Expected retention rate |
| reasons | string[] | Why this clip was selected |

### Insight
| Field | Type | Description |
|-------|------|-------------|
| title | string | Insight headline |
| description | string | Detailed explanation |
| severity | "high" \| "medium" \| "low" | Impact level |

## Notes
- All scores are 0-1 range (float)
- "Potential Virality Score" — never guarantees virality
- MVP returns mock/heuristic data; same contract when real AI is plugged in
