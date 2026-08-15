"""Markdown/text chunking for research documents (no OHLCV)."""

from __future__ import annotations

import re


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ0-9_]+", text.lower())


def chunk_text(
    text: str,
    *,
    chunk_size: int = 900,
    overlap: int = 120,
) -> list[str]:
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    cleaned = text.replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", cleaned) if p.strip()]
    chunks: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            flush()
            start = 0
            while start < len(para):
                end = min(len(para), start + chunk_size)
                chunks.append(para[start:end].strip())
                if end >= len(para):
                    break
                start = max(0, end - overlap)
            continue
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if len(candidate) <= chunk_size:
            buf = candidate
        else:
            flush()
            buf = para
    flush()

    if overlap <= 0 or len(chunks) <= 1:
        return [c for c in chunks if c]

    # Soft overlap between consecutive chunks for boundary terms
    overlapped: list[str] = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            overlapped.append(chunk)
            continue
        prev_tail = chunks[i - 1][-overlap:]
        merged = f"{prev_tail}\n{chunk}".strip()
        overlapped.append(merged[: chunk_size + overlap])
    return overlapped
