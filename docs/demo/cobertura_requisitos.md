# Cobertura de requisitos — TradeLab AI

**Documento de contraste** entre lo solicitado (propuesta de proyecto final, constitución Spec Kit y spec `001-tradelab-mvp`) y lo implementado en el repositorio.

| | |
|--|--|
| Alumno | Casildo Caparrós Díaz |
| Fecha de este inventario | 28 de agosto de 2026 |
| Entrega prevista | 3 de septiembre de 2026 |
| Rama de entrega | `finalproject-TLAI` (GitHub: `ccaparros/tradelab-ai`) |
| Referencias | [`PROPUESTA_PROYECTO_FINAL.md`](../PROPUESTA_PROYECTO_FINAL.md), [`.specify/memory/constitution.md`](../.specify/memory/constitution.md), [`specs/001-tradelab-mvp/spec.md`](../specs/001-tradelab-mvp/spec.md) |

Leyenda: **Cumple** · **Parcial** (hay implementación pero no el 100 % del enunciado) · **Pendiente** (entregable o recorte aún abierto).

---

## 1. Resumen ejecutivo

El **flujo académico end-to-end está construido**: ingesta dual IBKR/NinjaTrader, calidad y reconciliación sin mezcla silenciosa, datasets canónicos versionados, backtest determinista con costes y holdout protegido, walk-forward y sensibilidad, copiloto con tools + verificador + DeepSeek, RAG sobre informes reales, UI Streamlit, API FastAPI, Docker Compose, CI y evals golden.

Lo que **aún no cierra al 100 % el papel** es sobre todo: RAG operativo sobre pgvector (el schema existe; el camino diario es corpus en fichero), persistencia diaria en Postgres frente a `store.json` y vídeo de 2–3 min. El agente **sí** usa LangGraph en runtime (`guards` → `research`). El histórico IBKR local cubre ~22 meses RTH 5m. Entrega en la rama `finalproject-TLAI`.

---

## 2. Objetivos específicos de la propuesta (§3)

| # | Requisito | Estado | Dónde está |
|---|-----------|--------|------------|
| 1 | Conectores NinjaTrader 8 e IBKR | **Cumple** | `connectors/ibkr/`, `connectors/ninjatrader-csharp/`, [`docs/demo/data_download.md`](data_download.md) |
| 2 | Modelo canónico OHLCV, timestamps UTC, sesiones | **Cumple** | `src/tradelab/ingestion/schemas.py`, `datasets/publisher.py` |
| 3 | Duplicados, gaps, OHLC, diferencias entre proveedores | **Cumple** | `src/tradelab/quality/`, informes en `data_catalog/reports/reconciliation/` |
| 4 | Versionado y procedencia (linaje, checksum) | **Cumple** | Parquet inmutable + manifiesto; `lineage` en el catálogo |
| 5 | Estrategia determinista + motor con costes | **Cumple** (de más) | ORB+ATR y fade a VWAP; comisión, slippage, tick, multiplicador |
| 6 | Splits temporales, holdout, walk-forward | **Cumple** | `splits.py`, `robustness.py`; holdout bloqueado salvo lectura final |
| 7 | Pipeline RAG sobre informes y políticas | **Parcial** | Indexado real + BM25/TF-IDF en `DATA_ROOT/rag/`; pgvector preparado, no es el runtime demo |
| 8 | Agente con tools tipadas | **Cumple** | `src/tradelab/agents/tools.py`, `graph.py`; allowlist sin órdenes |
| 9 | Guardrails (no inventar cifras/fuentes) | **Cumple** | Schema Pydantic + `verify_analysis`; rechazo de predicción y trading en vivo |
| 10 | Tests, evals, golden dataset | **Cumple** | 38 golden + Recall@5 + faithfulness proxy en CI |
| 11 | UI y documentación de ejecución | **Parcial** | Guía evaluador lista; falta vídeo |

---

## 3. Alcance del MVP (§4)

| Elemento | Solicitado | Implementado | Estado |
|----------|------------|--------------|--------|
| Instrumentos | MES y MNQ | Ambos, contrato explícito (p. ej. 202609) | **Cumple** |
| Temporalidad | 5 minutos | Barras 5m | **Cumple** |
| Histórico | 12–24 meses (condicionado a permisos) | ~22 meses RTH 5m (MES nov-2024→ago-2026; MNQ oct-2024→ago-2026), stitch nearest-expiry | **Cumple** — IB no sirve vencimientos anteriores a Z5 |
| Contratos | Vencimientos explícitos, no continuo | Futuros FUT trimestrales (Z5/H6/M6/U6) cosidos nearest-expiry; no ContFuture | **Cumple** |
| Estrategia | ORB+ATR intradía | ORB+ATR **y** `vwap_fade_intraday` seleccionable en UI | **Cumple** |
| Gestión | Stop, objetivo, salida de sesión, 1 entrada/sesión | En ambas estrategias | **Cumple** |
| Costes | Comisión, slippage, multiplicador, tick | Configurables + sensibilidad a comisión/slippage | **Cumple** |
| Interfaz | Streamlit + FastAPI | Catálogo, backtest, análisis | **Cumple** |
| Ejecución | Solo investigación, sin órdenes reales | Constitución V; tests `test_no_trading_routes` | **Cumple** |

