"""
run_embedding.py — CLI script executing the Phase 10 Embedding Generation & Vector Index Pipeline.

Usage:
    python scripts/run_embedding.py
    python scripts/run_embedding.py --provider mock --model mock-embedding-768
    python scripts/run_embedding.py --chunks-dir data/chunks --vector-store chroma
"""
import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.engines.embeddings.embedding_engine import EmbeddingEngine, get_embedding_provider
from app.repositories.vector_repository import VectorRepository
from app.database.vector_store import get_vector_store
from app.core.logger import service_logger


def main():
    parser = argparse.ArgumentParser(
        description="THRESHOLD AI Phase 10 Embedding Generation & Vector Index Preparation"
    )
    parser.add_argument(
        "--chunks-dir",
        default="data/chunks",
        help="Directory containing Phase 9 chunk JSON files (default: data/chunks)",
    )
    parser.add_argument(
        "--manifest-dir",
        default="data/indexing_manifests",
        help="Directory to save indexing manifests (default: data/indexing_manifests)",
    )
    parser.add_argument(
        "--provider",
        default=settings.EMBEDDING_PROVIDER,
        help=f"Embedding provider: 'mock', 'gemini', or 'local' (default: {settings.EMBEDDING_PROVIDER})",
    )
    parser.add_argument(
        "--model",
        default=settings.EMBEDDING_MODEL,
        help=f"Embedding model identifier (default: {settings.EMBEDDING_MODEL})",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=settings.EMBEDDING_BATCH_SIZE,
        help=f"Batch size for embedding generation (default: {settings.EMBEDDING_BATCH_SIZE})",
    )
    parser.add_argument(
        "--vector-store",
        default=settings.VECTOR_STORE_PROVIDER,
        help=f"Vector store provider: 'chroma' or 'in_memory' (default: {settings.VECTOR_STORE_PROVIDER})",
    )
    parser.add_argument(
        "--store-path",
        default=settings.VECTOR_STORE_PATH,
        help=f"Path for persistent vector store (default: {settings.VECTOR_STORE_PATH})",
    )
    parser.add_argument(
        "--collection",
        default=settings.VECTOR_STORE_COLLECTION,
        help=f"Vector collection name (default: {settings.VECTOR_STORE_COLLECTION})",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("      THRESHOLD ENTERPRISE SYSTEMS — EMBEDDING & VECTOR INDEX PIPELINE")
    print("      Phase 10: Dense Embedding Generation & Vector Persistence")
    print("=" * 80)
    print(f" Chunks Dir   : {args.chunks_dir}")
    print(f" Manifest Dir : {args.manifest_dir}")
    print(f" Provider     : {args.provider}")
    print(f" Model        : {args.model}")
    print(f" Batch Size   : {args.batch_size}")
    print(f" Vector Store : {args.vector_store}")
    print(f" Store Path   : {args.store_path}")
    print(f" Collection   : {args.collection}")
    print("=" * 80)

    try:
        # 1. Initialize components via factories
        provider_instance = get_embedding_provider(
            provider_name=args.provider,
            model_name=args.model,
        )
        engine_instance = EmbeddingEngine(
            provider=provider_instance,
            batch_size=args.batch_size,
        )
        store_instance = get_vector_store(
            provider=args.vector_store,
            path=args.store_path,
            collection_name=args.collection,
        )
        repo_instance = VectorRepository(store=store_instance)

        # 2. Run service
        service = EmbeddingService(
            chunks_dir=args.chunks_dir,
            manifest_dir=args.manifest_dir,
            embedding_engine=engine_instance,
            vector_repository=repo_instance,
            batch_size=args.batch_size,
        )

        manifest = service.run_indexing()

        print("\n" + "-" * 80)
        print(f" {'DOCUMENT ID':<14} | {'STATUS':<9} | {'CHUNKS':<8} | {'INDEXED':<8} | {'TIME (ms)':<10}")
        print("-" * 80)

        for res in manifest.results:
            print(
                f" {res.document_id:<14} | {res.status:<9} | {res.chunks_processed:<8} | "
                f"{res.chunks_indexed:<8} | {res.execution_time_ms:<10.1f}"
            )

        print("=" * 80)
        print(" VECTOR INDEXING SUMMARY:")
        print(f"   Run ID               : {manifest.indexing_run_id}")
        print(f"   Embedding Provider   : {manifest.embedding_provider}")
        print(f"   Embedding Model      : {manifest.embedding_model}")
        print(f"   Vector Collection    : {manifest.collection_name}")
        print(f"   Total Documents      : {manifest.total_documents}")
        print(f"   Total Chunks         : {manifest.total_chunks}")
        print(f"   Successful Chunks    : {manifest.successful_chunks}")
        print(f"   Failed Chunks        : {manifest.failed_chunks}")
        print(f"   Vectors Upserted     : {manifest.vectors_upserted}")
        print(f"   Vector Store Total   : {repo_instance.count()} records")
        print("=" * 80)

        if manifest.failed_chunks > 0:
            print("\n[WARNING] Indexing run completed with one or more chunk failures.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] All chunks successfully embedded and indexed.")
            print(f"Manifest published to: {args.manifest_dir}/indexing_manifest.json")
            print("READY FOR PHASE 11: SEMANTIC RETRIEVAL PIPELINE.")
            sys.exit(0)

    except Exception as e:
        service_logger.exception(f"Fatal error during embedding execution: {str(e)}")
        print(f"\n[FATAL ERROR] Embedding pipeline aborted: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
