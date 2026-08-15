"""OHLC validators and quality report builder."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pandera.errors

from tradelab.ingestion.schemas import validate_bars
from tradelab.quality.gaps import detect_gaps


def count_duplicates(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int(df.duplicated(subset=["source", "contract_month", "bar_size", "timestamp_utc"]).sum())


def count_ohlc_violations(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    bad = ~(
        (df["low"] <= df["open"])
        & (df["open"] <= df["high"])
        & (df["low"] <= df["close"])
        & (df["close"] <= df["high"])
        & (df["open"] > 0)
        & (df["high"] > 0)
        & (df["low"] > 0)
        & (df["close"] > 0)
    )
    return int(bad.sum())


def build_quality_report(df: pd.DataFrame, *, bar_minutes: int = 5) -> dict[str, Any]:
    schema_ok = True
    try:
        if not df.empty:
            validate_bars(df)
    except (pandera.errors.SchemaError, pandera.errors.SchemaErrors):
        schema_ok = False

    duplicates = count_duplicates(df)
    ohlc_violations = count_ohlc_violations(df)
    gaps = detect_gaps(df, bar_minutes=bar_minutes)

    if duplicates > 0 or ohlc_violations > 0 or not schema_ok:
        status = "quarantine"
    elif df.empty:
        status = "insufficient"
    else:
        status = "usable"

    return {
        "duplicate_count": duplicates,
        "gap_count": len(gaps),
        "gaps": gaps,
        "ohlc_violations": ohlc_violations,
        "quality_status": status,
        "schema_ok": schema_ok,
    }
