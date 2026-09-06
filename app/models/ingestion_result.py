"""
ingestion_result.py — Domain dataclasses for ingestion results and manifests.
"""
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any


@dataclass
class IngestionResult:
    """Represents the processing outcome for a single document."""
    document_id: str
    status: str  # "SUCCESS" or "FAILED"
    file_path: str
    file_format: str
    execution_time_ms: float
    content_hash: Optional[str] = None
    character_count: Optional[int] = None
    word_count: Optional[int] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IngestionManifest:
    """Represents the complete batch execution manifest."""
    manifest_id: str
    timestamp: str
    total_documents: int
    success_count: int
    failure_count: int
    execution_time_seconds: float
    documents: List[IngestionResult] = field(default_factory=list)
    pipeline_version: str = "1.0.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "timestamp": self.timestamp,
            "pipeline_version": self.pipeline_version,
            "total_documents": self.total_documents,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "execution_time_seconds": round(self.execution_time_seconds, 3),
            "documents": [doc.to_dict() for doc in self.documents],
        }