Fuera de alcance (correctamente no implementado): HFT, libro de órdenes, optimización masiva, ejecución automática, muchos mercados.

---

## 4. Arquitectura y componentes (§5)

| Componente propuesto | Estado | Notas |
|----------------------|--------|--------|
| Ingesta offline raw Parquet + checksum | **Cumple** | IBKR `download_history.py`; NT export C# + `import_csv.py` |
| Normalización y calidad | **Cumple** | Gaps clasificados (`session_closed`, etc.) |
| Cuarentena de discrepancias | **Cumple** | Política `ibkr_canonical_nt_quarantine`; no hay merge silencioso |
| Datasets canónicos versionados | **Cumple** | `connectors/publish_canonical.py` |
| Backtesting determinista | **Cumple** | Hash de integridad (dataset + código + params + strategy) |
| CAG (prompts/políticas) | **Cumple** | Jinja `system_research.j2` + documentos de política con IDs fijos |
| RAG PostgreSQL + pgvector | **Parcial** | Compose usa `pgvector/pgvector:pg16`; migración `0002_rag_documents`; retrieval demo = corpus JSON |
| Agente LangGraph + function calling | **Cumple** | `StateGraph` (guards → research) + `MemorySaver`; tools tipadas + DeepSeek |
| FastAPI + Streamlit | **Cumple** | `/v1/datasets`, experiments, analysis, documents/search |
| Observabilidad | **Parcial** | Settings, logging; tracing de tokens/latencia es esqueleto |
| Docker + CI + secretos | **Cumple** | `docker-compose.yml`, `.github/workflows/ci.yml`, `.env` gitignored |

---

## 5. Aplicación de IA (§6) y constitución IV–V

| Requisito | Estado | Evidencia |
|-----------|--------|-----------|
| El LLM no calcula PnL, DD, Sharpe | **Cumple** | ADR 0001; métricas solo de tools |
| Tools: calidad, métricas, trades, RAG, backtest | **Cumple** | Allowlist en `tools.py` |
| Schema: answer, metrics, assumptions, warnings, sources, confidence | **Cumple** | `AnalysisOutput` |
| Evidencia insuficiente / rechazo | **Cumple** | Preguntas sin `experiment_id`; predicción; órdenes en vivo |
| Citas con `document_id` existentes | **Cumple** | Verificador + evals `expect_citation` |
| Sin trading real | **Cumple** | ADR 0003; no hay endpoints de órdenes |

LLM por defecto: **DeepSeek `deepseek-v4-flash`** (OpenAI-compatible). Sin API key, síntesis determinista. En red corporativa Havas `api.deepseek.com` puede estar bloqueado.

---

## 6. Datos y calidad (§7) vs realidad

| Requisito | Estado |
|-----------|--------|
| Dual fuente, UTC, sesión explícita | **Cumple** |
| Informe reproducible NT vs IBKR | **Cumple** (timestamps alinean; OHLC/volumen divergen; correlación alta) |
| Gaps 100 % clasificados | **Cumple** (tests de clasificación) |
| Dataset DEMO 2024 vs históricos 2026 | **Cumple** en UI (etiqueta DEMO vs real) — no mezclar en la defensa |

---

## 7. Backtesting y anti sobreajuste (§8, constitución III)

| Requisito | Estado |
|-----------|--------|
| Splits train / validation / holdout temporales | **Cumple** (~60 / 20 / 20) |
| Holdout no usado para elegir parámetros | **Cumple** | Claim persistido de lectura final única por dataset |
| Walk-forward | **Cumple** | Expanding sobre train+validation; holdout excluido |
| Sensibilidad a costes y parámetros cercanos | **Cumple** | Informe + UI Backtest |
| Baseline simple | **Cumple** | Largo ingenuo open→close por sesión |
| Anti look-ahead en indicadores | **Cumple** | ATR/VWAP con `shift(1)`; test dedicado |
| Determinismo (mismo hash) | **Cumple** | Test de integridad |
| Rentabilidad como éxito del proyecto | **No aplica** (correcto) | La propuesta lo excluye |

