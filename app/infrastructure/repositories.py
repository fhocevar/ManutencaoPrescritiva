from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import DocumentEvidence, SensorEvent, SimilarEvent
from app.infrastructure.models import AnalysisModel, DocumentChunkModel, DocumentModel, EventModel, FeedbackModel


class SqlAlchemyEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: SensorEvent, vector: list[float]) -> UUID:
        model = EventModel(
            external_id=event.external_id,
            created_at=event.created_at,
            fault=event.fault,
            metrics=event.metrics,
            sensor_vector=vector,
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model.id

    async def find_similar(
        self,
        vector: list[float],
        limit: int,
        max_distance: float,
        exclude_id: UUID | None = None,
    ) -> list[SimilarEvent]:
        distance = EventModel.sensor_vector.cosine_distance(vector).label("distance")
        query = select(EventModel, distance).where(distance <= max_distance)
        if exclude_id:
            query = query.where(EventModel.id != exclude_id)
        rows = (await self.session.execute(query.order_by(distance).limit(limit))).all()
        return [
            SimilarEvent(
                event_id=model.id,
                external_id=model.external_id,
                created_at=model.created_at,
                fault=model.fault,
                distance=float(dist),
                metrics=model.metrics,
            )
            for model, dist in rows
        ]

    async def count_by_fault(self, fault: str) -> int:
        result = await self.session.scalar(
            select(func.count()).select_from(EventModel).where(EventModel.fault == fault)
        )
        return int(result or 0)


class SqlAlchemyDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_document(self, filename: str, source_path: str, checksum: str) -> UUID:
        existing = await self.session.scalar(
            select(DocumentModel).where(DocumentModel.filename == filename)
        )
        if existing:
            existing.source_path = source_path
            existing.checksum = checksum
            await self.session.commit()
            return existing.id

        model = DocumentModel(filename=filename, source_path=source_path, checksum=checksum)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model.id

    async def replace_chunks(
        self,
        document_id: UUID,
        chunks: list[tuple[int, str, list[float], dict]],
    ) -> None:
        await self.session.execute(
            delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document_id)
        )
        self.session.add_all(
            [
                DocumentChunkModel(
                    document_id=document_id,
                    chunk_index=index,
                    content=content,
                    embedding=embedding,
                    metadata_json=metadata,
                )
                for index, content, embedding, metadata in chunks
            ]
        )
        await self.session.commit()

    async def search(
        self,
        query_vector: list[float],
        fault: str,
        limit: int,
        minimum_similarity: float,
    ) -> list[DocumentEvidence]:
        distance = DocumentChunkModel.embedding.cosine_distance(query_vector).label("distance")
        similarity = (1 - distance).label("similarity")
        query = (
            select(DocumentChunkModel, DocumentModel, similarity)
            .join(DocumentModel, DocumentModel.id == DocumentChunkModel.document_id)
            .where(similarity >= minimum_similarity)
            .order_by(distance)
            .limit(limit * 3)
        )
        rows = (await self.session.execute(query)).all()
        fault_lower = (fault or "").lower().replace("_", " ")
        ranked = []
        for chunk, document, score in rows:
            content_lower = chunk.content.lower().replace("_", " ")
            lexical_boost = 0.08 if fault_lower and fault_lower in content_lower else 0.0
            ranked.append((float(score) + lexical_boost, chunk, document, float(score)))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            DocumentEvidence(
                document_id=document.id,
                filename=document.filename,
                chunk_id=chunk.id,
                content=chunk.content,
                similarity=score,
            )
            for _, chunk, document, score in ranked[:limit]
        ]


class SqlAlchemyAnalysisRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(
        self,
        event_id: UUID,
        anomaly_score: float | None,
        similar_count: int,
        frequency_per_month: float,
        recommendation_status: str,
        recommendation_text: str,
    ) -> UUID:
        model = AnalysisModel(
            event_id=event_id,
            anomaly_score=anomaly_score,
            similar_count=similar_count,
            frequency_per_month=frequency_per_month,
            recommendation_status=recommendation_status,
            recommendation_text=recommendation_text,
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model.id


class SqlAlchemyFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        event_id: UUID | None,
        analysis_id: UUID | None,
        rating: int,
        comment: str | None,
        created_by: str | None,
    ) -> UUID:
        model = FeedbackModel(
            event_id=event_id,
            analysis_id=analysis_id,
            rating=rating,
            comment=comment,
            created_by=created_by,
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return model.id


class SqlAlchemyStatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self) -> dict:
        events = await self.session.scalar(select(func.count()).select_from(EventModel))
        docs = await self.session.scalar(select(func.count()).select_from(DocumentModel))
        chunks = await self.session.scalar(select(func.count()).select_from(DocumentChunkModel))
        analyses = await self.session.scalar(select(func.count()).select_from(AnalysisModel))
        top_faults = (
            await self.session.execute(
                select(EventModel.fault, func.count().label("total"))
                .group_by(EventModel.fault)
                .order_by(text("total DESC"))
                .limit(10)
            )
        ).all()
        return {
            "events": int(events or 0),
            "documents": int(docs or 0),
            "document_chunks": int(chunks or 0),
            "analyses": int(analyses or 0),
            "top_faults": [{"fault": fault, "total": int(total)} for fault, total in top_faults],
        }
