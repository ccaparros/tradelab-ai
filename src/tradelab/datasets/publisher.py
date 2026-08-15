"""Publish canonical datasets from validated bars (no silent merge)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pandas as pd

from tradelab.ingestion.storage import write_immutable_parquet
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
    report = build_quality_report(df)
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
