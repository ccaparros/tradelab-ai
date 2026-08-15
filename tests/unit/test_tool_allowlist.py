"""Tool allowlist / no trading tools."""

from __future__ import annotations

import pytest

from tradelab.agents.tools import ALLOWED_TOOLS, FORBIDDEN_TOOLS, assert_tool_allowed


@pytest.mark.unit
def test_forbidden_tools_rejected():
    for name in FORBIDDEN_TOOLS:
        with pytest.raises(PermissionError):
            assert_tool_allowed(name)


@pytest.mark.unit
def test_allowed_tools_ok():
    for name in ALLOWED_TOOLS:
        assert_tool_allowed(name)


@pytest.mark.unit
def test_no_order_substring_in_allowlist():
    for name in ALLOWED_TOOLS:
        assert "order" not in name.lower()
