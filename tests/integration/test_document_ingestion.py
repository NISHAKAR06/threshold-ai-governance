"""
test_document_ingestion.py — Integration test for the Phase 8 Document Ingestion Pipeline.
"""
import os
import json
import pytest
from pathlib import Path
from app.services.ingestion_service import IngestionService


def test_end_to_end_document_ingestion(tmp_path: Path):
    """
    Test end-to-end ingestion of the synthetic enterprise dataset.
    Validates:
    - Exactly 40 documents processed
    - All 40 succeed (0 failures)
    - Normalized JSON files exist and contain content hash
    - Manifest is generated and valid
    """
    registry_path = Path("dataset/threshold-enterprise-dataset/metadata/document_registry.json")
    assert registry_path.exists(), "document_registry.json must exist"

    test_output_dir = tmp_path / "normalized_documents"
    test_manifest_dir = tmp_path / "ingestion_manifests"

    service = IngestionService(
        registry_path=registry_path,
        output_dir=test_output_dir,
        manifest_dir=test_manifest_dir,
    )

    manifest = service.run_ingestion()

    # 1. Check counts
    assert manifest.total_documents == 40
    assert manifest.success_count == 40
    assert manifest.failure_count == 0

    # 2. Check output directory contents
    normalized_files = list(test_output_dir.glob("*.json"))
    assert len(normalized_files) == 40

    # 3. Check sample normalized document content
    sample_json_path = test_output_dir / "HR-001.json"
    assert sample_json_path.exists()
    with open(sample_json_path, "r", encoding="utf-8") as f:
        doc_data = json.load(f)

    assert doc_data["document_id"] == "HR-001"
    assert doc_data["file_format"] == "DOCX"
    assert len(doc_data["content_hash"]) == 64
    assert doc_data["normalized_word_count"] > 500
    assert len(doc_data["content"]) > 0

    # 4. Check manifest file
    manifest_files = list(test_manifest_dir.glob("*.json"))
    assert len(manifest_files) == 1
