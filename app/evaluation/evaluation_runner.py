"""
evaluation_runner.py — Orchestrates comprehensive evaluation runs for Threshold AI Governance.
Loads datasets, executes retrieval, governance filtering, and RAG generation pipelines,
computes deterministic evaluation metrics, and persists timestamped reports.
"""
from __future__ import annotations

import json
import uuid
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.evaluation.models import (
    EvaluationTestCase,
    CaseEvaluationResult,
    EvaluationReport,
)
from app.evaluation.retrieval_evaluator import RetrievalEvaluator
from app.evaluation.rag_evaluator import RAGEvaluator
from app.evaluation.governance_evaluator import GovernanceEvaluator
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from app.core.logger import get_logger

logger = get_logger("threshold.evaluation.runner")


class EvaluationRunner:
    """
    Executes end-to-end evaluation batches against test cases and compiles structured reports.
    """

    def __init__(
        self,
        rag_service: Optional[RAGService] = None,
        retrieval_service: Optional[RetrievalService] = None,
        output_dir: str = "data/evaluations",
    ) -> None:
        self.rag_service = rag_service or RAGService()
        self.retrieval_service = retrieval_service or RetrievalService()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.retrieval_evaluator = RetrievalEvaluator()
        self.rag_evaluator = RAGEvaluator()
        self.governance_evaluator = GovernanceEvaluator()

    def load_dataset(self, dataset_path: str) -> List[EvaluationTestCase]:
        """Load benchmark cases from a JSON file."""
        p = Path(dataset_path)
        if not p.exists():
            raise FileNotFoundError(f"Evaluation dataset not found at: {dataset_path}")

        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "cases" in data:
            data = data["cases"]

        return [EvaluationTestCase.from_dict(item) for item in data]

    def run_evaluation(
        self,
        test_cases: List[EvaluationTestCase],
        run_id: Optional[str] = None,
        top_k: int = 5,
    ) -> EvaluationReport:
        """
        Execute evaluation across all supplied test cases.
        """
        run_uuid = run_id or f"eval_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        start_time = datetime.now(timezone.utc).isoformat()
        case_results: List[CaseEvaluationResult] = []

        gov_results_list = []

        logger.info("Starting evaluation run '%s' with %d cases", run_uuid, len(test_cases))

        for idx, case in enumerate(test_cases, start=1):
            t0 = time.monotonic()
            try:
                # 1. Execute RAG pipeline with security access context
                rag_resp = self.rag_service.generate_answer(
                    question=case.question,
                    access_context=case.access_context,
                    top_k=top_k,
                )

                # Extract retrieved / authorized chunks
                retrieved_chunk_ids = [s.chunk_id for s in rag_resp.sources]
                denied_chunk_ids = []
                # If retrieval metadata provides denied candidate details
                meta = rag_resp.retrieval_metadata or {}
                if "denied_candidates" in meta:
                    denied_chunk_ids = [c.get("chunk_id") for c in meta["denied_candidates"] if isinstance(c, dict)]

                # 2. Evaluate Retrieval
                retrieval_res = self.retrieval_evaluator.evaluate(
                    retrieved_chunk_ids=retrieved_chunk_ids,
                    expected_chunk_ids=case.expected_chunk_ids,
                    authorized_chunk_ids=set(retrieved_chunk_ids),
                    k=top_k,
                )

                # 3. Evaluate RAG Generation
                sources_dicts = [
                    {"chunk_id": s.chunk_id, "document_id": s.document_id, "source_reference": s.source_reference}
                    for s in rag_resp.sources
                ]
                rag_res = self.rag_evaluator.evaluate(
                    generated_answer=rag_resp.answer,
                    authorized_sources=sources_dicts,
                    expected_answer=case.expected_answer,
                )

                # 4. Evaluate Governance
                gov_res = self.governance_evaluator.evaluate_case(
                    actual_decision=rag_resp.status,
                    expected_decision=case.expected_authorization,
                    denied_chunk_ids=denied_chunk_ids,
                    context_chunk_ids=retrieved_chunk_ids,
                    final_answer_text=rag_resp.answer or "",
                )
                gov_results_list.append(gov_res)

                exec_time = (time.monotonic() - t0) * 1000.0
                case_results.append(
                    CaseEvaluationResult(
                        test_case=case,
                        retrieval_result=retrieval_res,
                        rag_result=rag_res,
                        governance_result=gov_res,
                        execution_time_ms=exec_time,
                    )
                )
            except Exception as exc:
                logger.error("Error evaluating test case %s: %s", case.evaluation_id, exc)
                exec_time = (time.monotonic() - t0) * 1000.0
                case_results.append(
                    CaseEvaluationResult(
                        test_case=case,
                        execution_time_ms=exec_time,
                    )
                )

        # Calculate Aggregates
        retrieval_metrics = self._aggregate_retrieval_metrics(case_results)
        rag_metrics = self._aggregate_rag_metrics(case_results)
        gov_metrics = self.governance_evaluator.calculate_aggregate_metrics(gov_results_list)

        report = EvaluationReport(
            evaluation_run_id=run_uuid,
            timestamp=start_time,
            total_cases=len(test_cases),
            retrieval_metrics=retrieval_metrics,
            rag_metrics=rag_metrics,
            governance_metrics=gov_metrics,
            case_results=case_results,
        )

        # Persist report to disk without overwriting previous runs
        report_path = self.output_dir / f"evaluation_report_{run_uuid}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info("Evaluation report saved to: %s", report_path)
        return report

    def _aggregate_retrieval_metrics(self, results: List[CaseEvaluationResult]) -> Dict[str, float]:
        valid = [r.retrieval_result for r in results if r.retrieval_result is not None]
        if not valid:
            return {"mean_precision_at_k": 0.0, "mean_recall_at_k": 0.0, "mrr": 0.0}

        return {
            "mean_precision_at_k": round(sum(v.precision_at_k for v in valid) / len(valid), 4),
            "mean_recall_at_k": round(sum(v.recall_at_k for v in valid) / len(valid), 4),
            "mrr": round(sum(v.mrr for v in valid) / len(valid), 4),
            "mean_authorized_accuracy": round(sum(v.authorized_retrieval_accuracy for v in valid) / len(valid), 4),
            "mean_unauthorized_rate": round(sum(v.unauthorized_retrieval_rate for v in valid) / len(valid), 4),
        }

    def _aggregate_rag_metrics(self, results: List[CaseEvaluationResult]) -> Dict[str, float]:
        valid = [r.rag_result for r in results if r.rag_result is not None]
        if not valid:
            return {"answer_generation_rate": 0.0, "citation_presence_rate": 0.0}

        gen_rate = sum(1 for v in valid if v.answer_generated) / len(valid)
        cit_rate = sum(1 for v in valid if v.source_citations_present) / len(valid)
        valid_cit_rate = sum(1 for v in valid if v.citations_valid) / len(valid)
        avg_grounding = sum(v.grounding_score for v in valid) / len(valid)

        return {
            "answer_generation_rate": round(gen_rate, 4),
            "citation_presence_rate": round(cit_rate, 4),
            "citation_validity_rate": round(valid_cit_rate, 4),
            "mean_grounding_score": round(avg_grounding, 4),
        }
