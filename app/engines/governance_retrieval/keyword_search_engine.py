"""
keyword_search_engine.py — Local lexical keyword search engine implementing BM25Okapi.
Indexes chunk records directly from the Phase 9 chunk dataset or in-memory records.
"""
from __future__ import annotations

import re
import math
import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Any, Optional, Union, Tuple

from app.core.logger import engine_logger
from app.core.exceptions import KeywordSearchError


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens."""
    if not text:
        return []
    return re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())


class KeywordSearchEngine:
    """
    In-memory BM25Okapi keyword search engine over enterprise document chunks.
    Deterministic, fast, and does not require external search services.
    """

    def __init__(
        self,
        chunks_dir: Optional[Union[str, Path]] = "data/chunks",
        k1: float = 1.5,
        b: float = 0.75,
        auto_index: bool = True,
    ):
        self.chunks_dir = Path(chunks_dir).resolve() if chunks_dir else None
        self.k1 = k1
        self.b = b

        # Corpus structures
        self.corpus: Dict[str, Dict[str, Any]] = {}  # chunk_id -> raw chunk dict
        self.doc_len: Dict[str, int] = {}            # chunk_id -> token count
        self.doc_freqs: Dict[str, int] = defaultdict(int)  # term -> count of docs containing term
        self.term_freqs: Dict[str, Counter] = {}    # chunk_id -> Counter(terms)
        self.avg_doc_len: float = 0.0
        self.total_docs: int = 0

        if auto_index and self.chunks_dir and self.chunks_dir.exists():
            self.build_index_from_directory(self.chunks_dir)

    def build_index_from_directory(self, directory: Union[str, Path]) -> int:
        """
        Load all chunk JSON files in directory and index text content.
        Returns total number of chunks indexed.
        """
        dir_path = Path(directory).resolve()
        if not dir_path.exists():
            engine_logger.warning(f"KeywordSearchEngine: chunks directory not found at {dir_path}")
            return 0

        engine_logger.info(f"KeywordSearchEngine: Building BM25 index from {dir_path}")
        chunk_files = list(dir_path.glob("*.json"))

        all_chunks: List[Dict[str, Any]] = []
        for cf in chunk_files:
            try:
                with open(cf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chunks = data.get("chunks", [])
                    all_chunks.extend(chunks)
            except Exception as exc:
                engine_logger.warning(f"KeywordSearchEngine: Error reading chunk file {cf}: {exc}")

        return self.index_chunks(all_chunks)

    def index_chunks(self, chunks: List[Dict[str, Any]]) -> int:
        """Index a list of chunk dictionaries."""
        self.corpus.clear()
        self.doc_len.clear()
        self.doc_freqs.clear()
        self.term_freqs.clear()

        total_length = 0

        for chunk in chunks:
            chunk_id = chunk.get("chunk_id")
            text = chunk.get("text", "")
            if not chunk_id or not text:
                continue

            self.corpus[chunk_id] = chunk
            tokens = tokenize(text)
            self.doc_len[chunk_id] = len(tokens)
            total_length += len(tokens)

            tf = Counter(tokens)
            self.term_freqs[chunk_id] = tf

            for term in tf:
                self.doc_freqs[term] += 1

        self.total_docs = len(self.corpus)
        self.avg_doc_len = (total_length / self.total_docs) if self.total_docs > 0 else 0.0

        engine_logger.info(
            f"KeywordSearchEngine: Successfully indexed {self.total_docs} chunks "
            f"(vocab size={len(self.doc_freqs)}, avg_len={self.avg_doc_len:.1f})"
        )
        return self.total_docs

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Perform BM25 similarity scoring against the indexed chunk corpus.

        Args:
            query: User search query string.
            top_k: Maximum candidate chunks to return.

        Returns:
            List of chunk records with 'score' or 'lexical_score'.
        """
        if not query or not query.strip() or self.total_docs == 0:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)

        for token in query_tokens:
            df = self.doc_freqs.get(token, 0)
            if df == 0:
                continue

            # Standard BM25 IDF with smoothing to guarantee positive value
            idf = math.log((self.total_docs - df + 0.5) / (df + 0.5) + 1.0)
            if idf <= 0.0:
                idf = 0.001

            for chunk_id, tf_counter in self.term_freqs.items():
                f = tf_counter.get(token, 0)
                if f > 0:
                    d_len = self.doc_len[chunk_id]
                    denom = f + self.k1 * (1.0 - self.b + self.b * (d_len / (self.avg_doc_len or 1.0)))
                    term_score = idf * (f * (self.k1 + 1.0)) / (denom or 1.0)
                    scores[chunk_id] += term_score

        if not scores:
            return []

        # Sort descending by score; break ties deterministically by chunk_id
        ranked_chunks = sorted(scores.items(), key=lambda item: (item[1], item[0]), reverse=True)

        results: List[Dict[str, Any]] = []
        for chunk_id, score in ranked_chunks[:top_k]:
            raw_chunk = self.corpus[chunk_id]
            results.append({
                "chunk_id": chunk_id,
                "document_id": raw_chunk.get("document_id", ""),
                "text": raw_chunk.get("text", ""),
                "metadata": raw_chunk.get("metadata", {}),
                "source": raw_chunk.get("source", {}),
                "score": round(float(score), 4),
                "lexical_score": round(float(score), 4),
            })

        return results

    def rebuild_index(self) -> int:
        """Rebuild index from configured chunks directory."""
        if self.chunks_dir and self.chunks_dir.exists():
            return self.build_index_from_directory(self.chunks_dir)
        return 0
