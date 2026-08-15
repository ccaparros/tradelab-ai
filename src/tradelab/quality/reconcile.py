"""Dual-source reconciliation with quarantine (no silent merge)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd


def reconcile_frames(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    tick_size: Decimal,
    left_label: str = "ninjatrader",
    right_label: str = "ibkr",
) -> dict[str, Any]:
    """Compare OHLC on common timestamps; quarantine price conflicts beyond 1 tick."""
    if left.empty or right.empty:
        return {
            "common_coverage": {"timestamps": 0},
            "price_discrepancies": [],
            "volume_rel_diff": {"mean_abs_pct": None},
            "quarantine": [],
        }

    l = left.set_index("timestamp_utc")
    r = right.set_index("timestamp_utc")
    common = l.index.intersection(r.index)
    tick = float(tick_size)
    discrepancies: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    vol_diffs: list[float] = []

    for ts in common:
        row_l = l.loc[ts]
        row_r = r.loc[ts]
        for field in ("open", "high", "low", "close"):
            a = float(row_l[field])
            b = float(row_r[field])
            if abs(a - b) > tick + 1e-9:
                item = {
                    "timestamp_utc": pd.Timestamp(ts).isoformat(),
                    "field": field,
                    "source_a_value": a,
                    "source_b_value": b,
                    "reason": f"{field} differs by more than 1 tick between {left_label} and {right_label}",
                }
                discrepancies.append(item)
                quarantine.append(item)
        va, vb = float(row_l["volume"]), float(row_r["volume"])
        if max(va, vb) > 0:
            vol_diffs.append(abs(va - vb) / max(va, vb))

    return {
        "common_coverage": {
            "timestamps": int(len(common)),
            "left_only": int(len(l.index.difference(r.index))),
            "right_only": int(len(r.index.difference(l.index))),
        },
        "price_discrepancies": discrepancies,
        "volume_rel_diff": {
            "mean_abs_pct": (sum(vol_diffs) / len(vol_diffs)) if vol_diffs else 0.0,
            "note": "Volume differences are informative; not automatic dataset failure",
        },
        "quarantine": quarantine,
    }
