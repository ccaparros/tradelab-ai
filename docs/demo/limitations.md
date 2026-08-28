# Limitations

- Spike de permisos puede reducir a un instrumento
- NT Add-On puede diferirse a export+manifest
- RAG MVP indexa informes reales (`data_catalog/reports`, ADRs, demo docs) en
  corpus file-backed `DATA_ROOT/rag/corpus.json` con retrieval híbrido BM25+TF-IDF;
  schema Postgres/pgvector preparado en Alembic `0002_rag_documents` para sync posterior
- Store JSON local para demo; Postgres+Alembic es el destino de producción
- Histórico IBKR ~22 meses RTH 5m (MES 2024-11-05→2026-08-28; MNQ 2024-10-09→2026-08-28). IB no califica vencimientos anteriores a Z5; el tramo temprano usa ese contrato como proxy, no el frente real
- Walk-forward / sensibilidad a costes: expanding walk-forward y shocks de
  comisión/slippage + parámetros cercanos sobre train/validation; el holdout no se usa

