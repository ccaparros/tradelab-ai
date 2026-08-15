"""Unit tests for canonical bar schema."""

from __future__ import annotations

import pandas as pd
import pandera.errors
import pytest

from tradelab.ingestion.schemas import validate_bars


@pytest.mark.unit
def test_valid_bars_pass(sample_bars_nt):
    out = validate_bars(sample_bars_nt)
    assert len(out) == len(sample_bars_nt)


@pytest.mark.unit
def test_invalid_ohlc_rejected(sample_bars_nt):
    bad = sample_bars_nt.copy()
    bad.loc[0, "low"] = float(bad.loc[0, "high"]) + 10
    with pytest.raises((pandera.errors.SchemaError, pandera.errors.SchemaErrors)):
        validate_bars(bad)
