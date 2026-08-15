"""Persistent file-backed RAG corpus under DATA_ROOT/rag/."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any

from tradelab.observability.settings import get_settings

_lock = threading.Lock()

# Stable IDs for built-in CAG companion policies (citations stay stable across runs).
POLICY_DOCS: list[dict[str, str]] = [
    {
        "document_id": "00000000-0000-0000-0000-000000000001",
        "title": "Risk policy",
        "doc_type": "policy",
        "content": (
            "TradeLab AI is research-only. No live orders. "
            "Financial metrics must come from deterministic tools. "
            "Holdout is protected during parameter selection."
        ),
    },
    {
        "document_id": "00000000-0000-0000-0000-000000000002",
        "title": "ORB+ATR strategy spec",
        "doc_type": "policy",
        "content": (
            "Opening Range Breakout with ATR filter, one entry per session, "
            "stop and target as risk multiples, mandatory session exit."
        ),
    },
    {
        "document_id": "00000000-0000-0000-0000-000000000004",
        "title": "VWAP fade strategy spec",
        "doc_type": "policy",
        "content": (
            "vwap_fade_intraday fades extensions from session VWAP back toward VWAP. "
            "ATR and VWAP are shifted one bar. Skip blow-off days above max_extension_atr. "
            "One entry per session, stop in ATR multiples, target is VWAP, mandatory session exit. "
            "Profitability is not a project success criterion; compare splits with citations."
        ),
    },
    {
        "document_id": "00000000-0000-0000-0000-000000000003",
        "title": "Validation vs train",
        "doc_type": "policy",
        "content": (
            "Validation results can be worse than train due to regime change, "
            "costs, or overfit. Compare net_pnl and drawdown by split with citations."
        ),
    },
]


def content_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def corpus_dir() -> Path:
    root = Path(get_settings().data_root)
    path = root / "rag"
    path.mkdir(parents=True, exist_ok=True)
    return path


def corpus_path() -> Path:
    return corpus_dir() / "corpus.json"


def empty_corpus() -> dict[str, Any]:
    return {"version": 1, "documents": {}, "chunks": {}}


def load_corpus() -> dict[str, Any]:
    path = corpus_path()
    if not path.exists():
        return empty_corpus()
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("documents", {})
    data.setdefault("chunks", {})
    return data


def save_corpus(data: dict[str, Any]) -> None:
    path = corpus_path()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def with_corpus(mutator) -> dict[str, Any]:
    with _lock:
        data = load_corpus()
        result = mutator(data)
        save_corpus(data)
        return result
