from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from time import perf_counter

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.chat_use_case import ChatWithDocumentsUseCase
from app.application.dtos import ChatCommand
from app.application.use_cases import AnalyzeEventUseCase, IngestDocumentUseCase
from app.infrastructure.config import get_settings
from app.infrastructure.db import engine, get_session
from app.infrastructure.models import Base
from app.infrastructure.observability import (
    ANALYSIS_COUNTER,
    REQUEST_COUNTER,
    REQUEST_LATENCY,
    configure_logging,
)
from app.infrastructure.repositories import SqlAlchemyFeedbackRepository, SqlAlchemyStatsRepository
from app.presentation.api.dependencies import (
    get_analyze_use_case,
    get_chat_use_case,
    get_ingest_document_use_case,
)
from app.presentation.api.schemas import (
    AnalysisResponse,
    ChatRequest,
    DocumentUploadResponse,
    EventRequest,
    FeedbackRequest,
    FeedbackResponse,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging(settings.log_level)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="API enterprise de manutenção preditiva e prescritiva com busca por similaridade e RAG.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = perf_counter()
    response = await call_next(request)
    latency = perf_counter() - start
    path = request.url.path
    REQUEST_COUNTER.labels(request.method, path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(latency)
    return response


@app.get("/health/live", tags=["health"])
async def live() -> dict:
    return {"status": "live", "environment": settings.app_env}


@app.get("/health/ready", tags=["health"])
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "environment": settings.app_env}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/stats", tags=["stats"])
async def stats(session: AsyncSession = Depends(get_session)) -> dict:
    return await SqlAlchemyStatsRepository(session).summary()


@app.post("/api/v1/events/analyze", response_model=AnalysisResponse, tags=["events"])
async def analyze_event(
    payload: EventRequest,
    use_case: AnalyzeEventUseCase = Depends(get_analyze_use_case),
) -> AnalysisResponse:
    try:
        result = await use_case.execute(payload.to_domain())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ANALYSIS_COUNTER.labels(result.recommendation.status).inc()
    evidence = [
        {
            "document_id": item.document_id,
            "filename": item.filename,
            "chunk_id": item.chunk_id,
            "content": item.content,
            "similarity": item.similarity,
        }
        for item in result.recommendation.evidence
    ]
    similar_events = [
        {
            "event_id": item.event_id,
            "external_id": item.external_id,
            "created_at": item.created_at,
            "fault": item.fault,
            "distance": item.distance,
            "metrics": item.metrics,
        }
        for item in result.similar_events
    ]
    return AnalysisResponse(
        event_id=result.event_id,
        detected_fault=result.detected_fault,
        is_problem=result.is_problem,
        anomaly_score=result.anomaly_score,
        similar_events_count=len(result.similar_events),
        frequency_per_month=result.frequency_per_month,
        similar_events=similar_events,
        documentation_found=bool(evidence),
        recommendation={
            "status": result.recommendation.status,
            "summary": result.recommendation.summary,
            "steps": list(result.recommendation.steps),
            "evidence": evidence,
        },
    )


@app.post("/api/v1/documents/upload", response_model=DocumentUploadResponse, tags=["documents"])
async def upload_document(
    file: UploadFile = File(...),
    use_case: IngestDocumentUseCase = Depends(get_ingest_document_use_case),
) -> DocumentUploadResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(status_code=415, detail="Formato suportado: PDF, TXT ou Markdown.")

    with NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
        temporary.write(await file.read())
        temporary_path = Path(temporary.name)

    try:
        target_dir = settings.documents_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / Path(file.filename or temporary_path.name).name
        target.write_bytes(temporary_path.read_bytes())
        document_id, chunks = await use_case.execute(target)
        return DocumentUploadResponse(document_id=document_id, filename=target.name, chunks=chunks)
    finally:
        temporary_path.unlink(missing_ok=True)


@app.post("/api/v1/chat", tags=["chat"])
async def chat(
    payload: ChatRequest,
    use_case: ChatWithDocumentsUseCase = Depends(get_chat_use_case),
) -> dict:
    result = await use_case.execute(ChatCommand(payload.question, payload.fault, payload.limit))
    evidence = result.get("evidence", [])
    result["evidence"] = [
        {
            "document_id": item.document_id,
            "filename": item.filename,
            "chunk_id": item.chunk_id,
            "content": item.content,
            "similarity": item.similarity,
        }
        for item in evidence
    ]
    return result


@app.post("/api/v1/feedback", response_model=FeedbackResponse, tags=["feedback"])
async def feedback(
    payload: FeedbackRequest,
    session: AsyncSession = Depends(get_session),
) -> FeedbackResponse:
    repository = SqlAlchemyFeedbackRepository(session)
    feedback_id = await repository.add(
        event_id=payload.event_id,
        analysis_id=payload.analysis_id,
        rating=payload.rating,
        comment=payload.comment,
        created_by=payload.created_by,
    )
    return FeedbackResponse(id=feedback_id)
