"""Integration backtest on fixture dataset."""

from __future__ import annotations

import uuid

import pandas as pd
import pytest

from tradelab.backtesting.service import run_experiment
from tradelab.datasets.publisher import publish_canonical_dataset
from tradelab.datasets.store import upsert_dataset


@pytest.mark.integration
def test_backtest_orb_fixture(data_root, sample_bars_nt):
    published = publish_canonical_dataset(sample_bars_nt, contract_id=uuid.uuid4())
    record = {
        "dataset_id": str(published["dataset_id"]),
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "quality_status": "usable",
        "quality": published["quality"],
    }
    upsert_dataset(record)
    exp = run_experiment(
        dataset_id=record["dataset_id"],
        parameters={
            "opening_range_minutes": 15,
            "atr_period": 5,
            "atr_filter_mult": 0.0,
            "stop_risk_mult": 1.0,
            "target_risk_mult": 2.0,
            "session_exit_time": "20:00",
            "commission_per_side": 0.62,
            "slippage_ticks": 1,
        },
        consume_holdout=False,
    )
    assert exp["holdout_consumed"] is False
    assert "train" in exp["metrics_by_split"]
    assert exp["metrics_by_split"]["holdout"].get("blocked") is True
    assert exp["strategy_id"] == "orb_atr_intraday"
    assert "walk_forward" in exp
    assert "sensitivity" in exp
    assert "baseline" in exp
    assert exp["walk_forward"].get("status") in {"ok", "skipped"}
    assert exp["sensitivity"].get("status") in {"ok", "skipped"}


@pytest.mark.integration
def test_backtest_vwap_fade_fixture(data_root, sample_bars_nt):
    published = publish_canonical_dataset(sample_bars_nt, contract_id=uuid.uuid4())
    record = {
        "dataset_id": str(published["dataset_id"]),
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "quality_status": "usable",
        "quality": published["quality"],
    }
    upsert_dataset(record)
    exp = run_experiment(
        dataset_id=record["dataset_id"],
        strategy_id="vwap_fade_intraday",
        parameters={
            "warmup_bars": 6,
            "atr_period": 5,
            "extension_atr": 0.4,
            "max_extension_atr": 4.0,
            "stop_atr_mult": 1.0,
            "session_exit_time": "20:00",
            "commission_per_side": 0.62,
            "slippage_ticks": 1,
        },
        consume_holdout=False,
    )
    assert exp["strategy_id"] == "vwap_fade_intraday"
    assert exp["integrity_hash"]
    assert exp["metrics_by_split"]["holdout"].get("blocked") is True


@pytest.mark.integration
def test_holdout_can_only_be_consumed_once(data_root, sample_bars_nt):
    sessions = []
    for offset in range(6):
        session = sample_bars_nt.copy()
        session["timestamp_utc"] = pd.to_datetime(
            session["timestamp_utc"], utc=True
        ) + pd.Timedelta(days=offset)
        sessions.append(session)
    multi_session = pd.concat(sessions, ignore_index=True)
    published = publish_canonical_dataset(multi_session, contract_id=uuid.uuid4())
    record = {
        "dataset_id": str(published["dataset_id"]),
        "instrument": "MES",
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "quality_status": "usable",
        "quality": published["quality"],
    }
    upsert_dataset(record)
    parameters = {
        "opening_range_minutes": 15,
        "atr_period": 5,
        "atr_filter_mult": 0.0,
        "stop_risk_mult": 1.0,
        "target_risk_mult": 2.0,
        "session_exit_time": "20:00",
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
    }
    final = run_experiment(
        dataset_id=record["dataset_id"],
        parameters=parameters,
        consume_holdout=True,
    )
    assert final["holdout_consumed"] is True
    assert final["metrics_by_split"]["holdout"].get("blocked") is not True

    with pytest.raises(PermissionError, match="holdout_already_consumed"):
        run_experiment(
            dataset_id=record["dataset_id"],
            parameters={**parameters, "target_risk_mult": 3.0},
            consume_holdout=True,
        )
