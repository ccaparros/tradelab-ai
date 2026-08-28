"""Nearest-expiry stitch for IBKR quarterly 5m history."""

from __future__ import annotations

import pandas as pd

from connectors.ibkr.download_history import stitch_nearest_expiry


def test_stitch_prefers_nearer_expiry_on_overlap() -> None:
    ts = pd.Timestamp("2026-05-01T14:00:00Z")
    df = pd.DataFrame(
        [
            {"timestamp_utc": ts, "contract_month": "202609", "close": 2.0},
            {"timestamp_utc": ts, "contract_month": "202606", "close": 1.0},
        ]
    )
    out = stitch_nearest_expiry(df)
    assert len(out) == 1
    assert out.iloc[0]["contract_month"] == "202606"
    assert out.iloc[0]["close"] == 1.0
