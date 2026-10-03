"""
context_validator.py — Validates built context blocks before prompt synthesis and LLM submission.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from app.config import settings
from app.engines.rag.context_builder import BuildContextResult
from app.core.logger import engine_logger


@dataclass
class ContextValidationResult:
    """Outcome of validating built RAG context."""
    is_valid: bool
    reason: str
    chunk_count: int = 0
    total_length: int = 0


class ContextValidator:
    """
    Validates that the built context meets security, integrity, and operational criteria.
    """

    def __init__(self, max_context_length: Optional[int] = None):
        self.max_context_length = max_context_length or settings.RAG_MAX_CONTEXT_LENGTH

    def validate(self, context_result: Optional[BuildContextResult]) -> ContextValidationResult:
        """
        Validate context integrity before prompt synthesis.

        Args:
            context_result: Outcome from ContextBuilder.

        Returns:
            ContextValidationResult indicating valid status and diagnostics.
        """
        if context_result is None:
            return ContextValidationResult(
                is_valid=False,
                reason="Context result is None",
                chunk_count=0,
                total_length=0,
            )

        # 1. Non-empty check
        if not context_result.formatted_context or not context_result.formatted_context.strip():
            return ContextValidationResult(
                is_valid=False,
                reason="Context is empty or whitespace only",
                chunk_count=0,
                total_length=0,
            )

        # 2. Chunk presence check
        if context_result.chunks_used <= 0 or not context_result.sources:
            return ContextValidationResult(
                is_valid=False,
                reason="No authorized chunks included in context",
                chunk_count=0,
                total_length=len(context_result.formatted_context),
            )

        # 3. Source uniqueness and ID validation
        seen_source_ids = set()
        for src in context_result.sources:
            if not src.source_id or not src.source_id.strip():
                return ContextValidationResult(
                    is_valid=False,
                    reason="Encountered source with empty source_id",
                    chunk_count=context_result.chunks_used,
                    total_length=len(context_result.formatted_context),
                )

            if src.source_id in seen_source_ids:
                return ContextValidationResult(
                    is_valid=False,
                    reason=f"Duplicate source_id detected: {src.source_id}",
                    chunk_count=context_result.chunks_used,
                    total_length=len(context_result.formatted_context),
                )
            seen_source_ids.add(src.source_id)

            if not src.document_id or not src.document_id.strip():
                return ContextValidationResult(
                    is_valid=False,
                    reason=f"Source '{src.source_id}' has missing or empty document_id",
                    chunk_count=context_result.chunks_used,
                    total_length=len(context_result.formatted_context),
                )

            if not src.chunk_id or not src.chunk_id.strip():
                return ContextValidationResult(
                    is_valid=False,
                    reason=f"Source '{src.source_id}' has missing or empty chunk_id",
                    chunk_count=context_result.chunks_used,
                    total_length=len(context_result.formatted_context),
                )

        # 4. Context length ceiling check
        ctx_len = len(context_result.formatted_context)
        if ctx_len > self.max_context_length * 1.5:  # Tolerance threshold
            return ContextValidationResult(
                is_valid=False,
                reason=f"Context length ({ctx_len}) severely exceeds maximum ({self.max_context_length})",
                chunk_count=context_result.chunks_used,
                total_length=ctx_len,
            )

        engine_logger.debug(
            f"ContextValidator: Context validation passed with {context_result.chunks_used} chunks "
            f"({ctx_len} chars)"
        )

        return ContextValidationResult(
            is_valid=True,
            reason="Context is valid",
            chunk_count=context_result.chunks_used,
            total_length=ctx_len,
        )
