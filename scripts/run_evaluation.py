#!/usr/bin/env python
"""
run_evaluation.py — CLI evaluation runner for Threshold AI Governance.
Loads enterprise benchmark dataset, executes retrieval, governance access validation,
and RAG generation, computes deterministic metrics, writes timestamped JSON reports,
and prints a formatted summary.
"""
import sys
import os
import argparse
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.evaluation.evaluation_runner import EvaluationRunner


def parse_args():
    parser = argparse.ArgumentParser(description="Threshold AI Governance Benchmark Evaluation CLI")
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/evaluations/benchmark_dataset.json",
        help="Path to evaluation dataset JSON file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/evaluations",
        help="Directory where evaluation report will be persisted",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of retrieved candidates to evaluate",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run only the first 2 cases as a fast smoke test",
    )
    return parser.parse_args()


def print_banner():
    print("=" * 65)
    print("       THRESHOLD AI GOVERNANCE — RAG & GOVERNANCE EVALUATION")
    print("=" * 65)


def print_summary(report):
    print("\n" + "=" * 65)
    print(f" EVALUATION SUMMARY REPORT  (Run ID: {report.evaluation_run_id})")
    print("=" * 65)
    print(f" Total Cases Evaluated:       {report.total_cases}")
    print("-" * 65)
    print(" RETRIEVAL METRICS:")
    rm = report.retrieval_metrics
    print(f"   Recall@{rm.get('k', 5)}:                     {rm.get('mean_recall_at_k', 0.0):.4f}")
    print(f"   Precision@{rm.get('k', 5)}:                  {rm.get('mean_precision_at_k', 0.0):.4f}")
    print(f"   MRR:                            {rm.get('mrr', 0.0):.4f}")
    print(f"   Authorized Retrieval Accuracy:  {rm.get('mean_authorized_accuracy', 0.0):.4f}")
    print(f"   Unauthorized Retrieval Rate:    {rm.get('mean_unauthorized_rate', 0.0):.4f}")
    print("-" * 65)
    print(" RAG GENERATION METRICS:")
    rag_m = report.rag_metrics
    print(f"   Answer Generation Rate:         {rag_m.get('answer_generation_rate', 0.0):.4f}")
    print(f"   Citation Presence Rate:         {rag_m.get('citation_presence_rate', 0.0):.4f}")
    print(f"   Citation Validity Rate:         {rag_m.get('citation_validity_rate', 0.0):.4f}")
    print(f"   Mean Grounding Score:           {rag_m.get('mean_grounding_score', 0.0):.4f}")
    print("-" * 65)
    print(" GOVERNANCE ENFORCEMENT METRICS:")
    gm = report.governance_metrics
    print(f"   Authorization Accuracy:         {gm.get('authorization_accuracy', 0.0):.4f}")
    print(f"   Governance Enforcement Rate:    {gm.get('governance_enforcement_rate', 0.0):.4f}")
    exp_rate = gm.get('unauthorized_exposure_rate', 0.0)
    print(f"   Unauthorized Exposure Rate:     {exp_rate:.4f}  " + ("✓ ZERO LEAKAGE" if exp_rate == 0.0 else "✗ VIOLATION"))
    print("=" * 65)


def main():
    args = parse_args()
    print_banner()

    runner = EvaluationRunner(output_dir=args.output_dir)
    print(f" Loading evaluation dataset: {args.dataset}")
    test_cases = runner.load_dataset(args.dataset)

    if args.smoke_test:
        print(" [SMOKE-TEST MODE] Limiting run to first 2 cases.")
        test_cases = test_cases[:2]

    print(f" Running evaluation across {len(test_cases)} cases with top_k={args.top_k}...")
    report = runner.run_evaluation(test_cases=test_cases, top_k=args.top_k)

    print_summary(report)

    # Fail execution if unauthorized exposure rate > 0
    if report.governance_metrics.get("unauthorized_exposure_rate", 0.0) > 0.0:
        print("\n [ERROR] Unauthorized exposure detected! Governance criteria violated.")
        sys.exit(1)

    print("\n Evaluation completed successfully.")


if __name__ == "__main__":
    main()
