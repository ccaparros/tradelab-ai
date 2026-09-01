"""Authoritative market conventions for supported research instruments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    tick_size: float
    multiplier: float
    session_timezone: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


INSTRUMENTS: dict[str, InstrumentSpec] = {
    "MES": InstrumentSpec(
        symbol="MES",
        tick_size=0.25,
        multiplier=5.0,
        session_timezone="America/Chicago",
    ),
    "MNQ": InstrumentSpec(
        symbol="MNQ",
        tick_size=0.25,
        multiplier=2.0,
        session_timezone="America/Chicago",
    ),
}


def get_instrument_spec(symbol: str) -> InstrumentSpec:
    normalized = str(symbol).strip().upper()
    try:
        return INSTRUMENTS[normalized]
    except KeyError as exc:
        allowed = ", ".join(sorted(INSTRUMENTS))
        raise ValueError(f"unsupported instrument '{symbol}'. Allowed: {allowed}") from exc


def resolve_instrument_spec(
    dataset: dict[str, Any],
    frame: pd.DataFrame,
) -> InstrumentSpec:
    """Resolve one instrument and reject catalog/data disagreements."""
    catalog_symbol = str(dataset.get("instrument") or "").strip().upper()
    frame_symbols: set[str] = set()
    if "instrument" in frame.columns:
        frame_symbols = {
            str(value).strip().upper()
            for value in frame["instrument"].dropna().unique()
            if str(value).strip()
        }
    if len(frame_symbols) > 1:
        raise ValueError(f"dataset contains multiple instruments: {sorted(frame_symbols)}")
    frame_symbol = next(iter(frame_symbols), "")
    if catalog_symbol and frame_symbol and catalog_symbol != frame_symbol:
        raise ValueError(
            f"dataset instrument mismatch: catalog={catalog_symbol} parquet={frame_symbol}"
        )
    symbol = catalog_symbol or frame_symbol
    if not symbol:
        raise ValueError("dataset instrument is missing from catalog and parquet")
    return get_instrument_spec(symbol)
