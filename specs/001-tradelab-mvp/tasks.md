---
description: Task list for TradeLab AI MVP implementation
---

# Tasks: TradeLab AI MVP

**Input**: Design documents from `/specs/001-tradelab-mvp/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Obligatorios (constitución) para calidad de datos, anti-look-ahead/determinismo, tools/citas y evals.

**Organization**: Por historia de usuario (P1→P4) para entregas incrementales independientes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Paralela (archivos distintos, sin dependencia incompleta)
- **[Story]**: [US1]…[US4] solo en fases de historias
- Paths relativos al root del monorepo TradeLab AI

---



## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Esqueleto del monorepo y tooling

- [x] T001 Create monorepo directories `apps/api/`, `apps/ui/`, `connectors/ibkr/`, `connectors/ninjatrader-csharp/`, `src/tradelab/{ingestion,quality,datasets,backtesting,rag,agents,prompts,observability}/`, `migrations/`, `data_catalog/`, `evals/{golden,regression}/`, `tests/{unit,integration,contract}/`, `docs/{architecture,adr,demo}/` per `specs/001-tradelab-mvp/plan.md`
- [x] T002 [P] Add Python project metadata and editable package `tradelab` in `pyproject.toml` (Python ≥3.11, deps: fastapi, uvicorn, streamlit, pydantic, sqlalchemy, alembic, pandera, pandas, pyarrow, langgraph, jinja2, httpx, pytest, ruff)
- [x] T003 [P] Add `ruff` config and `pytest.ini`/`pyproject` pytest markers (`unit`, `integration`, `contract`, `fast`) at repo root
- [x] T004 [P] Create `.env.example` with placeholders for `DATABASE_URL`, `LLM_API_KEY`, `DATA_ROOT`, `DEMO_MODE=true` (no broker secrets) and `.gitignore` excluding `.env`, raw data volumes, `__pycache__`
- [x] T005 [P] Create `docker-compose.yml` with services `api`, `ui`, `postgres` (pgvector image) and volume for `DATA_ROOT`
- [x] T006 [P] Add minimal `README.md` with install, compose up, and link to `specs/001-tradelab-mvp/quickstart.md`
- [x] T007 [P] Add stub `apps/api/main.py` FastAPI app with `GET /health` and `apps/ui/app.py` Streamlit placeholder page

**Checkpoint**: `docker compose up` + `/health` reachable (even if DB empty)

---



## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infra compartida que BLOQUEA todas las user stories

**⚠️ CRITICAL**: No empezar US1–US4 hasta completar esta fase

- [x] T008 Define SQLAlchemy models for Instrument, Contract, SourceSystem, IngestionRun, RawBarBatch, CanonicalDataset in `src/tradelab/datasets/models.py` per `specs/001-tradelab-mvp/data-model.md`
- [x] T009 [P] Configure Alembic in `migrations/` and generate initial migration creating core catalog tables + pgvector extension
- [x] T010 [P] Implement settings/config loader in `src/tradelab/observability/settings.py` (pydantic-settings from env)
- [x] T011 [P] Implement structured logging helpers in `src/tradelab/observability/logging.py` (correlation fields ready for analysis_id/experiment_id)
- [x] T012 Implement Pandera bar schema `CanonicalBarSchema` in `src/tradelab/ingestion/schemas.py` (OHLC rules, tick alignment hooks, UTC timestamps)
- [x] T013 Implement checksum + immutable Parquet write utilities in `src/tradelab/ingestion/storage.py` (refuse overwrite of existing checksum path)
- [x] T014 Wire DB session dependency and include OpenAPI skeleton routes mounting in `apps/api/main.py` from `specs/001-tradelab-mvp/contracts/openapi.yaml` (health already present)
- [x] T015 [P] Add fixture factory helpers in `tests/conftest.py` (temp DATA_ROOT, test DB URL, sample bar frames)
- [x] T016 [P] Create tiny versioned fixture Parquet + manifest under `data_catalog/fixtures/bars_sample/` for offline tests
- [x] T017 Add GitHub Actions workflow `.github/workflows/ci.yml` running ruff, unit tests, and integration tests without broker

**Checkpoint**: Migrations apply on Compose Postgres; fixture loads; CI config present

---



## Phase 3: User Story 1 - Confiar en el histórico de dos fuentes (Priority: P1) 🎯 MVP

**Goal**: Cargar raw de NT/IBKR (o registro de archivo), validar, reconciliar, publicar dataset canónico con informe de calidad/cuarentena

**Independent Test**: Con fixtures de ambas fuentes (o una), completar carga → informe gaps/discrepancias → `quality_status` usable/quarantine/insufficient — sin backtest ni copiloto

### Tests for User Story 1 (MANDATORY)

- [x] T018 [P] [US1] Contract tests for `GET /v1/datasets`, `GET /v1/datasets/{id}/quality`, `POST /v1/reconciliations`, `POST /v1/ingestions` in `tests/contract/test_catalog_quality_api.py` from `contracts/openapi.yaml`
- [x] T019 [P] [US1] Unit tests for Pandera schema reject invalid OHLC/duplicates in `tests/unit/test_bar_schema.py`
- [x] T020 [P] [US1] Unit tests for gap classification coverage (100% classified) in `tests/unit/test_gap_classification.py`
- [x] T021 [US1] Integration test: register two fixture sources → reconcile → quarantine conflicts in `tests/integration/test_reconcile_pipeline.py`



### Implementation for User Story 1

- [x] T022 [P] [US1] Implement QualityReport / Gap / Reconciliation / QuarantineItem models in `src/tradelab/quality/models.py`
- [x] T023 [P] [US1] Implement gap detector + classifier in `src/tradelab/quality/gaps.py`
- [x] T024 [P] [US1] Implement OHLC/tick validators and quality report builder in `src/tradelab/quality/validators.py`
- [x] T025 [US1] Implement reconciler (tick tolerance, volume relative diff, quarantine writer) in `src/tradelab/quality/reconcile.py`
- [x] T026 [US1] Implement normalize → CanonicalDataset publisher in `src/tradelab/datasets/publisher.py` (lineage jsonb, content_checksum, no silent merge)
- [x] T027 [P] [US1] Implement IBKR historical adapter skeleton with pacing/backoff interfaces in `connectors/ibkr/historical.py` (callable offline via recorded responses)
- [x] T028 [P] [US1] Document NinjaTrader export fallback + manifest contract in `connectors/ninjatrader-csharp/README.md` and shared ingest entry `src/tradelab/ingestion/register.py`
- [x] T029 [US1] Implement API routers: ingestions, datasets, quality, reconciliations in `apps/api/routers/catalog.py` and `apps/api/routers/quality.py`
- [x] T030 [US1] Add Streamlit catalog + quality views in `apps/ui/pages/1_Catalog.py` (list datasets, show quality report)
- [x] T031 [US1] Generate Markdown quality/reconciliation report files under `data_catalog/reports/` and register as ResearchDocument stubs for later RAG

**Checkpoint**: US1 independiente — quickstart §2 verde con fixtures

---



## Phase 4: User Story 2 - Ejecutar un experimento reproducible (Priority: P2)

**Goal**: Backtest ORB+ATR determinista con costes, splits temporales, hash de integridad, trades y métricas

**Independent Test**: Desde `dataset_id` usable (fixture), dos ejecuciones idénticas → mismo `integrity_hash` y métricas netas; holdout no consumido en selección de params

### Tests for User Story 2 (MANDATORY)

- [x] T032 [P] [US2] Contract tests for strategies/experiments/trades/report endpoints in `tests/contract/test_experiments_api.py`
- [x] T033 [P] [US2] Unit test anti-look-ahead fails if indicator uses future bar in `tests/unit/test_anti_lookahead.py`
- [x] T034 [P] [US2] Unit test determinism: same inputs → same integrity_hash in `tests/unit/test_experiment_hash.py`
- [x] T035 [US2] Integration test full backtest on fixture dataset in `tests/integration/test_backtest_orb.py` (costs present, holdout flag)



### Implementation for User Story 2

- [x] T036 [P] [US2] Add StrategyDefinition / Experiment / Trade / MetricSnapshot models in `src/tradelab/backtesting/models.py`
- [x] T037 [P] [US2] Implement allowed parameter schema for `orb_atr_intraday` in `src/tradelab/backtesting/strategies/orb_atr.py`
- [x] T038 [US2] Implement event-driven bar engine (fills, commission, slippage, session exit, max 1 entry/session) in `src/tradelab/backtesting/engine.py`
- [x] T039 [US2] Implement temporal split + walk-forward helpers and holdout guard in `src/tradelab/backtesting/splits.py`
- [x] T040 [US2] Implement metrics calculator (net return, DD, Sharpe/Sortino with documented convention, PF, etc.) in `src/tradelab/backtesting/metrics.py`
- [x] T041 [US2] Implement integrity hash builder (dataset checksum + code_version + params) in `src/tradelab/backtesting/hashing.py`
- [x] T042 [US2] Implement experiment service orchestrating run + persistence in `src/tradelab/backtesting/service.py`
- [x] T043 [US2] Implement API routers for strategies/experiments/trades/report in `apps/api/routers/experiments.py`
- [x] T044 [US2] Add Streamlit wizard page dataset→params→run→equity/metrics in `apps/ui/pages/2_Backtest.py`
- [x] T045 [US2] Auto-generate experiment Markdown/JSON report in `src/tradelab/backtesting/reporting.py` written to `data_catalog/reports/experiments/`

**Checkpoint**: US2 independiente — quickstart §3 (doble run mismo hash)

---



## Phase 5: User Story 3 - Explicación auditada sin cifras inventadas (Priority: P3)

**Goal**: Copiloto con tools tipadas, RAG documental, schema Pydantic, verificador de cifras/citas; cero órdenes

**Independent Test**: Con corpus indexado + un experimento, 5–10 preguntas golden → respuestas citadas sin cifras huérfanas; predicción de precio → rejected/insufficient

### Tests for User Story 3 (MANDATORY)

- [x] T046 [P] [US3] Contract tests for `/v1/analysis` and `/v1/documents/search` in `tests/contract/test_analysis_api.py`
- [x] T047 [P] [US3] Unit tests for numeric/citation verifier rejecting hallucinated metrics/IDs in `tests/unit/test_response_verifier.py`
- [x] T048 [P] [US3] Unit tests proving forbidden order tools are not registered in `tests/unit/test_tool_allowlist.py`
- [x] T049 [US3] Integration test analysis path with stub LLM + real tools against fixture experiment in `tests/integration/test_analysis_flow.py`



### Implementation for User Story 3

- [x] T050 [P] [US3] Add ResearchDocument / DocumentChunk / AnalysisSession / ToolInvocation models in `src/tradelab/rag/models.py` and `src/tradelab/agents/models.py`
- [x] T051 [P] [US3] Implement chunking + embedding + hybrid search (pgvector + FTS) in `src/tradelab/rag/indexer.py` and `src/tradelab/rag/retrieve.py`
- [x] T052 [P] [US3] Version CAG prompts (risk policy, output schema, limits) as Jinja2 in `src/tradelab/prompts/`
- [x] T053 [US3] Implement typed tools per `specs/001-tradelab-mvp/contracts/agent-tools.md` in `src/tradelab/agents/tools.py` (map to services/API; no order tools)
- [x] T054 [US3] Implement LangGraph agent + checkpointer + `analysis_id` wiring in `src/tradelab/agents/graph.py`
- [x] T055 [US3] Implement structured response models + post-hoc verifier in `src/tradelab/agents/schema.py` and `src/tradelab/agents/verifier.py`
- [x] T056 [US3] Implement analysis + documents API routers in `apps/api/routers/analysis.py` and `apps/api/routers/documents.py`
- [x] T057 [US3] Add Streamlit analysis page with citations panel in `apps/ui/pages/3_Analysis.py`
- [x] T058 [US3] Seed golden eval dataset skeleton (30–40 Q stubs) in `evals/golden/questions.jsonl` and runner `evals/golden/run_eval.py` measuring schema/tools/citations thresholds

**Checkpoint**: US3 independiente — quickstart §4–5; tool allowlist sin órdenes

---



## Phase 6: User Story 4 - Recorrido E2E de demo (Priority: P4)

**Goal**: Happy path evaluador sin broker: snapshot + UI completa + estados de error comprensibles + guion demo

**Independent Test**: Tercero sigue solo README/quickstart ≤15 min y completa catálogo→backtest→análisis citado

### Tests for User Story 4 (MANDATORY)

- [x] T059 [P] [US4] Integration smoke test happy path API sequence in `tests/integration/test_demo_happy_path.py` using `data_catalog/demo_snapshot/`
- [x] T060 [US4] Assert OpenAPI paths contain zero order endpoints in `tests/contract/test_no_trading_routes.py`



### Implementation for User Story 4

- [x] T061 [US4] Build `data_catalog/demo_snapshot/` pack (canonical dataset, sample experiment, reports, chunks) loadable with `DEMO_MODE=true`
- [x] T062 [US4] Implement demo bootstrap command `src/tradelab/datasets/load_demo.py` (CLI entry in `pyproject.toml`)
- [x] T063 [US4] Unify Streamlit home wizard linking pages 1→2→3 in `apps/ui/app.py` with clear error states (insufficient data, timeout, source unavailable)
- [x] T064 [P] [US4] Write demo script checklist in `docs/demo/script_2-3min.md` matching spec guion
- [x] T065 [P] [US4] Expand `README.md` to single-path evaluator guide (compose, load demo, UI URL, no broker needed)
- [x] T066 [US4] Align `specs/001-tradelab-mvp/quickstart.md` commands with actual CLI/API after implementation (fix path drift)

**Checkpoint**: US4 — evaluador completa quickstart sin credenciales

---



## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Observabilidad, ADRs, evals completas, endurecimiento constitución

- [x] T067 [P] Add token/cost and tool latency logging fields in `src/tradelab/observability/tracing.py` correlated to `analysis_id`
- [x] T068 [P] Write architecture overview diagram notes in `docs/architecture/overview.md`
- [x] T069 [P] Write ADRs for numeric-not-embedded, CAG vs RAG, no-live-trading in `docs/adr/0001-numeric-truth.md`, `docs/adr/0002-cag-rag.md`, `docs/adr/0003-research-only.md`
- [x] T070 [P] Complete golden eval suite + at least one regression case in `evals/regression/` for a known citation failure
- [x] T071 [P] Add CI job step for `evals/golden` marked `fast` in `.github/workflows/ci.yml`
- [x] T072 Security pass: ensure `.env` ignored, no broker creds in compose for cloud, secrets scan notes in `README.md`
- [x] T073 Run full `specs/001-tradelab-mvp/quickstart.md` validation and record results in `docs/demo/quickstart_results.md`
- [x] T074 [P] Document known limitations and sacrifice order in `docs/demo/limitations.md` (constitution recortes)

---



## Dependencies & Execution Order



### Phase Dependencies

- **Phase 1 Setup** → sin dependencias
- **Phase 2 Foundational** → depende de Setup; **BLOQUEA** US1–US4
- **US1 (P1)** → tras Foundational
- **US2 (P2)** → tras Foundational; usa datasets usable de US1 (puede usar fixtures si US1 parcial)
- **US3 (P3)** → tras Foundational; idealmente un Experiment de US2 (stub experiment permitido para desbloquear)
- **US4 (P4)** → integra US1–US3 (snapshot puede empaquetar outputs previos)
- **Polish** → tras historias deseadas (mínimo US1+US2+US3 para demo completa)



### User Story Dependencies

- **US1**: Independiente tras foundational
- **US2**: Requiere CanonicalDataset usable (fixture o US1)
- **US3**: Requiere documentos + experiment metrics (fixtures/stubs OK)
- **US4**: Empaqueta el happy path; no bloquea desarrollo temprano de US1–US3



### Within Each Story

1. Tests contract/unit (deben fallar primero)
2. Models → services → API → UI
3. Checkpoint de historia antes de avanzar prioridad



### Parallel Opportunities

- Setup: T002–T007 en paralelo
- Foundational: T009–T011, T015–T016 en paralelo tras modelos base
- US1: T018–T020, T022–T024, T027–T028 en paralelo
- US2: T032–T034, T036–T037 en paralelo
- US3: T046–T048, T050–T052 en paralelo
- Polish: T067–T071, T074 en paralelo

---



## Parallel Example: User Story 1

```bash
# Tests en paralelo:
Task: "T018 Contract tests catalog/quality API"
Task: "T019 Unit tests bar schema"
Task: "T020 Unit tests gap classification"

