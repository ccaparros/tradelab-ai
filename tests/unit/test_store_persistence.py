"""File-backed store durability tests."""

from __future__ import annotations

import json

import pytest

import tradelab.ingestion.storage as storage
from tradelab.datasets.store import get_dataset, upsert_dataset


@pytest.mark.unit
def test_failed_atomic_replace_preserves_previous_store(data_root, monkeypatch):
    original = {"dataset_id": "dataset-1", "quality_status": "usable"}
    upsert_dataset(original)

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    monkeypatch.setattr(storage.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        upsert_dataset({**original, "quality_status": "quarantine"})

    persisted = json.loads((data_root / "store.json").read_text(encoding="utf-8"))
    assert persisted["datasets"]["dataset-1"] == original
    assert get_dataset("dataset-1") == original
