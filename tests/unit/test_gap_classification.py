"""Gap classification coverage tests."""

from __future__ import annotations

import pytest

from tradelab.quality.gaps import GAP_CLASSES, detect_gaps


@pytest.mark.unit
def test_gaps_fully_classified(sample_bars_nt):
    gaps = detect_gaps(sample_bars_nt, bar_minutes=5)
    assert gaps, "fixture should include at least one gap"
    for g in gaps:
        assert g["classification"] in GAP_CLASSES
