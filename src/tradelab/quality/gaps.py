"""Gap detection and mandatory classification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

GAP_CLASSES = ("session_closed", "maintenance", "unavailable", "error")


def classify_gap(start: datetime, end: datetime, *, expected_freq: timedelta) -> str:
    """Heuristic classifier for MVP fixtures (always returns a valid class)."""
    duration = end - start
    # Overnight / weekend sized gaps → session_closed
    if duration >= timedelta(hours=6):
        return "session_closed"
    # Short unexpected hole → unavailable (data missing)
    if duration <= expected_freq * 3:
        return "unavailable"
    return "maintenance"


def detect_gaps(df: pd.DataFrame, *, bar_minutes: int = 5) -> list[dict[str, Any]]:
    if df.empty:
        return []
    ts = pd.to_datetime(df["timestamp_utc"], utc=True).sort_values()
    expected = timedelta(minutes=bar_minutes)
    gaps: list[dict[str, Any]] = []
    for prev, curr in zip(ts.iloc[:-1], ts.iloc[1:], strict=False):
        delta = curr.to_pydatetime() - prev.to_pydatetime()
        if delta > expected + timedelta(seconds=1):
            start = prev.to_pydatetime().astimezone(UTC)
            end = curr.to_pydatetime().astimezone(UTC)
            gaps.append(
                {
                    "start_utc": start.isoformat(),
                    "end_utc": end.isoformat(),
                    "classification": classify_gap(start, end, expected_freq=expected),
                }
            )
    # Constitution: 100% classified
    for g in gaps:
        assert g["classification"] in GAP_CLASSES
    return gaps
