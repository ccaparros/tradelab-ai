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


def expanding_walk_forward_windows(
    df: pd.DataFrame,
    *,
    n_folds: int = 3,
    min_train_sessions: int = 5,
) -> list[dict[str, Any]]:
    """Causal expanding windows. Train sessions always precede test sessions."""
    if df.empty:
        return []
    work = df.copy()
    ts = pd.to_datetime(work["timestamp_utc"], utc=True)
    if "session_date" not in work.columns:
        work["session_date"] = ts.dt.strftime("%Y-%m-%d")
    sessions = sorted(work["session_date"].astype(str).unique())
    n = len(sessions)
    if n < min_train_sessions + 1:
        return []
    remain = n - min_train_sessions
    n_folds = max(1, min(n_folds, remain))
    fold_size = max(1, remain // n_folds)
    windows: list[dict[str, Any]] = []
    for i in range(n_folds):
        test_start = min_train_sessions + i * fold_size
        test_end = n if i == n_folds - 1 else min(n, test_start + fold_size)
        if test_start >= n or test_start >= test_end:
            break
        train_sess = sessions[:test_start]
        test_sess = sessions[test_start:test_end]
        train_df = work[work["session_date"].astype(str).isin(train_sess)].copy()
        test_df = work[work["session_date"].astype(str).isin(test_sess)].copy()
        if train_df.empty or test_df.empty:
            continue
        windows.append(
            {
                "fold": i + 1,
                "train_start": train_sess[0],
                "train_end": train_sess[-1],
                "test_start": test_sess[0],
                "test_end": test_sess[-1],
                "train_sessions": len(train_sess),
                "test_sessions": len(test_sess),
                "train_df": train_df,
                "test_df": test_df,
            }
        )
    return windows
