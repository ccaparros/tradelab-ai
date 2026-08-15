"""Demo happy path smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

from tradelab.datasets.load_demo import main as load_demo


@pytest.mark.integration
def test_demo_happy_path(client, data_root, monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    load_demo()
    listed = client.get("/v1/datasets")
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert items
    ds = items[0]
    # usable or quarantine still listed
    assert "dataset_id" in ds
