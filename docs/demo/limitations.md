# Limitations

- Spike de permisos puede reducir a un instrumento
- NT Add-On puede diferirse a export+manifest
- RAG MVP indexa informes reales (`data_catalog/reports`, ADRs, demo docs) en
  corpus file-backed `DATA_ROOT/rag/corpus.json` con retrieval híbrido BM25+TF-IDF;
  schema Postgres/pgvector preparado en Alembic `0002_rag_documents` para sync posterior
- Store JSON local para demo; Postgres+Alembic es el destino de producción
- Histórico actual ~meses RTH (no 12–24) según permisos/descarga IBKR
- Walk-forward / sensibilidad a costes: helpers parciales; no afirmamos robustez completa
