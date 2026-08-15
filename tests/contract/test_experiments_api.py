"""Experiments API contract tests."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _dataset(client) -> str:
    parquet = ROOT / "data_catalog/fixtures/bars_sample/ninjatrader_mes_5m.parquet"
    manifest = ROOT / "data_catalog/fixtures/bars_sample/ninjatrader_mes_5m.manifest.json"
    r = client.post(
        "/v1/ingestions",
        json={
            "source": "ninjatrader",
            "instrument": "MES",
            "contract_month": "202609",
            "parquet_uri": str(parquet),
            "manifest_uri": str(manifest),
            "publish": True,
        },
    )
    assert r.status_code == 201
    # force usable for backtest path
    from tradelab.datasets.store import get_dataset, upsert_dataset

    ds = get_dataset(r.json()["dataset_id"])
    assert ds
    ds["quality_status"] = "usable"
    upsert_dataset(ds)
    return r.json()["dataset_id"]


@pytest.mark.contract
def test_run_backtest_and_report(client):
    dataset_id = _dataset(client)
    payload = {
        "dataset_id": dataset_id,
        "strategy_id": "orb_atr_intraday",
        "parameters": {
            "opening_range_minutes": 15,
            "atr_period": 5,
            "atr_filter_mult": 0.0,
            "stop_risk_mult": 1.0,
            "target_risk_mult": 2.0,
            "session_exit_time": "20:00",
            "commission_per_side": 0.62,
            "slippage_ticks": 1,
        },
        "consume_holdout": False,
    }
    r1 = client.post("/v1/experiments", json=payload)
    r2 = client.post("/v1/experiments", json=payload)
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()["integrity_hash"] == r2.json()["integrity_hash"]
    exp_id = r1.json()["experiment_id"]
    trades = client.get(f"/v1/experiments/{exp_id}/trades")
    assert trades.status_code == 200
    report = client.get(f"/v1/experiments/{exp_id}/report")
    assert report.status_code == 200
    assert report.json()["integrity_hash"] == r1.json()["integrity_hash"]


@pytest.mark.contract
def test_list_strategies_includes_vwap(client):
    r = client.get("/v1/strategies")
    assert r.status_code == 200
    ids = {s["strategy_id"] for s in r.json()["items"]}
    assert {"orb_atr_intraday", "vwap_fade_intraday"} <= ids
