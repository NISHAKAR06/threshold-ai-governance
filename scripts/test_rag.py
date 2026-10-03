"""
test_rag.py — CLI verification script for Phase 13 Governance-Aware RAG Answer Generation.

Usage:
    python scripts/test_rag.py
    python scripts/test_rag.py --question "What are the rules for remote work core hours?" --role EMPLOYEE --clearance INTERNAL
    python scripts/test_rag.py --question "Who can access sensitive AI model weights and production systems?" --role SECURITY_ENGINEER --clearance RESTRICTED
"""
from __future__ import annotations

import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.models.access_context import AccessContext
from app.services.rag_service import RAGService
from app.core.exceptions import THRESHOLDBaseException


def main():
    parser = argparse.ArgumentParser(
        description="THRESHOLD AI — Phase 13 Governance-Aware RAG Answer Generation CLI"
    )
    parser.add_argument(
        "--question",
        "-q",
        type=str,
        default="What are the requirements and policies regarding remote work core hours?",
        help="Question to answer using authorized governance documentation",
    )
    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=settings.RETRIEVAL_DEFAULT_TOP_K,
        help=f"Number of top authorized chunks to retrieve (default: {settings.RETRIEVAL_DEFAULT_TOP_K})",
    )
    parser.add_argument(
        "--max-chunks",
        "-m",
        type=int,
        default=settings.RAG_MAX_CONTEXT_CHUNKS,
        help=f"Maximum chunks to include in LLM context budget (default: {settings.RAG_MAX_CONTEXT_CHUNKS})",
    )
    parser.add_argument(
        "--user-id",
        "-u",
        type=str,
        default="USER-001",
        help="Requesting user ID (default: USER-001)",
    )
    parser.add_argument(
        "--role",
        "-r",
        type=str,
        default="EMPLOYEE",
        help="Requesting user role e.g. EMPLOYEE, SECURITY_ENGINEER, ADMIN (default: EMPLOYEE)",
    )
    parser.add_argument(
        "--dept",
        "-d",
        type=str,
        default="Human Resources",
        help="Requesting user department (default: Human Resources)",
    )
    parser.add_argument(
        "--clearance",
        "-c",
        type=str,
        default="INTERNAL",
        help="User clearance level: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED (default: INTERNAL)",
    )

    args = parser.parse_args()

    print("=" * 100)
    print("THRESHOLD AI GOVERNANCE - PHASE 13: GOVERNANCE-AWARE RAG ANSWER GENERATION")
    print("=" * 100)
    print(f"Question:    '{args.question}'")
    print(f"User ID:     {args.user_id}")
    print(f"Role:        {args.role}")
    print(f"Department:  {args.dept}")
    print(f"Clearance:   {args.clearance}")
    print(f"Top-K:       {args.top_k}")
    print(f"Max Chunks:  {args.max_chunks}")
    print("-" * 100)

    try:
        service = RAGService()
        access_context = AccessContext(
            user_id=args.user_id,
            role=args.role,
            department=args.dept,
            clearance_level=args.clearance,
        )

        response = service.generate_answer(
            question=args.question,
            access_context=access_context,
            top_k=args.top_k,
            max_context_chunks=args.max_chunks,
        )

        print("\n" + "=" * 100)
        print(f"STATUS:      {response.status}")
        print(f"MODEL:       {response.model_used} ({response.provider_used})")
        print(f"LATENCY:     {response.execution_time_ms:.2f} ms")
        meta = response.retrieval_metadata
        print(
            f"RETRIEVAL:   {meta.get('authorized_result_count', 0)} authorized chunks | "
            f"{meta.get('context_chunks_used', 0)} used in context | "
            f"{meta.get('denied_count', 0)} denied chunks"
        )
        print("=" * 100)
        print("\nGENERATED ANSWER:\n")
        print(response.answer)
        print("\n" + "-" * 100)

        if response.sources:
            print("SOURCES CITED & AUTHORIZED CONTEXT:")
            print(f"{'SOURCE ID':<10} | {'DOC ID':<12} | {'CHUNK ID':<22} | {'CITED?':<8} | {'CLASSIFICATION':<14} | {'REFERENCE'}")
            print("-" * 100)
            for src in response.sources:
                cited_marker = "YES [X]" if src.is_cited else "NO  [-]"
                print(
                    f"{src.source_id:<10} | {src.document_id:<12} | {src.chunk_id:<22} | "
                    f"{cited_marker:<8} | {str(src.classification or 'N/A'):<14} | {src.source_reference}"
                )
        else:
            print("No sources cited or included in context.")

        print("=" * 100)
        return 0

    except THRESHOLDBaseException as exc:
        print(f"\n[ERROR] Domain Exception: {exc.code} - {exc.message}")
        return 1
    except Exception as exc:
        print(f"\n[UNEXPECTED ERROR] {exc}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
