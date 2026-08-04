import asyncio
from pathlib import Path

from app.application.use_cases import IngestDocumentUseCase
from app.infrastructure.config import get_settings
from app.infrastructure.db import SessionFactory, engine
from app.infrastructure.documents import MultiFormatDocumentParser
from app.infrastructure.embeddings import SentenceTransformerEmbeddingService
from app.infrastructure.models import Base
from app.infrastructure.repositories import SqlAlchemyDocumentRepository

DEMO_DOC = """
Procedimento técnico para cocked_rotor_2.
Sintomas: vibração elevada nos eixos X e Z, aumento de fator de crista e aceleração de pico.
Inspeção: bloquear a máquina, confirmar condição segura, verificar fixação, acoplamento, alinhamento do rotor e condição dos mancais.
Correção: corrigir desalinhamento, reapertar fixações conforme torque do fabricante, substituir componente danificado quando aplicável e registrar evidências.
Validação: religar em condição controlada, monitorar RMS de velocidade, aceleração de pico, temperatura e ruído anormal por pelo menos um ciclo operacional.
"""


async def main() -> None:
    settings = get_settings()
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    path = settings.documents_dir / "procedimento_cocked_rotor_2.md"
    path.write_text(DEMO_DOC, encoding="utf-8")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionFactory() as session:
        use_case = IngestDocumentUseCase(
            repository=SqlAlchemyDocumentRepository(session),
            parser=MultiFormatDocumentParser(),
            embeddings=SentenceTransformerEmbeddingService(settings.embedding_model),
        )
        document_id, chunks = await use_case.execute(path)
        print(f"Documento demo indexado: {document_id} / {chunks} chunks")


if __name__ == "__main__":
    asyncio.run(main())
