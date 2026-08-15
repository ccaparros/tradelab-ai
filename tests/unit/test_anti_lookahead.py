"""Anti look-ahead ATR shift tests."""

from __future__ import annotations

import pytest

from tradelab.backtesting.engine import _shifted_atr


@pytest.mark.unit
def test_atr_is_shifted(sample_bars_nt):
    atr = _shifted_atr(sample_bars_nt, period=5)
    # First period+1 values should be NaN due to rolling+shift
    assert atr.iloc[:5].isna().all()
    # ATR at i must not equal unshifted rolling mean at i (when both exist)
    highs = sample_bars_nt["high"].astype(float)
    lows = sample_bars_nt["low"].astype(float)
    closes = sample_bars_nt["close"].astype(float)
    prev = closes.shift(1)
    import pandas as pd

    tr = pd.concat([highs - lows, (highs - prev).abs(), (lows - prev).abs()], axis=1).max(axis=1)
    unshifted = tr.rolling(5, min_periods=5).mean()
    # Where both valid, shifted value equals previous unshifted
    both = atr.notna() & unshifted.shift(1).notna()
    assert (atr[both] == unshifted.shift(1)[both]).all()
