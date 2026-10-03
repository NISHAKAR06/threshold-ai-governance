"""
test_governance_retrieval.py — CLI verification script for Phase 12 Hybrid Search & Governance-Aware Retrieval.

Usage:
    python scripts/test_governance_retrieval.py
    python scripts/test_governance_retrieval.py --query "remote work core hours" --role EMPLOYEE --clearance INTERNAL
    python scripts/test_governance_retrieval.py --query "AI model access restrictions" --role SECURITY_ENGINEER --clearance RESTRICTED
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
from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.core.exceptions import THRESHOLDBaseException


def main():
    parser = argparse.ArgumentParser(
        description="THRESHOLD AI — Phase 12 Hybrid Search & Governance-Aware Retrieval CLI"
    )
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        default="What are the access control and security protocols for sensitive AI models?",
        help="Search query to retrieve relevant chunks for",
    )
    parser.add_argument(
        "--top-k",
        "-k",
        type=int,
        default=settings.RETRIEVAL_DEFAULT_TOP_K,
        help=f"Number of top authorized chunks to retrieve (default: {settings.RETRIEVAL_DEFAULT_TOP_K})",
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
        default="SECURITY_ENGINEER",
        help="Requesting user role e.g. EMPLOYEE, SECURITY_ENGINEER, ADMIN (default: SECURITY_ENGINEER)",
    )
    parser.add_argument(
        "--dept",
        "-d",
        type=str,
        default="Information Security",
        help="Requesting user department (default: Information Security)",
    )
    parser.add_argument(
        "--clearance",
        "-c",
        type=str,
        default="RESTRICTED",
        help="User clearance level: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED (default: RESTRICTED)",
    )

    args = parser.parse_args()

    print("=" * 100)
    print("THRESHOLD AI GOVERNANCE - PHASE 12: HYBRID SEARCH & GOVERNANCE RETRIEVAL")
    print("=" * 100)
    print(f"Query:       '{args.query}'")
    print(f"Requested K: {args.top_k}")
    print(f"User ID:     {args.user_id}")
    print(f"Role:        {args.role}")
    print(f"Department:  {args.dept}")
    print(f"Clearance:   {args.clearance}")
    print("-" * 100)

    try:
        service = HybridRetrievalService()
        access_context = AccessContext(
            user_id=args.user_id,
            role=args.role,
            department=args.dept,
            clearance_level=args.clearance,
        )

        response = service.retrieve(
            query=args.query,
            access_context=access_context,
            top_k=args.top_k,
        )

        print(f"\nRetrieval Completed successfully!")
        print(f"Strategy:         {response.fusion_strategy}")
        print(f"Candidates:       {response.semantic_candidate_count} semantic, {response.keyword_candidate_count} keyword")
        print(f"Latency:          {response.execution_time_ms:.2f} ms")
        print(f"Authorized Count: {response.authorized_result_count}")
        print(f"Denied Count:     {response.denied_count} (omitted from results)\n")

        if response.authorized_result_count == 0:
            print("No authorized candidate chunks found for this query and access context.")
            return 0

        # Display concise ranked authorized results
        print(f"{'RANK':<5} | {'FUSED':<8} | {'SEM':<7} | {'KW':<7} | {'DOC ID':<12} | {'CHUNK ID':<22} | {'PREVIEW'}")
        print("-" * 110)

        for item in response.results:
            text_snippet = item.text.replace("\n", " ").strip()
            if len(text_snippet) > 50:
                text_snippet = text_snippet[:47] + "..."

            sem_str = f"{item.semantic_score:.4f}" if item.semantic_score is not None else "N/A"
            kw_str = f"{item.keyword_score:.4f}" if item.keyword_score is not None else "N/A"

            print(
                f"{item.rank:<5} | {item.fused_score:<8.6f} | {sem_str:<7} | {kw_str:<7} | "
                f"{item.document_id:<12} | {item.chunk_id:<22} | {text_snippet}"
            )
            dept = item.metadata.get("department", "N/A")
            classif = item.metadata.get("classification", "N/A")
            roles = item.metadata.get("allowed_roles", [])
            print(f"      +-- Dept: {dept} | Classification: {classif} | Allowed Roles: {roles}")

        print("=" * 110)
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
