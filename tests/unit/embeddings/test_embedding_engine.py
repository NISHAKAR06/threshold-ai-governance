"""
test_embedding_engine.py — Unit tests for EmbeddingEngine and providers.
"""
import pytest
from typing import List
from app.engines.embeddings.embedding_engine import (
    EmbeddingEngine,
    MockEmbeddingProvider,
    BaseEmbeddingProvider,
    get_embedding_provider,
)
from app.core.exceptions import EmbeddingError, InvalidEmbeddingConfigurationError


class FailingProvider(BaseEmbeddingProvider):
    """Test stub simulating a failing upstream embedding provider."""

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        raise RuntimeError("Simulated network outage or rate limit")

    def get_dimension(self) -> int:
        return 768

    def get_model_name(self) -> str:
        return "failing-model"

    def get_provider_name(self) -> str:
        return "failing"


def test_mock_embedding_provider_deterministic():
    """Verify mock provider produces identical normalized vectors for identical text."""
    provider = MockEmbeddingProvider(dimension=384)
    vec1 = provider.embed_texts(["Threshold AI governance policy"])
    vec2 = provider.embed_texts(["Threshold AI governance policy"])

    assert len(vec1) == 1
    assert len(vec1[0]) == 384
    assert vec1[0] == vec2[0]


def test_mock_embedding_provider_different_texts():
    """Verify different texts produce different vectors."""
    provider = MockEmbeddingProvider(dimension=128)
    vecs = provider.embed_texts([
        "Human resources employee handbook",
        "Cybersecurity incident response protocol",
    ])
    assert len(vecs) == 2
    assert vecs[0] != vecs[1]


def test_embedding_engine_batch_processing():
    """Verify engine processes texts in batches correctly."""
    provider = MockEmbeddingProvider(dimension=64)
    engine = EmbeddingEngine(provider=provider, batch_size=2)

    texts = [f"Sample governance requirement {i}" for i in range(5)]
    embeddings = engine.generate_embeddings(texts)

    assert len(embeddings) == 5
    for emb in embeddings:
        assert len(emb) == 64


def test_embedding_engine_empty_input():
    """Verify engine returns empty list for empty texts list."""
    engine = EmbeddingEngine()
    assert engine.generate_embeddings([]) == []


def test_embedding_engine_rejects_empty_string():
    """Verify engine raises EmbeddingError if any text in list is empty or whitespace."""
    engine = EmbeddingEngine()
    with pytest.raises(EmbeddingError):
        engine.generate_embeddings(["valid text", "   "])

    with pytest.raises(EmbeddingError):
        engine.generate_embeddings([""])


def test_embedding_engine_provider_failure():
    """Verify engine cleanly wraps provider failures into EmbeddingError."""
    engine = EmbeddingEngine(provider=FailingProvider())
    with pytest.raises(EmbeddingError) as exc_info:
        engine.generate_embeddings(["Valid input text"])
    assert "Simulated network outage" in str(exc_info.value)


def test_get_embedding_provider_invalid():
    """Verify factory raises InvalidEmbeddingConfigurationError for unknown provider."""
    with pytest.raises(InvalidEmbeddingConfigurationError):
        get_embedding_provider("unknown_provider_xyz")
