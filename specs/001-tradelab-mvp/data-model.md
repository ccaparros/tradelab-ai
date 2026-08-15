# Data Model: TradeLab AI MVP

**Feature**: `001-tradelab-mvp` | **Date**: 2026-07-22  
**Source entities**: [spec.md](./spec.md) Key Entities

## Overview

```text
Instrument ──< Contract
SourceSystem ──< IngestionRun ──< RawBarBatch (Parquet path + checksum)
IngestionRun ──> QualityReport
Contract + timeframe ──< CanonicalDataset ──< DatasetBar (or Parquet ref)
CanonicalDataset ──< ReconciliationReport ──< QuarantineItem
CanonicalDataset ──< Experiment ──< Trade ──< MetricSnapshot
Experiment ──< ResearchDocument (report)
ResearchDocument ──< DocumentChunk (embedding)
AnalysisSession ──< ToolInvocation ──> (reads datasets/experiments/docs)
```

Persistencia lógica: metadatos y resultados en PostgreSQL; series grandes en
Parquet referenciadas por path + checksum. IDs públicos: UUID (`dataset_id`,
`experiment_id`, `analysis_id`, …).

---

## Entities

### Instrument

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| symbol_root | string | `MES` \| `MNQ` (u otro tras spike) |
| asset_class | string | `future_micro_index` |
| tick_size | decimal | > 0 |
| multiplier | decimal | > 0 |
| timezone_session | string | p.ej. `America/Chicago` |
| session_calendar_id | string | calendario RTH explícito |

### Contract

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| instrument_id | UUID | FK |
| contract_month | string | YYYYMM explícito |
| exchange | string | required |
| local_symbol | string | símbolo broker |
| ib_con_id | int? | si fuente IBKR |
| status | enum | `active` \| `expired` \| `demo` |

**Unique**: `(instrument_id, contract_month, exchange)`

### SourceSystem

| Field | Type | Rules |
|-------|------|-------|
| id | string | PK: `ninjatrader` \| `ibkr` |
| display_name | string | |
| connector_version | string | semver del adapter |

### IngestionRun

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK (`ingestion_run_id`) |
| source_id | string | FK SourceSystem |
| contract_id | UUID | FK |
| bar_size | string | `5 mins` |
| start_utc | timestamptz | |
| end_utc | timestamptz | end > start |
| request_params | jsonb | whatToShow, useRTH, session template, … |
| timezone_original | string | |
| status | enum | `running` \| `succeeded` \| `failed` \| `partial` |
| created_at | timestamptz | |

### RawBarBatch

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| ingestion_run_id | UUID | FK |
| storage_uri | string | path Parquet inmutable |
| raw_checksum | string | SHA-256 |
| row_count | int | ≥ 0 |
| manifest_uri | string | JSON manifiesto |
| immutable | bool | always true after write |

**Validation**: no update in-place; nueva run = nuevo batch.

### Canonical bar contract (logical row / Parquet schema)

Campos mínimos (FR-003):

`source`, `instrument`, `contract_month`, `exchange`, `bar_size`,
`timestamp_utc`, `session_date`, `open`, `high`, `low`, `close`, `volume`,
`trade_count?`, `wap?`, `rth`, `timezone_original`, `ingestion_run_id`,
`raw_checksum`

**Rules**:
- unique `(source, contract, bar_size, timestamp_utc)`
- prices > 0; aligned to tick
- `low <= open/close <= high`
- timestamps monótonos UTC
- cero duplicados tras normalización

### CanonicalDataset

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK (`dataset_id`) |
| contract_id | UUID | FK |
| bar_size | string | `5 mins` |
| version | int | monotonic per contract/bar_size |
| normalizer_version | string | |
| preferred_source_id | string? | configurable |
| coverage_start_utc | timestamptz | |
| coverage_end_utc | timestamptz | |
| storage_uri | string | Parquet canónico |
| content_checksum | string | hash del dataset |
| quality_status | enum | `usable` \| `quarantine` \| `insufficient` |
| lineage | jsonb | runs, sources, params |
| created_at | timestamptz | |

**States**: `draft` → `usable` | `quarantine` | `insufficient` (publicado solo
si gaps 100% clasificados).

### QualityReport

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| dataset_id | UUID? | FK nullable si pre-canónico |
| ingestion_run_id | UUID? | FK |
| duplicate_count | int | 0 en canónico publicado |
| gap_count | int | |
| gaps | jsonb | lista clasificada |
| ohlc_violations | int | |
| summary_markdown_uri | string | citable por RAG |
| created_at | timestamptz | |

### GapClassification

Enum: `session_closed` | `maintenance` | `unavailable` | `error`

### ReconciliationReport

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| dataset_a_id / run refs | UUID | NT vs IBKR |
| instrument_id | UUID | |
| common_coverage | jsonb | |
| price_discrepancies | jsonb | vs tick tolerance |
| volume_rel_diff | jsonb | informativo |
| report_uri | string | versionado |
| created_at | timestamptz | |

