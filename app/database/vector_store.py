"""
vector_store.py — Vector database abstraction and concrete store implementations.
Supports persistent ChromaDB as well as in-memory stores for isolated testing.
"""
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from app.models.embedding_record import VectorRecord
from app.utils.file_utils import ensure_directory
from app.core.exceptions import VectorStoreError, VectorPersistenceError
from app.core.logger import repo_logger
from app.config import settings


class BaseVectorStore(ABC):
    """Abstract base class defining vector storage interface."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize collection/index."""
        pass

    @abstractmethod
    def upsert(self, records: List[VectorRecord]) -> int:
        """Upsert a list of VectorRecord objects into the store. Returns count of upserted records."""
        pass

    @abstractmethod
    def get_by_id(self, vector_id: str) -> Optional[VectorRecord]:
        """Retrieve a VectorRecord by its unique identifier."""
        pass

    @abstractmethod
    def delete_by_id(self, vector_id: str) -> bool:
        """Delete a vector record by ID. Returns True if deleted."""
        pass

    @abstractmethod
    def delete_by_document_id(self, document_id: str) -> int:
        """Delete all vector records originating from a document ID. Returns count deleted."""
        pass

    @abstractmethod
    def count(self) -> int:
        """Return total number of vectors in the collection."""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Verify vector store connectivity and readiness."""
        pass

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 5) -> List[tuple[VectorRecord, float]]:
        """Perform vector similarity search, returning ordered (VectorRecord, similarity_score) pairs."""
        pass


class InMemoryVectorStore(BaseVectorStore):
    """In-memory dictionary-backed vector store for testing and offline environments."""
    provider_name: str = "in_memory"

    def __init__(self, collection_name: str = "in_memory_vectors"):
        self.collection_name = collection_name
        self._store: Dict[str, VectorRecord] = {}
        self._initialized = False

    def initialize(self) -> None:
        self._store = {}
        self._initialized = True

    def upsert(self, records: List[VectorRecord]) -> int:
        if not self._initialized:
            self.initialize()
        for r in records:
            self._store[r.vector_id] = r
        return len(records)

    def get_by_id(self, vector_id: str) -> Optional[VectorRecord]:
        return self._store.get(vector_id)

    def delete_by_id(self, vector_id: str) -> bool:
        if vector_id in self._store:
            del self._store[vector_id]
            return True
        return False

    def delete_by_document_id(self, document_id: str) -> int:
        to_delete = [vid for vid, rec in self._store.items() if rec.document_id == document_id]
        for vid in to_delete:
            del self._store[vid]
        return len(to_delete)

    def count(self) -> int:
        return len(self._store)

    def health_check(self) -> bool:
        return True

    def search(self, query_vector: List[float], top_k: int = 5) -> List[tuple[VectorRecord, float]]:
        """Perform cosine similarity search across in-memory records."""
        if not self._store or not query_vector or top_k <= 0:
            return []

        import math
        q_norm = math.sqrt(sum(x * x for x in query_vector)) or 1.0

        scored: List[tuple[VectorRecord, float]] = []
        for rec in self._store.values():
            r_norm = math.sqrt(sum(x * x for x in rec.embedding)) or 1.0
            dot_prod = sum(q * r for q, r in zip(query_vector, rec.embedding))
            sim = dot_prod / (q_norm * r_norm)
            sim_clamped = max(0.0, min(1.0, round(sim, 4)))
            scored.append((rec, sim_clamped))

        # Sort descending by similarity score
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:top_k]


class ChromaVectorStore(BaseVectorStore):
    """Production vector store using ChromaDB persistent client."""
    provider_name: str = "chroma"

    def __init__(
        self,
        path: Union[str, Path] = "data/vector_store",
        collection_name: str = "threshold_enterprise_chunks",
    ):
        self.path = Path(path).resolve()
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def initialize(self) -> None:
        """Initialize persistent ChromaDB client and acquire collection."""
        try:
            import chromadb
            ensure_directory(self.path)
            self._client = chromadb.PersistentClient(path=str(self.path))
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            repo_logger.info(
                f"ChromaVectorStore initialized collection '{self.collection_name}' at {self.path}"
            )
        except Exception as e:
            raise VectorStoreError(
                f"Failed to initialize Chroma vector store at {self.path}: {str(e)}",
                provider="chroma",
            )

    def _ensure_ready(self) -> None:
        if self._collection is None or self._client is None:
            self.initialize()

    def upsert(self, records: List[VectorRecord]) -> int:
        """Upsert records into Chroma collection with flattened metadata."""
        if not records:
            return 0
        self._ensure_ready()

        ids = [r.vector_id for r in records]
        embeddings = [r.embedding for r in records]
        documents = [r.text for r in records]
        metadatas = [self._flatten_metadata(r) for r in records]

        try:
            self._collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            return len(records)
        except Exception as e:
            raise VectorPersistenceError(
                f"Failed to upsert {len(records)} vectors into Chroma collection '{self.collection_name}': {str(e)}",
                collection=self.collection_name,
            )

    def get_by_id(self, vector_id: str) -> Optional[VectorRecord]:
        """Retrieve record by ID from Chroma."""
        self._ensure_ready()
        try:
            res = self._collection.get(
                ids=[vector_id],
                include=["embeddings", "documents", "metadatas"],
            )
            if not res or not res.get("ids") or len(res["ids"]) == 0:
                return None

            idx = 0
            vid = res["ids"][idx]
            emb = res["embeddings"][idx] if res.get("embeddings") is not None and len(res["embeddings"]) > 0 else []
            doc = res["documents"][idx] if res.get("documents") else ""
            meta_flat = res["metadatas"][idx] if res.get("metadatas") else {}

            return self._unflatten_metadata(vid, emb, doc, meta_flat)
        except Exception as e:
            repo_logger.warning(f"Error fetching vector '{vector_id}' from Chroma: {str(e)}")
            return None

    def delete_by_id(self, vector_id: str) -> bool:
        """Delete vector by ID."""
        self._ensure_ready()
        try:
            self._collection.delete(ids=[vector_id])
            return True
        except Exception as e:
            repo_logger.warning(f"Error deleting vector '{vector_id}' from Chroma: {str(e)}")
            return False

    def delete_by_document_id(self, document_id: str) -> int:
        """Delete all vectors matching document_id in metadata."""
        self._ensure_ready()
        try:
            # First count how many exist
            existing = self._collection.get(where={"document_id": document_id})
            count = len(existing["ids"]) if existing and existing.get("ids") else 0
            if count > 0:
                self._collection.delete(where={"document_id": document_id})
            return count
        except Exception as e:
            repo_logger.warning(f"Error deleting document vectors for '{document_id}' from Chroma: {str(e)}")
            return 0

    def count(self) -> int:
        """Get collection item count."""
        self._ensure_ready()
        try:
            return self._collection.count()
        except Exception as e:
            repo_logger.warning(f"Error counting Chroma collection: {str(e)}")
            return 0

    def health_check(self) -> bool:
        """Check Chroma heartbeat."""
        try:
            self._ensure_ready()
            return self._client.heartbeat() is not None or self._collection is not None
        except Exception:
            return False

    def search(self, query_vector: List[float], top_k: int = 5) -> List[tuple[VectorRecord, float]]:
        """Perform vector similarity search, returning ordered (VectorRecord, similarity_score) pairs."""
        if not query_vector or top_k <= 0:
            return []

        self._ensure_ready()
        try:
            total = self._collection.count()
            if total == 0:
                return []

            actual_k = min(top_k, total)
            res = self._collection.query(
                query_embeddings=[query_vector],
                n_results=actual_k,
                include=["embeddings", "documents", "metadatas", "distances"],
            )

            if not res or not res.get("ids") or len(res["ids"]) == 0 or len(res["ids"][0]) == 0:
                return []

            ids = res["ids"][0]
            docs = res.get("documents", [[]])[0] if res.get("documents") else [""] * len(ids)
            metas = res.get("metadatas", [[]])[0] if res.get("metadatas") else [{}] * len(ids)
            distances = res.get("distances", [[]])[0] if res.get("distances") else [0.0] * len(ids)
            embeddings = res.get("embeddings", [[]])[0] if res.get("embeddings") else [[]] * len(ids)

            scored_records: List[tuple[VectorRecord, float]] = []
            for i, vid in enumerate(ids):
                doc_text = docs[i] if i < len(docs) else ""
                meta_dict = metas[i] if i < len(metas) else {}
                dist = distances[i] if i < len(distances) else 0.0
                emb = embeddings[i] if i < len(embeddings) else []

                record = self._unflatten_metadata(vid, emb, doc_text, meta_dict)
                # In cosine space, cosine distance d = 1 - similarity.
                # Convert to similarity: sim = max(0.0, min(1.0, 1.0 - dist))
                sim_score = max(0.0, min(1.0, round(1.0 - dist, 4)))
                scored_records.append((record, sim_score))

            # Ensure sorted descending by similarity score
            scored_records.sort(key=lambda item: item[1], reverse=True)
            return scored_records
        except Exception as e:
            repo_logger.exception(f"ChromaVectorStore: Error executing vector search: {str(e)}")
            raise VectorStoreError(f"Vector search failed in Chroma: {str(e)}", provider="chroma")

    @staticmethod
    def _flatten_metadata(record: VectorRecord) -> Dict[str, Union[str, int, float, bool]]:
        """Flatten record metadata for ChromaDB (requires primitive scalar values)."""
        flat: Dict[str, Union[str, int, float, bool]] = {
            "vector_id": record.vector_id,
            "chunk_id": record.chunk_id,
            "document_id": record.document_id,
            "parent_content_hash": record.parent_content_hash,
            "chunk_content_hash": record.chunk_content_hash,
            "embedding_provider": record.embedding_provider,
            "embedding_model": record.embedding_model,
            "embedding_dimension": record.embedding_dimension,
            "indexed_at": record.indexed_at,
        }

        # Flatten source provenance
        if record.source:
            flat["source_file_path"] = str(record.source.get("file_path", ""))
            flat["source_file_format"] = str(record.source.get("file_format", ""))
            file_name = record.source.get("file_name") or Path(str(record.source.get("file_path", ""))).name
            flat["source_file_name"] = str(file_name)

        # Flatten governance metadata
        meta = record.metadata or {}
        flat["department"] = str(meta.get("department", ""))
        flat["classification"] = str(meta.get("classification", ""))
        flat["document_type"] = str(meta.get("document_type", ""))
        flat["status"] = str(meta.get("status", ""))
        flat["title"] = str(meta.get("title", ""))
        flat["version"] = str(meta.get("version", "1.0"))

        # Allowed roles stored as JSON array string or comma separated
        roles = meta.get("allowed_roles", [])
        flat["allowed_roles"] = json.dumps(roles if isinstance(roles, list) else [str(roles)])

        keywords = meta.get("keywords", [])
        flat["keywords"] = json.dumps(keywords if isinstance(keywords, list) else [str(keywords)])

        flat["summary"] = str(meta.get("summary", ""))

        return flat

    @staticmethod
    def _unflatten_metadata(
        vector_id: str,
        embedding: List[float],
        text: str,
        flat: Dict[str, Any],
    ) -> VectorRecord:
        """Reconstruct VectorRecord from flat Chroma metadata."""
        # Unpack allowed_roles
        roles_raw = flat.get("allowed_roles", "[]")
        try:
            allowed_roles = json.loads(roles_raw) if isinstance(roles_raw, str) else list(roles_raw)
        except Exception:
            allowed_roles = [r.strip() for r in str(roles_raw).split(",") if r.strip()]

        # Unpack keywords
        keywords_raw = flat.get("keywords", "[]")
        try:
            keywords = json.loads(keywords_raw) if isinstance(keywords_raw, str) else list(keywords_raw)
        except Exception:
            keywords = [k.strip() for k in str(keywords_raw).split(",") if k.strip()]

        governance_metadata = {
            "department": flat.get("department", ""),
            "classification": flat.get("classification", ""),
            "allowed_roles": allowed_roles,
            "document_type": flat.get("document_type", ""),
            "status": flat.get("status", ""),
            "title": flat.get("title", ""),
            "version": flat.get("version", "1.0"),
            "summary": flat.get("summary", ""),
            "keywords": keywords,
        }

        source = {
            "file_path": flat.get("source_file_path", ""),
            "file_format": flat.get("source_file_format", ""),
            "file_name": flat.get("source_file_name", Path(str(flat.get("source_file_path", ""))).name if flat.get("source_file_path") else ""),
        }

        return VectorRecord(
            vector_id=vector_id,
            embedding=embedding,
            chunk_id=flat.get("chunk_id", ""),
            document_id=flat.get("document_id", ""),
            text=text,
            metadata=governance_metadata,
            source=source,
            parent_content_hash=flat.get("parent_content_hash", ""),
            chunk_content_hash=flat.get("chunk_content_hash", ""),
            embedding_provider=flat.get("embedding_provider", ""),
            embedding_model=flat.get("embedding_model", ""),
            embedding_dimension=int(flat.get("embedding_dimension", len(embedding))),
            indexed_at=flat.get("indexed_at", ""),
        )


def get_vector_store(
    provider: Optional[str] = None,
    path: Optional[Union[str, Path]] = None,
    collection_name: Optional[str] = None,
) -> BaseVectorStore:
    """Factory function returning configured vector store instance."""
    resolved_provider = provider or settings.VECTOR_STORE_PROVIDER or "chroma"
    resolved_path = path or settings.VECTOR_STORE_PATH or "data/vector_store"
    resolved_collection = collection_name or settings.VECTOR_STORE_COLLECTION or "threshold_enterprise_chunks"

    prov = resolved_provider.lower().strip()
    if prov == "chroma":
        return ChromaVectorStore(path=resolved_path, collection_name=resolved_collection)
    elif prov in {"in_memory", "inmemory", "memory", "mock"}:
        return InMemoryVectorStore(collection_name=resolved_collection)
    else:
        raise ValueError(f"Unknown vector store provider: '{provider}'")
