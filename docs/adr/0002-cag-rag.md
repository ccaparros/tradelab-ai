# ADR 0002: CAG for stable policy, RAG for evolving reports

## Decision

Stable definitions/policies live in versioned Jinja prompts (CAG). Large/changing
reports are chunked and indexed for hybrid retrieval (RAG): BM25 + TF-IDF over
`DATA_ROOT/rag/corpus.json`, with Postgres/pgvector schema ready for later sync.

## Status

Accepted
