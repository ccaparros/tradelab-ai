"""Fixtures for evals (tests/conftest.py is not visible here)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("DATA_ROOT", str(root))
    monkeypatch.setenv("LLM_API_KEY", "")
    from tradelab.observability.settings import get_settings

    get_settings.cache_clear()
    yield root
    get_settings.cache_clear()


@pytest.fixture()
def sample_bars_nt() -> pd.DataFrame:
    path = ROOT / "data_catalog/fixtures/bars_sample/ninjatrader_mes_5m.parquet"
    return pd.read_parquet(path)
