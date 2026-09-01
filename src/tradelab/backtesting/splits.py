"""Temporal train/validation/holdout splits with holdout guard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from tradelab.backtesting.sessions import with_session_date


@dataclass
class SplitSpec:
    train_end: str
    validation_end: str
    holdout_end: str | None = None


def _utc_timestamp(value: str | pd.Timestamp) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def apply_temporal_split(
    df: pd.DataFrame,
    spec: SplitSpec,
    *,
    session_timezone: str = "America/Chicago",
) -> dict[str, pd.DataFrame]:
    work = with_session_date(df, session_timezone)
    ts = work["timestamp_utc"]
    train_end = _utc_timestamp(spec.train_end)
    val_end = _utc_timestamp(spec.validation_end)
    holdout_end = _utc_timestamp(spec.holdout_end) if spec.holdout_end else ts.max()
    if not train_end <= val_end <= holdout_end:
        raise ValueError("split boundaries must satisfy train_end <= validation_end <= holdout_end")

    parts = {
        "train": work.loc[ts <= train_end].copy(),
        "validation": work.loc[(ts > train_end) & (ts <= val_end)].copy(),
        "holdout": work.loc[(ts > val_end) & (ts <= holdout_end)].copy(),
    }
    session_sets = {
        label: set(part["session_date"].astype(str).unique()) for label, part in parts.items()
    }
    if (
        session_sets["train"] & session_sets["validation"]
        or session_sets["train"] & session_sets["holdout"]
        or session_sets["validation"] & session_sets["holdout"]
    ):
        raise ValueError("split boundary cuts through an exchange session")
    return parts


def default_split_from_frame(
    df: pd.DataFrame,
    *,
    session_timezone: str = "America/Chicago",
) -> SplitSpec:
    if df.empty:
        raise ValueError("cannot split an empty dataset")
    work = with_session_date(df, session_timezone).sort_values("timestamp_utc")
    session_ends = work.groupby("session_date", sort=False)["timestamp_utc"].max()
    n_sessions = len(session_ends)
    if n_sessions == 1:
        only_end = session_ends.iloc[0]
        return SplitSpec(
            train_end=str(only_end),
            validation_end=str(only_end),
            holdout_end=str(only_end),
        )
    if n_sessions == 2:
        return SplitSpec(
            train_end=str(session_ends.iloc[0]),
            validation_end=str(session_ends.iloc[1]),
            holdout_end=str(session_ends.iloc[1]),
        )
    train_sessions = max(1, int(n_sessions * 0.6))
    validation_sessions = max(train_sessions + 1, int(n_sessions * 0.8))
    validation_sessions = min(validation_sessions, n_sessions - 1)
    return SplitSpec(
        train_end=str(session_ends.iloc[train_sessions - 1]),
        validation_end=str(session_ends.iloc[validation_sessions - 1]),
        holdout_end=str(session_ends.iloc[-1]),
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
    session_timezone: str = "America/Chicago",
) -> list[dict[str, Any]]:
    """Causal expanding windows. Train sessions always precede test sessions."""
    if df.empty:
        return []
    work = with_session_date(df, session_timezone)
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
