"""Golden eval runner — schema, tools, citations, status (no live LLM required)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from pydantic import ValidationError

from tradelab.agents.graph import run_analysis
from tradelab.agents.schema import AnalysisOutput
from tradelab.backtesting.service import run_experiment
from tradelab.datasets.publisher import publish_canonical_dataset
from tradelab.datasets.store import upsert_dataset
from tradelab.rag.indexer import ensure_policy_documents, index_markdown

QUESTIONS = Path(__file__).with_name("questions.jsonl")
ROOT = Path(__file__).resolve().parents[2]

# Constitution baselines (adjustable once with registry — keep strict for CI).
MIN_TOOL_SELECTION = 0.90
MIN_SCHEMA_VALIDITY = 1.0
MIN_CITATION_PRECISION = 0.95
MIN_STATUS_ACCURACY = 0.90


def _load_questions() -> list[dict[str, Any]]:
    rows = []
    for line in QUESTIONS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


@pytest.fixture(scope="module")
def golden_context(tmp_path_factory, monkeypatch_module):
    """Isolated DATA_ROOT with fixture dataset + experiment + RAG policies/reports."""
    root = tmp_path_factory.mktemp("golden_data")
    monkeypatch_module.setenv("DATA_ROOT", str(root))
    monkeypatch_module.setenv("LLM_API_KEY", "")  # force stub path; empty overrides .env
    from tradelab.observability.settings import get_settings

    get_settings.cache_clear()

    fixture = ROOT / "data_catalog/fixtures/bars_sample/ninjatrader_mes_5m.parquet"
    df = pd.read_parquet(fixture)
    published = publish_canonical_dataset(
        df,
        contract_id=uuid.uuid4(),
        preferred_source_id="ninjatrader",
        lineage={"demo": True, "eval": "golden"},
    )
    dataset_id = str(published["dataset_id"])
    upsert_dataset(
        {
            "dataset_id": dataset_id,
            "contract_id": str(published["contract_id"]),
            "instrument": "MES",
            "contract_month": "202609",
            "bar_size": "5 mins",
            "quality_status": published["quality_status"],
            "content_checksum": published["content_checksum"],
            "storage_uri": published["storage_uri"],
            "coverage_start_utc": str(published["coverage_start_utc"]),
            "coverage_end_utc": str(published["coverage_end_utc"]),
            "quality": published["quality"],
            "lineage": published["lineage"],
            "preferred_source": "ninjatrader",
        }
    )
    exp = run_experiment(
        dataset_id=dataset_id,
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
    ensure_policy_documents()
    index_markdown(
        "CAG versus RAG",
        "CAG holds stable policy in prompts; RAG indexes evolving reports for hybrid retrieval.",
        source_uri="eval://cag-rag",
        doc_type="adr",
    )
    index_markdown(
        "Numeric truth outside the LLM",
        "Financial metrics must come from deterministic tools. ADR numeric truth: never embed Sharpe or PnL in the model.",
        source_uri="eval://numeric-truth",
        doc_type="adr",
    )
    index_markdown(
        "Demo limitations",
        "Known project limitations for demo and RAG: file-backed corpus, short history window.",
        source_uri="eval://limitations",
        doc_type="demo",
    )
    # Keep golden corpus small/fast: policies + eval docs only (no full report tree).
    get_settings.cache_clear()
    yield {"dataset_id": dataset_id, "experiment_id": exp["experiment_id"]}
    get_settings.cache_clear()


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Module-scoped monkeypatch (pytest built-in is function-scoped)."""
    from _pytest.monkeypatch import MonkeyPatch

    m = MonkeyPatch()
    yield m
    m.undo()


def _score_row(row: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    tools_used = {t.get("tool_name") for t in out.get("tool_invocations") or []}
    expect_tools = set(row.get("expect_tools") or [])
    tools_ok = expect_tools.issubset(tools_used) if expect_tools else True

    expect_status = row.get("expect_status")
    status_ok = out.get("status") == expect_status if expect_status else True

    schema_ok = True
    try:
        AnalysisOutput.model_validate(out)
    except ValidationError:
        schema_ok = False

    sources = out.get("sources") or []
    citation_ok = True
    if row.get("expect_citation"):
        citation_ok = len(sources) >= 1 and all(s.get("document_id") for s in sources)

    # Citation precision: every cited document_id must be non-empty string
    citation_precision_ok = all(isinstance(s.get("document_id"), str) and s["document_id"] for s in sources)

    return {
        "id": row["id"],
        "tools_ok": tools_ok,
        "status_ok": status_ok,
        "schema_ok": schema_ok,
        "citation_ok": citation_ok,
        "citation_precision_ok": citation_precision_ok,
        "status": out.get("status"),
        "tools_used": sorted(tools_used),
    }


@pytest.mark.fast
def test_golden_suite_thresholds(golden_context):
    rows = _load_questions()
    assert len(rows) >= 30, f"expected >=30 golden questions, got {len(rows)}"

    scores: list[dict[str, Any]] = []
    for row in rows:
        ds = golden_context["dataset_id"] if row.get("require_dataset") else None
        ex = golden_context["experiment_id"] if row.get("require_experiment") else None
        out = run_analysis(query=row["question"], dataset_id=ds, experiment_id=ex)
        scores.append(_score_row(row, out))

    n = len(scores)
    tool_rate = sum(1 for s in scores if s["tools_ok"]) / n
    schema_rate = sum(1 for s in scores if s["schema_ok"]) / n
    status_rate = sum(1 for s in scores if s["status_ok"]) / n
    citation_rows = [s for s, r in zip(scores, rows, strict=True) if r.get("expect_citation")]
    citation_rate = (
        sum(1 for s in citation_rows if s["citation_ok"] and s["citation_precision_ok"]) / len(citation_rows)
        if citation_rows
        else 1.0
    )

    failures = [s for s in scores if not (s["tools_ok"] and s["status_ok"] and s["schema_ok"])]
    summary = {
        "n": n,
        "tool_selection": round(tool_rate, 4),
        "schema_validity": round(schema_rate, 4),
        "status_accuracy": round(status_rate, 4),
        "citation_precision": round(citation_rate, 4),
        "failures": failures[:10],
    }
    assert schema_rate >= MIN_SCHEMA_VALIDITY, summary
    assert tool_rate >= MIN_TOOL_SELECTION, summary
    assert status_rate >= MIN_STATUS_ACCURACY, summary
    assert citation_rate >= MIN_CITATION_PRECISION, summary


@pytest.mark.fast
def test_prediction_case_rejected(golden_context):
    rows = _load_questions()
    pred = next(r for r in rows if r["id"] == "g003")
    out = run_analysis(query=pred["question"])
    assert out["status"] == "rejected"
