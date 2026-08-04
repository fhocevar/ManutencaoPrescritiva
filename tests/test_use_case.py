from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.use_cases import AnalyzeEventUseCase
from app.domain.entities import SensorEvent


class FakeEvents:
    async def add(self, event, vector):
        return uuid4()

    async def find_similar(self, vector, limit, max_distance, exclude_id=None):
        return []

    async def count_by_fault(self, fault):
        return 0


class FakeDocuments:
    async def search(self, query_vector, fault, limit, minimum_similarity):
        return []


class FakeAnalyses:
    async def save(self, **kwargs):
        return uuid4()


class FakeModel:
    def transform(self, event):
        return [0.0] * 23

    def anomaly_score(self, event):
        return 0.8


class FakeEmbeddings:
    def embed(self, texts):
        return [[0.0] * 384 for _ in texts]


class FakeGenerator:
    async def generate(self, fault, evidence):
        raise AssertionError("Não deve chamar gerador sem documentos.")


@pytest.mark.asyncio
async def test_problem_without_document_is_unsupported():
    use_case = AnalyzeEventUseCase(
        FakeEvents(),
        FakeDocuments(),
        FakeAnalyses(),
        FakeModel(),
        FakeEmbeddings(),
        FakeGenerator(),
        similar_limit=10,
        max_event_distance=0.3,
        min_document_similarity=0.5,
    )
    event = SensorEvent(
        external_id=1,
        created_at=datetime.now(timezone.utc),
        fault="unknown_fault",
        metrics={},
    )
    result = await use_case.execute(event)
    assert result.recommendation.status == "unsupported"
    assert result.recommendation.evidence == ()
