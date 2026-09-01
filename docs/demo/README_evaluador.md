# Guía del evaluador — TradeLab AI

Un solo camino, **sin broker** y **sin credenciales de Interactive Brokers**.  
Tiempo estimado: menos de 15 minutos.

## Qué se demuestra

1. Catálogo y calidad de un dataset (DEMO o históricos ya publicados).
2. Backtest determinista (ORB+ATR o fade a VWAP) con costes, holdout bloqueado, walk-forward y sensibilidad.
3. Copiloto: tools + citas; no hay envío de órdenes.

## Opción A — Docker (recomendada para evaluación)

Requisitos: Docker Desktop, Python no obligatorio.

```bash
git clone https://github.com/ccaparros/tradelab-ai.git
cd tradelab-ai
copy .env.example .env
docker compose up -d --build
```

En otro terminal:

```bash
docker compose exec api python -m tradelab.datasets.load_demo
docker compose exec api python -m tradelab.rag.indexer
curl http://localhost:8000/health
```

- UI: http://localhost:8501  
- API: http://localhost:8000  
- OpenAPI: http://localhost:8000/docs  

`LLM_API_KEY` puede quedar vacío: el copiloto usa síntesis determinista.

## Opción B — Local (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
$env:PYTHONPATH = "src"
$env:DATA_ROOT = (Resolve-Path .\data).Path
python -m tradelab.datasets.load_demo
python -m tradelab.rag.indexer
python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

Otro terminal:

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8000"
python -m streamlit run apps/ui/app.py --server.port 8501 --server.address 127.0.0.1
```

## Recorrido en la UI

1. **Catálogo** — elige un dataset. El marcado **DEMO** es un fixture corto de 2024. MES/MNQ **real** cubren 2026 (si están en `data/`).
2. **Backtest** — estrategia + parámetros → Ejecutar. Comprueba train / validation / holdout bloqueado, walk-forward y sensibilidad.
3. **Análisis** — selecciona el dataset y el experimento en las listas (no pegues UUIDs). Pregunta: *¿Por qué validation puede diferir de train?* Revisa métricas, fuentes y tools.

## Tests (sin broker)

```bash
pytest tests -q
pytest evals -q -m fast
```

## Lo que no se pide al evaluador

- TWS / NinjaTrader / cuenta IBKR.
- VPN o API key de DeepSeek (opcional para síntesis LLM).
- Rentabilidad de la estrategia: no es criterio de éxito.

## Documentación extra

- Contraste propuesta vs código: [`cobertura_requisitos.md`](cobertura_requisitos.md)
- Guía para grabar el vídeo 2–3 min: [`script_2-3min.md`](script_2-3min.md)
- Limitaciones: [`limitations.md`](limitations.md)
