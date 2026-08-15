"""LLM client behaves safely when API key missing."""

from __future__ import annotations

import pytest

from tradelab.agents.llm import llm_configured
from tradelab.observability.settings import get_settings


@pytest.mark.unit
def test_llm_not_configured_without_key(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    get_settings.cache_clear()
    assert llm_configured() is False
    get_settings.cache_clear()
