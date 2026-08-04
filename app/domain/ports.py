from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.domain.entities import DocumentEvidence, SensorEvent, SimilarEvent


class EventRepository(Protocol):
    async def add(self, event: SensorEvent, vector: list[float]) -> UUID: ...
    async def find_similar(
        self,
        vector: list[float],
        limit: int,
        max_distance: float,
        exclude_id: UUID | None = None,
    ) -> list[SimilarEvent]: ...
    async def count_by_fault(self, fault: str) -> int: ...


class DocumentRepository(Protocol):
    async def add_document(self, filename: str, source_path: str, checksum: str) -> UUID: ...
    async def replace_chunks(
        self,
        document_id: UUID,
        chunks: list[tuple[int, str, list[float], dict]],
    ) -> None: ...
    async def search(
        self,
        query_vector: list[float],
        fault: str,
        limit: int,
        minimum_similarity: float,
    ) -> list[DocumentEvidence]: ...


class AnalysisRepository(Protocol):
    async def save(
        self,
        event_id: UUID,
        anomaly_score: float | None,
        similar_count: int,
        frequency_per_month: float,
        recommendation_status: str,
        recommendation_text: str,
    ) -> UUID: ...


class SensorModel(Protocol):
    def transform(self, event: SensorEvent) -> list[float]: ...
    def anomaly_score(self, event: SensorEvent) -> float | None: ...


class EmbeddingService(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class RecommendationGenerator(Protocol):
    async def generate(self, fault: str, evidence: list[DocumentEvidence]) -> tuple[str, list[str]]: ...


class DocumentParser(Protocol):
    def parse(self, path: Path) -> str: ...
