"""Catalog and ingestion API routes."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from tradelab.datasets.publisher import publish_canonical_dataset
from tradelab.datasets.store import get_dataset, list_datasets, upsert_dataset
from tradelab.ingestion.register import register_raw_batch
from tradelab.quality.reconcile import reconcile_frames
from tradelab.quality.validators import build_quality_report

router = APIRouter()


class RegisterIngestionRequest(BaseModel):
    source: str
    instrument: str
    contract_month: str
    parquet_uri: str
    manifest_uri: str
    checksum: str | None = None
    request_params: dict[str, Any] = Field(default_factory=dict)
    publish: bool = True


class CompareSourcesRequest(BaseModel):
    instrument: str
    start_utc: str | None = None
    end_utc: str | None = None
    contract_month: str | None = None
    left_parquet_uri: str
    right_parquet_uri: str
    tick_size: float = 0.25


@router.get("/v1/datasets")
def api_list_datasets(quality_status: str | None = None, instrument: str | None = None) -> dict:
    items = list_datasets(quality_status=quality_status)
    if instrument:
        items = [d for d in items if d.get("instrument") == instrument]
    return {"items": items}


@router.get("/v1/datasets/{dataset_id}")
def api_get_dataset(dataset_id: str) -> dict:
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="not_found")
    return ds


@router.get("/v1/datasets/{dataset_id}/quality")
def api_get_quality(dataset_id: str) -> dict:
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="not_found")
    quality = ds.get("quality") or {}
    return {
        "dataset_id": dataset_id,
        "duplicate_count": quality.get("duplicate_count", 0),
        "gap_count": quality.get("gap_count", 0),
        "gaps": quality.get("gaps", []),
        "ohlc_violations": quality.get("ohlc_violations", 0),
        "report_uri": ds.get("report_uri"),
        "quality_status": ds.get("quality_status"),
    }


@router.post("/v1/ingestions", status_code=201)
def api_register_ingestion(body: RegisterIngestionRequest) -> dict:
    try:
        run = register_raw_batch(
            source=body.source,
            instrument=body.instrument,
            contract_month=body.contract_month,
            parquet_uri=body.parquet_uri,
            manifest_uri=body.manifest_uri,
            checksum=body.checksum,
            request_params=body.request_params,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if body.publish:
        df = pd.read_parquet(body.parquet_uri)
        published = publish_canonical_dataset(
            df,
            contract_id=uuid.uuid4(),
            preferred_source_id=body.source,
            lineage={"ingestion_run_id": str(run["ingestion_run_id"]), "source": body.source},
        )
        record = {
            **published,
            "dataset_id": str(published["dataset_id"]),
            "contract_id": str(published["contract_id"]),
            "instrument": body.instrument,
            "contract_month": body.contract_month,
            "bar_size": "5 mins",
            "coverage_start_utc": str(published["coverage_start_utc"]),
            "coverage_end_utc": str(published["coverage_end_utc"]),
        }
        # serialize nested uuid
        record["quality"] = published["quality"]
        upsert_dataset(record)
        run["dataset_id"] = record["dataset_id"]
    return run


@router.post("/v1/reconciliations")
def api_compare_sources(body: CompareSourcesRequest) -> dict:
    left_path, right_path = Path(body.left_parquet_uri), Path(body.right_parquet_uri)
    if not left_path.exists() or not right_path.exists():
        raise HTTPException(status_code=400, detail="parquet paths required for MVP compare")
    left = pd.read_parquet(left_path)
    right = pd.read_parquet(right_path)
    from decimal import Decimal

    result = reconcile_frames(left, right, tick_size=Decimal(str(body.tick_size)))
    return {
        "reconciliation_id": str(uuid.uuid4()),
        "instrument": body.instrument,
        "common_coverage": result["common_coverage"],
        "price_discrepancy_count": len(result["price_discrepancies"]),
        "volume_rel_diff_summary": result["volume_rel_diff"],
        "quarantine_count": len(result["quarantine"]),
        "report_uri": None,
    }
