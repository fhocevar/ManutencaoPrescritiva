from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.chat_use_case import ChatWithDocumentsUseCase
from app.application.use_cases import AnalyzeEventUseCase, IngestDocumentUseCase
from app.infrastructure.config import get_settings
from app.infrastructure.db import get_session
from app.infrastructure.documents import MultiFormatDocumentParser
from app.infrastructure.embeddings import SentenceTransformerEmbeddingService
from app.infrastructure.llm import (
    OpenAICompatibleRecommendationGenerator,
    TemplateRecommendationGenerator,
)
from app.infrastructure.ml import SklearnSensorModel
from app.infrastructure.repositories import (
    SqlAlchemyAnalysisRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyEventRepository,
)


_embedding_service = None
_sensor_model = None


def get_embedding_service():
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = SentenceTransformerEmbeddingService(get_settings().embedding_model)
    return _embedding_service


def get_sensor_model():
    global _sensor_model
    if _sensor_model is None:
        _sensor_model = SklearnSensorModel(get_settings().model_artifact_dir)
    return _sensor_model


def get_recommendation_generator():
    settings = get_settings()
    return (
        OpenAICompatibleRecommendationGenerator(
            settings.llm_base_url,
            settings.llm_api_key,
            settings.llm_model,
            settings.llm_timeout_seconds,
        )
        if settings.llm_provider == "openai_compatible"
        else TemplateRecommendationGenerator()
    )


async def get_analyze_use_case(
    session: AsyncSession = Depends(get_session),
) -> AnalyzeEventUseCase:
    settings = get_settings()
    return AnalyzeEventUseCase(
        event_repository=SqlAlchemyEventRepository(session),
        document_repository=SqlAlchemyDocumentRepository(session),
        analysis_repository=SqlAlchemyAnalysisRepository(session),
        sensor_model=get_sensor_model(),
        embedding_service=get_embedding_service(),
        recommendation_generator=get_recommendation_generator(),
        similar_limit=settings.event_similarity_limit,
        max_event_distance=settings.event_max_distance,
        min_document_similarity=settings.document_min_similarity,
    )


async def get_ingest_document_use_case(
    session: AsyncSession = Depends(get_session),
) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(
        repository=SqlAlchemyDocumentRepository(session),
        parser=MultiFormatDocumentParser(),
        embeddings=get_embedding_service(),
    )


async def get_chat_use_case(
    session: AsyncSession = Depends(get_session),
) -> ChatWithDocumentsUseCase:
    settings = get_settings()
    return ChatWithDocumentsUseCase(
        documents=SqlAlchemyDocumentRepository(session),
        embeddings=get_embedding_service(),
        generator=get_recommendation_generator(),
        minimum_similarity=settings.document_min_similarity,
    )
