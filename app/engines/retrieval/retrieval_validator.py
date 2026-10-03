"""
retrieval_validator.py — Validates raw vector search results and structures ranked candidates.
"""
import math
from typing import List, Tuple, Set, Dict, Any, Optional, Union

from app.models.embedding_record import VectorRecord
from app.models.retrieval_result import RetrievalResultItem
from app.core.logger import engine_logger


class RetrievalValidator:
    """Validates raw search candidate records, filters malformed entries, dedupes, and ranks results."""

    REQUIRED_GOVERNANCE_FIELDS = [
        "department",
        "classification",
        "allowed_roles",
        "document_type",
        "status",
    ]

    def validate_and_rank(
        self,
        raw_results: List[Any],
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[RetrievalResultItem]:
        """
        Validate candidates, exclude malformed records, remove duplicates, and assign 1-based ranks.

        Args:
            raw_results: List of (VectorRecord, score) tuples or candidate dictionaries.
            embedding_provider: Name of provider used.
            embedding_model: Identifier of model used.
            top_k: Optional maximum number of results to return.

        Returns:
            Ordered list of validated RetrievalResultItem models.
        """
        if not raw_results:
            return []

        # 1. Unpack candidates into a uniform list of dict representations
        unpacked_candidates = []
        for item in raw_results:
            cand = self._unpack_candidate(item, embedding_provider, embedding_model)
            if cand is not None:
                unpacked_candidates.append(cand)

        # 2. Sort descending by score
        unpacked_candidates.sort(key=lambda c: c["score"], reverse=True)

        # 3. Deduplicate by chunk_id, validate text, and rank
        validated_items: List[RetrievalResultItem] = []
        seen_chunk_ids: Set[str] = set()

        for cand in unpacked_candidates:
            chunk_id = cand["chunk_id"]

            # Deduplication
            if chunk_id in seen_chunk_ids:
                engine_logger.debug(f"RetrievalValidator: Skipping duplicate chunk_id '{chunk_id}'")
                continue

            # Governance fields check
            metadata = cand["metadata"]
            for field in self.REQUIRED_GOVERNANCE_FIELDS:
                if field not in metadata:
                    engine_logger.debug(
                        f"RetrievalValidator: Chunk '{chunk_id}' missing governance field '{field}'"
                    )

            rank = len(validated_items) + 1
            score = cand["score"]

            item = RetrievalResultItem(
                rank=rank,
                score=round(score, 4),
                chunk_id=chunk_id,
                document_id=cand["document_id"],
                text=cand["text"],
                metadata=metadata,
                source=cand["source"],
                distance=round(1.0 - score, 4) if score <= 1.0 else 0.0,
                embedding_provider=cand["embedding_provider"],
                embedding_model=cand["embedding_model"],
            )

            seen_chunk_ids.add(chunk_id)
            validated_items.append(item)

            if top_k is not None and len(validated_items) >= top_k:
                break

        return validated_items

    @classmethod
    def _unpack_candidate(
        cls,
        item: Any,
        default_provider: Optional[str],
        default_model: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Unpack candidate record into standardized dictionary or return None if invalid."""
        if isinstance(item, (tuple, list)) and len(item) >= 2:
            rec = item[0]
            raw_score = item[1]
        elif isinstance(item, dict):
            rec = item
            raw_score = item.get("score", 0.0)
        else:
            rec = item
            raw_score = getattr(item, "score", 0.0)

        # 1. Validate score
        if not isinstance(raw_score, (int, float)) or math.isnan(raw_score) or math.isinf(raw_score):
            engine_logger.warning(f"RetrievalValidator: Dropping record with invalid score: {raw_score}")
            return None

        if raw_score < 0.0:
            engine_logger.warning(f"RetrievalValidator: Dropping record with negative score: {raw_score}")
            return None

        clamped_score = min(1.0, float(raw_score))

        # 2. Extract fields from rec
        if isinstance(rec, dict):
            chunk_id = rec.get("chunk_id")
            doc_id = rec.get("document_id")
            text = rec.get("text")
            metadata = rec.get("metadata", {})
            source = rec.get("source", {})
            provider = rec.get("embedding_provider") or default_provider
            model = rec.get("embedding_model") or default_model
        else:
            chunk_id = getattr(rec, "chunk_id", None)
            doc_id = getattr(rec, "document_id", None)
            text = getattr(rec, "text", None)
            metadata = getattr(rec, "metadata", {})
            source = getattr(rec, "source", {})
            provider = getattr(rec, "embedding_provider", None) or default_provider
            model = getattr(rec, "embedding_model", None) or default_model

        # 3. Validate IDs and text
        if not chunk_id or not str(chunk_id).strip():
            engine_logger.warning("RetrievalValidator: Dropping candidate missing chunk_id")
            return None

        if not doc_id or not str(doc_id).strip():
            engine_logger.warning("RetrievalValidator: Dropping candidate missing document_id")
            return None

        if not text or not str(text).strip():
            engine_logger.warning(f"RetrievalValidator: Dropping chunk '{chunk_id}' with empty text")
            return None

        return {
            "chunk_id": str(chunk_id).strip(),
            "document_id": str(doc_id).strip(),
            "text": str(text),
            "score": clamped_score,
            "metadata": metadata if isinstance(metadata, dict) else {},
            "source": source if isinstance(source, dict) else {},
            "embedding_provider": provider,
            "embedding_model": model,
        }
