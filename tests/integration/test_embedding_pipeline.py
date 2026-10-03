"""
test_embedding_pipeline.py — End-to-end integration test for Phase 10 Embedding & Vector Index Pipeline.
"""
import json
from pathlib import Path
from app.services.embedding_service import EmbeddingService
from app.engines.embeddings.embedding_engine import EmbeddingEngine, MockEmbeddingProvider
from app.database.vector_store import ChromaVectorStore
from app.repositories.vector_repository import VectorRepository


def test_end_to_end_embedding_pipeline(tmp_path: Path):
    """
    Test end-to-end embedding and indexing using Phase 9 chunks in data/chunks.
    Validates:
    - Discovers 40 chunk files
    - Embeds and indexes all 631 chunks
    - Successfully stores in persistent Chroma store
    - Preserves governance metadata
    - Re-indexing is idempotent (no duplicate count)
    - Validates generated manifest
    """
    chunks_dir = Path("data/chunks")
    assert chunks_dir.exists(), "data/chunks directory must exist from Phase 9"

    store_path = tmp_path / "vector_db"
    manifest_dir = tmp_path / "indexing_manifests"

    # Setup isolated test store and repository
    store = ChromaVectorStore(path=store_path, collection_name="test_integration_chunks")
    repo = VectorRepository(store=store)

    provider = MockEmbeddingProvider(dimension=384)
    engine = EmbeddingEngine(provider=provider, batch_size=64)

    service = EmbeddingService(
        chunks_dir=chunks_dir,
        manifest_dir=manifest_dir,
        embedding_engine=engine,
        vector_repository=repo,
        batch_size=64,
    )

    # 1. First run: index all chunks
    manifest = service.run_indexing()

    assert manifest.total_documents == 40
    assert manifest.total_chunks == 631
    assert manifest.successful_chunks == 631
    assert manifest.failed_chunks == 0
    assert manifest.vectors_upserted == 631

    # Verify vector repository count
    total_vectors = repo.count()
    assert total_vectors == 631

    # Verify a sample record in the store
    sample_rec = repo.get_record("HR-001_CHUNK_0001_VEC")
    assert sample_rec is not None
    assert sample_rec.document_id == "HR-001"
    assert sample_rec.metadata["department"] == "Human Resources"
    assert "EMPLOYEE" in sample_rec.metadata["allowed_roles"]
    assert len(sample_rec.embedding) == 384
    assert sample_rec.embedding_dimension == 384

    # 2. Verify manifest file written to disk
    primary_manifest = manifest_dir / "indexing_manifest.json"
    assert primary_manifest.exists()
    with open(primary_manifest, "r", encoding="utf-8") as f:
        manifest_json = json.load(f)

    assert manifest_json["total_documents"] == 40
    assert manifest_json["successful_chunks"] == 631
    assert manifest_json["embedding_provider"] == "mock"
    assert len(manifest_json["results"]) == 40

    # 3. Verify Idempotence: Re-run indexing on the exact same chunks
    manifest_2 = service.run_indexing()
    assert manifest_2.successful_chunks == 631
    assert repo.count() == 631  # MUST remain 631, never 1262!


def test_pipeline_fault_tolerance(tmp_path: Path):
    """Verify that malformed chunks in one document do not crash the entire pipeline."""
    chunks_dir = tmp_path / "chunks"
    chunks_dir.mkdir()
    manifest_dir = tmp_path / "manifests"

    # 1. Valid document chunk file
    doc_1 = {
        "document_id": "VALID-001",
        "chunks": [
            {
                "chunk_id": "VALID-001_CHUNK_0001",
                "document_id": "VALID-001",
                "chunk_index": 1,
                "text": "Valid chunk content for testing.",
                "metadata": {
                    "department": "Engineering",
                    "classification": "INTERNAL",
                    "allowed_roles": ["ENGINEER"],
                    "document_type": "GUIDE",
                    "status": "ACTIVE",
                },
                "source": {"file_path": "valid.txt", "file_format": "TXT"},
                "parent_content_hash": "a" * 64,
                "chunk_content_hash": "b" * 64,
                "created_at": "2026-09-06T12:00:00Z",
            }
        ],
    }
    with open(chunks_dir / "VALID-001.json", "w", encoding="utf-8") as f:
        json.dump(doc_1, f)

    # 2. Corrupted document chunk file (empty text)
    doc_corrupt = {
        "document_id": "CORRUPT-001",
        "chunks": [
            {
                "chunk_id": "CORRUPT-001_CHUNK_0001",
                "document_id": "CORRUPT-001",
                "chunk_index": 1,
                "text": "   ",  # Invalid empty text
                "metadata": {},
                "source": {},
                "parent_content_hash": "",
                "chunk_content_hash": "",
                "created_at": "",
            }
        ],
    }
    with open(chunks_dir / "CORRUPT-001.json", "w", encoding="utf-8") as f:
        json.dump(doc_corrupt, f)

    # 3. Another valid document chunk file
    doc_2 = {
        "document_id": "VALID-002",
        "chunks": [
            {
                "chunk_id": "VALID-002_CHUNK_0001",
                "document_id": "VALID-002",
                "chunk_index": 1,
                "text": "Second valid chunk content.",
                "metadata": {
                    "department": "Security",
                    "classification": "RESTRICTED",
                    "allowed_roles": ["SECURITY_ENGINEER"],
                    "document_type": "POLICY",
                    "status": "ACTIVE",
                },
                "source": {"file_path": "valid2.txt", "file_format": "TXT"},
                "parent_content_hash": "c" * 64,
                "chunk_content_hash": "d" * 64,
                "created_at": "2026-09-06T12:00:00Z",
            }
        ],
    }
    with open(chunks_dir / "VALID-002.json", "w", encoding="utf-8") as f:
        json.dump(doc_2, f)

    service = EmbeddingService(
        chunks_dir=chunks_dir,
        manifest_dir=manifest_dir,
    )

    manifest = service.run_indexing()

    assert manifest.total_documents == 3
    assert manifest.total_chunks == 3
    assert manifest.successful_chunks == 2
    assert manifest.failed_chunks == 1
