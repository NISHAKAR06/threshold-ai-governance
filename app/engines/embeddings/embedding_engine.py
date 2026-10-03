"""
embedding_engine.py — Pluggable embedding engine and provider abstractions.
Coordinates batch vector generation across configured providers (Mock, Gemini, Local).
"""
import math
import hashlib
from abc import ABC, abstractmethod
from typing import List, Optional

from app.config import settings
from app.core.exceptions import EmbeddingError, InvalidEmbeddingConfigurationError
from app.core.logger import engine_logger


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding generation models."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of texts."""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """Return the dimensionality of the generated vectors."""
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the model identifier."""
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name."""
        pass


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic, offline embedding provider generating unit-normalized vectors.
    Seeded by SHA-256 hash of text for 100% reproducible testing without API keys.
    """

    def __init__(self, model_name: str = "mock-embedding-768", dimension: int = 768):
        self.model_name = model_name
        self.dimension = dimension

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        for text in texts:
            if not text or not str(text).strip():
                raise EmbeddingError("Cannot generate embedding for empty text", provider="mock")

            # Deterministic pseudo-random vector from SHA-256 hash
            h = hashlib.sha256(text.encode("utf-8")).digest()
            raw_floats: List[float] = []
            for i in range(self.dimension):
                # Cycle through hash bytes with index permutation
                byte_val = h[(i * 7 + 13) % len(h)]
                val = ((byte_val / 255.0) * 2.0) - 1.0  # Range [-1.0, 1.0]
                raw_floats.append(val)

            # Normalize to unit length
            norm = math.sqrt(sum(x * x for x in raw_floats)) or 1.0
            unit_vector = [round(x / norm, 6) for x in raw_floats]
            embeddings.append(unit_vector)

        return embeddings

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return self.model_name

    def get_provider_name(self) -> str:
        return "mock"


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini GenAI embedding provider using models/text-embedding-004."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/text-embedding-004",
        dimension: int = 768,
    ):
        self.model_name = model_name
        self.dimension = dimension
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise InvalidEmbeddingConfigurationError(
                "GEMINI_API_KEY is required for GeminiEmbeddingProvider"
            )

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._genai = genai
        except Exception as e:
            raise EmbeddingError(f"Failed to configure Google GenAI client: {str(e)}", provider="gemini")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings: List[List[float]] = []
        try:
            for text in texts:
                if not text or not str(text).strip():
                    raise EmbeddingError("Cannot generate embedding for empty text", provider="gemini")

                result = self._genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document",
                )
                vec = result.get("embedding", [])
                if hasattr(vec, "values"):
                    vec = vec.values
                embeddings.append(list(vec))

            return embeddings
        except Exception as e:
            raise EmbeddingError(f"Gemini API embedding generation failed: {str(e)}", provider="gemini")

    def get_dimension(self) -> int:
        return self.dimension

    def get_model_name(self) -> str:
        return self.model_name

    def get_provider_name(self) -> str:
        return "gemini"


def get_embedding_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseEmbeddingProvider:
    """Factory creating the configured embedding provider."""
    provider = (provider_name or settings.EMBEDDING_PROVIDER).lower().strip()
    model = model_name or settings.EMBEDDING_MODEL

    if provider in {"mock", "test", "local_mock"}:
        return MockEmbeddingProvider(model_name=model)
    elif provider == "gemini":
        return GeminiEmbeddingProvider(model_name=model)
    else:
        raise InvalidEmbeddingConfigurationError(f"Unsupported embedding provider: '{provider}'")


class EmbeddingEngine:
    """
    Coordinates batch vector generation using the configured EmbeddingProvider:
    - Receives text inputs
    - Batches requests
    - Generates embeddings
    - Handles errors
    """

    def __init__(
        self,
        provider: Optional[BaseEmbeddingProvider] = None,
        batch_size: Optional[int] = None,
    ):
        self.provider = provider or get_embedding_provider()
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings in batches.
        Returns list of dense float vectors matching input order.
        """
        if not texts:
            return []

        # Validate that no text is empty
        for idx, t in enumerate(texts):
            if not t or not str(t).strip():
                raise EmbeddingError(
                    f"Text at index {idx} is empty or whitespace only",
                    provider=self.provider.get_provider_name(),
                )

        all_embeddings: List[List[float]] = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            engine_logger.info(
                f"EmbeddingEngine: Generating batch {i // self.batch_size + 1} "
                f"({len(batch)} items) via {self.provider.get_provider_name()}"
            )
            try:
                batch_vectors = self.provider.embed_texts(batch)
                all_embeddings.extend(batch_vectors)
            except Exception as e:
                engine_logger.exception(f"EmbeddingEngine: Error generating embeddings: {str(e)}")
                if isinstance(e, EmbeddingError):
                    raise
                raise EmbeddingError(
                    f"Failed during batch embedding generation: {str(e)}",
                    provider=self.provider.get_provider_name(),
                )

        return all_embeddings

    @property
    def dimension(self) -> int:
        return self.provider.get_dimension()

    @property
    def model_name(self) -> str:
        return self.provider.get_model_name()

    @property
    def provider_name(self) -> str:
        return self.provider.get_provider_name()
