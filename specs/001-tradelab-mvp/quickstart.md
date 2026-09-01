# Quickstart Validation: TradeLab AI MVP

**Feature**: `001-tradelab-mvp` | **Date**: 2026-07-22  
**Goal**: Probar el happy path **sin credenciales de broker** usando el snapshot
de demo (FR-016, SC-006).

Contratos: [openapi.yaml](./contracts/openapi.yaml),
[agent-tools.md](./contracts/agent-tools.md).  
Modelo: [data-model.md](./data-model.md).

---

## Prerequisites

- Docker + Docker Compose
- Git clone del repo en la rama/feature `001-tradelab-mvp`
- Copia de `.env.example` → `.env` **sin** secrets de broker (LLM key solo si se
  prueba el copiloto completo; modo fixture puede stubear respuestas)
- Snapshot en `data_catalog/demo_snapshot/` (se creará en implementación; para
  validación temprana usar fixtures de tests)

---

## 1. Levantar stack

```bash
docker compose up -d --build
curl -s http://localhost:8000/health
```

**Expected**: `{"status":"ok", ...}`

---

## 2. Catálogo y calidad (User Story 1)

```bash
curl -s http://localhost:8000/v1/datasets | jq .
DATASET_ID=<uuid usable del listado>
curl -s http://localhost:8000/v1/datasets/$DATASET_ID/quality | jq .
```

**Expected**:
- Al menos un dataset `quality_status=usable`
- `duplicate_count=0`
- Todos los `gaps[].classification` en
  `{session_closed, maintenance, unavailable, error}`

UI alternativa: abrir Streamlit → sección Catálogo → ver informe de
reconciliación/calidad.

---

## 3. Backtest determinista (User Story 2)

```bash
curl -s -X POST http://localhost:8000/v1/experiments \
  -H "content-type: application/json" \
  -d "{
    \"dataset_id\": \"$DATASET_ID\",
    \"strategy_id\": \"orb_atr_intraday\",
    \"parameters\": {
      \"opening_range_minutes\": 15,
      \"atr_period\": 14,
      \"atr_filter_mult\": 1.0,
      \"stop_risk_mult\": 1.0,
      \"target_risk_mult\": 2.0,
      \"session_exit_time\": \"14:55\",
      \"commission_per_side\": 0.62,
      \"slippage_ticks\": 1
    },
    \"consume_holdout\": false
  }" | jq .
```

`session_exit_time` se interpreta en `America/Chicago`; la conversión a UTC
sigue automáticamente el horario de verano. Los splits automáticos siempre
terminan en fronteras de sesión completas.

Guardar `experiment_id` e `integrity_hash`. Repetir el mismo POST.

**Expected**:
- Segundo run → mismo `integrity_hash` y mismas métricas netas (SC-002)
- Métricas incluyen costes
- `holdout_consumed=false`

El holdout se revela una sola vez por dataset usando `consume_holdout=true`.
Intentos posteriores reciben `409 holdout_already_consumed`.

```bash
curl -s http://localhost:8000/v1/experiments/$EXPERIMENT_ID/trades?limit=10 | jq .
curl -s http://localhost:8000/v1/experiments/$EXPERIMENT_ID/report | jq .
```

---

## 4. Copiloto citado (User Story 3)

```bash
curl -s -X POST http://localhost:8000/v1/analysis \
  -H "content-type: application/json" \
  -d "{
    \"query\": \"¿Por qué el resultado de validación es peor que train y qué evidencia lo demuestra?\",
    \"experiment_id\": \"$EXPERIMENT_ID\",
    \"dataset_id\": \"$DATASET_ID\"
  }" | jq .
```

**Expected**:
- `analysis_id` presente
- `metrics[*].experiment_id` = experimento real
- `sources` con `document_id` existentes
- status ≠ completed con cifras huérfanas
- Pregunta de predicción de precio → `rejected` o `insufficient_evidence` con
  aviso de política

---

## 5. Guardrail anti-trading (SC-007)

- Confirmar que OpenAPI **no** lista endpoints de órdenes
- En UI, no hay botón/acción “enviar orden”
- Tool allowlist = [agent-tools.md](./contracts/agent-tools.md) forbidden list

---

## 6. Tests automatizados locales

```bash
pytest tests/unit tests/integration -q
pytest evals/golden -q -m "fast"   # cuando existan
```

**Expected**: verde sin red hacia TWS/IB Gateway.

---

## 7. Criterio de salida del quickstart

| Check | OK? |
|-------|-----|
| `/health` OK | |
| Dataset usable + gaps clasificados | |
| Dos backtests idénticos → mismo hash | |
| Análisis con citas y métricas trazables | |
| Cero rutas de trading real | |
| Recorrido UI ≤ 15 min para evaluador | |

Si todos pasan, el diseño Phase 1 está listo para `/speckit-tasks` e
implementación por historias P1→P4.
