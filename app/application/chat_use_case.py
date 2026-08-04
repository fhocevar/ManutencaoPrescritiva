from app.application.dtos import ChatCommand
from app.domain.ports import DocumentRepository, EmbeddingService, RecommendationGenerator


class ChatWithDocumentsUseCase:
    def __init__(
        self,
        documents: DocumentRepository,
        embeddings: EmbeddingService,
        generator: RecommendationGenerator,
        minimum_similarity: float,
    ) -> None:
        self.documents = documents
        self.embeddings = embeddings
        self.generator = generator
        self.minimum_similarity = minimum_similarity

    async def execute(self, command: ChatCommand) -> dict:
        query = command.question if not command.fault else f"{command.fault}. {command.question}"
        vector = self.embeddings.embed([query])[0]
        evidence = await self.documents.search(
            query_vector=vector,
            fault=command.fault or "",
            limit=command.limit,
            minimum_similarity=self.minimum_similarity,
        )
        if not evidence:
            return {
                "status": "unsupported",
                "answer": "Não encontrei documentação suficiente para responder com segurança.",
                "evidence": [],
            }
        fault = command.fault or "consulta_documental"
        summary, steps = await self.generator.generate(fault, evidence)
        return {
            "status": "supported",
            "answer": summary,
            "steps": steps,
            "evidence": evidence,
        }
