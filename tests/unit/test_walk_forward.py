"""Walk-forward window causality and robustness payloads."""

from __future__ import annotations

import pandas as pd
import pytest

from tradelab.backtesting.splits import expanding_walk_forward_windows
from tradelab.backtesting.robustness import neighbor_parameter_sets, run_session_long_baseline


def _sessions(n: int) -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2026-06-01 13:30:00", tz="UTC")
    for d in range(n):
        day = start + pd.Timedelta(days=d)
        for i in range(3):
            px = 5000.0 + d + i * 0.25
            rows.append(
                {
                    "timestamp_utc": day + pd.Timedelta(minutes=5 * i),
                    "open": px,
                    "high": px + 0.5,
                    "low": px - 0.5,
                    "close": px + 0.1,
                    "volume": 100,
                    "session_date": day.strftime("%Y-%m-%d"),
                }
            )
    return pd.DataFrame(rows)


@pytest.mark.unit
def test_walk_forward_windows_are_causal():
    df = _sessions(12)
    windows = expanding_walk_forward_windows(df, n_folds=3, min_train_sessions=5)
    assert len(windows) >= 2
    for w in windows:
        assert w["train_end"] < w["test_start"]
        train_max = pd.to_datetime(w["train_df"]["timestamp_utc"], utc=True).max()
        test_min = pd.to_datetime(w["test_df"]["timestamp_utc"], utc=True).min()
        assert train_max < test_min


@pytest.mark.unit
def test_walk_forward_skips_tiny_frames():
    df = _sessions(3)
    assert expanding_walk_forward_windows(df, n_folds=3, min_train_sessions=5) == []


@pytest.mark.unit
def test_baseline_one_trade_per_session():
    df = _sessions(4)
    blob = run_session_long_baseline(df, commission_per_side=0.62, slippage_ticks=1)
    assert blob["trade_count"] == 4
    assert blob["kind"] == "session_long"


@pytest.mark.unit
def test_orb_neighbors_include_alternate_opening_range():
    variants = neighbor_parameter_sets(
        "orb_atr_intraday",
        {
            "opening_range_minutes": 15,
            "atr_period": 14,
            "atr_filter_mult": 1.0,
            "stop_risk_mult": 1.0,
            "target_risk_mult": 2.0,
            "session_exit_time": "20:00",
            "commission_per_side": 0.62,
            "slippage_ticks": 1,
        },
    )
    ors = {v["opening_range_minutes"] for v in variants}
    assert 30 in ors
