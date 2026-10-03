"""
rag_service.py — Orchestrates governance-aware RAG answer generation over Phase 12 authorized retrieval results.
"""
from __future__ import annotations

import time
from typing import Optional, Union, Dict, Any, List

from app.config import settings
from app.models.access_context import AccessContext
from app.models.rag_request import RAGRequest
from app.models.rag_response import RAGResponse
from app.models.rag_source import RAGSource
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.engines.rag.context_builder import ContextBuilder
from app.engines.rag.context_validator import ContextValidator
from app.engines.rag.prompt_builder import PromptBuilder
from app.engines.rag.answer_validator import AnswerValidator
from app.engines.rag.citation_builder import CitationBuilder
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.factory import get_llm_provider
from app.core.exceptions import (
    AccessContextValidationError,
    InvalidRetrievalQueryError,
    RAGError,
    LLMGenerationError,
)
from app.core.logger import service_logger


class RAGService:
    """
    Orchestration layer coordinating Phase 13 Governance-Aware RAG Answer Generation:
    1. Validates question and requester AccessContext.
    2. Calls Phase 12 HybridRetrievalService to retrieve strictly authorized chunks.
    3. Handles insufficient context safely without fabricating answers or calling the LLM.
    4. Formats authorized chunks with deterministic source identifiers ([SOURCE_1], ...).
    5. Enforces context size and integrity checks.
    6. Assembles an injection-resilient, grounded prompt.
    7. Calls the configured LLM provider.
    8. Validates answer text and citation integrity.
    9. Returns a structured RAGResponse with source traceability and audit metadata.
    """

    def __init__(
        self,
        retrieval_service: Optional[HybridRetrievalService] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
        context_builder: Optional[ContextBuilder] = None,
        context_validator: Optional[ContextValidator] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        answer_validator: Optional[AnswerValidator] = None,
        citation_builder: Optional[CitationBuilder] = None,
    ):
        self.retrieval_service = retrieval_service or HybridRetrievalService()
        self.llm_provider = llm_provider or get_llm_provider()
        self.context_builder = context_builder or ContextBuilder()
        self.context_validator = context_validator or ContextValidator()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.answer_validator = answer_validator or AnswerValidator()
        self.citation_builder = citation_builder or CitationBuilder()

    def generate_answer(
        self,
        question: str,
        access_context: Union[AccessContext, Dict[str, Any]],
        top_k: Optional[int] = None,
        max_context_chunks: Optional[int] = None,
    ) -> RAGResponse:
        """
        Execute governance-aware RAG pipeline and generate grounded response.

        Args:
            question: User question string.
            access_context: Verified AccessContext or dictionary.
            top_k: Optional candidate retrieval count.
            max_context_chunks: Optional max chunks to include in LLM context.

        Returns:
            RAGResponse object.
        """
        start_time = time.perf_counter()

        # 1. Validate Input Question & Access Context
        clean_question = self._validate_question(question)
        ctx = self._resolve_access_context(access_context)

        service_logger.info(
            f"RAGService: Generating answer for user='{ctx.user_id}' role='{ctx.role}' "
            f"clearance='{ctx.clearance_level}' (question_len={len(clean_question)})"
        )

        # 2. Call Phase 12 Hybrid Retrieval (ONLY source of truth; never bypassed)
        try:
            retrieval_response = self.retrieval_service.retrieve(
                query=clean_question,
                access_context=ctx,
                top_k=top_k or settings.RETRIEVAL_DEFAULT_TOP_K,
            )
        except Exception as exc:
            service_logger.error(f"RAGService: Phase 12 retrieval failed: {exc}")
            raise RAGError(f"Retrieval error during RAG answer generation: {exc}") from exc

        authorized_chunks = retrieval_response.results
        authorized_count = len(authorized_chunks)
        denied_count = retrieval_response.denied_count

        service_logger.info(
            f"RAGService: Phase 12 returned {authorized_count} authorized chunks "
            f"({denied_count} denied)"
        )

        retrieval_meta = {
            "authorized_result_count": authorized_count,
            "context_chunks_used": 0,
            "denied_count": denied_count,
            "fusion_strategy": retrieval_response.fusion_strategy,
        }

        # 3. Handle Insufficient Context (No authorized chunks found or all denied)
        if authorized_count == 0:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            service_logger.info(
                f"RAGService: No authorized chunks available for user='{ctx.user_id}'. "
                "Returning INSUFFICIENT_CONTEXT without calling LLM."
            )
            return RAGResponse(
                question=clean_question,
                answer=(
                    "Based on the available authorized governance documents, "
                    "there is insufficient information to answer this question."
                ),
                status="INSUFFICIENT_CONTEXT",
                sources=[],
                retrieval_metadata=retrieval_meta,
                execution_time_ms=elapsed_ms,
                model_used=self.llm_provider.model_name,
                provider_used=self.llm_provider.provider_name,
            )

        # 4. Build Context
        context_result = self.context_builder.build_context(
            authorized_chunks=authorized_chunks,
            max_chunks_override=max_context_chunks,
        )

        # 5. Validate Context
        val_result = self.context_validator.validate(context_result)
        if not val_result.is_valid:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            service_logger.warning(
                f"RAGService: Context validation failed ({val_result.reason}). Returning INSUFFICIENT_CONTEXT."
            )
            return RAGResponse(
                question=clean_question,
                answer=(
                    "Based on the available authorized governance documents, "
                    "there is insufficient information to answer this question."
                ),
                status="INSUFFICIENT_CONTEXT",
                sources=[],
                retrieval_metadata=retrieval_meta,
                execution_time_ms=elapsed_ms,
                model_used=self.llm_provider.model_name,
                provider_used=self.llm_provider.provider_name,
            )

        retrieval_meta["context_chunks_used"] = context_result.chunks_used

        # 6. Build Prompt
        built_prompt = self.prompt_builder.build_prompt(
            question=clean_question,
            formatted_context=context_result.formatted_context,
        )

        # 7. Call LLM Provider
        service_logger.info(
            f"RAGService: Invoking LLM provider='{self.llm_provider.provider_name}' "
            f"model='{self.llm_provider.model_name}'"
        )
        try:
            raw_answer = self.llm_provider.generate(
                prompt=built_prompt.prompt_text,
                system_instruction=built_prompt.system_instruction,
            )
        except Exception as exc:
            service_logger.error(f"RAGService: LLM generation error: {exc}")
            raise LLMGenerationError(f"Failed to generate answer from LLM: {exc}") from exc

        # 8. Validate Generated Answer & Citations
        valid_source_ids = {s.source_id for s in context_result.sources}
        validated_answer = self.answer_validator.validate(
            raw_answer=raw_answer,
            valid_source_ids=valid_source_ids,
        )

        # 9. Build Structured Citations
        sources = self.citation_builder.build_citations(
            context_sources=context_result.sources,
            cited_source_ids=validated_answer.cited_source_ids,
            only_cited=False,
        )

        # 10. Determine Final Status
        status = "INSUFFICIENT_CONTEXT" if validated_answer.is_insufficient_context else "SUCCESS"

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        service_logger.info(
            f"RAGService: Completed in {elapsed_ms:.1f}ms status='{status}' "
            f"cited_sources={len(validated_answer.cited_source_ids)}"
        )

        return RAGResponse(
            question=clean_question,
            answer=validated_answer.text,
            status=status,
            sources=sources,
            retrieval_metadata=retrieval_meta,
            execution_time_ms=elapsed_ms,
            model_used=self.llm_provider.model_name,
            provider_used=self.llm_provider.provider_name,
        )

    @staticmethod
    def _validate_question(question: str) -> str:
        """Validate question string."""
        if not question or not question.strip():
            raise InvalidRetrievalQueryError("Question cannot be empty or whitespace only")
        clean = question.strip()
        if len(clean) < settings.RETRIEVAL_MIN_QUERY_LENGTH:
            raise InvalidRetrievalQueryError(
                f"Question too short (minimum {settings.RETRIEVAL_MIN_QUERY_LENGTH} characters required)"
            )
        if len(clean) > settings.RETRIEVAL_MAX_QUERY_LENGTH:
            raise InvalidRetrievalQueryError(
                f"Question too long (maximum {settings.RETRIEVAL_MAX_QUERY_LENGTH} characters allowed)"
            )
        return clean

    @staticmethod
    def _resolve_access_context(
        access_context: Union[AccessContext, Dict[str, Any]],
    ) -> AccessContext:
        """Validate and construct an AccessContext domain object."""
        if access_context is None:
            raise AccessContextValidationError("Access context is required for RAG answer generation")

        if isinstance(access_context, AccessContext):
            ctx = access_context
        elif isinstance(access_context, dict):
            ctx = AccessContext.from_dict(access_context)
        else:
            raise AccessContextValidationError(
                f"Unsupported access context format: {type(access_context).__name__}"
            )

        if not ctx.user_id or not ctx.user_id.strip():
            raise AccessContextValidationError("AccessContext user_id is missing or empty")
        if not ctx.role or not ctx.role.strip():
            raise AccessContextValidationError("AccessContext role is missing or empty")

        return ctx