# Models/servicios en paralelo tras tests esqueleto:
Task: "T022 Quality models"
Task: "T023 Gap classifier"
Task: "T024 Validators"
```

---



## Parallel Example: User Story 2

```bash
Task: "T032 Contract tests experiments API"
Task: "T033 Anti-look-ahead unit test"
Task: "T034 Determinism hash unit test"
```

---



## Implementation Strategy



### MVP First (User Story 1 Only)

1. Phase 1 Setup
2. Phase 2 Foundational
3. Phase 3 US1 (calidad/reconciliación)
4. **STOP & VALIDATE** con fixtures + UI catálogo
5. Luego US2 → US3 → US4



### Incremental Delivery

1. Setup + Foundational
2. US1 → demo calidad
3. US2 → demo experimento hasheado
4. US3 → demo explicación citada
5. US4 → pack evaluador sin broker
6. Polish → evals/CI/ADRs/vídeo



### Suggested MVP Scope

**MVP mínimo demostrable de producto**: Phase 1–3 (US1).  
**MVP académico completo (rúbrica)**: US1+US2+US3+US4 + Polish evals/CI.

---



## Notes

- Toda métrica financiera solo desde código/tools (constitución IV)
- Prohibido añadir endpoints/tools de órdenes (constitución V)
- Si el spike de brokers falla: recortar a 1 instrumento y NT export fallback (T028) sin cambiar IDs de tarea
- Commit tras cada tarea o grupo lógico; no saltar checkpoints de historia

