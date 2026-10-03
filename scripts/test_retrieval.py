"""
test_retrieval.py — CLI verification script for Phase 11 Semantic Retrieval.

Usage:
    python scripts/test_retrieval.py
    python scripts/test_retrieval.py --query "What are the rules for remote work and office hours?"
    python scripts/test_retrieval.py --query "accessing sensitive AI systems" --top-k 3
"""
import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.services.retrieval_service import RetrievalService
from app.engines.embeddings.embedding_engine import EmbeddingEngine, get_embedding_provider
from app.repositories.vector_repository import VectorRepository
from app.database.vector_store import get_vector_store
from app.core.exceptions import THRESHOLDBaseException


def main():
    parser = argparse.ArgumentParser(
        description="THRESHOLD AI — Phase 11 Semantic Retrieval Verification CLI"
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="What are the access requirements and security protocols for sensitive AI systems?",
        help="Search query to retrieve relevant chunks for (default: sample enterprise query)",
    )
    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=settings.RETRIEVAL_DEFAULT_TOP_K,
        help=f"Number of top chunks to retrieve (default: {settings.RETRIEVAL_DEFAULT_TOP_K})",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="Optional embedding provider override ('mock', 'gemini', 'local')",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Optional embedding model override",
    )
    parser.add_argument(
        "--vector-store",
        type=str,
        default=None,
        help="Optional vector store provider override ('chroma', 'in_memory')",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("THRESHOLD AI GOVERNANCE — PHASE 11: SEMANTIC RETRIEVAL")
    print("=" * 80)
    print(f"Query:        '{args.query}'")
    print(f"Requested K:  {args.top_k}")
    print("-" * 80)

    try:
        # Build dependencies (respecting CLI overrides if provided)
        provider = get_embedding_provider(provider_name=args.provider, model_name=args.model)
        engine = EmbeddingEngine(provider=provider)
        store = get_vector_store(provider=args.vector_store)
        repo = VectorRepository(store=store)

        service = RetrievalService(
            embedding_engine=engine,
            vector_repository=repo,
        )

        response = service.retrieve(query=args.query, top_k=args.top_k)

        print(f"\nRetrieval Completed successfully!")
        print(f"Provider:     {response.provider_name} ({response.model_name})")
        print(f"Latency:      {response.query_time_ms:.2f} ms")
        print(f"Result Count: {response.result_count}\n")

        if response.result_count == 0:
            print("No matching candidate chunks found.")
            return 0

        # Display concise ranked results
        print(f"{'RANK':<5} | {'SCORE':<7} | {'DOC ID':<15} | {'CHUNK ID':<25} | {'PREVIEW'}")
        print("-" * 100)

        for item in response.results:
            text_snippet = item.text.replace("\n", " ").strip()
            if len(text_snippet) > 60:
                text_snippet = text_snippet[:57] + "..."

            print(
                f"{item.rank:<5} | {item.score:<7.4f} | {item.document_id:<15} | "
                f"{item.chunk_id:<25} | {text_snippet}"
            )
            dept = item.metadata.get("department", "N/A")
            classif = item.metadata.get("classification", "N/A")
            roles = item.metadata.get("allowed_roles", [])
            print(f"      +-- Dept: {dept} | Classification: {classif} | Allowed Roles: {roles}")

        print("=" * 100)
        return 0

    except THRESHOLDBaseException as exc:
        print(f"\n[ERROR] Domain Exception: {exc.code} - {exc.message}")
        if exc.details:
            print(f"Details: {exc.details}")
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
