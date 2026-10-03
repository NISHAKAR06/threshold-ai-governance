"""
chunk_result.py — Domain dataclasses for chunking results and manifests.
"""
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any
from app.models.chunk import Chunk


@dataclass
class DocumentChunkResult:
    """Represents the chunking execution outcome for a single normalized document."""
    document_id: str
    status: str  # "SUCCESS" or "FAILED"
    chunks_created: int
    output_file: Optional[str] = None
    chunks: List[Chunk] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "document_id": self.document_id,
            "status": self.status,
            "chunks_created": self.chunks_created,
            "output_file": self.output_file,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "error_message": self.error_message,
            "validation_errors": self.validation_errors,
        }


@dataclass
class ChunkingManifest:
    """Represents the complete batch execution manifest for Phase 9 chunking."""
    chunking_run_id: str
    started_at: str
    completed_at: str
    total_documents: int
    successful_documents: int
    failed_documents: int
    total_chunks: int
    configuration: Dict[str, Any]
    results: List[DocumentChunkResult] = field(default_factory=list)
    pipeline_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest dataclass to dictionary."""
        return {
            "chunking_run_id": self.chunking_run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "pipeline_version": self.pipeline_version,
            "total_documents": self.total_documents,
            "successful_documents": self.successful_documents,
            "failed_documents": self.failed_documents,
            "total_chunks": self.total_chunks,
            "configuration": self.configuration,
            "results": [r.to_dict() for r in self.results],
        }
