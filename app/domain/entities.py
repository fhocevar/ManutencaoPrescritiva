from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class SensorEvent:
    external_id: int | None
    created_at: datetime
    fault: str
    metrics: dict[str, float]

    def metric(self, name: str) -> float:
        value = self.metrics.get(name)
        if value is None:
            raise ValueError(f"Métrica obrigatória ausente: {name}")
        return float(value)


@dataclass(frozen=True)
class SimilarEvent:
    event_id: UUID
    external_id: int | None
    created_at: datetime
    fault: str
    distance: float
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentEvidence:
    document_id: UUID
    filename: str
    chunk_id: UUID
    content: str
    similarity: float


@dataclass(frozen=True)
class Recommendation:
    status: str
    summary: str
    steps: tuple[str, ...]
    evidence: tuple[DocumentEvidence, ...]


@dataclass(frozen=True)
class EventAnalysis:
    event_id: UUID
    detected_fault: str
    is_problem: bool
    anomaly_score: float | None
    similar_events: tuple[SimilarEvent, ...]
    frequency_per_month: float
    recommendation: Recommendation
