import argparse
import asyncio
import sys
from pathlib import Path

from app.application.use_cases import IngestDocumentUseCase
from app.infrastructure.config import get_settings
from app.infrastructure.db import SessionFactory, engine
from app.infrastructure.documents import MultiFormatDocumentParser
from app.infrastructure.embeddings import SentenceTransformerEmbeddingService
from app.infrastructure.models import Base
from app.infrastructure.repositories import SqlAlchemyDocumentRepository


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


async def main(directory: Path) -> int:
    if not directory.exists():
        print(f"[ERRO] Diretório não encontrado: {directory}")
        return 2

    if not directory.is_dir():
        print(f"[ERRO] O caminho informado não é um diretório: {directory}")
        return 2

    paths = sorted(
        (
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: str(path).lower(),
    )

    if not paths:
        print(
            "[AVISO] Nenhum documento suportado encontrado. "
            "Formatos aceitos: PDF, TXT e Markdown."
        )
        return 0

    settings = get_settings()

    print(f"Diretório: {directory.resolve()}")
    print(f"Documentos encontrados: {len(paths)}")
    print(f"Modelo de embeddings: {settings.embedding_model}")
    print("-" * 80)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    processed = 0
    ignored = 0
    failed = 0
    total_chunks = 0

    async with SessionFactory() as session:
        use_case = IngestDocumentUseCase(
            repository=SqlAlchemyDocumentRepository(session),
            parser=MultiFormatDocumentParser(),
            embeddings=SentenceTransformerEmbeddingService(
                settings.embedding_model
            ),
        )

        for path in paths:
            try:
                if path.stat().st_size == 0:
                    ignored += 1
                    print(f"[IGNORADO] {path.name}: arquivo vazio.")
                    continue

                document_id, chunks = await use_case.execute(path)

                processed += 1
                total_chunks += chunks

                print(
                    f"[OK] {path.name}: "
                    f"{chunks} chunks "
                    f"(document_id={document_id})"
                )

            except ValueError as exc:
                ignored += 1
                print(f"[IGNORADO] {path.name}: {exc}")

            except Exception as exc:
                failed += 1

                try:
                    await session.rollback()
                except Exception:
                    pass

                print(
                    f"[ERRO] {path.name}: "
                    f"{type(exc).__name__}: {exc}"
                )

    print("-" * 80)
    print("Resumo da ingestão")
    print(f"Processados com sucesso: {processed}")
    print(f"Ignorados: {ignored}")
    print(f"Falhas: {failed}")
    print(f"Chunks gerados: {total_chunks}")
    print(f"Total encontrado: {len(paths)}")

    if failed > 0:
        print(
            "[AVISO] A ingestão terminou com falhas em alguns documentos. "
            "Os demais arquivos foram processados."
        )
        return 1

    print("[SUCESSO] Ingestão documental concluída.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extrai, segmenta, vetoriza e persiste documentos "
            "na base de conhecimento."
        )
    )
    parser.add_argument(
        "--directory",
        type=Path,
        required=True,
        help="Diretório contendo documentos PDF, TXT ou Markdown.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()

    try:
        exit_code = asyncio.run(main(arguments.directory))
    except KeyboardInterrupt:
        print("\n[INTERROMPIDO] Execução cancelada pelo usuário.")
        exit_code = 130
    except Exception as exc:
        print(
            f"[ERRO FATAL] {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        exit_code = 1

    raise SystemExit(exit_code)