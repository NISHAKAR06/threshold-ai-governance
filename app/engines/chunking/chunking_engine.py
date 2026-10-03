"""
chunking_engine.py — Ingestion engine responsible for processing an individual normalized document.
"""
import time
import json
from pathlib import Path
from typing import Union, Optional, Dict, Any, List

from app.models.normalized_document import NormalizedDocument
from app.models.chunk import Chunk
from app.models.chunk_result import DocumentChunkResult
from app.engines.chunking.structure_splitter import StructureSplitter
from app.engines.chunking.chunk_metadata_builder import ChunkMetadataBuilder
from app.engines.chunking.chunk_validator import ChunkValidator
from app.core.exceptions import EmptyDocumentError, ChunkingError
from app.core.logger import engine_logger


class ChunkingEngine:
    """
    Coordinates chunk processing for a single normalized document:
    1. Validates document input
    2. Invokes StructureSplitter to generate raw chunks
    3. Builds complete Chunk domain models via ChunkMetadataBuilder
    4. Validates each chunk via ChunkValidator
    5. Returns structured DocumentChunkResult
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        splitter: Optional[StructureSplitter] = None,
        metadata_builder: Optional[ChunkMetadataBuilder] = None,
        validator: Optional[ChunkValidator] = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = splitter or StructureSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self.metadata_builder = metadata_builder or ChunkMetadataBuilder()
        self.validator = validator or ChunkValidator()

    def process_document(
        self,
        document: Union[NormalizedDocument, Dict[str, Any], Path, str],
    ) -> DocumentChunkResult:
        """
        Process a single normalized document into validated chunks.

        Args:
            document: NormalizedDocument dataclass, dictionary, or Path to JSON file.

        Returns:
            DocumentChunkResult containing chunks, counts, and validation status.
        """
        start_time = time.perf_counter()

        # 1. Resolve document representation
        doc_data = self._resolve_document_data(document)
        doc_id = doc_data.get("document_id", "UNKNOWN")

        engine_logger.info(f"ChunkingEngine: Processing document '{doc_id}'")

        try:
            # 2. Validate document content
            content = doc_data.get("content", "")
            if not content or not str(content).strip():
                raise EmptyDocumentError(
                    f"Document '{doc_id}' contains empty or whitespace-only content",
                    document_id=doc_id,
                )

            # 3. Structure-aware splitting
            raw_chunks = self.splitter.split_text(content)
            if not raw_chunks:
                raise EmptyDocumentError(
                    f"StructureSplitter yielded 0 chunks for document '{doc_id}'",
                    document_id=doc_id,
                )

            engine_logger.info(
                f"ChunkingEngine: '{doc_id}' split into {len(raw_chunks)} raw chunks "
                f"(size={self.chunk_size}, overlap={self.chunk_overlap})"
            )

            # 4. Build Chunk objects and validate
            valid_chunks: List[Chunk] = []
            all_errors: List[str] = []

            for idx, raw_chunk_text in enumerate(raw_chunks, start=1):
                chunk_obj = self.metadata_builder.build_chunk(
                    parent_doc=doc_data,
                    chunk_text=raw_chunk_text,
                    chunk_index=idx,
                )

                validation = self.validator.validate(chunk_obj, raise_exception=False)
                if validation.is_valid:
                    valid_chunks.append(chunk_obj)
                else:
                    engine_logger.warning(
                        f"ChunkingEngine: Validation failed for chunk '{chunk_obj.chunk_id}': {validation.errors}"
                    )
                    all_errors.extend([f"[{chunk_obj.chunk_id}] {e}" for e in validation.errors])

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            # If any chunks were invalid, mark status as FAILED or partial
            if all_errors:
                status = "FAILED"
                error_msg = f"{len(all_errors)} chunk validation failure(s) occurred"
            else:
                status = "SUCCESS"
                error_msg = None

            return DocumentChunkResult(
                document_id=doc_id,
                status=status,
                chunks_created=len(valid_chunks),
                chunks=valid_chunks,
                execution_time_ms=elapsed_ms,
                error_message=error_msg,
                validation_errors=all_errors,
            )

        except EmptyDocumentError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            engine_logger.error(f"ChunkingEngine: Empty document error for '{doc_id}': {e.message}")
            return DocumentChunkResult(
                document_id=doc_id,
                status="FAILED",
                chunks_created=0,
                chunks=[],
                execution_time_ms=elapsed_ms,
                error_message=e.message,
                validation_errors=[e.message],
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            engine_logger.exception(f"ChunkingEngine: Unexpected error processing '{doc_id}': {str(e)}")
            return DocumentChunkResult(
                document_id=doc_id,
                status="FAILED",
                chunks_created=0,
                chunks=[],
                execution_time_ms=elapsed_ms,
                error_message=str(e),
                validation_errors=[str(e)],
            )

    @staticmethod
    def _resolve_document_data(document: Union[NormalizedDocument, Dict[str, Any], Path, str]) -> Dict[str, Any]:
        """Convert input document to dictionary format."""
        if isinstance(document, (str, Path)):
            p = Path(document)
            if not p.exists():
                raise FileNotFoundError(f"Document file does not exist: {p}")
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        elif isinstance(document, NormalizedDocument):
            return document.to_dict()
        elif hasattr(document, "model_dump"):
            return document.model_dump()
        elif isinstance(document, dict):
            return dict(document)
        else:
            raise ValueError(f"Unsupported document input type: {type(document)}")
