"""VWAP fade strategy unit tests."""

from __future__ import annotations

import pandas as pd
import pytest

from tradelab.backtesting.strategies.registry import get_strategy, list_strategy_specs
from tradelab.backtesting.strategies.vwap_fade import VwapFadeParams, run_vwap_fade


@pytest.mark.unit
def test_registry_has_two_strategies():
    ids = {s["strategy_id"] for s in list_strategy_specs()}
    assert "orb_atr_intraday" in ids
    assert "vwap_fade_intraday" in ids


@pytest.mark.unit
def test_unknown_strategy_rejected():
    with pytest.raises(ValueError, match="unsupported strategy"):
        get_strategy("place_order")


def _ranging_session() -> pd.DataFrame:
    """Synthetic RTH-like 5m bars that stretch above VWAP then revert."""
    rows = []
    price = 5000.0
    ts = pd.Timestamp("2026-06-02 13:30:00", tz="UTC")
    for i in range(48):
        if 12 <= i < 20:
            price += 1.5
        elif i >= 20:
            price -= 0.8
        high = price + 0.5
        low = price - 0.5
        rows.append(
            {
                "timestamp_utc": ts + pd.Timedelta(minutes=5 * i),
                "open": price,
                "high": high,
                "low": low,
                "close": price + 0.1,
                "volume": 1000 + i,
            }
        )
    return pd.DataFrame(rows)


@pytest.mark.unit
def test_vwap_fade_takes_mean_reversion_trade():
    fills = run_vwap_fade(
        _ranging_session(),
        VwapFadeParams(
            warmup_bars=8,
            atr_period=5,
            extension_atr=0.3,
            max_extension_atr=8.0,
            stop_atr_mult=3.0,
            session_exit_time="20:00",
            commission_per_side=0.62,
            slippage_ticks=1,
        ),
    )
    assert fills
    assert all(t.exit_reason in {"target", "stop", "session_exit"} for t in fills)
    assert len({t.session_date for t in fills}) == 1


@pytest.mark.unit
def test_vwap_fade_is_deterministic():
    df = _ranging_session()
    params = VwapFadeParams(warmup_bars=8, atr_period=5, extension_atr=0.3, max_extension_atr=8.0)
    a = run_vwap_fade(df, params)
    b = run_vwap_fade(df, params)
    assert [(t.entry_ts, t.exit_ts, t.pnl_net) for t in a] == [
        (t.entry_ts, t.exit_ts, t.pnl_net) for t in b
    ]
