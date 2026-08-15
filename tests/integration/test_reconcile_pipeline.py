"""Integration: reconcile two fixture sources."""

from __future__ import annotations

from decimal import Decimal

import pytest

from tradelab.quality.reconcile import reconcile_frames


@pytest.mark.integration
def test_reconcile_quarantines_price_conflict(sample_bars_nt, sample_bars_ibkr):
    result = reconcile_frames(sample_bars_nt, sample_bars_ibkr, tick_size=Decimal("0.25"))
    assert result["common_coverage"]["timestamps"] > 0
    assert result["quarantine"], "expected at least one quarantined price discrepancy"
