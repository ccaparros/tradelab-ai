# Research: TradeLab AI MVP

**Feature**: `001-tradelab-mvp` | **Date**: 2026-07-22

Resuelve el contexto técnico del plan. No quedan ítems NEEDS CLARIFICATION.

---

## 1. Stack de aplicación

**Decision**: Python 3.11+, FastAPI (API OpenAPI), Streamlit (UI wizard),
paquete de dominio `tradelab` instalable en editable mode.

**Rationale**: Cumple rúbrica del máster (FastAPI + producto usable), acelera
dashboard de investigación y mantiene un solo lenguaje para pipeline, backtest
y agente.

**Alternatives considered**:
- Next.js + FastAPI: más coste UI para un solo usuario MVP
- Gradio: menos control del flujo wizard catálogo→backtest→análisis
- Solo CLI: no cumple FR-020 (flujo sin código)

---

## 2. Almacenamiento numérico vs documental

**Decision**: Barras raw en Parquet inmutable + checksum; catálogo, linaje,
experimentos, trades, métricas e informes en PostgreSQL; embeddings/chunks solo
para documentos en pgvector. Nunca embeber OHLCV.

**Rationale**: Constitución IV — verdad numérica determinista vía SQL/Python;
RAG para texto cambiante (informes, políticas, ADRs).

**Alternatives considered**:
- DuckDB-only: excelente analítica local, peor para pgvector/checkpointer compartido
- Object store + solo archivos: dificulta catálogo relacional y citas tipadas
- Embeddings de ventanas de precio: viola constitución y ensucia retrieval

---

## 3. Validación de calidad de datos

**Decision**: Contrato canónico de barra con Pandera (+ reglas de tick/sesión);
gaps clasificados (`session_closed` | `maintenance` | `unavailable` | `error`);
reconciliación OHLC por tolerancia de tick; volumen como diferencia relativa
informativa; cuarentena de conflictos.

**Rationale**: FR-003–005 y SC-003; evita datasets “verdes” con fugas de calidad.

**Alternatives considered**:
- Solo asserts ad hoc: no versionable ni citable por RAG
- Great Expectations completo: overhead alto para MVP académico
- Mezclar fuentes en una serie “best of”: merge silencioso prohibido

---

## 4. Conectores de mercado

**Decision**:
- IBKR: adapter Python `reqHistoricalData` con ventanas, pacing, backoff, resume;
  persistir `whatToShow`, `useRTH`, timezone, contrato resuelto.
- NinjaTrader: Add-On C# `BarsRequest` preferido; **fallback MVP**: export de
  archivo + manifiesto JSON idéntico al contrato de ingesta.

**Rationale**: Disponibilidad real depende de permisos (spike); constitución
permite recorte #2 (export NT) sin invalidar linaje.

**Alternatives considered**:
- Solo IBKR Web API history: límites de concurrencia y sesión distintos; TWS API
  es el camino documentado en el plan
- Continuo sintético del broker: diferir; MVP usa vencimientos explícitos

---

## 5. Motor de backtest y estrategia

**Decision**: Motor propio determinista (event-driven sobre barras 5m) para ORB
+ filtro ATR; fills con comisión/slippage/tick; splits temporales
train/validation/holdout; walk-forward básico; hash
`dataset + code_version + params (+ prompt_id si aplica)`.

**Rationale**: Una familia de estrategia; control total anti-look-ahead; evita
depender de frameworks opacos para la nota de reproducibilidad.

**Alternatives considered**:
- backtesting.py / vectorbt: rápidos pero más trabajo para auditoría de fuga y
  hash estable académico
- Optimización masiva de parámetros: fuera de alcance (sobreajuste)

---

## 6. Capa de IA (CAG / RAG / agente)

**Decision**:
- **CAG**: glosario, esquema de salida, límites del agente y política de riesgo
  en prompts Jinja2 versionados.
- **RAG**: híbrido (vector HNSW + full-text) sobre documentos/informes; metadata
  tipada (instrumento, fecha, tipo).
- **Agente**: LangGraph con tools tipadas de solo lectura/ejecución de backtest
  permitido; salida Pydantic; verificador post-hoc de cifras/citas; checkpointer
  + `analysis_id`.

**Rationale**: Constitución IV–V; pipeline determinista por defecto, agente solo
para intención + síntesis con evidencia.

**Alternatives considered**:
- LLM calcula métricas: prohibido
- Multiagente crítico: post-MVP (recorte #3)
- SQL libre al LLM: riesgo de fuga/alucinación; tools parametrizadas en su lugar

### Tools MVP (nombres de contrato)

| Tool | Propósito |
|------|-----------|
| `get_dataset_quality` | Informe de calidad/linaje |
| `compare_sources` | Reconciliación |
| `run_backtest` | Experimento con params allowlist |
| `get_experiment_metrics` | Métricas netas |
| `get_trade_sample` | Muestra de trades |
| `search_research_documents` | Retrieval documental |
| `generate_experiment_report` | Informe Markdown/JSON |

Sin tool de órdenes.

---

## 7. Evals y observabilidad

**Decision**: Golden set 30–40 preguntas; métricas constitución; pytest hard +
pocos casos LLM-as-judge documentados; logs estructurados con correlación
`analysis_id` / `experiment_id`; coste tokens visible; CI sin broker.

**Rationale**: SC-005 y gates de constitución; regresiones por fallo importante.

**Alternatives considered**:
- Solo LLM-as-judge: no reproducible ni barato en CI
- Observabilidad solo print: insuficiente para auditoría

---

## 8. Despliegue y demo

**Decision**: Docker Compose (api, ui, postgres); ingesta broker solo local;
demo con `data_catalog/demo_snapshot/`; vídeo 2–3 min obligatorio aunque exista
URL.

**Rationale**: FR-016, SC-006/008; credenciales nunca en cloud.

**Alternatives considered**:
- Conectar TWS en cloud: frágil y viola constitución V
- Redis/SSE: recorte #4 si el calendario aprieta

---

## 9. Decisiones de producto fijadas (defaults del spec)

| Tema | Default |
|------|---------|
| ORB opening range | 15 min (allowlist 15\|30) |
| Histórico | ≥12 meses si permisos; documentar menos tras spike |
| Instrumentos | MES + MNQ; degradar a 1 si spike falla |
| Usuarios | Single-user MVP, sin IdP complejo |
| Éxito | Reproducibilidad/evals, no Sharpe mínimo |

---

## Resolved clarifications

Todos los huecos del Technical Context se resolvieron con el plan de proyecto y
la constitución. **0 NEEDS CLARIFICATION pendientes.**
