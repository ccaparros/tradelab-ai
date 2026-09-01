"""Determinism / integrity hash tests."""

from __future__ import annotations

import uuid

import pytest

from tradelab.backtesting.hashing import experiment_integrity_hash
from tradelab.backtesting.service import run_experiment
from tradelab.datasets.publisher import publish_canonical_dataset
from tradelab.datasets.store import upsert_dataset


@pytest.mark.unit
def test_hash_stable():
    a = experiment_integrity_hash(
        dataset_checksum="abc",
        code_version="0.1.0:0.1.0",
        strategy_id="orb_atr_intraday",
        parameters={"opening_range_minutes": 15},
    )
    b = experiment_integrity_hash(
        dataset_checksum="abc",
        code_version="0.1.0:0.1.0",
        strategy_id="orb_atr_intraday",
        parameters={"opening_range_minutes": 15},
    )
    assert a == b


@pytest.mark.unit
def test_hash_changes_with_split_or_holdout_scope():
    common = {
        "dataset_checksum": "abc",
        "code_version": "0.1.0:0.1.0:source",
        "strategy_id": "orb_atr_intraday",
        "parameters": {"opening_range_minutes": 15},
    }
    research = experiment_integrity_hash(
        **common,
        split_spec={"train_end": "2026-01-01", "validation_end": "2026-02-01"},
        consume_holdout=False,
    )
    other_split = experiment_integrity_hash(
        **common,
        split_spec={"train_end": "2026-01-15", "validation_end": "2026-02-01"},
        consume_holdout=False,
    )
    final = experiment_integrity_hash(
        **common,
        split_spec={"train_end": "2026-01-01", "validation_end": "2026-02-01"},
        consume_holdout=True,
    )
    assert len({research, other_split, final}) == 3


@pytest.mark.unit
def test_experiment_determinism(data_root, sample_bars_nt):
    published = publish_canonical_dataset(sample_bars_nt, contract_id=uuid.uuid4())
    record = {
        "dataset_id": str(published["dataset_id"]),
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "quality_status": "usable",
        "quality": published["quality"],
    }
    # force usable for engine path even if gaps exist
    record["quality_status"] = "usable"
    upsert_dataset(record)
    params = {
        "opening_range_minutes": 15,
        "atr_period": 5,
        "atr_filter_mult": 0.0,
        "stop_risk_mult": 1.0,
        "target_risk_mult": 2.0,
        "session_exit_time": "20:00",
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
    }
    e1 = run_experiment(dataset_id=record["dataset_id"], parameters=params)
    e2 = run_experiment(dataset_id=record["dataset_id"], parameters=params)
    assert e1["integrity_hash"] == e2["integrity_hash"]
    assert e1["metrics_by_split"] == e2["metrics_by_split"]
