# Implementation Plan: TradeLab AI MVP

**Branch**: `001-tradelab-mvp` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-tradelab-mvp/spec.md`

## Summary

TradeLab AI MVP entrega un flujo auditable: ingesta dual (NinjaTrader + IBKR) →
validación/reconciliación → dataset canónico versionado → backtest determinista
ORB+ATR con costes y splits temporales → copiloto con tools tipadas, RAG de
documentos e informes, y citas verificables — sin órdenes reales.

Enfoque técnico: monorepo Python con FastAPI + Streamlit; raw Parquet inmutable;
catálogo/experimentos/corpus en PostgreSQL + pgvector; métricas solo en código;
agente LangGraph con salida Pydantic y verificador de cifras/citas; demo vía
snapshot local/Docker Compose.

## Technical Context

**Language/Version**: Python 3.11+ (API, pipeline, agente); C# (.NET) solo para
exportador NinjaTrader opcional — fallback: export manual + mismo contrato de
ingesta

**Primary Dependencies**: FastAPI, Streamlit, Pydantic v2, SQLAlchemy/Alembic,
Pandera, pandas/pyarrow, LangGraph + OpenAI-compatible LLM client, Jinja2
(prompts CAG), ibapi (TWS API), pytest + httpx, ruff

**Storage**: Parquet (raw inmutable en disco/volumen); PostgreSQL 16 + pgvector
(catálogo, linaje, experimentos, chunks RAG, checkpointer ligero)

**Testing**: pytest (unit/integration sin broker), fixtures Parquet versionados,
evals golden/regression en `evals/`, CI GitHub Actions (lint + tests + evals
rápidas)

**Target Platform**: Windows/Linux local para conectores de broker; Docker
Compose para API + UI + Postgres; demo cloud solo con snapshot (sin credenciales
broker)

**Project Type**: Monorepo web-service (API) + dashboard (UI) + librería de
dominio (`src/tradelab`) + conectores

**Performance Goals**: Happy path demo < 15 min; consulta copiloto típica < 60 s
con tools; backtest de ~12 meses MES 5m en < 5 min en laptop de desarrollo

**Constraints**: Sin trading real; sin embeddings de series numéricas; holdout
protegido; secrets solo locales; pacing IBKR; determinismo hasheado; umbrales
evals constitución (schema 100%, citas ≥95%, etc.)

**Scale/Scope**: 1–2 instrumentos (MES/MNQ), barras 5m, 12–24 meses, 1 estrategia,
1 agente, ~80 h / entrega 2026-09-03

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (TradeLab AI v1.0.0+)*

### Pre-Phase 0

- [x] **I. Reproducibilidad**: `dataset_id` / `experiment_id` / `analysis_id` +
      hash de integridad en experimentos y métricas trazables
- [x] **II. Linaje del dato**: Raw Parquet + manifiesto/checksum; cuarentena;
      sin merge silencioso
- [x] **III. Honestidad temporal**: Splits train/val/holdout; indicadores
      shifted; tests anti-look-ahead en CI
- [x] **IV. IA acotada**: Tools tipadas para cifras; schema Pydantic + verificador;
      embeddings solo documentos
- [x] **V. Sin trading real**: Catálogo de tools sin órdenes; connectors locales;
      demo snapshot
- [x] **Alcance**: MVP completo según spec; sin multiagente/paper/HFT
- [x] **Evals/CI**: Matriz SC-005 + gates de constitución

### Post-Phase 1 (re-check)

- [x] Contratos API/tools no exponen envío de órdenes
- [x] Modelo de datos separa raw / canónico / cuarentena / experimentos / corpus
- [x] Quickstart valida happy path sin broker
- [x] Design no introduce complejidad post-MVP injustificada (Complexity Tracking
      vacío)

## Project Structure

### Documentation (this feature)

```text
specs/001-tradelab-mvp/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── openapi.yaml
│   └── agent-tools.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (pendiente)
```

### Source Code (repository root)

```text
apps/
├── api/                 # FastAPI app
└── ui/                  # Streamlit dashboard
connectors/
├── ibkr/                # reqHistoricalData adapter
└── ninjatrader-csharp/  # BarsRequest exporter (or docs for file fallback)
src/tradelab/
├── ingestion/
├── quality/
├── datasets/
├── backtesting/
├── rag/
├── agents/
├── prompts/
└── observability/
migrations/              # Alembic
data_catalog/            # fixtures + demo snapshot metadata
evals/
├── golden/
└── regression/
tests/
docs/
├── architecture/
├── adr/
└── demo/
docker-compose.yml
.env.example
README.md
```

**Structure Decision**: Monorepo TradeLab AI (opción canónica de constitución/
plan de proyecto). Dominio en `src/tradelab`; apps delgadas; conectores
aislados; sin layout backend/frontend genérico paralelo.

## Complexity Tracking

> Sin violaciones de constitución que requieran justificación. Dual-connector +
> un agente + RAG documental son requisitos MVP explícitos, no complejidad extra.
