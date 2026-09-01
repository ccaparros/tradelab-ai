"""Contract-ish API tests for catalog/quality."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.contract
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.contract
def test_ingest_and_quality(client):
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
    assert r.status_code == 201, r.text
    dataset_id = r.json()["dataset_id"]
    q = client.get(f"/v1/datasets/{dataset_id}/quality")
    assert q.status_code == 200
    body = q.json()
    assert "gaps" in body
    for g in body["gaps"]:
        assert g["classification"] in {"session_closed", "maintenance", "unavailable", "error"}
    listed = client.get("/v1/datasets")
    assert listed.status_code == 200
    assert any(d["dataset_id"] == dataset_id for d in listed.json()["items"])


@pytest.mark.contract
def test_ingestion_rejects_instrument_mismatch(client):
    parquet = ROOT / "data_catalog/fixtures/bars_sample/ninjatrader_mes_5m.parquet"
    manifest = ROOT / "data_catalog/fixtures/bars_sample/ninjatrader_mes_5m.manifest.json"
    response = client.post(
        "/v1/ingestions",
        json={
            "source": "ninjatrader",
            "instrument": "MNQ",
            "contract_month": "202609",
            "parquet_uri": str(parquet),
            "manifest_uri": str(manifest),
            "publish": True,
        },
    )
    assert response.status_code == 400
    assert "instrument mismatch" in response.json()["detail"]
