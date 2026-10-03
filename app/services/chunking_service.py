"""
chunking_service.py — Service orchestrating batch document chunking and manifest publication.
"""
import time
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Union, Optional, List, Dict, Any

from app.config import settings
from app.models.chunk_result import ChunkingManifest, DocumentChunkResult
from app.schemas.chunk_schema import DocumentChunksFileSchema
from app.schemas.chunking_schema import ChunkingManifestSchema
from app.engines.chunking.chunking_engine import ChunkingEngine
from app.utils.file_utils import ensure_directory
from app.core.logger import service_logger
from app.core.exceptions import ChunkPersistenceError


class ChunkingService:
    """
    Orchestrates batch chunking across normalized enterprise documents:
    1. Discovers normalized document JSON files from input directory.
    2. Processes each document independently using ChunkingEngine.
    3. Persists valid chunks grouped by document to {output_dir}/{document_id}.json.
    4. Compiles execution metrics and validation failures.
    5. Saves and publishes the final batch ChunkingManifest.
    """

    def __init__(
        self,
        input_dir: Optional[Union[str, Path]] = None,
        output_dir: Union[str, Path] = "data/chunks",
        manifest_dir: Union[str, Path] = "data/chunking_manifests",
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        chunking_engine: Optional[ChunkingEngine] = None,
    ):
        # 1. Resolve configuration
        self.chunk_size = chunk_size if chunk_size is not None else settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap if chunk_overlap is not None else settings.CHUNK_OVERLAP
        settings.validate_chunk_config(self.chunk_size, self.chunk_overlap)

        # 2. Resolve input directory (with fallback)
        if input_dir:
            self.input_dir = Path(input_dir).resolve()
        else:
            primary_path = Path("dataset/threshold-enterprise-dataset/data/normalized_documents").resolve()
            fallback_path = Path("data/normalized_documents").resolve()
            self.input_dir = primary_path if primary_path.exists() else fallback_path

        # 3. Ensure output and manifest directories exist
        self.output_dir = ensure_directory(output_dir)
        self.manifest_dir = ensure_directory(manifest_dir)

        # 4. Initialize engine
        self.engine = chunking_engine or ChunkingEngine(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    def discover_documents(self) -> List[Path]:
        """Discover all normalized document JSON files sorted by filename."""
        if not self.input_dir.exists():
            service_logger.warning(f"Input directory does not exist: {self.input_dir}")
            return []

        doc_files = sorted(
            [p for p in self.input_dir.glob("*.json") if p.is_file()],
            key=lambda p: p.name,
        )
        return doc_files

    def run_chunking(self) -> ChunkingManifest:
        """
        Execute the complete batch chunking workflow across all discovered documents.

        Returns:
            ChunkingManifest containing execution details, counts, and per-document results.
        """
        run_id = f"chunk_run_{uuid.uuid4().hex[:8]}"
        started_at = datetime.now(timezone.utc).isoformat()
        start_perf = time.perf_counter()

        service_logger.info(
            f"Starting Chunking Run: {run_id} | Input: {self.input_dir} | "
            f"Config: size={self.chunk_size}, overlap={self.chunk_overlap}"
        )

        doc_files = self.discover_documents()
        total_documents = len(doc_files)

        results: List[DocumentChunkResult] = []
        successful_docs = 0
        failed_docs = 0
        total_chunks = 0

        for idx, doc_file in enumerate(doc_files, start=1):
            doc_id = doc_file.stem
            service_logger.info(f"[{idx}/{total_documents}] Chunking document '{doc_id}' from {doc_file.name}")

            try:
                # Process single document through engine
                result = self.engine.process_document(doc_file)

                # If successful, persist chunk file
                if result.status == "SUCCESS" and result.chunks:
                    output_file_path = self._persist_chunks(doc_id, result)
                    result.output_file = str(output_file_path.relative_to(Path.cwd()) if output_file_path.is_relative_to(Path.cwd()) else output_file_path)
                    successful_docs += 1
                    total_chunks += result.chunks_created
                    service_logger.info(
                        f"Saved {result.chunks_created} chunks for '{doc_id}' to {result.output_file}"
                    )
                else:
                    failed_docs += 1
                    service_logger.error(
                        f"Chunking failed for '{doc_id}': {result.error_message or result.validation_errors}"
                    )

                results.append(result)

            except Exception as e:
                failed_docs += 1
                service_logger.exception(f"Unhandled error processing document '{doc_id}': {str(e)}")
                results.append(
                    DocumentChunkResult(
                        document_id=doc_id,
                        status="FAILED",
                        chunks_created=0,
                        chunks=[],
                        error_message=str(e),
                        validation_errors=[str(e)],
                    )
                )

        completed_at = datetime.now(timezone.utc).isoformat()

        # Compile final manifest
        manifest = ChunkingManifest(
            chunking_run_id=run_id,
            started_at=started_at,
            completed_at=completed_at,
            total_documents=total_documents,
            successful_documents=successful_docs,
            failed_documents=failed_docs,
            total_chunks=total_chunks,
            configuration={
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "input_dir": str(self.input_dir),
                "output_dir": str(self.output_dir),
            },
            results=results,
            pipeline_version="1.0.0",
        )

        # Validate manifest schema
        ChunkingManifestSchema.model_validate(manifest.to_dict())

        # Persist manifest
        self._persist_manifest(manifest)

        service_logger.info(
            f"Chunking Run Completed: {successful_docs}/{total_documents} succeeded, "
            f"{failed_docs} failed, {total_chunks} total chunks generated in "
            f"{(time.perf_counter() - start_perf):.2f}s"
        )

        return manifest

    def _persist_chunks(self, document_id: str, result: DocumentChunkResult) -> Path:
        """Persist valid chunks for a document to JSON."""
        output_path = self.output_dir / f"{document_id}.json"
        payload = {
            "document_id": document_id,
            "chunks": [chunk.to_dict() for chunk in result.chunks],
        }

        # Validate schema before writing
        DocumentChunksFileSchema.model_validate(payload)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return output_path
        except Exception as e:
            raise ChunkPersistenceError(
                f"Failed to persist chunks to {output_path}: {str(e)}",
                target_path=str(output_path),
            )

    def _persist_manifest(self, manifest: ChunkingManifest) -> Path:
        """Persist batch chunking manifest."""
        manifest_data = manifest.to_dict()

        # Primary manifest file
        primary_manifest_path = self.manifest_dir / "chunking_manifest.json"
        with open(primary_manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        # Historical timestamped manifest file
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        history_manifest_path = self.manifest_dir / f"chunking_manifest_{timestamp_str}.json"
        with open(history_manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)

        return primary_manifest_path
