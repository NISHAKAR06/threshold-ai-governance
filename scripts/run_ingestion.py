"""
run_ingestion.py — CLI script executing the Phase 8 Document Ingestion Pipeline.

Usage:
    python scripts/run_ingestion.py
    python scripts/run_ingestion.py --registry dataset/threshold-enterprise-dataset/metadata/document_registry.json
"""
import sys
import argparse
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.ingestion_service import IngestionService
from app.core.logger import ingestion_logger


def main():
    parser = argparse.ArgumentParser(
        description="THRESHOLD AI Phase 8 Document Ingestion Pipeline"
    )
    parser.add_argument(
        "--registry",
        default="dataset/threshold-enterprise-dataset/metadata/document_registry.json",
        help="Path to document_registry.json",
    )
    parser.add_argument(
        "--output-dir",
        default="dataset/threshold-enterprise-dataset/data/normalized_documents",
        help="Directory to save normalized document JSONs",
    )
    parser.add_argument(
        "--manifest-dir",
        default="dataset/threshold-enterprise-dataset/data/ingestion_manifests",
        help="Directory to save ingestion manifests",
    )
    args = parser.parse_args()

    print("=" * 75)
    print("      THRESHOLD ENTERPRISE SYSTEMS — DOCUMENT INGESTION PIPELINE")
    print("      Phase 8: Multi-Format Extraction, Normalization & Validation")
    print("=" * 75)
    print(f" Registry Path : {args.registry}")
    print(f" Output Dir    : {args.output_dir}")
    print(f" Manifest Dir  : {args.manifest_dir}")
    print("=" * 75)

    try:
        service = IngestionService(
            registry_path=args.registry,
            output_dir=args.output_dir,
            manifest_dir=args.manifest_dir,
        )
        manifest = service.run_ingestion()

        print("\n" + "-" * 75)
        print(f" {'DOCUMENT ID':<12} | {'STATUS':<9} | {'FORMAT':<6} | {'WORDS':<8} | {'TIME (ms)':<10} | {'FILE PATH'}")
        print("-" * 75)

        for doc in manifest.documents:
            words_str = str(doc.word_count) if doc.word_count is not None else "N/A"
            print(
                f" {doc.document_id:<12} | {doc.status:<9} | {doc.file_format:<6} | {words_str:<8} | {doc.execution_time_ms:<10.1f} | {doc.file_path}"
            )

        print("=" * 75)
        print(" INGESTION SUMMARY:")
        print(f"   Total Documents : {manifest.total_documents}")
        print(f"   Success Count   : {manifest.success_count}")
        print(f"   Failure Count   : {manifest.failure_count}")
        print(f"   Execution Time  : {manifest.execution_time_seconds:.2f} seconds")
        print("=" * 75)

        if manifest.failure_count > 0:
            print("\n[ERROR] Ingestion completed with errors. One or more documents failed.")
            sys.exit(1)
        else:
            print("\n[SUCCESS] All 40 documents successfully ingested and normalized.")
            print("READY FOR PHASE 9: DOCUMENT CHUNKING PIPELINE.")
            sys.exit(0)

    except Exception as e:
        ingestion_logger.exception(f"Fatal error during ingestion: {str(e)}")
        print(f"\n[FATAL ERROR] Ingestion aborted: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
