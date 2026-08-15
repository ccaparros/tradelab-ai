"""Experiments API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tradelab.agents.tools import generate_experiment_report, list_strategies
from tradelab.backtesting.service import run_experiment
from tradelab.datasets.store import get_experiment, list_experiments

router = APIRouter()


class RunBacktestRequest(BaseModel):
    dataset_id: str
    strategy_id: str = "orb_atr_intraday"
    parameters: dict[str, Any]
    split_spec: dict[str, Any] | None = None
    consume_holdout: bool = False


@router.get("/v1/strategies")
def api_list_strategies() -> dict:
    return {"items": list_strategies()}


@router.get("/v1/experiments")
def api_list_experiments(dataset_id: str | None = None) -> dict:
    return {"items": list_experiments(dataset_id=dataset_id)}


@router.post("/v1/experiments", status_code=201)
def api_run_backtest(body: RunBacktestRequest) -> dict:
    try:
        return run_experiment(
            dataset_id=body.dataset_id,
            strategy_id=body.strategy_id,
            parameters=body.parameters,
            consume_holdout=body.consume_holdout,
            split_spec=body.split_spec,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/v1/experiments/{experiment_id}")
def api_get_experiment(experiment_id: str) -> dict:
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="not_found")
    return exp


@router.get("/v1/experiments/{experiment_id}/trades")
def api_get_trades(experiment_id: str, split_label: str | None = None, limit: int = 50) -> dict:
    exp = get_experiment(experiment_id)
    if not exp:
        raise HTTPException(status_code=404, detail="not_found")
    trades = exp.get("trades") or []
    if split_label:
        trades = [t for t in trades if t.get("split_label") == split_label]
    return {"items": trades[: max(1, min(limit, 500))]}


@router.get("/v1/experiments/{experiment_id}/report")
def api_report(experiment_id: str) -> dict:
    try:
        return generate_experiment_report(experiment_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
