"""Unit tests for canonical bar schema."""

from __future__ import annotations

import pandera.errors
import pytest

from tradelab.datasets.publisher import publish_canonical_dataset
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


@pytest.mark.unit
def test_tick_misalignment_quarantines_dataset(data_root, sample_bars_nt):
    import uuid

    bad = sample_bars_nt.copy()
    for column in ("open", "high", "low", "close"):
        bad.loc[0, column] = float(bad.loc[0, column]) + 0.1
    published = publish_canonical_dataset(bad, contract_id=uuid.uuid4())
    assert published["quality_status"] == "quarantine"
    assert published["quality"]["tick_violations"] == 4
    assert published["quality"]["tick_alignment_ok"] is False
