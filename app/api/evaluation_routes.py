"""
evaluation_routes.py — API endpoints for Phase 15/16 RAG & Governance Evaluation Reports.
Exposes read-only access to evaluation benchmark reports and allows triggering benchmark runs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel

from app.evaluation.evaluation_runner import EvaluationRunner
from app.core.logger import get_logger

logger = get_logger("threshold.api.evaluation")

router = APIRouter()

EVAL_DIR = Path("data/evaluations")


class RunEvaluationRequest(BaseModel):
    dataset_path: Optional[str] = "data/evaluations/benchmark_dataset.json"
    top_k: Optional[int] = 5
    smoke_test: Optional[bool] = False


@router.get("/latest", summary="Get latest evaluation report")
async def get_latest_evaluation() -> Dict[str, Any]:
    """
    Returns the most recent evaluation benchmark report JSON.
    """
    if not EVAL_DIR.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NO_EVALUATION_FOUND", "message": "No evaluation reports found."},
        )

    report_files = sorted(
        EVAL_DIR.glob("evaluation_report_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not report_files:
        # Fallback: if benchmark dataset exists, generate initial report on the fly
        benchmark_file = EVAL_DIR / "benchmark_dataset.json"
        if benchmark_file.exists():
            runner = EvaluationRunner(output_dir=str(EVAL_DIR))
            cases = runner.load_dataset(str(benchmark_file))
            report = runner.run_evaluation(cases[:4], top_k=3)
            data = report.to_dict()
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NO_EVALUATION_FOUND", "message": "No evaluation reports found."},
            )
    else:
        with open(report_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)

    data["run_id"] = data.get("evaluation_run_id") or data.get("run_id")
    if "unauthorized_exposure_rate" not in data and "governance_metrics" in data:
        data["unauthorized_exposure_rate"] = data["governance_metrics"].get("unauthorized_exposure_rate", 0.0)
    return data


@router.get("/runs", summary="List all evaluation runs")
async def list_evaluation_runs() -> Dict[str, Any]:
    """
    Returns a list of all historical evaluation runs with high-level summary metrics.
    """
    if not EVAL_DIR.exists():
        return {"runs": []}

    report_files = sorted(
        EVAL_DIR.glob("evaluation_report_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    runs = []
    for p in report_files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
                run_id = data.get("evaluation_run_id", p.stem)
                runs.append({
                    "run_id": run_id,
                    "evaluation_run_id": run_id,
                    "timestamp": data.get("timestamp"),
                    "total_cases": data.get("total_cases", 0),
                    "retrieval_metrics": data.get("retrieval_metrics", {}),
                    "rag_metrics": data.get("rag_metrics", {}),
                    "governance_metrics": data.get("governance_metrics", {}),
                })
        except Exception as exc:
            logger.debug("Failed to read report %s: %s", p.name, exc)
    return {"runs": runs, "total": len(runs)}


@router.get("/runs/{run_id}", summary="Get specific evaluation report")
async def get_evaluation_run(run_id: str) -> Dict[str, Any]:
    """
    Retrieves a specific evaluation run report by its run_id.
    """
    safe_id = Path(run_id).name  # Prevent directory traversal
    report_path = EVAL_DIR / f"evaluation_report_{safe_id}.json"
    if not report_path.exists():
        report_path = EVAL_DIR / f"{safe_id}.json"

    if not report_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "EVAL_RUN_NOT_FOUND", "message": f"Run '{run_id}' not found."},
        )

    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/run", summary="Trigger benchmark evaluation run")
async def trigger_evaluation(payload: RunEvaluationRequest) -> Dict[str, Any]:
    """
    Triggers an evaluation execution on the benchmark dataset.
    """
    runner = EvaluationRunner(output_dir=str(EVAL_DIR))
    ds_path = payload.dataset_path or "data/evaluations/benchmark_dataset.json"
    if not Path(ds_path).exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "DATASET_NOT_FOUND", "message": f"Dataset '{ds_path}' does not exist."},
        )

    cases = runner.load_dataset(ds_path)
    if payload.smoke_test:
        cases = cases[:2]

    report = runner.run_evaluation(cases, top_k=payload.top_k or 5)
    return report.to_dict()
