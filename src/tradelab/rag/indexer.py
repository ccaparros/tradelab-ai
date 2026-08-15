"""Indexer stub — documents are seeded in retrieve for MVP demo."""

from __future__ import annotations

from tradelab.rag.retrieve import seed_document


def index_markdown(title: str, body: str) -> dict:
    return seed_document(title, body)
