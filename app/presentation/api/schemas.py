from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.constants import SENSOR_FEATURES
from app.domain.entities import SensorEvent


class EventRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | None = None
    created_at: datetime
    fault: str = Field(min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_metrics(self) -> "EventRequest":
        data = self.model_dump()
        missing = [name for name in SENSOR_FEATURES if data.get(name) is None]
        if missing:
            raise ValueError(f"Métricas obrigatórias ausentes: {', '.join(missing)}")
        return self

    def to_domain(self) -> SensorEvent:
        raw = self.model_dump()
        metrics = {name: float(raw[name]) for name in SENSOR_FEATURES}
        return SensorEvent(
            external_id=self.id,
            created_at=self.created_at,
            fault=self.fault,
            metrics=metrics,
        )


class SimilarEventResponse(BaseModel):
    event_id: UUID
    external_id: int | None
    created_at: datetime
    fault: str
    distance: float
    metrics: dict[str, Any]


class EvidenceResponse(BaseModel):
    document_id: UUID
    filename: str
    chunk_id: UUID
    content: str
    similarity: float


class RecommendationResponse(BaseModel):
    status: str
    summary: str
    steps: list[str]
    evidence: list[EvidenceResponse]


class AnalysisResponse(BaseModel):
    event_id: UUID
    detected_fault: str
    is_problem: bool
    anomaly_score: float | None
    similar_events_count: int
    frequency_per_month: float
    similar_events: list[SimilarEventResponse]
    documentation_found: bool
    recommendation: RecommendationResponse


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    filename: str
    chunks: int


class ChatRequest(BaseModel):
    question: str = Field(min_length=3)
    fault: str | None = None
    limit: int = Field(default=5, ge=1, le=10)


class FeedbackRequest(BaseModel):
    event_id: UUID | None = None
    analysis_id: UUID | None = None
    rating: int = Field(ge=1, le=5)
    comment: str | None = None
    created_by: str | None = None


class FeedbackResponse(BaseModel):
    id: UUID
    status: str = "created"
