"""RAG indexing and hybrid retrieval tests."""

from __future__ import annotations

import pytest

from tradelab.rag.chunking import chunk_text
from tradelab.rag.indexer import clear_corpus, index_markdown, reindex_reports
from tradelab.rag.retrieve import hybrid_search


@pytest.mark.unit
def test_chunk_text_splits_long_body():
    body = "para uno.\n\n" + ("palabra " * 200) + "\n\nfin."
    chunks = chunk_text(body, chunk_size=120, overlap=20)
    assert len(chunks) >= 2
    assert all(chunks)


@pytest.mark.unit
def test_index_and_retrieve_report(data_root, tmp_path):
    clear_corpus()
    report = tmp_path / "MES_reconciliation.md"
    report.write_text(
        "# Reconciliation report — MES\n\n"
        "Preferred source for canonical MVP: ibkr_canonical_nt_quarantine.\n"
        "Quarantine conflicting timestamps; do not blend OHLC.\n"
        "Close correlation between IBKR and NinjaTrader.\n",
        encoding="utf-8",
    )
    stats = reindex_reports(roots=[tmp_path], include_policies=True)
    assert stats["documents"] >= 4  # 3 policies + report
    assert stats["chunks"] >= 4

    hits = hybrid_search("ibkr quarantine reconciliation MES", top_k=3)
    assert hits
    top = hits[0]
    assert "document_id" in top and "chunk_id" in top
    blob = (top.get("excerpt") or "") + (top.get("title") or "")
    assert (
        "quarantine" in blob.lower() or "reconciliation" in blob.lower() or "ibkr" in blob.lower()
    )


@pytest.mark.unit
def test_policy_retrieval_holdout(data_root):
    clear_corpus()
    index_markdown(
        "Risk policy",
        "TradeLab AI is research-only. Holdout is protected during parameter selection.",
        document_id="00000000-0000-0000-0000-000000000001",
        doc_type="policy",
    )
    hits = hybrid_search("holdout risk policy", top_k=2)
    assert hits
    assert hits[0]["document_id"] == "00000000-0000-0000-0000-000000000001"
