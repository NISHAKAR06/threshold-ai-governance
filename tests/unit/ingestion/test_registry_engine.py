"""
test_registry_engine.py — Unit tests for RegistryEngine.
"""
import json
import pytest
from pathlib import Path
from app.engines.ingestion.registry_engine import RegistryEngine
from app.core.exceptions import RegistryValidationError


def test_registry_engine_valid(tmp_path: Path):
    # Setup mock dataset structure
    dataset_base = tmp_path / "dataset"
    meta_dir = dataset_base / "metadata"
    source_dir = dataset_base / "source_documents" / "hr"
    source_dir.mkdir(parents=True)
    meta_dir.mkdir(parents=True)

    dummy_doc = source_dir / "test_doc.txt"
    dummy_doc.write_text("Test content", encoding="utf-8")

    registry_file = meta_dir / "document_registry.json"
    registry_data = {
        "dataset_name": "Test Registry",
        "company": "Threshold Enterprise Systems",
        "version": "1.0",
        "documents": [
            {
                "document_id": "HR-001",
                "title": "Test Title",
                "department": "Human Resources",
                "classification": "INTERNAL",
                "version": "1.0",
                "status": "ACTIVE",
                "effective_date": "2026-01-15",
                "allowed_roles": ["EMPLOYEE"],
                "document_type": "POLICY",
                "summary": "This is a summary of the test document.",
                "keywords": ["test", "policy"],
                "file_path": "source_documents/hr/test_doc.txt",
                "file_format": "TXT",
            }
        ]
    }
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    engine = RegistryEngine(registry_path=registry_file, dataset_base_dir=dataset_base)
    docs = engine.load_and_validate()
    assert len(docs) == 1
    assert docs[0].document_id == "HR-001"


def test_registry_engine_duplicate_id(tmp_path: Path):
    dataset_base = tmp_path / "dataset"
    meta_dir = dataset_base / "metadata"
    source_dir = dataset_base / "source_documents" / "hr"
    source_dir.mkdir(parents=True)
    meta_dir.mkdir(parents=True)

    dummy_doc = source_dir / "test_doc.txt"
    dummy_doc.write_text("Test content", encoding="utf-8")

    registry_file = meta_dir / "document_registry.json"
    registry_data = {
        "dataset_name": "Test Registry",
        "company": "Threshold Enterprise Systems",
        "version": "1.0",
        "documents": [
            {
                "document_id": "HR-001",
                "title": "Doc 1",
                "department": "Human Resources",
                "classification": "INTERNAL",
                "version": "1.0",
                "status": "ACTIVE",
                "effective_date": "2026-01-15",
                "allowed_roles": ["EMPLOYEE"],
                "document_type": "POLICY",
                "summary": "This is a summary of document one.",
                "keywords": ["test"],
                "file_path": "source_documents/hr/test_doc.txt",
                "file_format": "TXT",
            },
            {
                "document_id": "HR-001",
                "title": "Doc 2 Duplicate",
                "department": "Human Resources",
                "classification": "INTERNAL",
                "version": "1.0",
                "status": "ACTIVE",
                "effective_date": "2026-01-15",
                "allowed_roles": ["EMPLOYEE"],
                "document_type": "POLICY",
                "summary": "This is a summary of duplicate document.",
                "keywords": ["test"],
                "file_path": "source_documents/hr/test_doc.txt",
                "file_format": "TXT",
            }
        ]
    }
    registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

    engine = RegistryEngine(registry_path=registry_file, dataset_base_dir=dataset_base)
    with pytest.raises(RegistryValidationError) as exc_info:
        engine.load_and_validate()
    assert "Duplicate document_id detected" in str(exc_info.value)
