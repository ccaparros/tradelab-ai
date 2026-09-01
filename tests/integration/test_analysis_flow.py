"""Integration analysis flow with tools."""

from __future__ import annotations

import uuid

import pytest

import tradelab.agents.graph as agent_graph
from tradelab.agents.graph import run_analysis
from tradelab.backtesting.service import run_experiment
from tradelab.datasets.publisher import publish_canonical_dataset
from tradelab.datasets.store import upsert_dataset


@pytest.mark.integration
def test_analysis_flow(data_root, sample_bars_nt):
    published = publish_canonical_dataset(sample_bars_nt, contract_id=uuid.uuid4())
    ds = {
        "dataset_id": str(published["dataset_id"]),
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "quality_status": "usable",
        "quality": published["quality"],
    }
    upsert_dataset(ds)
    exp = run_experiment(
        dataset_id=ds["dataset_id"],
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
    )
    out = run_analysis(
        query="¿Por qué validation puede ser peor que train?",
        dataset_id=ds["dataset_id"],
        experiment_id=exp["experiment_id"],
    )
    assert out["status"] in {"completed", "insufficient_evidence"}
    assert out["analysis_id"]
    assert out["tool_invocations"]


@pytest.mark.integration
def test_live_llm_numeric_hallucination_is_discarded(
    data_root,
    sample_bars_nt,
    monkeypatch,
):
    published = publish_canonical_dataset(sample_bars_nt, contract_id=uuid.uuid4())
    dataset = {
        "dataset_id": str(published["dataset_id"]),
        "instrument": "MES",
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "quality_status": "usable",
        "quality": published["quality"],
    }
    upsert_dataset(dataset)
    experiment = run_experiment(
        dataset_id=dataset["dataset_id"],
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
    )
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def fake_completion(**_kwargs):
        return {
            "parsed": {
                "answer": "El net PnL demostrado es 999.99.",
                "assumptions": [],
                "warnings": [],
                "confidence": 0.99,
            },
            "model": "fake-model",
            "base_url": "https://example.invalid",
            "usage": None,
        }

    monkeypatch.setattr(agent_graph, "chat_completion", fake_completion)
    output = run_analysis(
        query="Compara net PnL de train y validation",
        dataset_id=dataset["dataset_id"],
        experiment_id=experiment["experiment_id"],
    )
    assert output["status"] == "insufficient_evidence"
    assert "fue descartada" in output["answer"]
    assert any("999.99" in warning for warning in output["warnings"])
