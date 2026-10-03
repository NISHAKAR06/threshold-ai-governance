"""
embedding_service.py — High-level service orchestrating document chunk embedding and vector indexing.
"""
import time
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Union, Optional, List, Dict, Any

from app.config import settings
from app.models.chunk import Chunk
from app.models.embedding_record import VectorRecord
from app.models.indexing_result import DocumentIndexingResult, IndexingManifest
from app.schemas.chunk_schema import ChunkSchema
from app.schemas.indexing_schema import IndexingManifestSchema
from app.engines.embeddings.embedding_engine import EmbeddingEngine, get_embedding_provider
from app.engines.embeddings.embedding_validator import EmbeddingValidator
from app.engines.embeddings.vector_record_builder import VectorRecordBuilder
from app.repositories.vector_repository import VectorRepository
from app.utils.file_utils import ensure_directory
from app.core.logger import service_logger
from app.core.exceptions import EmbeddingError, VectorPersistenceError


class EmbeddingService:
    """
    Orchestrates batch vector embedding and indexing:
    1. Discovers chunk files produced by Phase 9.
    2. Loads and validates chunk records.
    3. Batches chunk text and generates dense vectors via EmbeddingEngine.
    4. Validates embedding vectors for finite numeric values and dimensionality.
    5. Builds VectorRecord objects binding embeddings with governance metadata.
    6. Persists vector records into VectorRepository.
    7. Tracks per-document and batch metrics with error isolation.
    8. Publishes the comprehensive IndexingManifest.
    """

    def __init__(
        self,
        chunks_dir: Optional[Union[str, Path]] = None,
        manifest_dir: Union[str, Path] = "data/indexing_manifests",
        embedding_engine: Optional[EmbeddingEngine] = None,
        vector_repository: Optional[VectorRepository] = None,
        embedding_validator: Optional[EmbeddingValidator] = None,
        batch_size: Optional[int] = None,
    ):
        # 1. Resolve chunks directory
        if chunks_dir:
            self.chunks_dir = Path(chunks_dir).resolve()
        else:
            primary_path = Path("data/chunks").resolve()
            fallback_path = Path("dataset/threshold-enterprise-dataset/data/chunks").resolve()
            self.chunks_dir = primary_path if primary_path.exists() else fallback_path

        # 2. Resolve manifest directory
        self.manifest_dir = ensure_directory(manifest_dir)

        # 3. Initialize components
        self.engine = embedding_engine or EmbeddingEngine(batch_size=batch_size)
        self.validator = embedding_validator or EmbeddingValidator(expected_dimension=self.engine.dimension)
        self.repository = vector_repository or VectorRepository()
        self.record_builder = VectorRecordBuilder()

        # Initialize vector store collection
        self.repository.initialize()

    def discover_chunk_files(self) -> List[Path]:
        """Discover all chunk JSON files sorted by filename."""
        if not self.chunks_dir.exists():
            service_logger.warning(f"Chunks directory does not exist: {self.chunks_dir}")
            return []

        files = sorted(
            [p for p in self.chunks_dir.glob("*.json") if p.is_file()],
            key=lambda p: p.name,
        )
        return files

    def run_indexing(self) -> IndexingManifest:
        """
        Execute end-to-end vector indexing across all discovered chunk files.

        Returns:
            IndexingManifest containing batch summary, counts, and per-document results.
        """
        run_id = f"idx_run_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(timezone.utc).isoformat()
        start_perf = time.perf_counter()

        service_logger.info(
            f"Starting Indexing Run: {run_id} | Chunks Dir: {self.chunks_dir} | "
            f"Provider: {self.engine.provider_name} | Model: {self.engine.model_name}"
        )

        chunk_files = self.discover_chunk_files()
        total_documents = len(chunk_files)

        results: List[DocumentIndexingResult] = []
        total_chunks = 0
        successful_chunks = 0
        failed_chunks = 0
        total_vectors_upserted = 0

        for idx, file_path in enumerate(chunk_files, start=1):
            doc_id = file_path.stem
            service_logger.info(f"[{idx}/{total_documents}] Indexing document chunks for '{doc_id}'")

            doc_result = self._process_document_chunks(doc_id, file_path)
            results.append(doc_result)

            total_chunks += doc_result.chunks_processed
            successful_chunks += doc_result.chunks_indexed
            failed_chunks += doc_result.chunks_failed
            if doc_result.status == "SUCCESS":
                total_vectors_upserted += doc_result.chunks_indexed

        completed_at = datetime.now(timezone.utc).isoformat()

        # Compile final manifest
        manifest = IndexingManifest(
            indexing_run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            embedding_provider=self.engine.provider_name,
            embedding_model=self.engine.model_name,
            vector_store_provider=getattr(self.repository.store, "provider_name", "vector_store"),
            collection_name=getattr(self.repository.store, "collection_name", settings.VECTOR_STORE_COLLECTION),
            total_documents=total_documents,
            total_chunks=total_chunks,
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks,
            vectors_upserted=total_vectors_upserted,
            results=results,
            pipeline_version="1.0.0",
        )

        # Validate schema before persisting
        IndexingManifestSchema.model_validate(manifest.to_dict())

        # Persist manifest
        self._persist_manifest(manifest)

        elapsed = time.perf_counter() - start_perf
        service_logger.info(
            f"Indexing Run Completed: {successful_chunks}/{total_chunks} chunks indexed, "
            f"{failed_chunks} failed across {total_documents} documents in {elapsed:.2f}s"
        )

        return manifest

    def _process_document_chunks(self, document_id: str, file_path: Path) -> DocumentIndexingResult:
        """Process, embed, validate, and store all chunks for one document."""
        start_time = time.perf_counter()
        validation_errors: List[str] = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            raw_chunks = payload.get("chunks", [])
            if not raw_chunks:
                return DocumentIndexingResult(
                    document_id=document_id,
                    chunks_processed=0,
                    chunks_indexed=0,
                    chunks_failed=0,
                    status="FAILED",
                    error_message="Document chunk file has no chunks",
                    validation_errors=["No chunks found in file"],
                    execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            valid_chunks: List[Dict[str, Any]] = []
            chunk_texts: List[str] = []

            # 1. Validate chunks
            for ch in raw_chunks:
                try:
                    ChunkSchema.model_validate(ch)
                    valid_chunks.append(ch)
                    chunk_texts.append(ch["text"])
                except Exception as e:
                    err = f"Chunk validation error for {ch.get('chunk_id', 'UNKNOWN')}: {str(e)}"
                    service_logger.warning(err)
                    validation_errors.append(err)

            if not valid_chunks:
                return DocumentIndexingResult(
                    document_id=document_id,
                    chunks_processed=len(raw_chunks),
                    chunks_indexed=0,
                    chunks_failed=len(raw_chunks),
                    status="FAILED",
                    error_message="All chunks failed validation",
                    validation_errors=validation_errors,
                    execution_time_ms=(time.perf_counter() - start_time) * 1000.0,
                )

            # 2. Generate embeddings
            embeddings = self.engine.generate_embeddings(chunk_texts)

            # 3. Validate embeddings and build vector records
            vector_records: List[VectorRecord] = []
            for ch, emb in zip(valid_chunks, embeddings):
                val_res = self.validator.validate(emb)
                if not val_res.is_valid:
                    err = f"Embedding validation error for {ch['chunk_id']}: {val_res.errors}"
                    service_logger.warning(err)
                    validation_errors.append(err)
                    continue

                record = self.record_builder.build_record(
                    chunk=ch,
                    embedding=emb,
                    embedding_provider=self.engine.provider_name,
                    embedding_model=self.engine.model_name,
                    embedding_dimension=len(emb),
                )
                vector_records.append(record)

            # 4. Upsert into vector repository
            if vector_records:
                self.repository.upsert_records(vector_records)

            indexed_count = len(vector_records)
            failed_count = len(raw_chunks) - indexed_count
            status = "SUCCESS" if failed_count == 0 else ("PARTIAL" if indexed_count > 0 else "FAILED")

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            return DocumentIndexingResult(
                document_id=document_id,
                chunks_processed=len(raw_chunks),
                chunks_indexed=indexed_count,
                chunks_failed=failed_count,
                status=status if status != "PARTIAL" else "SUCCESS",
                error_message=None if not validation_errors else f"{len(validation_errors)} error(s) occurred",
                validation_errors=validation_errors,
                execution_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            service_logger.exception(f"Unhandled error processing document chunks for '{document_id}': {str(e)}")
            return DocumentIndexingResult(
                document_id=document_id,
                chunks_processed=0,
                chunks_indexed=0,
                chunks_failed=0,
                status="FAILED",
                error_message=str(e),
                validation_errors=[str(e)],
                execution_time_ms=elapsed_ms,
            )

    def _persist_manifest(self, manifest: IndexingManifest) -> Path:
        """Persist batch indexing manifest to disk."""
        manifest_data = manifest.to_dict()

        primary_manifest_path = self.manifest_dir / "indexing_manifest.json"
        with open(primary_manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        history_manifest_path = self.manifest_dir / f"indexing_manifest_{timestamp_str}.json"
        with open(history_manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        return primary_manifest_path
