"""Index research markdown/JSON reports into the local RAG corpus."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from tradelab.rag.chunking import chunk_text
from tradelab.rag.corpus import (
    POLICY_DOCS,
    content_checksum,
    load_corpus,
    save_corpus,
    with_corpus,
)

DEFAULT_REPORT_ROOTS = (
    Path("data_catalog/reports"),
    Path("docs/adr"),
    Path("docs/demo"),
)


def _stable_chunk_id(document_id: str, ordinal: int) -> str:
    return str(uuid.uuid5(uuid.UUID(document_id), f"chunk-{ordinal}"))


def _doc_id_from_checksum(checksum: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tradelab-doc:{checksum}"))


def _remove_document(data: dict[str, Any], document_id: str) -> None:
    data["documents"].pop(document_id, None)
    stale = [cid for cid, ch in data["chunks"].items() if ch.get("document_id") == document_id]
    for cid in stale:
        del data["chunks"][cid]


def index_markdown(
    title: str,
    body: str,
    *,
    source_uri: str | None = None,
    doc_type: str = "markdown",
    document_id: str | None = None,
) -> dict[str, Any]:
    """Index a markdown/text body; replace previous version with same document_id or checksum."""

    def mutate(data: dict[str, Any]) -> dict[str, Any]:
        checksum = content_checksum(f"{title}\n{body}")
        doc_id = document_id or _doc_id_from_checksum(checksum)
        # Idempotent: same checksum already present
        existing = data["documents"].get(doc_id)
        if existing and existing.get("content_checksum") == checksum:
            return {
                "document_id": doc_id,
                "chunk_count": sum(1 for c in data["chunks"].values() if c.get("document_id") == doc_id),
                "skipped": True,
            }
        _remove_document(data, doc_id)
        pieces = chunk_text(body)
        if not pieces:
            pieces = [body.strip() or title]
        data["documents"][doc_id] = {
            "document_id": doc_id,
            "title": title,
            "source_uri": source_uri or f"memory://{doc_id}",
            "doc_type": doc_type,
            "content_checksum": checksum,
            "chunk_count": len(pieces),
        }
        for i, piece in enumerate(pieces):
            cid = _stable_chunk_id(doc_id, i)
            data["chunks"][cid] = {
                "chunk_id": cid,
                "document_id": doc_id,
                "ordinal": i,
                "title": title,
                "text": piece,
                "source_uri": source_uri or f"memory://{doc_id}",
                "doc_type": doc_type,
            }
        return {"document_id": doc_id, "chunk_count": len(pieces), "skipped": False}

    return with_corpus(mutate)


def index_file(path: Path) -> dict[str, Any] | None:
    path = Path(path)
    if not path.is_file():
        return None
    suffix = path.suffix.lower()
    if suffix not in {".md", ".json", ".txt"}:
        return None
    raw = path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".json":
        try:
            payload = json.loads(raw)
            body = json.dumps(payload, indent=2, ensure_ascii=False)
            title = path.stem
        except json.JSONDecodeError:
            body = raw
            title = path.stem
    else:
        body = raw
        # First markdown heading as title if present
        title = path.stem
        for line in raw.splitlines():
            if line.startswith("# "):
                title = line[2:].strip() or title
                break
    rel = str(path).replace("\\", "/")
    doc_type = "report"
    if "reconciliation" in rel:
        doc_type = "reconciliation"
    elif "experiment" in rel:
        doc_type = "experiment"
    elif "canonical" in rel:
        doc_type = "canonical"
    elif "adr" in rel:
        doc_type = "adr"
    elif "demo" in rel:
        doc_type = "demo"
    return index_markdown(title, body, source_uri=rel, doc_type=doc_type)


def ensure_policy_documents() -> int:
    n = 0
    for doc in POLICY_DOCS:
        out = index_markdown(
            doc["title"],
            doc["content"],
            source_uri=f"policy://{doc['document_id']}",
            doc_type=doc["doc_type"],
            document_id=doc["document_id"],
        )
        if not out.get("skipped"):
            n += 1
    return n


def reindex_reports(
    roots: list[Path] | tuple[Path, ...] | None = None,
    *,
    include_policies: bool = True,
) -> dict[str, Any]:
    """Scan report directories and (re)index all supported files."""
    if include_policies:
        ensure_policy_documents()
    roots = list(roots) if roots is not None else list(DEFAULT_REPORT_ROOTS)
    indexed = 0
    skipped = 0
    errors: list[str] = []
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".json", ".txt"}:
                continue
            try:
                result = index_file(path)
                if result is None:
                    continue
                if result.get("skipped"):
                    skipped += 1
                else:
                    indexed += 1
            except Exception as exc:  # noqa: BLE001 — continue indexing remaining files
                errors.append(f"{path}: {exc}")
    corpus = load_corpus()
    return {
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "documents": len(corpus["documents"]),
        "chunks": len(corpus["chunks"]),
        "corpus_uri": str(Path(get_settings_data_root()) / "rag" / "corpus.json"),
    }


def get_settings_data_root() -> Path:
    from tradelab.observability.settings import get_settings

    return Path(get_settings().data_root)


def corpus_stats() -> dict[str, Any]:
    data = load_corpus()
    return {
        "documents": len(data["documents"]),
        "chunks": len(data["chunks"]),
        "corpus_uri": str(corpus_path_safe()),
    }


def corpus_path_safe() -> Path:
    from tradelab.rag.corpus import corpus_path

    return corpus_path()


def clear_corpus() -> None:
    save_corpus({"version": 1, "documents": {}, "chunks": {}})


def main() -> None:
    """CLI: tradelab-index-rag"""
    stats = reindex_reports()
    print(json.dumps({"ok": True, **stats}, indent=2))


if __name__ == "__main__":
    main()
