import asyncio
from pathlib import Path

from app.application.use_cases import IngestDocumentUseCase
from app.infrastructure.config import get_settings
from app.infrastructure.db import SessionFactory, engine
from app.infrastructure.documents import MultiFormatDocumentParser
from app.infrastructure.embeddings import SentenceTransformerEmbeddingService
from app.infrastructure.models import Base
from app.infrastructure.repositories import SqlAlchemyDocumentRepository


DEMO_DOCUMENTS = {
    "procedimento_cocked_rotor_2.md": """
Procedimento técnico para cocked_rotor_2.

Sintomas:
- vibração elevada nos eixos X e Z;
- aumento de fator de crista;
- aceleração de pico elevada;
- vibração axial significativa.

Inspeção:
- bloquear a máquina;
- confirmar condição segura;
- verificar fixação;
- verificar acoplamento;
- verificar alinhamento do rotor;
- verificar condição dos mancais;
- medir batimento radial e axial.

Correção:
- corrigir montagem inadequada;
- corrigir desalinhamento;
- reapertar fixações conforme especificação técnica;
- substituir rolamentos ou componentes danificados quando necessário;
- corrigir rotor ou eixo caso exista deformação.

Validação:
- religar em condição controlada;
- monitorar RMS de velocidade;
- monitorar aceleração de pico;
- monitorar temperatura;
- avaliar ruído anormal;
- confirmar redução de vibração.
""",

    "procedimento_desalinhado.md": """
Procedimento técnico para desalinhamento de motor e conjunto rotativo.

Sintomas:
- vibração elevada;
- aumento de temperatura nos mancais;
- ruído anormal;
- desgaste irregular do acoplamento;
- presença de componentes em 1x RPM e 2x RPM.

Inspeção:
- bloquear e etiquetar a fonte de energia;
- verificar condição do acoplamento;
- verificar fixações;
- avaliar pé manco;
- medir desalinhamento horizontal e vertical;
- verificar temperatura dos mancais.

Correção:
- corrigir pé manco;
- adicionar ou remover calços calibrados;
- realizar ajuste horizontal do motor;
- reapertar os parafusos;
- repetir as medições até atingir tolerância adequada.

Validação:
- girar manualmente o eixo quando possível;
- realizar partida controlada;
- monitorar vibração;
- monitorar temperatura;
- monitorar ruído;
- comparar os valores antes e depois da intervenção.
""",

    "procedimento_desbalanceado.md": """
Procedimento técnico para desbalanceamento em máquinas rotativas.

Sintomas:
- vibração radial elevada;
- pico predominante em 1x RPM;
- aumento de ruído;
- desgaste de rolamentos;
- afrouxamento de parafusos.

Inspeção:
- bloquear a máquina;
- verificar acúmulo de material;
- verificar desgaste de pás ou rotores;
- verificar contrapesos;
- coletar vibração horizontal, vertical e axial;
- analisar espectro de frequência.

Correção:
- realizar limpeza do rotor;
- executar balanceamento estático quando aplicável;
- executar balanceamento dinâmico quando necessário;
- adicionar ou remover massa corretiva conforme cálculo técnico.

Validação:
- realizar nova coleta de vibração;
- confirmar redução do pico em 1x RPM;
- verificar temperatura;
- verificar ruído;
- registrar vibração inicial e final.
""",
}


async def main() -> None:
    settings = get_settings()

    settings.documents_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    embeddings = SentenceTransformerEmbeddingService(
        settings.embedding_model
    )

    async with SessionFactory() as session:
        use_case = IngestDocumentUseCase(
            repository=SqlAlchemyDocumentRepository(session),
            parser=MultiFormatDocumentParser(),
            embeddings=embeddings,
        )

        total_documents = 0
        total_chunks = 0
        failures = 0

        print("=" * 80)
        print("Inicializando documentos de demonstração")
        print("=" * 80)

        for filename, content in DEMO_DOCUMENTS.items():
            path = settings.documents_dir / filename

            try:
                path.write_text(
                    content.strip(),
                    encoding="utf-8",
                )

                document_id, chunks = await use_case.execute(path)

                total_documents += 1
                total_chunks += chunks

                print(
                    f"[OK] {filename}: "
                    f"{chunks} chunks "
                    f"(document_id={document_id})"
                )

            except Exception as exc:
                failures += 1

                try:
                    await session.rollback()
                except Exception:
                    pass

                print(
                    f"[ERRO] {filename}: "
                    f"{type(exc).__name__}: {exc}"
                )

        print("-" * 80)
        print("Resumo do seed")
        print(f"Documentos processados: {total_documents}")
        print(f"Chunks gerados: {total_chunks}")
        print(f"Falhas: {failures}")

        if failures == 0:
            print("[SUCESSO] Seed de demonstração concluído.")
        else:
            print("[AVISO] Seed concluído com falhas.")


if __name__ == "__main__":
    asyncio.run(main())