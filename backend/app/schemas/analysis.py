from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class VideoMeta(BaseModel):
    filename: str
    duration_seconds: Optional[float] = None
    fps: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None


class TimelineEntry(BaseModel):
    time_seconds: float
    virality: Optional[float] = Field(None, ge=0, le=1)
    valence: Optional[float] = Field(None, ge=0, le=1)
    arousal: Optional[float] = Field(None, ge=0, le=1)
    retention: Optional[float] = Field(None, ge=0, le=1)
    label: Optional[str] = None


class TopClip(BaseModel):
    start_seconds: float
    end_seconds: float
    score: float = Field(ge=0, le=1)
    predicted_retention: Optional[float] = Field(None, ge=0, le=1)
    reasons: Optional[list[str]] = None


class InsightSeverity(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Insight(BaseModel):
    title: str
    description: str
    severity: InsightSeverity
    timestamp: Optional[float] = None
    action: Optional[str] = None


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class TextHook(BaseModel):
    text: str
    hook_type: str
    timestamp: float
    confidence: float = Field(ge=0, le=1)


class Transcript(BaseModel):
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    hooks: list[TextHook] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    id: str
    user_id: Optional[str] = None
    status: AnalysisStatus
    progress: Optional[float] = Field(None, ge=0, le=1)
    video: Optional[VideoMeta] = None
    overall_virality_score: Optional[float] = Field(None, ge=0, le=1)
    retention_score: Optional[float] = Field(None, ge=0, le=1)
    rewatch_factor: Optional[float] = None
    action_recognition_score: Optional[float] = Field(None, ge=0, le=1)
    dominant_emotion: Optional[str] = None
    timeline: Optional[list[TimelineEntry]] = None
    top_clips: Optional[list[TopClip]] = None
    insights: Optional[list[Insight]] = None
    transcript: Optional[Transcript] = None


class AnalysisSummary(BaseModel):
    id: str
    user_id: Optional[str] = None
    status: AnalysisStatus
    video: Optional[VideoMeta] = None
    overall_virality_score: Optional[float] = Field(None, ge=0, le=1)
    created_at: Optional[str] = None


class AnalysisCreateResponse(BaseModel):
    id: str
    status: AnalysisStatus
    progress: Optional[float] = Field(None, ge=0, le=1)
    message: Optional[str] = None
