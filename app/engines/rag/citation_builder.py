"""
citation_builder.py — Maps validated citations and context sources into structured RAG response sources.
"""
from __future__ import annotations

from typing import List, Set, Optional

from app.models.rag_source import RAGSource
from app.core.logger import engine_logger


class CitationBuilder:
    """
    Transforms internal context sources into safe, structured RAGSource items for the client.
    """

    def build_citations(
        self,
        context_sources: List[RAGSource],
        cited_source_ids: List[str],
        only_cited: bool = False,
    ) -> List[RAGSource]:
        """
        Produce structured sources with attribution flags.

        Args:
            context_sources: Sources that were included in the authorized context.
            cited_source_ids: Source IDs that were explicitly cited in the validated answer.
            only_cited: If True, returns only sources that were cited. If False, returns all
                        authorized context sources with is_cited flag appropriately set.

        Returns:
            List of RAGSource objects.
        """
        if not context_sources:
            return []

        cited_set: Set[str] = set(cited_source_ids)
        result_sources: List[RAGSource] = []

        for src in context_sources:
            is_cited = src.source_id in cited_set

            if only_cited and not is_cited:
                continue

            # Create clean copy with is_cited updated
            structured_source = RAGSource(
                source_id=src.source_id,
                document_id=src.document_id,
                chunk_id=src.chunk_id,
                document_type=src.document_type or "DOCUMENT",
                source_reference=src.source_reference or src.document_id,
                classification=src.classification,
                department=src.department,
                fused_score=src.fused_score,
                is_cited=is_cited,
            )
            result_sources.append(structured_source)

        engine_logger.debug(
            f"CitationBuilder: Processed {len(result_sources)} sources "
            f"({len(cited_set)} cited in text)"
        )

        return result_sources
