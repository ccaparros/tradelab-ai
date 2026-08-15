"""Minimal hybrid retrieval over seeded research documents."""

from __future__ import annotations

import re
import uuid
from typing import Any

_DOCS: list[dict[str, Any]] = [
    {
        "document_id": "00000000-0000-0000-0000-000000000001",
        "chunk_id": "00000000-0000-0000-0000-000000000011",
        "title": "Risk policy",
        "content": (
            "TradeLab AI is research-only. No live orders. "
            "Financial metrics must come from deterministic tools. "
            "Holdout is protected during parameter selection."
        ),
    },
    {
        "document_id": "00000000-0000-0000-0000-000000000002",
        "chunk_id": "00000000-0000-0000-0000-000000000012",
        "title": "ORB+ATR strategy spec",
        "content": (
            "Opening Range Breakout with ATR filter, one entry per session, "
            "stop and target as risk multiples, mandatory session exit."
        ),
    },
    {
        "document_id": "00000000-0000-0000-0000-000000000003",
        "chunk_id": "00000000-0000-0000-0000-000000000013",
        "title": "Validation vs train",
        "content": (
            "Validation results can be worse than train due to regime change, "
            "costs, or overfit. Compare net_pnl and drawdown by split with citations."
        ),
    },
]


def hybrid_search(query: str, *, top_k: int = 5) -> list[dict[str, Any]]:
    tokens = set(re.findall(r"[a-zA-Záéíóúñ0-9]+", query.lower()))
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in _DOCS:
        text = (doc["title"] + " " + doc["content"]).lower()
        overlap = sum(1 for t in tokens if t in text)
        score = overlap / max(1, len(tokens))
        scored.append(
            (
                score,
                {
                    "document_id": doc["document_id"],
                    "chunk_id": doc["chunk_id"],
                    "score": score,
                    "excerpt": doc["content"][:280],
                    "title": doc["title"],
                },
            )
        )
    scored.sort(key=lambda x: x[0], reverse=True)
    # Always return at least top doc for demo citations
    results = [s[1] for s in scored[:top_k] if s[0] > 0]
    if not results:
        best = scored[0][1]
        best["score"] = 0.01
        results = [best]
    return results


def seed_document(title: str, content: str) -> dict[str, Any]:
    doc = {
        "document_id": str(uuid.uuid4()),
        "chunk_id": str(uuid.uuid4()),
        "title": title,
        "content": content,
    }
    _DOCS.append(doc)
    return doc
