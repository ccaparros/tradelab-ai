"""TradeLab RAG: chunk, index reports, hybrid retrieve."""

from __future__ import annotations

from typing import Any

__all__ = [
    "hybrid_search",
    "index_file",
    "index_markdown",
    "reindex_reports",
]


def hybrid_search(*args: Any, **kwargs: Any):
    from tradelab.rag.retrieve import hybrid_search as _hs

    return _hs(*args, **kwargs)


def index_file(*args: Any, **kwargs: Any):
    from tradelab.rag.indexer import index_file as _if

    return _if(*args, **kwargs)


def index_markdown(*args: Any, **kwargs: Any):
    from tradelab.rag.indexer import index_markdown as _im

    return _im(*args, **kwargs)


def reindex_reports(*args: Any, **kwargs: Any):
    from tradelab.rag.indexer import reindex_reports as _rr

    return _rr(*args, **kwargs)
