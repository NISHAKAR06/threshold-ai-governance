"""
test_chunking_pipeline.py — End-to-end integration test for Phase 9 Chunking Pipeline.
"""
import json
from pathlib import Path
from app.services.chunking_service import ChunkingService


def test_end_to_end_chunking_pipeline(tmp_path: Path):
    """
    Test end-to-end batch chunking across the 40 Phase 8 normalized documents.
    Validates:
    - Discovers 40 normalized documents
    - Successfully chunks all 40 documents (0 failures)
    - Saves 40 chunk JSON files matching {document_id}.json
    - Chunk files adhere to {document_id, chunks: [...]} format
    - Each chunk retains governance metadata, parent hash, and SHA-256 chunk hash
    - Manifest is generated and validated
    """
    normalized_docs_dir = Path("dataset/threshold-enterprise-dataset/data/normalized_documents")
    assert normalized_docs_dir.exists(), "Normalized documents directory must exist"

    test_output_dir = tmp_path / "chunks"
    test_manifest_dir = tmp_path / "chunking_manifests"

    service = ChunkingService(
        input_dir=normalized_docs_dir,
        output_dir=test_output_dir,
        manifest_dir=test_manifest_dir,
        chunk_size=1000,
        chunk_overlap=150,
    )

    manifest = service.run_chunking()

    # 1. Check document counts
    assert manifest.total_documents == 40
    assert manifest.successful_documents == 40
    assert manifest.failed_documents == 0
    assert manifest.total_chunks > 40

    # 2. Check output directory contents
    chunk_files = list(test_output_dir.glob("*.json"))
    assert len(chunk_files) == 40

    # 3. Inspect a sample chunk file (HR-001.json)
    hr_chunk_file = test_output_dir / "HR-001.json"
    assert hr_chunk_file.exists()

    with open(hr_chunk_file, "r", encoding="utf-8") as f:
        doc_payload = json.load(f)

    assert doc_payload["document_id"] == "HR-001"
    assert "chunks" in doc_payload
    chunks = doc_payload["chunks"]
    assert len(chunks) > 0

    first_chunk = chunks[0]
    assert first_chunk["chunk_id"] == "HR-001_CHUNK_0001"
    assert first_chunk["document_id"] == "HR-001"
    assert first_chunk["chunk_index"] == 1
    assert len(first_chunk["text"]) > 0
    assert first_chunk["metadata"]["department"] == "Human Resources"
    assert "EMPLOYEE" in first_chunk["metadata"]["allowed_roles"]
    assert first_chunk["metadata"]["classification"] == "INTERNAL"
    assert len(first_chunk["parent_content_hash"]) == 64
    assert len(first_chunk["chunk_content_hash"]) == 64
    assert "created_at" in first_chunk

    # 4. Check manifest files
    manifest_files = list(test_manifest_dir.glob("*.json"))
    assert len(manifest_files) >= 1

    primary_manifest = test_manifest_dir / "chunking_manifest.json"
    assert primary_manifest.exists()

    with open(primary_manifest, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    assert manifest_data["total_documents"] == 40
    assert manifest_data["successful_documents"] == 40
    assert manifest_data["failed_documents"] == 0
    assert manifest_data["total_chunks"] == manifest.total_chunks
    assert len(manifest_data["results"]) == 40


def test_pipeline_fault_tolerance(tmp_path: Path):
    """
    Verify that an invalid/corrupted document does NOT halt processing of valid documents.
    """
    input_dir = tmp_path / "normalized"
    input_dir.mkdir()

    # 1. Create a valid document
    valid_doc = {
        "document_id": "TEST-001",
        "title": "Valid Doc",
        "department": "Engineering",
        "classification": "INTERNAL",
        "allowed_roles": ["ENGINEER"],
        "document_type": "GUIDE",
        "status": "ACTIVE",
        "file_path": "source/test.txt",
        "file_format": "TXT",
        "content_hash": "a" * 64,
        "content": "Valid engineering content that will be chunked.",
    }
    with open(input_dir / "TEST-001.json", "w", encoding="utf-8") as f:
        json.dump(valid_doc, f)

    # 2. Create an invalid document (empty content)
    invalid_doc = {
        "document_id": "TEST-002",
        "title": "Invalid Empty Doc",
        "department": "Engineering",
        "classification": "INTERNAL",
        "allowed_roles": ["ENGINEER"],
        "document_type": "GUIDE",
        "status": "ACTIVE",
        "file_path": "source/test_empty.txt",
        "file_format": "TXT",
        "content_hash": "b" * 64,
        "content": "   ",
    }
    with open(input_dir / "TEST-002.json", "w", encoding="utf-8") as f:
        json.dump(invalid_doc, f)

    # 3. Create another valid document
    valid_doc_2 = {
        "document_id": "TEST-003",
        "title": "Another Valid Doc",
        "department": "Security",
        "classification": "RESTRICTED",
        "allowed_roles": ["SECURITY_ENGINEER"],
        "document_type": "POLICY",
        "status": "ACTIVE",
        "file_path": "source/test_sec.txt",
        "file_format": "TXT",
        "content_hash": "c" * 64,
        "content": "Valid security policy content.",
    }
    with open(input_dir / "TEST-003.json", "w", encoding="utf-8") as f:
        json.dump(valid_doc_2, f)

    output_dir = tmp_path / "chunks"
    manifest_dir = tmp_path / "manifests"

    service = ChunkingService(
        input_dir=input_dir,
        output_dir=output_dir,
        manifest_dir=manifest_dir,
        chunk_size=500,
        chunk_overlap=50,
    )

    manifest = service.run_chunking()

    assert manifest.total_documents == 3
    assert manifest.successful_documents == 2
    assert manifest.failed_documents == 1

    # Output files must exist for TEST-001 and TEST-003, but not for TEST-002
    assert (output_dir / "TEST-001.json").exists()
    assert (output_dir / "TEST-003.json").exists()
    assert not (output_dir / "TEST-002.json").exists()
