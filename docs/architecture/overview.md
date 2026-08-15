# Architecture overview

TradeLab AI separates:

1. **Ingestion** (local brokers / file register) → immutable raw Parquet
2. **Quality** → gaps, OHLC, reconciliation, quarantine
3. **Canonical datasets** → versioned research series
4. **Backtesting** → deterministic ORB+ATR, hashed experiments
5. **RAG corpus** → documents/reports only (never OHLCV embeddings)
6. **Agent** → typed tools + verifier; research-only

See `specs/001-tradelab-mvp/plan.md` and constitution v1.0.0.
