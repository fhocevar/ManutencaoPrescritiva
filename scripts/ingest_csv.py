import argparse
import asyncio
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, insert

from app.domain.constants import SENSOR_FEATURES
from app.infrastructure.config import get_settings
from app.infrastructure.db import SessionFactory, engine
from app.infrastructure.ml import SklearnSensorModel
from app.infrastructure.models import AnalysisModel, Base, EventModel


REQUIRED_COLUMNS = {
    "id",
    "created_at",
    "fault",
    *SENSOR_FEATURES,
}


def count_csv_rows(csv_path: Path) -> int:
    """
    Conta as linhas para exibir o progresso.

    Para o banner.csv fornecido, que não possui quebras de linha internas
    nos campos, essa contagem corresponde ao número de registros.
    """
    with csv_path.open("r", encoding="utf-8", errors="replace") as file:
        return max(sum(1 for _ in file) - 1, 0)


def validate_columns(columns: list[str]) -> None:
    missing = sorted(REQUIRED_COLUMNS.difference(columns))

    if missing:
        raise ValueError(
            "O CSV não contém todas as colunas obrigatórias. "
            f"Colunas ausentes: {', '.join(missing)}"
        )


def prepare_chunk(chunk: pd.DataFrame) -> pd.DataFrame:
    chunk = chunk.copy()

    chunk["created_at"] = pd.to_datetime(
        chunk["created_at"],
        utc=True,
        errors="coerce",
    )

    invalid_dates = int(chunk["created_at"].isna().sum())

    if invalid_dates:
        print(
            f"[AVISO] {invalid_dates} registro(s) possuem created_at inválido "
            "e serão ignorados."
        )
        chunk = chunk.dropna(subset=["created_at"])

    chunk["fault"] = (
        chunk["fault"]
        .fillna("desconhecido")
        .astype(str)
        .str.strip()
    )

    for feature in SENSOR_FEATURES:
        chunk[feature] = pd.to_numeric(
            chunk[feature],
            errors="coerce",
        )

    feature_columns = list(SENSOR_FEATURES)

    # Como o dataset oficial não possui nulos, isto funciona principalmente
    # como proteção para novas cargas.
    medians = chunk[feature_columns].median(numeric_only=True)

    chunk[feature_columns] = (
        chunk[feature_columns]
        .fillna(medians)
        .fillna(0.0)
    )

    return chunk


def build_records(
    chunk: pd.DataFrame,
    vectors: list[list[float]],
) -> list[dict]:
    records: list[dict] = []

    for position, (_, row) in enumerate(chunk.iterrows()):
        external_id = None

        if pd.notna(row.get("id")):
            external_id = int(row["id"])

        metrics = {
            feature: float(row[feature])
            for feature in SENSOR_FEATURES
        }

        records.append(
            {
                "external_id": external_id,
                "created_at": row["created_at"].to_pydatetime(),
                "fault": str(row["fault"]),
                "metrics": metrics,
                "sensor_vector": vectors[position],
            }
        )

    return records


async def clear_existing_events() -> None:
    """
    Remove análises e eventos previamente carregados.

    Isso é importante porque a execução anterior foi interrompida e pode ter
    deixado uma carga parcial no PostgreSQL.
    """
    async with SessionFactory() as session:
        print("[INFO] Removendo análises e eventos existentes...")

        await session.execute(delete(AnalysisModel))
        await session.execute(delete(EventModel))
        await session.commit()

        print("[OK] Dados anteriores removidos.")


async def main(
    csv_path: Path,
    batch_size: int,
    truncate: bool,
) -> int:
    if not csv_path.exists():
        print(f"[ERRO] Arquivo não encontrado: {csv_path}")
        return 2

    if not csv_path.is_file():
        print(f"[ERRO] O caminho não é um arquivo: {csv_path}")
        return 2

    if batch_size <= 0:
        print("[ERRO] O tamanho do lote deve ser maior que zero.")
        return 2

    settings = get_settings()
    sensor_model = SklearnSensorModel(settings.model_artifact_dir)

    print(f"CSV: {csv_path.resolve()}")
    print(f"Artefatos: {settings.model_artifact_dir}")
    print(f"Tamanho do lote: {batch_size}")

    total_rows = count_csv_rows(csv_path)

    print(f"Registros estimados: {total_rows:,}".replace(",", "."))
    print("-" * 80)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    if truncate:
        await clear_existing_events()

    processed = 0
    failed_batches = 0
    started_at = time.perf_counter()

    reader = pd.read_csv(
        csv_path,
        chunksize=batch_size,
        low_memory=False,
    )

    async with SessionFactory() as session:
        for batch_number, chunk in enumerate(reader, start=1):
            try:
                if batch_number == 1:
                    validate_columns(list(chunk.columns))

                chunk = prepare_chunk(chunk)

                if chunk.empty:
                    print(
                        f"[AVISO] Lote {batch_number} ficou vazio "
                        "após a validação."
                    )
                    continue

                feature_frame = chunk[list(SENSOR_FEATURES)]

                # Transformação vetorial de todo o lote de uma vez.
                # Mantém os nomes das colunas e elimina o warning do sklearn.
                vectors = sensor_model.transform_frame(feature_frame)

                records = build_records(chunk, vectors)

                await session.execute(
                    insert(EventModel),
                    records,
                )
                await session.commit()

                processed += len(records)

                elapsed = max(time.perf_counter() - started_at, 0.001)
                rate = processed / elapsed
                percentage = (
                    processed / total_rows * 100
                    if total_rows
                    else 0
                )

                print(
                    f"[OK] Lote {batch_number}: "
                    f"{len(records)} registros | "
                    f"total={processed}/{total_rows} "
                    f"({percentage:.2f}%) | "
                    f"{rate:.1f} registros/s"
                )

            except Exception as exc:
                failed_batches += 1
                await session.rollback()

                print(
                    f"[ERRO] Lote {batch_number}: "
                    f"{type(exc).__name__}: {exc}"
                )

                return 1

    elapsed = time.perf_counter() - started_at

    print("-" * 80)
    print("Resumo da ingestão")
    print(f"Registros carregados: {processed}")
    print(f"Lotes com falha: {failed_batches}")
    print(f"Tempo total: {elapsed:.2f} segundos")

    if elapsed > 0:
        print(f"Velocidade média: {processed / elapsed:.1f} registros/s")

    print("[SUCESSO] Ingestão do CSV concluída.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Carrega eventos de sensores no PostgreSQL utilizando "
            "processamento e inserção em lotes."
        )
    )

    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Caminho do arquivo banner.csv.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=2000,
        help="Quantidade de registros por transação. Padrão: 2000.",
    )

    parser.add_argument(
        "--truncate",
        action="store_true",
        help=(
            "Remove análises e eventos existentes antes da carga. "
            "Use após uma importação interrompida ou para recarga integral."
        ),
    )

    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()

    try:
        exit_code = asyncio.run(
            main(
                csv_path=arguments.csv,
                batch_size=arguments.batch_size,
                truncate=arguments.truncate,
            )
        )
    except KeyboardInterrupt:
        print("\n[INTERROMPIDO] Ingestão cancelada pelo usuário.")
        exit_code = 130
    except Exception as exc:
        print(
            f"[ERRO FATAL] {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        exit_code = 1

    raise SystemExit(exit_code)