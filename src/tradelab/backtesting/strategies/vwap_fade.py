"""Intraday fade toward session VWAP (mean reversion), anti look-ahead."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from tradelab.backtesting.engine import (
    TradeFill,
    _close_trade,
    _parse_hhmm,
    _shifted_atr,
    _shifted_session_vwap,
)
from tradelab.backtesting.sessions import exchange_local_time, with_session_date

STRATEGY_ID = "vwap_fade_intraday"
STRATEGY_VERSION = "0.1.0"


class VwapFadeParams(BaseModel):
    warmup_bars: int = Field(default=8, ge=4, le=36)
    atr_period: int = Field(default=14, ge=2)
    extension_atr: float = Field(default=0.7, gt=0)
    max_extension_atr: float = Field(default=2.4, gt=0)
    stop_atr_mult: float = Field(default=0.8, gt=0)
    session_exit_time: str = Field(default="14:55")
    commission_per_side: float = Field(default=0.62, ge=0)
    slippage_ticks: int = Field(default=1, ge=0)
    max_entries_per_session: int = Field(default=1)

    @field_validator("max_entries_per_session")
    @classmethod
    def _one_entry(cls, v: int) -> int:
        if v != 1:
            raise ValueError("MVP allows exactly 1 entry per session")
        return v

    @field_validator("max_extension_atr")
    @classmethod
    def _max_gt_min(cls, v: float, info) -> float:
        ext = info.data.get("extension_atr")
        if ext is not None and v <= ext:
            raise ValueError("max_extension_atr must be greater than extension_atr")
        return v


def allowed_parameters_schema() -> dict[str, Any]:
    return VwapFadeParams.model_json_schema()


def validate_parameters(raw: dict[str, Any]) -> VwapFadeParams:
    return VwapFadeParams.model_validate(raw)


def run_vwap_fade(
    df: pd.DataFrame,
    params: VwapFadeParams,
    *,
    tick_size: float = 0.25,
    multiplier: float = 5.0,
    session_timezone: str = "America/Chicago",
    split_label: str = "train",
) -> list[TradeFill]:
    """Fade stretched prices back to session VWAP.

    Signal uses prior-bar VWAP/ATR/close (shifted). Fill at current open ± slippage.
    Skip blow-off moves (extension > max_extension_atr) so we do not fade a trend day.
    """
    if df.empty:
        return []

    work = with_session_date(df, session_timezone)
    work = work.sort_values("timestamp_utc").reset_index(drop=True)
    work["atr"] = _shifted_atr(work, params.atr_period)

    exit_t = _parse_hhmm(params.session_exit_time)
    slip = params.slippage_ticks * tick_size
    trades: list[TradeFill] = []

    for session, session_df in work.groupby("session_date", sort=True):
        session_df = session_df.reset_index(drop=True)
        if len(session_df) <= params.warmup_bars + 1:
            continue
        session_df = session_df.copy()
        session_df["vwap"] = _shifted_session_vwap(session_df)

        entries = 0
        position: dict[str, Any] | None = None

        for i in range(params.warmup_bars, len(session_df)):
            row = session_df.iloc[i]
            ts: datetime = row["timestamp_utc"].to_pydatetime()
            local_t = exchange_local_time(ts, session_timezone)
            atr = row["atr"]
            vwap = row["vwap"]
            if pd.isna(atr) or pd.isna(vwap) or float(atr) <= 0:
                continue

            price_open = float(row["open"])
            price_high = float(row["high"])
            price_low = float(row["low"])
            price_close = float(row["close"])
            atr_f = float(atr)
            vwap_f = float(vwap)
            prev_close = float(session_df.iloc[i - 1]["close"])
            extension = (prev_close - vwap_f) / atr_f

            if position is None and entries < params.max_entries_per_session:
                if params.extension_atr <= abs(extension) <= params.max_extension_atr:
                    if extension > 0:
                        entry = price_open - slip
                        position = {
                            "side": "short",
                            "entry_ts": ts.isoformat(),
                            "entry_price": entry,
                            "stop": entry + params.stop_atr_mult * atr_f,
                            "target": vwap_f,
                        }
                        entries += 1
                    else:
                        entry = price_open + slip
                        position = {
                            "side": "long",
                            "entry_ts": ts.isoformat(),
                            "entry_price": entry,
                            "stop": entry - params.stop_atr_mult * atr_f,
                            "target": vwap_f,
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
                    trades.append(
                        _close_trade(
                            session_date=str(session),
                            position=position,
                            ts=ts,
                            exit_price=exit_price,
                            reason=reason,
                            split_label=split_label,
                            commission_per_side=params.commission_per_side,
                            multiplier=multiplier,
                        )
                    )
                    position = None

        if position is not None:
            row = session_df.iloc[-1]
            ts = row["timestamp_utc"].to_pydatetime()
            trades.append(
                _close_trade(
                    session_date=str(session),
                    position=position,
                    ts=ts,
                    exit_price=float(row["close"]),
                    reason="session_exit",
                    split_label=split_label,
                    commission_per_side=params.commission_per_side,
                    multiplier=multiplier,
                )
            )

    return trades
