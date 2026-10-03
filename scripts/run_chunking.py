"""
run_chunking.py — CLI script executing the Phase 9 Document Chunking Pipeline.

Usage:
    python scripts/run_chunking.py
    python scripts/run_chunking.py --input-dir dataset/threshold-enterprise-dataset/data/normalized_documents
    python scripts/run_chunking.py --chunk-size 1000 --chunk-overlap 150
"""
import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.services.chunking_service import ChunkingService
from app.core.logger import service_logger


def main():
    parser = argparse.ArgumentParser(
        description="THRESHOLD AI Phase 9 Document Chunking & Chunk Metadata Pipeline"
    )
    parser.add_argument(
        "--input-dir",
        default=None,
        help="Directory containing normalized document JSONs (defaults to dataset/threshold-enterprise-dataset/data/normalized_documents or data/normalized_documents)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/chunks",
        help="Directory to save generated chunk JSON files (default: data/chunks)",
    )
    parser.add_argument(
        "--manifest-dir",
        default="data/chunking_manifests",
        help="Directory to save chunking manifests (default: data/chunking_manifests)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=settings.CHUNK_SIZE,
        help=f"Maximum chunk size in characters (default: {settings.CHUNK_SIZE})",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=settings.CHUNK_OVERLAP,
        help=f"Chunk overlap in characters (default: {settings.CHUNK_OVERLAP})",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("      THRESHOLD ENTERPRISE SYSTEMS — DOCUMENT CHUNKING PIPELINE")
    print("      Phase 9: Structure-Aware Chunking & Governance Metadata Generation")
    print("=" * 80)
    print(f" Input Dir     : {args.input_dir or 'Auto-detected'}")
    print(f" Output Dir    : {args.output_dir}")
    print(f" Manifest Dir  : {args.manifest_dir}")
    print(f" Chunk Size    : {args.chunk_size}")
    print(f" Chunk Overlap : {args.chunk_overlap}")
    print("=" * 80)

    try:
        service = ChunkingService(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            manifest_dir=args.manifest_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )

        manifest = service.run_chunking()

        print("\n" + "-" * 80)
        print(f" {'DOCUMENT ID':<14} | {'STATUS':<9} | {'CHUNKS':<8} | {'TIME (ms)':<10} | {'OUTPUT FILE'}")
        print("-" * 80)

        for res in manifest.results:
            out_file = res.output_file or "N/A"
            print(
                f" {res.document_id:<14} | {res.status:<9} | {res.chunks_created:<8} | "
                f"{res.execution_time_ms:<10.1f} | {out_file}"
            )

        print("=" * 80)
        print(" CHUNKING EXECUTION SUMMARY:")
        print(f"   Run ID               : {manifest.chunking_run_id}")
        print(f"   Total Documents      : {manifest.total_documents}")
        print(f"   Successful Documents : {manifest.successful_documents}")
        print(f"   Failed Documents     : {manifest.failed_documents}")
        print(f"   Total Chunks Created : {manifest.total_chunks}")
        print("=" * 80)

        if manifest.failed_documents > 0:
            print("\n[ERROR] Chunking run completed with one or more failures.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] Chunking pipeline executed successfully for all documents.")
            print(f"Output files saved to: {args.output_dir}")
            print(f"Manifest published to: {args.manifest_dir}/chunking_manifest.json")
            print("READY FOR PHASE 10: EMBEDDING GENERATION PIPELINE.")
            sys.exit(0)

    except Exception as e:
        service_logger.exception(f"Fatal error during chunking pipeline execution: {str(e)}")
        print(f"\n[FATAL ERROR] Chunking pipeline aborted: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
