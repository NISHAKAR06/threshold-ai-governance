"""
vector_repository.py — Repository abstraction for vector storage operations.
Ensures application logic depends on high-level repository interface rather than a specific DB client.
"""
from typing import List, Optional, Union
from pathlib import Path

from app.models.embedding_record import VectorRecord
from app.database.vector_store import BaseVectorStore, get_vector_store
from app.config import settings
from app.core.logger import repo_logger


class VectorRepository:
    """
    Domain repository mediating between business logic and the underlying vector database.
    Provides idempotent upserts, record lookups, deletions, and health checks.
    """

    def __init__(
        self,
        store: Optional[BaseVectorStore] = None,
        vector_store: Optional[BaseVectorStore] = None,
        provider: Optional[str] = None,
        path: Optional[Union[str, Path]] = None,
        collection_name: Optional[str] = None,
    ):
        resolved_store = store or vector_store
        if resolved_store is not None:
            self.store = resolved_store
        else:
            self.store = get_vector_store(
                provider=provider or settings.VECTOR_STORE_PROVIDER,
                path=path or settings.VECTOR_STORE_PATH,
                collection_name=collection_name or settings.VECTOR_STORE_COLLECTION,
            )

    def initialize(self) -> None:
        """Initialize the vector store collection/index."""
        self.store.initialize()

    def upsert_records(self, records: List[VectorRecord]) -> int:
        """
        Idempotently insert or update vector records.
        Returns count of records upserted.
        """
        if not records:
            return 0
        repo_logger.info(f"VectorRepository: Upserting {len(records)} vector records")
        return self.store.upsert(records)

    def get_record(self, vector_id: str) -> Optional[VectorRecord]:
        """Retrieve vector record by unique ID."""
        return self.store.get_by_id(vector_id)

    def delete_record(self, vector_id: str) -> bool:
        """Delete vector record by unique ID."""
        return self.store.delete_by_id(vector_id)

    def delete_document_vectors(self, document_id: str) -> int:
        """Delete all vector records belonging to a parent document ID."""
        repo_logger.info(f"VectorRepository: Deleting vectors for document '{document_id}'")
        return self.store.delete_by_document_id(document_id)

    def count(self) -> int:
        """Get total number of vectors in the collection."""
        return self.store.count()

    def health_check(self) -> bool:
        """Verify vector store connectivity and readiness."""
        return self.store.health_check()

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[tuple[VectorRecord, float]]:
        """
        Perform vector similarity search against the configured vector store.
        Returns ordered list of (VectorRecord, similarity_score) pairs.
        """
        repo_logger.info(f"VectorRepository: Executing similarity search (top_k={top_k})")
        return self.store.search(query_vector=query_vector, top_k=top_k)
