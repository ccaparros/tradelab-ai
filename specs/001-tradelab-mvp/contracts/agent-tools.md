# Agent Tools Contract: TradeLab AI MVP

**Feature**: `001-tradelab-mvp` | **Date**: 2026-07-22  
**Alignment**: [openapi.yaml](./openapi.yaml), constitución IV–V

Todas las tools son **allowlist**. Validación de argumentos y permisos ocurre
**fuera del prompt**. No existe ni existirá tool de envío de órdenes.

## Shared response policy

Tras cada turno, el runtime MUST:

1. Ejecutar solo tools de esta lista.
2. Materializar salida Pydantic:
   `answer`, `metrics`, `assumptions`, `warnings`, `sources`, `confidence`.
3. Verificar que cada cifra en `metrics` aparece en resultados de tools.
4. Verificar que cada `document_id` / `experiment_id` citado existe.
5. Si falla verificación → `insufficient_evidence` o corrección, nunca inventar.

---

## `get_dataset_quality`

| | |
|--|--|
| **Args** | `dataset_id: UUID` |
| **Returns** | QualityReport (gaps clasificados, duplicados, status) |
| **Maps to** | `GET /v1/datasets/{dataset_id}/quality` |
| **Errors** | `not_found` |

## `compare_sources`

| | |
|--|--|
| **Args** | `instrument: str`, `start: datetime`, `end: datetime`, `contract_month?: str` |
| **Returns** | ReconciliationReport + quarantine counts |
| **Maps to** | `POST /v1/reconciliations` |
| **Errors** | `insufficient_coverage`, `validation_error` |

## `run_backtest`

| | |
|--|--|
| **Args** | `strategy_id: "orb_atr_intraday"`, `dataset_id: UUID`, `allowed_parameters: object`, `consume_holdout: bool=false` |
| **Returns** | ExperimentDetail (`experiment_id`, `integrity_hash`, metrics by split) |
| **Maps to** | `POST /v1/experiments` |
| **Guards** | Params must pass strategy JSON schema; dataset `usable`; reject unknown keys; if `consume_holdout=true` during param search → `policy_violation` |
| **Errors** | `dataset_not_usable`, `invalid_parameters`, `policy_violation` |

## `get_experiment_metrics`

| | |
|--|--|
| **Args** | `experiment_id: UUID` |
| **Returns** | metrics_by_split + conventions documentadas |
| **Maps to** | subset of `GET /v1/experiments/{experiment_id}` |
| **Errors** | `not_found` |

## `get_trade_sample`

| | |
|--|--|
| **Args** | `experiment_id: UUID`, `filters?: {split_label, limit}` |
| **Returns** | list[Trade] (cap 500) |
| **Maps to** | `GET /v1/experiments/{experiment_id}/trades` |
| **Errors** | `not_found` |

## `search_research_documents`

| | |
|--|--|
| **Args** | `query: str`, `filters?: object`, `top_k?: int=5` |
| **Returns** | ranked chunks with `document_id`, `chunk_id`, excerpt, score |
| **Maps to** | `POST /v1/documents/search` |
| **Notes** | Solo corpus documental; no series OHLCV |

## `generate_experiment_report`

| | |
|--|--|
| **Args** | `experiment_id: UUID` |
| **Returns** | ExperimentReport URIs + integrity_hash |
| **Maps to** | `GET /v1/experiments/{experiment_id}/report` |
| **Errors** | `not_found`, `experiment_not_ready` |

---

## Explicitly forbidden

- `place_order`, `submit_order`, `cancel_order`, `modify_order`
- Raw SQL execution tools
- Broker credential mutation tools
- Price prediction / “forecast next bar” tools

Any model request for forbidden capabilities MUST yield status `rejected` with
warning pointing to research-only policy.
