"""
rag_evaluator.py — Deterministic RAG Quality and Grounding Evaluator.
Evaluates:
- Answer presence and generation completion
- Source citations syntax and presence
- Citation validity against authorized sources
- Structural token grounding (overlap of key nouns/terms from sources)
- Optional expected answer lexical similarity (Jaccard / token F1 without requiring LLMs)
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional, Set
from app.evaluation.models import RAGEvaluationResult


class RAGEvaluator:
    """
    Evaluates grounded generation quality through deterministic structural analysis.
    Does not require external LLM calls for evaluation metrics.
    """

    CITATION_REGEX = re.compile(r"\[(?:Source|Doc|Chunk)\s*(\d+)\]", re.IGNORECASE)

    def evaluate(
        self,
        generated_answer: Optional[str],
        authorized_sources: List[Dict[str, Any]],
        expected_answer: Optional[str] = None,
    ) -> RAGEvaluationResult:
        """
        Evaluate RAG answer quality deterministically.

        Args:
            generated_answer: The answer text produced by RAG.
            authorized_sources: List of source dictionaries provided in context.
            expected_answer: Optional ground truth answer.

        Returns:
            RAGEvaluationResult with deterministic validation scores.
        """
        # 1. Answer Generated
        if not generated_answer or not generated_answer.strip():
            return RAGEvaluationResult(
                answer_generated=False,
                source_citations_present=False,
                citations_valid=False,
                grounding_score=0.0,
                similarity_score=0.0 if expected_answer else None,
                generated_answer="",
            )

        text = generated_answer.strip()
        answer_generated = len(text) > 10

        # 2. Source Citations Present
        matches = list(self.CITATION_REGEX.finditer(text))
        citations_found = [m.group(0) for m in matches]
        source_citations_present = len(citations_found) > 0

        # 3. Citations Valid
        valid_count = len(authorized_sources)
        citations_valid = False
        if source_citations_present:
            extracted_indices = []
            for m in matches:
                try:
                    idx = int(m.group(1))
                    extracted_indices.append(idx)
                except ValueError:
                    pass
            # Citations must be between 1 and valid_count
            citations_valid = all(1 <= idx <= valid_count for idx in extracted_indices)

        # 4. Structural Grounding Score
        # Measures overlap of informative content words from sources present in answer
        grounding_score = self._compute_grounding_overlap(text, authorized_sources)

        # 5. Expected Answer Similarity (if provided)
        similarity_score: Optional[float] = None
        if expected_answer:
            similarity_score = self._compute_token_jaccard(text, expected_answer)

        return RAGEvaluationResult(
            answer_generated=answer_generated,
            source_citations_present=source_citations_present,
            citations_valid=citations_valid,
            grounding_score=grounding_score,
            similarity_score=similarity_score,
            generated_answer=text,
            citations_found=citations_found,
        )

    def _compute_grounding_overlap(self, answer: str, sources: List[Dict[str, Any]]) -> float:
        """Calculate token overlap ratio between sources and answer."""
        if not sources or not answer:
            return 0.0

        source_tokens: Set[str] = set()
        for s in sources:
            content = s.get("content") or s.get("text") or s.get("source_reference") or ""
            source_tokens.update(self._tokenize(content))

        if not source_tokens:
            return 0.0

        answer_tokens = set(self._tokenize(answer))
        if not answer_tokens:
            return 0.0

        overlap = answer_tokens.intersection(source_tokens)
        return len(overlap) / len(answer_tokens)

    def _compute_token_jaccard(self, text_a: str, text_b: str) -> float:
        """Token Jaccard similarity."""
        set_a = set(self._tokenize(text_a))
        set_b = set(self._tokenize(text_b))
        if not set_a or not set_b:
            return 0.0
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        return len(intersection) / len(union)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace and punctuation tokenizer filtering stopwords."""
        words = re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower())
        stopwords = {
            "the", "and", "is", "in", "it", "to", "of", "for", "with", "on",
            "at", "by", "from", "an", "as", "are", "was", "were", "this", "that",
        }
        return [w for w in words if w not in stopwords]
