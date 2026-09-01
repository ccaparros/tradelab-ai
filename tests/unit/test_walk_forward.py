"""Walk-forward window causality and robustness payloads."""

from __future__ import annotations

import pandas as pd
import pytest

from tradelab.backtesting.robustness import neighbor_parameter_sets, run_session_long_baseline
from tradelab.backtesting.sessions import exchange_local_time, with_session_date
from tradelab.backtesting.splits import (
    apply_temporal_split,
    default_split_from_frame,
    expanding_walk_forward_windows,
)


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


@pytest.mark.unit
def test_default_split_never_divides_an_exchange_session():
    frame = _sessions(10)
    split = default_split_from_frame(frame)
    parts = apply_temporal_split(frame, split)
    session_sets = {label: set(part["session_date"].unique()) for label, part in parts.items()}
    assert len(session_sets["train"]) == 6
    assert len(session_sets["validation"]) == 2
    assert len(session_sets["holdout"]) == 2
    assert session_sets["train"].isdisjoint(session_sets["validation"])
    assert session_sets["train"].isdisjoint(session_sets["holdout"])
    assert session_sets["validation"].isdisjoint(session_sets["holdout"])


@pytest.mark.unit
def test_session_labels_and_clock_follow_chicago_dst():
    frame = pd.DataFrame(
        {
            "timestamp_utc": [
                "2026-06-04T00:30:00Z",
                "2026-06-04T01:00:00Z",
            ]
        }
    )
    labeled = with_session_date(frame, "America/Chicago")
    assert set(labeled["session_date"]) == {"2026-06-03"}

    winter = pd.Timestamp("2026-01-15T20:00:00Z").to_pydatetime()
    summer = pd.Timestamp("2026-07-15T20:00:00Z").to_pydatetime()
    assert exchange_local_time(winter, "America/Chicago").hour == 14
    assert exchange_local_time(summer, "America/Chicago").hour == 15
