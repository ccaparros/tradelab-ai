"""Ensure OpenAPI has no order/trading routes."""

from __future__ import annotations

import pytest

from apps.api.main import app


@pytest.mark.contract
def test_no_trading_routes():
    paths = app.openapi()["paths"]
    joined = " ".join(paths.keys()).lower()
    for banned in ("order", "orders", "submit_trade", "place_order"):
        assert banned not in joined
