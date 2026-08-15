"""Analysis API contract tests."""

from __future__ import annotations

import pytest


@pytest.mark.contract
def test_analysis_rejects_prediction(client):
    r = client.post("/v1/analysis", json={"query": "Predict the next bar close for MES"})
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


@pytest.mark.contract
def test_documents_search(client):
    r = client.post("/v1/documents/search", json={"query": "holdout risk policy", "top_k": 3})
    assert r.status_code == 200
    assert len(r.json()["items"]) >= 1
