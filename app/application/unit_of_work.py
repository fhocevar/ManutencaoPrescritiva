from typing import Protocol

from app.domain.ports import AnalysisRepository, DocumentRepository, EventRepository


class UnitOfWork(Protocol):
    events: EventRepository
    documents: DocumentRepository
    analyses: AnalysisRepository

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, traceback) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
