"""
app/engines/embeddings package — Vector embedding generation, validation, and record construction.
"""
from app.engines.embeddings.embedding_engine import (
    BaseEmbeddingProvider,
    MockEmbeddingProvider,
    GeminiEmbeddingProvider,
    EmbeddingEngine,
    get_embedding_provider,
)
from app.engines.embeddings.embedding_validator import (
    EmbeddingValidator,
    EmbeddingValidationResult,
)
from app.engines.embeddings.vector_record_builder import VectorRecordBuilder

__all__ = [
    "BaseEmbeddingProvider",
    "MockEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "EmbeddingEngine",
    "get_embedding_provider",
    "EmbeddingValidator",
    "EmbeddingValidationResult",
    "VectorRecordBuilder",
]
