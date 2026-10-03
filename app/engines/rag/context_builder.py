"""
context_builder.py — Formats authorized retrieval chunks into structured LLM context with deterministic source IDs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.config import settings
from app.models.governance_retrieval_result import GovernanceRetrievalResultItem
from app.models.rag_source import RAGSource
from app.core.logger import engine_logger


@dataclass
class BuildContextResult:
    """Outcome of building LLM context from authorized retrieval results."""
    formatted_context: str
    sources: List[RAGSource] = field(default_factory=list)
    source_map: Dict[str, GovernanceRetrievalResultItem] = field(default_factory=dict)
    chunks_used: int = 0
    total_chunks_available: int = 0
    total_length: int = 0


class ContextBuilder:
    """
    Constructs bounded, deterministic context blocks for LLM generation from authorized Phase 12 results.
    """

    def __init__(
        self,
        max_chunks: Optional[int] = None,
        max_context_length: Optional[int] = None,
    ):
        self.max_chunks = max_chunks or settings.RAG_MAX_CONTEXT_CHUNKS
        self.max_context_length = max_context_length or settings.RAG_MAX_CONTEXT_LENGTH

    def build_context(
        self,
        authorized_chunks: List[GovernanceRetrievalResultItem],
        max_chunks_override: Optional[int] = None,
    ) -> BuildContextResult:
        """
        Build formatted context from authorized retrieval items.

        Args:
            authorized_chunks: Pre-authorized, ranked retrieval result items.
            max_chunks_override: Optional override for maximum chunks to include.

        Returns:
            BuildContextResult containing formatted text, structured sources, and audit counters.
        """
        if not authorized_chunks:
            return BuildContextResult(
                formatted_context="",
                sources=[],
                source_map={},
                chunks_used=0,
                total_chunks_available=0,
                total_length=0,
            )

        limit_chunks = max_chunks_override or self.max_chunks

        formatted_blocks: List[str] = []
        sources: List[RAGSource] = []
        source_map: Dict[str, GovernanceRetrievalResultItem] = {}
        current_length = 0
        chunks_used = 0

        # Preserve retrieval ranking strictly
        for idx, item in enumerate(authorized_chunks, start=1):
            if chunks_used >= limit_chunks:
                break

            source_id = f"SOURCE_{idx}"

            # Extract metadata and provenance
            doc_id = item.document_id or "UNKNOWN_DOC"
            chunk_id = item.chunk_id or f"{doc_id}_CHUNK_{idx:04d}"
            metadata = item.metadata or {}
            source_meta = item.source or {}

            doc_type = metadata.get("document_type", "POLICY")
            doc_title = metadata.get("title", doc_id)
            classification = metadata.get("classification")
            department = metadata.get("department")
            file_path = source_meta.get("file_path", "")
            source_ref = file_path if file_path else doc_title

            clean_text = item.text.strip() if item.text else ""
            if not clean_text:
                continue

            block = (
                f"[{source_id}]\n"
                f"Document ID: {doc_id}\n"
                f"Chunk ID: {chunk_id}\n"
                f"Document Type: {doc_type}\n"
                f"Department: {department or 'N/A'}\n"
                f"Classification: {classification or 'N/A'}\n"
                f"Content:\n{clean_text}\n"
            )

            block_len = len(block)
            if current_length + block_len > self.max_context_length and chunks_used > 0:
                # Context limit reached; do not truncate mid-chunk to avoid splitting content
                engine_logger.info(
                    f"ContextBuilder: Context length budget reached ({current_length} + {block_len} > {self.max_context_length}). "
                    f"Stopping at {chunks_used} chunks."
                )
                break

            formatted_blocks.append(block)
            current_length += block_len
            chunks_used += 1

            source_map[source_id] = item
            sources.append(
                RAGSource(
                    source_id=source_id,
                    document_id=doc_id,
                    chunk_id=chunk_id,
                    document_type=doc_type,
                    source_reference=source_ref,
                    classification=classification,
                    department=department,
                    fused_score=item.fused_score,
                    is_cited=False,
                )
            )

        full_context = "\n---\n".join(formatted_blocks)

        engine_logger.info(
            f"ContextBuilder: Built context from {chunks_used}/{len(authorized_chunks)} "
            f"authorized chunks (total_chars={len(full_context)})"
        )

        return BuildContextResult(
            formatted_context=full_context,
            sources=sources,
            source_map=source_map,
            chunks_used=chunks_used,
            total_chunks_available=len(authorized_chunks),
            total_length=len(full_context),
        )
