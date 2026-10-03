"""
indexing_result.py — Domain dataclasses for vector indexing results and manifests.
"""
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any


@dataclass
class DocumentIndexingResult:
    """Represents the indexing execution outcome for a single document's chunks."""
    document_id: str
    chunks_processed: int
    chunks_indexed: int
    chunks_failed: int
    status: str  # "SUCCESS" or "FAILED"
    error_message: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "document_id": self.document_id,
            "chunks_processed": self.chunks_processed,
            "chunks_indexed": self.chunks_indexed,
            "chunks_failed": self.chunks_failed,
            "status": self.status,
            "error_message": self.error_message,
            "validation_errors": self.validation_errors,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


@dataclass
class IndexingManifest:
    """Represents the complete batch execution manifest for Phase 10 vector indexing."""
    indexing_run_id: str
    started_at: str
    completed_at: str
    embedding_provider: str
    embedding_model: str
    vector_store_provider: str
    collection_name: str
    total_documents: int
    total_chunks: int
    successful_chunks: int
    failed_chunks: int
    vectors_upserted: int
    results: List[DocumentIndexingResult] = field(default_factory=list)
    pipeline_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest dataclass to dictionary."""
        return {
            "indexing_run_id": self.indexing_run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "vector_store_provider": self.vector_store_provider,
            "collection_name": self.collection_name,
            "total_documents": self.total_documents,
            "total_chunks": self.total_chunks,
            "successful_chunks": self.successful_chunks,
            "failed_chunks": self.failed_chunks,
            "vectors_upserted": self.vectors_upserted,
            "pipeline_version": self.pipeline_version,
            "results": [r.to_dict() for r in self.results],
        }
