"""
ingestion_service.py — High-level service coordinating document ingestion workflow.
"""
import time
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Union, Optional, List

from app.schemas.ingestion_schema import IngestionManifestSchema
from app.models.ingestion_result import IngestionManifest, IngestionResult
from app.engines.ingestion.registry_engine import RegistryEngine
from app.engines.ingestion.ingestion_engine import IngestionEngine
from app.utils.file_utils import ensure_directory
from app.core.logger import ingestion_logger


class IngestionService:
    """Service coordinating end-to-end ingestion from registry loading to manifest publication."""

    def __init__(
        self,
        registry_path: Union[str, Path] = "dataset/threshold-enterprise-dataset/metadata/document_registry.json",
        dataset_base_dir: Optional[Union[str, Path]] = None,
        output_dir: Union[str, Path] = "dataset/threshold-enterprise-dataset/data/normalized_documents",
        manifest_dir: Union[str, Path] = "dataset/threshold-enterprise-dataset/data/ingestion_manifests",
    ):
        self.registry_path = Path(registry_path).resolve()
        if dataset_base_dir:
            self.dataset_base_dir = Path(dataset_base_dir).resolve()
        else:
            self.dataset_base_dir = self.registry_path.parent.parent.resolve()

        self.output_dir = ensure_directory(output_dir)
        self.manifest_dir = ensure_directory(manifest_dir)

        self.registry_engine = RegistryEngine(
            registry_path=self.registry_path,
            dataset_base_dir=self.dataset_base_dir,
        )
        self.ingestion_engine = IngestionEngine(
            dataset_base_dir=self.dataset_base_dir,
            output_dir=self.output_dir,
        )

    def run_ingestion(self) -> IngestionManifest:
        """
        Execute the complete ingestion lifecycle:
        1. Validate & load registry records
        2. Ingest each document via IngestionEngine
        3. Compile IngestionManifest
        4. Save manifest JSON
        5. Return manifest
        """
        start_time = time.perf_counter()
        manifest_id = f"manifest_{uuid.uuid4().hex[:8]}"
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        ingestion_logger.info(f"Starting Phase 8 batch ingestion run: {manifest_id}")

        # 1. Load and validate registry
        metadata_list = self.registry_engine.load_and_validate()
        total_docs = len(metadata_list)

        results: List[IngestionResult] = []
        success_count = 0
        failure_count = 0

        # 2. Process each document
        for idx, meta in enumerate(metadata_list, start=1):
            ingestion_logger.info(f"[{idx}/{total_docs}] Processing {meta.document_id} ({meta.title})")
            result = self.ingestion_engine.process_document(meta)
            results.append(result)
            if result.status == "SUCCESS":
                success_count += 1
            else:
                failure_count += 1

        total_elapsed = time.perf_counter() - start_time

        # 3. Create manifest
        manifest = IngestionManifest(
            manifest_id=manifest_id,
            timestamp=timestamp_iso,
            total_documents=total_docs,
            success_count=success_count,
            failure_count=failure_count,
            execution_time_seconds=total_elapsed,
            documents=results,
            pipeline_version="1.0.0",
        )

        # Validate manifest with Pydantic
        IngestionManifestSchema.model_validate(manifest.to_dict())

        # 4. Save manifest
        manifest_filename = f"ingestion_manifest_{timestamp_str}.json"
        manifest_path = self.manifest_dir / manifest_filename
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

        ingestion_logger.info(
            f"Ingestion complete: {success_count}/{total_docs} succeeded, {failure_count} failed in {total_elapsed:.2f}s. "
            f"Manifest saved to {manifest_path}"
        )

        return manifest
