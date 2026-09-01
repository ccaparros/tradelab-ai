"""Instrument economics must flow into monetary backtest results."""

from __future__ import annotations

import pandas as pd
import pytest

from tradelab.backtesting.robustness import run_session_long_baseline
from tradelab.instruments import get_instrument_spec, resolve_instrument_spec


@pytest.mark.unit
def test_mes_and_mnq_have_distinct_contract_multipliers() -> None:
    assert get_instrument_spec("MES").multiplier == 5.0
    assert get_instrument_spec("MNQ").multiplier == 2.0


@pytest.mark.unit
def test_multiplier_changes_monetary_baseline() -> None:
    frame = pd.DataFrame(
        [
            {
                "timestamp_utc": "2026-06-01T13:30:00Z",
                "session_date": "2026-06-01",
                "open": 100.0,
                "close": 100.0,
            },
            {
                "timestamp_utc": "2026-06-01T20:00:00Z",
                "session_date": "2026-06-01",
                "open": 102.0,
                "close": 102.0,
            },
        ]
    )
    mes = run_session_long_baseline(
        frame,
        commission_per_side=0,
        slippage_ticks=0,
        multiplier=get_instrument_spec("MES").multiplier,
    )
    mnq = run_session_long_baseline(
        frame,
        commission_per_side=0,
        slippage_ticks=0,
        multiplier=get_instrument_spec("MNQ").multiplier,
    )
    assert mes["net_pnl"] == 10.0
    assert mnq["net_pnl"] == 4.0


@pytest.mark.unit
def test_catalog_and_parquet_instrument_must_match() -> None:
    frame = pd.DataFrame({"instrument": ["MES"]})
    with pytest.raises(ValueError, match="instrument mismatch"):
        resolve_instrument_spec({"instrument": "MNQ"}, frame)
