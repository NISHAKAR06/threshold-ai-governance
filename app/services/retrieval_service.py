"""
retrieval_service.py — High-level service coordinating semantic retrieval pipeline.
"""
import time
from typing import Optional, Union, Dict, Any

from app.config import settings
from app.models.retrieval_query import RetrievalQuery
from app.models.retrieval_response import RetrievalResponse
from app.engines.retrieval.query_validator import QueryValidator
from app.engines.retrieval.query_processor import QueryProcessor
from app.engines.retrieval.retrieval_validator import RetrievalValidator
from app.engines.embeddings.embedding_engine import EmbeddingEngine
from app.repositories.vector_repository import VectorRepository
from app.core.exceptions import (
    QueryValidationError,
    QueryEmbeddingError,
    VectorSearchError,
    RetrievalError,
)
from app.core.logger import service_logger


class RetrievalService:
    """
    Coordinates semantic vector search workflow:
    1. Validates query string and top_k bounds via QueryValidator.
    2. Normalizes query text via QueryProcessor.
    3. Computes dense query embedding using Phase 10 EmbeddingEngine.
    4. Executes vector similarity search in VectorRepository.
    5. Validates, dedupes, and ranks candidates via RetrievalValidator.
    6. Returns structured RetrievalResponse.
    """

    def __init__(
        self,
        query_validator: Optional[QueryValidator] = None,
        query_processor: Optional[QueryProcessor] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        vector_repository: Optional[VectorRepository] = None,
        retrieval_validator: Optional[RetrievalValidator] = None,
    ):
        self.validator = query_validator or QueryValidator()
        self.processor = query_processor or QueryProcessor()
        self.engine = embedding_engine or EmbeddingEngine()
        self.repository = vector_repository or VectorRepository()
        self.retrieval_validator = retrieval_validator or RetrievalValidator()

    def retrieve(
        self,
        query: Union[str, RetrievalQuery, Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> RetrievalResponse:
        """
        Execute semantic retrieval for a user query.

        Args:
            query: Query string, RetrievalQuery dataclass, or dictionary.
            top_k: Optional override for number of top results to retrieve.

        Returns:
            RetrievalResponse containing ranked chunk items and metadata.
        """
        start_time = time.perf_counter()

        # 1. Unpack query input
        raw_query_str, requested_top_k = self._unpack_query(query, top_k)

        service_logger.info(
            f"RetrievalService: Received query (length={len(raw_query_str) if raw_query_str else 0}, "
            f"top_k={requested_top_k})"
        )

        # 2. Validate query and top_k
        val_result = self.validator.validate(raw_query_str, top_k=requested_top_k, raise_exception=True)
        cleaned_query = val_result.cleaned_query
        effective_top_k = val_result.cleaned_top_k

        # 3. Process query string
        processed_query = self.processor.process_query(cleaned_query)

        # 4. Generate query embedding
        try:
            query_embeddings = self.engine.generate_embeddings([processed_query])
            if not query_embeddings or len(query_embeddings) == 0:
                raise QueryEmbeddingError("EmbeddingEngine returned empty vector list for query")
            query_vector = query_embeddings[0]
        except Exception as e:
            service_logger.exception(f"RetrievalService: Query embedding generation failed: {str(e)}")
            if isinstance(e, (QueryValidationError, QueryEmbeddingError)):
                raise
            raise QueryEmbeddingError(f"Query embedding generation failed: {str(e)}")

        # 5. Vector similarity search
        try:
            raw_search_results = self.repository.search(
                query_vector=query_vector,
                top_k=effective_top_k,
            )
            service_logger.info(
                f"RetrievalService: Vector search yielded {len(raw_search_results)} raw results"
            )
        except Exception as e:
            service_logger.exception(f"RetrievalService: Vector search failed: {str(e)}")
            raise VectorSearchError(f"Vector search failed: {str(e)}", code="VECTOR_SEARCH_FAILED")

        # 6. Validate, deduplicate, and rank results
        ranked_items = self.retrieval_validator.validate_and_rank(
            raw_results=raw_search_results,
            embedding_provider=self.engine.provider_name,
            embedding_model=self.engine.model_name,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        service_logger.info(
            f"RetrievalService: Completed in {elapsed_ms:.1f}ms returning {len(ranked_items)} items"
        )

        return RetrievalResponse(
            query=cleaned_query,
            result_count=len(ranked_items),
            results=ranked_items,
            execution_time_ms=elapsed_ms,
            embedding_provider=self.engine.provider_name,
            embedding_model=self.engine.model_name,
        )

    @staticmethod
    def _unpack_query(
        query: Union[str, RetrievalQuery, Dict[str, Any]],
        top_k: Optional[int],
    ) -> tuple[Optional[str], Optional[int]]:
        """Unpack query string and top_k from varied input representations."""
        if isinstance(query, str):
            return query, top_k
        elif isinstance(query, RetrievalQuery):
            return query.query, top_k or query.top_k
        elif isinstance(query, dict):
            return query.get("query"), top_k or query.get("top_k")
        elif hasattr(query, "query"):
            return getattr(query, "query"), top_k or getattr(query, "top_k", None)
        else:
            return str(query), top_k
