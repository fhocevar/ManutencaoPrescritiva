from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories import (
    SqlAlchemyAnalysisRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyEventRepository,
)


class SqlAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.events = SqlAlchemyEventRepository(session)
        self.documents = SqlAlchemyDocumentRepository(session)
        self.analyses = SqlAlchemyAnalysisRepository(session)

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
