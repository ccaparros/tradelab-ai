"""Publish canonical datasets from validated bars (no silent merge)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from tradelab.ingestion.storage import write_immutable_parquet
from tradelab.instruments import get_instrument_spec
from tradelab.observability.settings import get_settings
from tradelab.quality.validators import build_quality_report


def publish_canonical_dataset(
    df: pd.DataFrame,
    *,
    contract_id: uuid.UUID,
    preferred_source_id: str | None = None,
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate, write immutable parquet, return dataset metadata + quality."""
    tick_size: Decimal | None = None
    if not df.empty:
        if "instrument" not in df.columns:
            raise ValueError("canonical frame is missing instrument")
        symbols = {str(value).strip().upper() for value in df["instrument"].dropna().unique()}
        if len(symbols) != 1:
            raise ValueError(f"canonical frame must contain one instrument, got {sorted(symbols)}")
        tick_size = Decimal(str(get_instrument_spec(next(iter(symbols))).tick_size))
    report = build_quality_report(df, tick_size=tick_size)
    if report["duplicate_count"] > 0:
        # Never publish duplicates into canonical usable set
        report["quality_status"] = "quarantine"

    settings = get_settings()
    dataset_id = uuid.uuid4()
    out_dir = Path(settings.data_root) / "canonical" / str(dataset_id)
    out_path = out_dir / "bars.parquet"
    checksum = write_immutable_parquet(df.copy(), out_path) if not df.empty else "empty"

    coverage_start = df["timestamp_utc"].min() if not df.empty else None
    coverage_end = df["timestamp_utc"].max() if not df.empty else None

    return {
        "dataset_id": dataset_id,
        "contract_id": contract_id,
        "storage_uri": str(out_path),
        "content_checksum": checksum,
        "quality_status": report["quality_status"],
        "quality": report,
        "coverage_start_utc": coverage_start,
        "coverage_end_utc": coverage_end,
        "lineage": lineage or {},
        "preferred_source_id": preferred_source_id,
    }