### QuarantineItem

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| reconciliation_report_id | UUID | FK |
| timestamp_utc | timestamptz | |
| field | string | open/high/low/close/… |
| source_a_value | decimal? | |
| source_b_value | decimal? | |
| reason | string | |
| status | enum | `open` \| `accepted_divergence` \| `resolved` |

### StrategyDefinition

| Field | Type | Rules |
|-------|------|-------|
| id | string | PK: `orb_atr_intraday` |
| name | string | |
| version | string | |
| allowed_parameters_schema | jsonb | JSON Schema / Pydantic dump |
| spec_document_id | UUID? | FK ResearchDocument |

**Allowed params (MVP)**: `opening_range_minutes` ∈ {15,30}, `atr_period`,
`atr_filter_mult`, `stop_risk_mult`, `target_risk_mult`, `session_exit_time`,
`commission_per_side`, `slippage_ticks`, `max_entries_per_session`=1.

### Experiment

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK (`experiment_id`) |
| dataset_id | UUID | FK, quality_status=`usable` |
| strategy_id | string | FK |
| parameters | jsonb | must validate allowlist |
| code_version | string | git sha / package version |
| integrity_hash | string | dataset+code+params |
| split_spec | jsonb | train/val/holdout windows |
| walk_forward_spec | jsonb? | |
| status | enum | `queued` \| `running` \| `succeeded` \| `failed` |
| holdout_consumed | bool | default false; once true, locked |
| report_uri | string? | |
| created_at | timestamptz | |

**Determinism**: same inputs → same `integrity_hash` and metrics (FR-010).

### Trade

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| experiment_id | UUID | FK |
| split_label | enum | `train` \| `validation` \| `holdout` \| `wf_fold_n` |
| session_date | date | |
| side | enum | `long` \| `short` |
| entry_ts / exit_ts | timestamptz | exit ≥ entry |
| entry_price / exit_price | decimal | tick-aligned |
| qty | int | |
| pnl_gross / pnl_net | decimal | net includes costs |
| exit_reason | enum | `stop` \| `target` \| `session_exit` \| `other` |

### MetricSnapshot

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| experiment_id | UUID | FK |
| split_label | string | |
| metrics | jsonb | net return, sharpe/sortino (convención doc), max DD, Calmar, PF, win rate, expectancy, trades, exposure, turnover, slippage sensitivity… |
| convention_notes | string | |

**Rule**: toda métrica expuesta referencia `experiment_id` (SC-004).

### ResearchDocument

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| doc_type | enum | `strategy_spec` \| `risk_policy` \| `quality_report` \| `experiment_report` \| `adr` \| `broker_limits` \| `catalog` |
| title | string | |
| body_uri | string | markdown/json |
| instrument_id | UUID? | |
| experiment_id | UUID? | |
| dataset_id | UUID? | |
| effective_at | timestamptz | |
| version | int | |

### DocumentChunk

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| document_id | UUID | FK |
| chunk_index | int | |
| content | text | contextual chunk |
| embedding | vector | pgvector |
| metadata | jsonb | filters |

### AnalysisSession

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK (`analysis_id`) |
| user_query | text | |
| structured_response | jsonb | answer, metrics, assumptions, warnings, sources, confidence |
| status | enum | `completed` \| `needs_clarification` \| `insufficient_evidence` \| `rejected` |
| model_prompt_ids | jsonb | CAG versions |
| token_usage | jsonb? | |
| created_at | timestamptz | |

### ToolInvocation

| Field | Type | Rules |
|-------|------|-------|
| id | UUID | PK |
| analysis_id | UUID | FK |
| tool_name | string | allowlist only |
| arguments | jsonb | validated |
| result_ref | jsonb | IDs / excerpts |
| latency_ms | int | |
| error | string? | |

**Forbidden tool names**: cualquier `*order*`, `place_*`, `submit_trade`, etc.

---

## Validation summary (constitution-aligned)

| Concern | Enforcement |
|---------|-------------|
| Raw immutability | RawBarBatch append-only |
| No silent merge | QuarantineItem required on conflict |
| Gaps | QualityReport.gaps fully classified |
| Anti look-ahead | backtest engine + CI tests |
| Holdout | Experiment.holdout_consumed |
| Numeric truth | MetricSnapshot + tools only |
| No live trading | tool allowlist + API surface |

---

## Relationships (quick)

- Un `CanonicalDataset` deriva de uno o más `IngestionRun` / `RawBarBatch`.
- Un `Experiment` pertenece a un `CanonicalDataset` usable y una `StrategyDefinition`.
- `ResearchDocument` de tipo informe se genera desde `QualityReport` / `Experiment`.
- `AnalysisSession` solo lee vía `ToolInvocation`; no escribe órdenes.
