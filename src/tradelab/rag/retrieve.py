"""Hybrid retrieval over indexed research documents (reports + policies)."""

from __future__ import annotations

from typing import Any

from tradelab.rag.chunking import tokenize
from tradelab.rag.corpus import load_corpus
from tradelab.rag.indexer import ensure_policy_documents
from tradelab.rag.scoring import build_idf, hybrid_score, tfidf_vector


def hybrid_search(query: str, *, top_k: int = 5, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Rank chunks with BM25 + TF-IDF cosine; bootstrap policies if corpus empty."""
    data = load_corpus()
    if not data["chunks"]:
        ensure_policy_documents()
        data = load_corpus()

    chunks = list(data["chunks"].values())
    if filters:
        doc_type = filters.get("doc_type")
        if doc_type:
            chunks = [c for c in chunks if c.get("doc_type") == doc_type]
        source_contains = filters.get("source_contains")
        if source_contains:
            needle = str(source_contains).replace("\\", "/")
            chunks = [c for c in chunks if needle in str(c.get("source_uri", "")).replace("\\", "/")]

    if not chunks:
        return []

    idf = build_idf(chunks)
    q_vec = tfidf_vector(tokenize(query), idf)
    scored: list[tuple[float, dict[str, Any]]] = []
    for ch in chunks:
        score = hybrid_score(query, ch, idf=idf, query_vec=q_vec)
        scored.append(
            (
                score,
                {
                    "document_id": ch["document_id"],
                    "chunk_id": ch["chunk_id"],
                    "title": ch.get("title"),
                    "score": round(float(score), 6),
                    "excerpt": (ch.get("text") or "")[:400],
                    "source_uri": ch.get("source_uri"),
                    "doc_type": ch.get("doc_type"),
                    "citation": (ch.get("text") or "")[:280],
                },
            )
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [item for s, item in scored[:top_k] if s > 0]
    if results:
        return results
    # Low-confidence fallback: best chunk so the agent can still cite policy corpus
    best = scored[0][1]
    best["score"] = 0.01
    return [best]


# Back-compat for older callers
def seed_document(title: str, content: str) -> dict[str, Any]:
    from tradelab.rag.indexer import index_markdown

    out = index_markdown(title, content, doc_type="seed")
    return {
        "document_id": out["document_id"],
        "chunk_id": out["document_id"],
        "title": title,
        "content": content,
    }
