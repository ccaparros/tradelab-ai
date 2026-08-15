"""Temporal train/validation/holdout splits with holdout guard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class SplitSpec:
    train_end: str
    validation_end: str
    holdout_end: str | None = None


def apply_temporal_split(df: pd.DataFrame, spec: SplitSpec) -> dict[str, pd.DataFrame]:
    ts = pd.to_datetime(df["timestamp_utc"], utc=True)
    train_end = pd.Timestamp(spec.train_end, tz="UTC")
    val_end = pd.Timestamp(spec.validation_end, tz="UTC")
    holdout_end = pd.Timestamp(spec.holdout_end, tz="UTC") if spec.holdout_end else ts.max()

    return {
        "train": df.loc[ts <= train_end].copy(),
        "validation": df.loc[(ts > train_end) & (ts <= val_end)].copy(),
        "holdout": df.loc[(ts > val_end) & (ts <= holdout_end)].copy(),
    }


def assert_holdout_policy(*, consume_holdout: bool, selecting_parameters: bool) -> None:
    if selecting_parameters and consume_holdout:
        raise PermissionError("policy_violation: holdout cannot be consumed during parameter selection")


def default_split_from_frame(df: pd.DataFrame) -> SplitSpec:
    ts = pd.to_datetime(df["timestamp_utc"], utc=True).sort_values()
    if len(ts) < 3:
        mid = ts.iloc[-1]
        return SplitSpec(train_end=str(mid), validation_end=str(mid), holdout_end=str(mid))
    n = len(ts)
    i_train = max(0, int(n * 0.6) - 1)
    i_val = max(i_train + 1, int(n * 0.8) - 1)
    return SplitSpec(
        train_end=str(ts.iloc[i_train]),
        validation_end=str(ts.iloc[i_val]),
        holdout_end=str(ts.iloc[-1]),
    )


def split_spec_to_dict(spec: SplitSpec) -> dict[str, Any]:
    return {
        "train_end": spec.train_end,
        "validation_end": spec.validation_end,
        "holdout_end": spec.holdout_end,
    }
