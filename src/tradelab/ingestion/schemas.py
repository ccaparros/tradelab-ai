"""Canonical bar schema (Pandera) and validation helpers."""

from __future__ import annotations

from decimal import Decimal

import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema


def _positive(series):
    return series > 0


CanonicalBarSchema = DataFrameSchema(
    {
        "source": Column(str),
        "instrument": Column(str),
        "contract_month": Column(str),
        "exchange": Column(str),
        "bar_size": Column(str),
        "timestamp_utc": Column("datetime64[ns, UTC]"),
        "session_date": Column(str),
        "open": Column(float, Check(_positive)),
        "high": Column(float, Check(_positive)),
        "low": Column(float, Check(_positive)),
        "close": Column(float, Check(_positive)),
        "volume": Column(float, Check(lambda s: s >= 0)),
        "rth": Column(bool),
        "timezone_original": Column(str),
        "ingestion_run_id": Column(str),
        "raw_checksum": Column(str),
    },
    checks=[
        Check(lambda df: (df["low"] <= df["open"]) & (df["open"] <= df["high"]), error="open not in [low,high]"),
        Check(lambda df: (df["low"] <= df["close"]) & (df["close"] <= df["high"]), error="close not in [low,high]"),
        Check(lambda df: df["timestamp_utc"].is_monotonic_increasing, error="timestamps not monotonic"),
    ],
    coerce=True,
    strict=False,
)


def assert_tick_aligned(prices: list[float], tick_size: Decimal) -> None:
    tick = float(tick_size)
    for p in prices:
        # Allow float noise within 1e-8 of a tick multiple
        steps = p / tick
        if abs(steps - round(steps)) > 1e-6:
            raise ValueError(f"price {p} not aligned to tick {tick}")


def validate_bars(df):
    return CanonicalBarSchema.validate(df, lazy=True)
