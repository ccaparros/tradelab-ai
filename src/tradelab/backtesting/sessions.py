"""Session labeling and exchange-local clock helpers."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd


def with_session_date(df: pd.DataFrame, session_timezone: str) -> pd.DataFrame:
    """Return a copy labeled by exchange-local calendar date.

    The MVP consumes RTH data, so the local calendar date is the trading
    session identifier. This avoids UTC-midnight splits and follows DST.
    """
    work = df.copy()
    timestamps = pd.to_datetime(work["timestamp_utc"], utc=True)
    work["timestamp_utc"] = timestamps
    work["session_date"] = timestamps.dt.tz_convert(session_timezone).dt.strftime("%Y-%m-%d")
    return work


def exchange_local_time(timestamp: datetime, session_timezone: str) -> time:
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return timestamp.astimezone(ZoneInfo(session_timezone)).timetz().replace(tzinfo=None)
