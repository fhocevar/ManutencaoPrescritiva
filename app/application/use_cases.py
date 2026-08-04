import hashlib
from pathlib import Path
from uuid import UUID

from app.domain.entities import EventAnalysis, Recommendation, SensorEvent
from app.domain.ports import (
    AnalysisRepository,
    DocumentParser,
    DocumentRepository,
    EmbeddingService,
    EventRepository,
    RecommendationGenerator,
    SensorModel,
)
from app.domain.services import FaultPolicy, FrequencyCalculator


class AnalyzeEventUseCase:
    def __init__(
        self,
        event_repository: EventRepository,
        document_repository: DocumentRepository,
        analysis_repository: AnalysisRepository,
        sensor_model: SensorModel,
        embedding_service: EmbeddingService,
        recommendation_generator: RecommendationGenerator,
        similar_limit: int,
        max_event_distance: float,
        min_document_similarity: float,
    ) -> None:
        self.events = event_repository
        self.documents = document_repository
        self.analyses = analysis_repository
        self.sensor_model = sensor_model
        self.embeddings = embedding_service
        self.generator = recommendation_generator
        self.similar_limit = similar_limit
        self.max_event_distance = max_event_distance
        self.min_document_similarity = min_document_similarity

    async def execute(self, event: SensorEvent) -> EventAnalysis:
        vector = self.sensor_model.transform(event)
        event_id = await self.events.add(event, vector)
        anomaly_score = self.sensor_model.anomaly_score(event)

        similar = await self.events.find_similar(
            vector=vector,
            limit=self.similar_limit,
            max_distance=self.max_event_distance,
            exclude_id=event_id,
        )
        frequency = FrequencyCalculator.per_month(similar, event.created_at)
        is_problem = FaultPolicy.is_problem(event.fault)

        evidence = []
        if is_problem:
            query = (
                f"Defeito {event.fault}. Procedimento de inspeção, diagnóstico, "
                "manutenção, correção, segurança e validação."
            )
            query_vector = self.embeddings.embed([query])[0]
            evidence = await self.documents.search(
                query_vector=query_vector,
                fault=event.fault,
                limit=5,
                minimum_similarity=self.min_document_similarity,
            )

        if not is_problem:
            recommendation = Recommendation(
                status="not_required",
                summary="O evento representa um estado operacional, não uma falha.",
                steps=("Continuar o monitoramento conforme a rotina operacional.",),
                evidence=(),
            )
        elif not evidence:
            recommendation = Recommendation(
                status="unsupported",
                summary=(
                    "Não há documentação suficiente para recomendar uma ação segura "
                    f"para o defeito '{event.fault}'."
                ),
                steps=(
                    "Registrar ou anexar um manual, procedimento ou relatório técnico para o defeito.",
                    "Submeter o documento à validação da equipe de manutenção.",
                    "Reprocessar o evento após a indexação do documento.",
                ),
                evidence=(),
            )
        else:
            summary, steps = await self.generator.generate(event.fault, evidence)
            recommendation = Recommendation(
                status="supported",
                summary=summary,
                steps=tuple(steps),
                evidence=tuple(evidence),
            )

        await self.analyses.save(
            event_id=event_id,
            anomaly_score=anomaly_score,
            similar_count=len(similar),
            frequency_per_month=frequency,
            recommendation_status=recommendation.status,
            recommendation_text=recommendation.summary,
        )

        return EventAnalysis(
            event_id=event_id,
            detected_fault=event.fault,
            is_problem=is_problem,
            anomaly_score=anomaly_score,
            similar_events=tuple(similar),
            frequency_per_month=frequency,
            recommendation=recommendation,
        )


class IngestDocumentUseCase:
    def __init__(
        self,
        repository: DocumentRepository,
        parser: DocumentParser,
        embeddings: EmbeddingService,
        chunk_size: int = 900,
        chunk_overlap: int = 150,
    ) -> None:
        self.repository = repository
        self.parser = parser
        self.embeddings = embeddings
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def execute(self, path: Path) -> tuple[UUID, int]:
        content = self.parser.parse(path)
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        document_id = await self.repository.add_document(path.name, str(path), checksum)
        text_chunks = self._chunk(content)
        vectors = self.embeddings.embed(text_chunks)
        chunks = [
            (index, text, vector, {"filename": path.name})
            for index, (text, vector) in enumerate(zip(text_chunks, vectors, strict=True))
        ]
        await self.repository.replace_chunks(document_id, chunks)
        return document_id, len(chunks)

    def _chunk(self, text: str) -> list[str]:
        normalized = " ".join(text.split())
        if not normalized:
            raise ValueError("Documento sem conteúdo textual.")
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + self.chunk_size, len(normalized))
            chunks.append(normalized[start:end])
            if end == len(normalized):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks
