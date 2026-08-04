from app.application.use_cases import IngestDocumentUseCase


class DummyRepo: pass
class DummyParser: pass
class DummyEmbeddings: pass


def test_chunking_creates_multiple_chunks():
    use_case = IngestDocumentUseCase(DummyRepo(), DummyParser(), DummyEmbeddings(), chunk_size=10, chunk_overlap=2)
    chunks = use_case._chunk("abcdefghijklmnopqrstuvwxyz")
    assert len(chunks) > 1
    assert chunks[0] == "abcdefghij"
