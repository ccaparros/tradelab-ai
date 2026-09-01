"""Persistent file-backed RAG corpus under DATA_ROOT/rag/."""

from __future__ import annotations

import hashlib
import json
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from filelock import FileLock

from tradelab.ingestion.storage import atomic_write_text
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
    {
        "document_id": "00000000-0000-0000-0000-000000000005",
        "title": "Walk-forward and sensitivity policy",
        "doc_type": "policy",
        "content": (
            "Walk-forward is expanding on train+validation only. "
            "Sensitivity covers nearby parameters and cost shocks (commission, slippage). "
            "Holdout is excluded from walk-forward, sensitivity, and baseline. "
            "A session-long naive baseline is reported for comparison. "
            "Profitability is not a project success criterion."
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
    atomic_write_text(
        path,
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
    )


@contextmanager
def _write_guard():
    with _lock:
        with FileLock(f"{corpus_path()}.lock"):
            yield


def with_corpus(mutator) -> dict[str, Any]:
    with _write_guard():
        data = load_corpus()
        result = mutator(data)
        save_corpus(data)
        return result
