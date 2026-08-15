"""Analysis and documents API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tradelab.agents.graph import run_analysis
from tradelab.datasets.store import get_analysis
from tradelab.rag.retrieve import hybrid_search

router = APIRouter()


class AnalysisRequest(BaseModel):
    query: str = Field(min_length=1)
    dataset_id: str | None = None
    experiment_id: str | None = None


class DocumentSearchRequest(BaseModel):
    query: str
    filters: dict | None = None
    top_k: int = 5


@router.post("/v1/analysis")
def api_create_analysis(body: AnalysisRequest) -> dict:
    return run_analysis(query=body.query, dataset_id=body.dataset_id, experiment_id=body.experiment_id)


@router.get("/v1/analysis/{analysis_id}")
def api_get_analysis(analysis_id: str) -> dict:
    row = get_analysis(analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="not_found")
    return row


@router.post("/v1/documents/search")
def api_search_docs(body: DocumentSearchRequest) -> dict:
    return {"items": hybrid_search(body.query, top_k=body.top_k)}
