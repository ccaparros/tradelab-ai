"""Hybrid lexical + TF-IDF scoring over chunk corpus (no financial calc)."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

from tradelab.rag.chunking import tokenize


def build_idf(chunks: list[dict[str, Any]]) -> dict[str, float]:
    df: Counter[str] = Counter()
    for ch in chunks:
        toks = set(tokenize(ch.get("text") or ""))
        df.update(toks)
    n = max(1, len(chunks))
    return {t: math.log(1.0 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}


def bm25_score(query_tokens: list[str], doc_tokens: list[str], idf: dict[str, float]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    tf = Counter(doc_tokens)
    dl = len(doc_tokens)
    avgdl = 200.0
    k1, b = 1.2, 0.75
    score = 0.0
    for t in query_tokens:
        if t not in tf:
            continue
        freq = tf[t]
        denom = freq + k1 * (1 - b + b * dl / avgdl)
        score += idf.get(t, 0.0) * (freq * (k1 + 1)) / denom
    return score


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    if not tokens:
        return {}
    tf = Counter(tokens)
    n = len(tokens)
    return {t: (c / n) * idf.get(t, 0.0) for t, c in tf.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) & set(b)
    if not keys:
        return 0.0
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def hybrid_score(
    query: str,
    chunk: dict[str, Any],
    *,
    idf: dict[str, float],
    query_vec: dict[str, float],
) -> float:
    q_toks = tokenize(query)
    title = chunk.get("title") or ""
    text = chunk.get("text") or ""
    d_toks = tokenize(f"{title} {text}")
    lexical = bm25_score(q_toks, d_toks, idf)
    dense = cosine(query_vec, tfidf_vector(d_toks, idf))
    # Title boost for short policy docs
    title_hits = sum(1 for t in set(q_toks) if t in tokenize(title))
    return 0.65 * lexical + 0.30 * dense * 10.0 + 0.05 * title_hits