---

## 8. Evaluación de IA (propuesta §9 y umbrales de la constitución)

| Métrica | Objetivo | Qué hay hoy | Estado |
|---------|----------|-------------|--------|
| Golden ~30–40 preguntas | 30–40 | 38 en español (`evals/golden/questions.jsonl`) | **Cumple** |
| Tool selection ≥ 90 % | Sí | Medido en CI (stub, sin LLM) | **Cumple** (camino determinista) |
| Schema validity = 100 % | Sí | Idem | **Cumple** |
| Status / rechazo / evidencia insuficiente | — | Cubierto en golden | **Cumple** |
| Citation precision ≥ 95 % | Sí | Filas `expect_citation` | **Cumple** (stub) |
| Retrieval Recall@5 ≥ 85 % | Sí | `evals/golden/test_retrieval_recall.py` (híbrido BM25/TF-IDF, top-5) | **Cumple** (retrieval léxico; no embeddings densos) |
| Faithfulness ≥ 0.90 | Sí | Números del fallback vs evidencia de tools en CI | **Cumple** (proxy determinista; no juez LLM) |
| Cero IDs/cifras inventados | Sí | Verifier + regresión de citas | **Cumple** |
| ≥ 1 regresión por fallo | Sí | `evals/regression/test_citation_failure.py` | **Cumple** |

CI ejecuta `pytest tests` y `pytest evals -q -m fast` **sin** `|| true`.

---

## 9. Entregables de la propuesta (§12)

| Entregable | Estado |
|------------|--------|
| Repositorio accesible | **Cumple** (privado en GitHub) |
| Rama `finalproject-TLAI` | **Cumple** — rama de entrega |
| Backend FastAPI | **Cumple** |
| Pipeline ingesta y calidad | **Cumple** |
| Conectores NT e IBKR | **Cumple** |
| Motor de backtest y estrategia documentada | **Cumple** |
| CAG/RAG con PostgreSQL y pgvector | **Parcial** — Postgres en Compose + migración; RAG demo en fichero |
| Agente con function calling y guardrails | **Cumple** | LangGraph + tools + JSON schema + verifier |
| Suite tests y evals | **Cumple** (con matices de §8) |
| Frontend Streamlit | **Cumple** (selectores legibles, 2 estrategias, robustez) |
| Docker Compose y CI | **Cumple** |
| README arquitectura / instalación / limitaciones | **Cumple** | [`README_evaluador.md`](README_evaluador.md) + README raíz |
| Vídeo 2–3 min o URL demo | **Pendiente** — hay guion [`script_2-3min.md`](script_2-3min.md) |
| Release `v1.0-final-TLAI` | **Pendiente** (opcional en la propuesta) |

---

## 10. Lo implementado de más (no pedido de forma estricta)

- Segunda estrategia **fade a VWAP** y selector en Backtest.
- Copiloto con **DeepSeek** y fallback si no hay red/key.
- UI de análisis **sin pegar UUIDs** (dataset DEMO vs real).
- Indexación automática de informes de reconciliación, canónicos y experimentos.

---

## 11. Lectura para la defensa

**Se puede afirmar con honestidad** que el proyecto cumple el espíritu del trabajo: dato trazable, backtest reproducible, IA acotada y demo local sin broker.

**No se debe afirmar** que:

- el RAG de cada consulta usa embeddings densos en pgvector (sí hay schema y Compose; el retrieval demo es BM25+TF-IDF);
- el tramo anterior a ~sep-2025 es frente líquido (IB ya no lista U5 y anteriores; se usa Z5 como proxy);
- faithfulness está juzgada por un LLM (en CI es un proxy: cifras del fallback ⊆ evidencia de tools).

Cierre restante hasta el 3 de septiembre: **vídeo 2–3 min**, y opcionalmente release `v1.0-final-TLAI` o activar pgvector en caliente.

---

## 12. Mapa rápido de código

| Capacidad | Ruta principal |
|-----------|----------------|
| Conectores | `connectors/ibkr/`, `connectors/ninjatrader-csharp/` |
| Calidad / reconciliación | `src/tradelab/quality/`, `connectors/reconcile_sources.py` |
| Canónico | `connectors/publish_canonical.py` |
| Backtest | `src/tradelab/backtesting/` |
| Estrategias | `strategies/orb_atr.py`, `strategies/vwap_fade.py`, `strategies/registry.py` |
| Robustez | `backtesting/robustness.py` |
| RAG | `src/tradelab/rag/` |
| Agente | `src/tradelab/agents/` |
| API | `apps/api/` |
| UI | `apps/ui/` |
| Evals | `evals/golden/` |
