# RAG setup (TradeLab AI)

Corpus documental (no OHLCV): políticas CAG + informes de reconciliación,
canónicos, experimentos, ADRs y docs de demo.

## Indexar

```bash
pip install -e .
tradelab-index-rag
```

Escribe `DATA_ROOT/rag/corpus.json` (por defecto `./data/rag/corpus.json`).

## Buscar

```bash
curl -s http://127.0.0.1:8000/v1/documents/search \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"ibkr quarantine reconciliation MES\",\"top_k\":5}"
```

O desde el agente: tool `search_research_documents`.

## Notas

- Retrieval híbrido: BM25 léxico + similitud TF-IDF (sin embeddings externos).
- Los informes de experimento se indexan al generarse (`write_experiment_report`).
- Postgres + `vector(384)` está migrado para un sync futuro; el camino demo no lo exige.
