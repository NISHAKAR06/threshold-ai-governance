"""
ingestion_engine.py — Ingestion engine responsible for processing individual documents.
"""
import time
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Union, Optional

from app.schemas.document_schema import DocumentMetadataSchema, NormalizedDocumentSchema
from app.models.normalized_document import NormalizedDocument
from app.models.ingestion_result import IngestionResult
from app.engines.ingestion.loader_factory import LoaderFactory
from app.engines.ingestion.document_normalizer import DocumentNormalizer
from app.engines.ingestion.document_validator import DocumentValidator
from app.utils.file_utils import resolve_path, ensure_directory
from app.utils.hash_utils import compute_sha256
from app.core.logger import ingestion_logger
from app.core.exceptions import DocumentIngestionError


class IngestionEngine:
    """Processes an individual document from source extraction to validated normalized JSON storage."""

    def __init__(
        self,
        dataset_base_dir: Union[str, Path],
        output_dir: Union[str, Path] = "dataset/threshold-enterprise-dataset/data/normalized_documents",
        loader_factory: Optional[LoaderFactory] = None,
        normalizer: Optional[DocumentNormalizer] = None,
        validator: Optional[DocumentValidator] = None,
    ):
        self.dataset_base_dir = Path(dataset_base_dir).resolve()
        self.output_dir = ensure_directory(output_dir)
        self.loader_factory = loader_factory or LoaderFactory()
        self.normalizer = normalizer or DocumentNormalizer()
        self.validator = validator or DocumentValidator()

    def process_document(self, metadata: DocumentMetadataSchema) -> IngestionResult:
        """
        Execute end-to-end ingestion pipeline for a single document:
        1. Resolve file path
        2. Select loader & extract raw text
        3. Normalize text content
        4. Validate metadata and text consistency
        5. Generate SHA-256 content hash
        6. Persist normalized document JSON
        7. Return IngestionResult
        """
        start_time = time.perf_counter()
        doc_id = metadata.document_id
        resolved_path = resolve_path(self.dataset_base_dir, metadata.file_path)

        ingestion_logger.info(f"Starting ingestion for {doc_id} from {resolved_path}")

        try:
            # 1. Resolve loader and extract raw text
            loader = self.loader_factory.get_loader_for_format(metadata.file_format)
            raw_text = loader.load(resolved_path)

            # 2. Normalize text
            norm_result = self.normalizer.normalize(raw_text)

            # 3. Validate normalized content & metadata
            self.validator.validate(
                metadata=metadata,
                normalized_text=norm_result.normalized_text,
                resolved_file_path=resolved_path,
            )

            # 4. Generate SHA-256 content hash
            content_hash = compute_sha256(norm_result.normalized_text)

            # 5. Build NormalizedDocument
            now_iso = datetime.now(timezone.utc).isoformat()
            norm_doc = NormalizedDocument(
                document_id=doc_id,
                title=metadata.title,
                department=metadata.department,
                classification=metadata.classification,
                version=metadata.version,
                status=metadata.status,
                effective_date=metadata.effective_date,
                allowed_roles=metadata.allowed_roles,
                document_type=metadata.document_type,
                summary=metadata.summary,
                keywords=metadata.keywords,
                file_path=metadata.file_path,
                file_format=metadata.file_format,
                raw_character_count=norm_result.raw_character_count,
                raw_word_count=norm_result.raw_word_count,
                normalized_character_count=norm_result.normalized_character_count,
                normalized_word_count=norm_result.normalized_word_count,
                content_hash=content_hash,
                content=norm_result.normalized_text,
                ingested_at=now_iso,
            )

            # Validate schema
            NormalizedDocumentSchema.model_validate(norm_doc.to_dict())

            # 6. Save JSON file to data/normalized_documents/{document_id}.json
            out_file = self.output_dir / f"{doc_id}.json"
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(norm_doc.to_dict(), f, indent=2, ensure_ascii=False)

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            ingestion_logger.info(
                f"Successfully ingested {doc_id} ({norm_result.normalized_word_count} words) in {elapsed_ms:.2f}ms"
            )

            return IngestionResult(
                document_id=doc_id,
                status="SUCCESS",
                file_path=metadata.file_path,
                file_format=metadata.file_format,
                execution_time_ms=round(elapsed_ms, 2),
                content_hash=content_hash,
                character_count=norm_result.normalized_character_count,
                word_count=norm_result.normalized_word_count,
                error_message=None,
            )

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            error_msg = str(e)
            ingestion_logger.error(f"Failed to ingest document {doc_id}: {error_msg}")

            return IngestionResult(
                document_id=doc_id,
                status="FAILED",
                file_path=metadata.file_path,
                file_format=metadata.file_format,
                execution_time_ms=round(elapsed_ms, 2),
                content_hash=None,
                character_count=None,
                word_count=None,
                error_message=error_msg,
            )
