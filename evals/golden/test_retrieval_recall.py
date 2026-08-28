"""Retrieval Recall@5 and numeric faithfulness (CI, no live LLM)."""

from __future__ import annotations

import json
import re

import pytest

from tradelab.agents.graph import run_analysis
from tradelab.rag.indexer import ensure_policy_documents, index_markdown
from tradelab.rag.retrieve import hybrid_search

MIN_RECALL_AT_5 = 0.85
MIN_FAITHFULNESS = 0.90

# Queries with at least one gold document_id that must appear in top-5.
RETRIEVAL_CASES = [
    {
        "query": "política research-only órdenes en vivo holdout",
        "relevant_ids": ["00000000-0000-0000-0000-000000000001"],
    },
    {
        "query": "Opening Range Breakout ATR una entrada por sesión",
        "relevant_ids": ["00000000-0000-0000-0000-000000000002"],
    },
    {
        "query": "validation peor que train overfit costes régimen",
        "relevant_ids": ["00000000-0000-0000-0000-000000000003"],
    },
    {
        "query": "vwap_fade_intraday fade VWAP sesión anti look-ahead",
        "relevant_ids": ["00000000-0000-0000-0000-000000000004"],
    },
    {
        "query": "walk-forward expanding sensibilidad comisión holdout excluido",
        "relevant_ids": ["00000000-0000-0000-0000-000000000005"],
    },
    {
        "query": "CAG versus RAG prompts informes híbrido",
        "relevant_ids": [],  # filled after seed
        "title_substr": "CAG versus RAG",
    },
    {
        "query": "verdad numérica métricas deterministas fuera del LLM ADR",
        "relevant_ids": [],
        "title_substr": "Numeric truth",
    },
]


@pytest.fixture()
def retrieval_corpus(data_root):
    ensure_policy_documents()
    index_markdown(
        "CAG versus RAG",
        "CAG holds stable policy in prompts; RAG indexes evolving reports for hybrid retrieval.",
        source_uri="eval://cag-rag",
        doc_type="adr",
    )
    index_markdown(
        "Numeric truth outside the LLM",
        "Financial metrics must come from deterministic tools. "
        "ADR numeric truth: never embed Sharpe or PnL in the model.",
        source_uri="eval://numeric-truth",
        doc_type="adr",
    )
    return True


@pytest.mark.fast
def test_retrieval_recall_at_5(retrieval_corpus):
    recalls: list[float] = []
    for case in RETRIEVAL_CASES:
        hits = hybrid_search(case["query"], top_k=5)
        hit_ids = {h["document_id"] for h in hits}
        titles = [(h.get("title") or "") for h in hits]
        gold = list(case.get("relevant_ids") or [])
        substr = case.get("title_substr")
        if gold:
            recalls.append(len(set(gold) & hit_ids) / len(gold))
        elif substr:
            recalls.append(1.0 if any(substr.lower() in t.lower() for t in titles) else 0.0)
        else:
            recalls.append(1.0)
    mean_recall = sum(recalls) / len(recalls)
    assert mean_recall >= MIN_RECALL_AT_5, {"recall@5": round(mean_recall, 4), "per_query": recalls}


def _numeric_tokens(text: str) -> set[str]:
    """Financial-like numbers; skip years and lone small ints used in prose."""
    toks = set(re.findall(r"-?\d+\.\d+", text))
    return toks


@pytest.mark.fast
def test_stub_faithfulness_numbers_from_tools(data_root, sample_bars_nt):
    """Fallback answer must only use numeric literals present in tool evidence."""
    import uuid

    from tradelab.backtesting.service import run_experiment
    from tradelab.datasets.publisher import publish_canonical_dataset
    from tradelab.datasets.store import upsert_dataset

    published = publish_canonical_dataset(sample_bars_nt, contract_id=uuid.uuid4())
    ds_id = str(published["dataset_id"])
    upsert_dataset(
        {
            "dataset_id": ds_id,
            "content_checksum": published["content_checksum"],
            "storage_uri": published["storage_uri"],
            "quality_status": "usable",
            "quality": published["quality"],
        }
    )
    exp = run_experiment(
        dataset_id=ds_id,
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
        query="Compara net pnl train y validation",
        dataset_id=ds_id,
        experiment_id=exp["experiment_id"],
    )
    evidence = json.dumps(
        {
            "metrics": out.get("metrics"),
            "experiment": exp.get("metrics_by_split"),
        },
        default=str,
    )
    answer_nums = _numeric_tokens(out.get("answer") or "")
    evidence_nums = _numeric_tokens(evidence)
    if not answer_nums:
        faithfulness = 1.0
    else:
        faithfulness = len(answer_nums & evidence_nums) / len(answer_nums)
    assert out.get("graph") == "langgraph" or (out.get("llm") or {}).get("provider")
    assert faithfulness >= MIN_FAITHFULNESS, {
        "faithfulness": round(faithfulness, 4),
        "answer_nums": sorted(answer_nums),
        "missing": sorted(answer_nums - evidence_nums),
    }
