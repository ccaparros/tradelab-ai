"""Deterministic ORB+ATR event-driven backtest on 5m bars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any

import pandas as pd

from tradelab.backtesting.strategies.orb_atr import OrbAtrParams


@dataclass
class TradeFill:
    session_date: str
    side: str
    entry_ts: str
    exit_ts: str
    entry_price: float
    exit_price: float
    qty: int
    pnl_gross: float
    pnl_net: float
    exit_reason: str
    split_label: str


def _parse_hhmm(value: str) -> time:
    hh, mm = value.split(":")
    return time(int(hh), int(mm))


def _true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def _shifted_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """ATR using only past bars (shift 1) — anti look-ahead."""
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    closes = df["close"].astype(float)
    prev_close = closes.shift(1)
    tr = pd.concat(
        [
            highs - lows,
            (highs - prev_close).abs(),
            (lows - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period, min_periods=period).mean()
    return atr.shift(1)  # decision-time ATR must be fully known


def _shifted_session_vwap(session_df: pd.DataFrame) -> pd.Series:
    """Session VWAP known at decision time (shifted 1 bar)."""
    typical = (
        session_df["high"].astype(float)
        + session_df["low"].astype(float)
        + session_df["close"].astype(float)
    ) / 3.0
    vol = session_df["volume"].astype(float).clip(lower=1.0)
    cum_pv = (typical * vol).cumsum()
    cum_v = vol.cumsum()
    vwap = cum_pv / cum_v
    return vwap.shift(1)


def _close_trade(
    *,
    session_date: str,
    position: dict[str, Any],
    ts: datetime,
    exit_price: float,
    reason: str,
    split_label: str,
    commission_per_side: float,
    multiplier: float,
    qty: int = 1,
) -> TradeFill:
    if position["side"] == "long":
        pnl_gross = (exit_price - position["entry_price"]) * multiplier * qty
    else:
        pnl_gross = (position["entry_price"] - exit_price) * multiplier * qty
    costs = 2 * commission_per_side
    return TradeFill(
        session_date=str(session_date),
        side=position["side"],
        entry_ts=position["entry_ts"],
        exit_ts=ts.isoformat(),
        entry_price=float(position["entry_price"]),
        exit_price=float(exit_price),
        qty=qty,
        pnl_gross=float(pnl_gross),
        pnl_net=float(pnl_gross - costs),
        exit_reason=reason,
        split_label=split_label,
    )


def run_orb_atr(
    df: pd.DataFrame,
    params: OrbAtrParams,
    *,
    tick_size: float = 0.25,
    multiplier: float = 5.0,
    split_label: str = "train",
) -> list[TradeFill]:
    if df.empty:
        return []

    work = df.copy()
    work["timestamp_utc"] = pd.to_datetime(work["timestamp_utc"], utc=True)
    work = work.sort_values("timestamp_utc").reset_index(drop=True)
    work["atr"] = _shifted_atr(work, params.atr_period)
    work["session_date"] = work["timestamp_utc"].dt.strftime("%Y-%m-%d")

    exit_t = _parse_hhmm(params.session_exit_time)
    slip = params.slippage_ticks * tick_size
    trades: list[TradeFill] = []

    for session, session_df in work.groupby("session_date", sort=True):
        session_df = session_df.reset_index(drop=True)
        if len(session_df) < 2:
            continue
        orb_bars = max(1, params.opening_range_minutes // 5)
        if len(session_df) <= orb_bars:
            continue
        opening = session_df.iloc[:orb_bars]
        orb_high = float(opening["high"].max())
        orb_low = float(opening["low"].min())
        orb_range = orb_high - orb_low
        if orb_range <= 0:
            continue

        entries = 0
        position: dict[str, Any] | None = None

        for i in range(orb_bars, len(session_df)):
            row = session_df.iloc[i]
            ts: datetime = row["timestamp_utc"].to_pydatetime()
            local_t = ts.timetz().replace(tzinfo=None)
            atr = row["atr"]
            if pd.isna(atr):
                continue

            # Volatility filter: require opening range >= atr * mult (known atr only)
            if orb_range < float(atr) * params.atr_filter_mult:
                continue

            price_open = float(row["open"])
            price_high = float(row["high"])
            price_low = float(row["low"])
            price_close = float(row["close"])

            if position is None and entries < params.max_entries_per_session:
                if price_high >= orb_high:
                    entry = orb_high + slip
                    risk = orb_range
                    position = {
                        "side": "long",
                        "entry_ts": ts.isoformat(),
                        "entry_price": entry,
                        "stop": entry - params.stop_risk_mult * risk,
                        "target": entry + params.target_risk_mult * risk,
                    }
                    entries += 1
                elif price_low <= orb_low:
                    entry = orb_low - slip
                    risk = orb_range
                    position = {
                        "side": "short",
                        "entry_ts": ts.isoformat(),
                        "entry_price": entry,
                        "stop": entry + params.stop_risk_mult * risk,
                        "target": entry - params.target_risk_mult * risk,
                    }
                    entries += 1

            if position is not None:
                exit_price = None
                reason = None
                if position["side"] == "long":
                    if price_low <= position["stop"]:
                        exit_price = position["stop"] - slip
                        reason = "stop"
                    elif price_high >= position["target"]:
                        exit_price = position["target"] - slip
                        reason = "target"
                else:
                    if price_high >= position["stop"]:
                        exit_price = position["stop"] + slip
                        reason = "stop"
                    elif price_low <= position["target"]:
                        exit_price = position["target"] + slip
                        reason = "target"

                if exit_price is None and local_t >= exit_t:
                    exit_price = price_close
                    reason = "session_exit"

                if exit_price is not None and reason is not None:
                    qty = 1
                    if position["side"] == "long":
                        pnl_gross = (exit_price - position["entry_price"]) * multiplier * qty
                    else:
                        pnl_gross = (position["entry_price"] - exit_price) * multiplier * qty
                    costs = 2 * params.commission_per_side
                    trades.append(
                        TradeFill(
                            session_date=str(session),
                            side=position["side"],
                            entry_ts=position["entry_ts"],
                            exit_ts=ts.isoformat(),
                            entry_price=float(position["entry_price"]),
                            exit_price=float(exit_price),
                            qty=qty,
                            pnl_gross=float(pnl_gross),
                            pnl_net=float(pnl_gross - costs),
                            exit_reason=reason,
                            split_label=split_label,
                        )
                    )
                    position = None

        # Force flatten at end of session data if still open
        if position is not None:
            row = session_df.iloc[-1]
            ts = row["timestamp_utc"].to_pydatetime()
            exit_price = float(row["close"])
            qty = 1
            if position["side"] == "long":
                pnl_gross = (exit_price - position["entry_price"]) * multiplier * qty
            else:
                pnl_gross = (position["entry_price"] - exit_price) * multiplier * qty
            costs = 2 * params.commission_per_side
            trades.append(
                TradeFill(
                    session_date=str(session),
                    side=position["side"],
                    entry_ts=position["entry_ts"],
                    exit_ts=ts.isoformat(),
                    entry_price=float(position["entry_price"]),
                    exit_price=exit_price,
                    qty=qty,
                    pnl_gross=float(pnl_gross),
                    pnl_net=float(pnl_gross - costs),
                    exit_reason="session_exit",
                    split_label=split_label,
                )
            )

    return trades
